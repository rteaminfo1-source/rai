<?php
/*
 * Push-уведомления Rai (Web Push): приходят, даже когда сайт закрыт, — в Chrome, Edge, Firefox, Opera, Яндекс Браузере,
 * Safari (macOS и iPhone с иконкой на экране «Домой»). Без внешних сервисов и ключей: только PHP (openssl + curl).
 *
 *   Ключи VAPID создаются сами при первом запуске (data/push_vapid.json.php) — не удаляйте их, иначе подписки пропадут.
 *   Подписки — data/push_subs.json.php: устройства пользователей (kind = user) и админов (kind = admin).
 *   Сообщение шифруется для каждого устройства (RFC 8291, aes128gcm) и подписывается ключом сайта (RFC 8292, VAPID).
 *
 * Кому что приходит:
 *   — пользователям: рассылки из админ-панели (всем или по логину), «оплата прошла»;
 *   — админам: новые нарушения правил, оплаты, новые пользователи (что именно — выбирается на устройстве).
 */

const PUSH_MAX_SUBS = 20000;
const PUSH_ADMIN_EVENTS = ['violations' => 'Нарушения правил', 'payments' => 'Оплаты', 'users' => 'Новые пользователи'];

function push_b64($s) { return rtrim(strtr(base64_encode($s), '+/', '-_'), '='); }
function push_unb64($s) { return (string)base64_decode(strtr((string)$s, '-_', '+/') . str_repeat('=', (4 - strlen((string)$s) % 4) % 4)); }

/** Работают ли push на этом хостинге: нужны openssl с кривыми P-256 и curl. */
function push_ready() {
    return function_exists('openssl_pkey_derive') && function_exists('curl_init')
        && in_array('prime256v1', openssl_get_curve_names() ?: [], true);
}

/** Сырой открытый ключ EC P-256 (65 байт: 0x04 || X || Y) из ключа openssl. */
function push_raw_public($key) {
    $d = openssl_pkey_get_details($key);
    $pad = function ($v) { return str_pad((string)$v, 32, "\0", STR_PAD_LEFT); };
    return "\x04" . $pad($d['ec']['x']) . $pad($d['ec']['y']);
}

/** Открытый ключ получателя (65 байт) → ключ openssl (через DER SubjectPublicKeyInfo). */
function push_public_key($raw) {
    $der = hex2bin('3059301306072a8648ce3d020106082a8648ce3d030107034200') . $raw;
    $pem = "-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($der), 64, "\n") . "-----END PUBLIC KEY-----\n";
    return openssl_pkey_get_public($pem);
}

function push_new_key() {
    return openssl_pkey_new(['curve_name' => 'prime256v1', 'private_key_type' => OPENSSL_KEYTYPE_EC]);
}

/** Ключи сайта (VAPID): создаются один раз. ['public' => base64url, 'pem' => закрытый ключ]. */
function push_vapid() {
    static $v = null;
    if ($v) return $v;
    $v = load_json('push_vapid.json', []);
    if (empty($v['pem']) || empty($v['public'])) {
        $v = update_json('push_vapid.json', function (&$data) {
            if (empty($data['pem'])) {   // кто-то другой мог создать их, пока мы ждали блокировку
                $key = push_new_key();
                openssl_pkey_export($key, $pem);
                $data = ['pem' => $pem, 'public' => push_b64(push_raw_public($key)), 'created' => time()];
            }
            return $data;
        });
    }
    return $v;
}

/** Подпись ES256 из DER (как отдаёт openssl) → 64 байта R||S (как требует JWT). */
function push_der_to_raw($der) {
    $pos = 2;
    if (ord($der[1]) & 0x80) $pos += ord($der[1]) & 0x7f;
    $out = '';
    for ($i = 0; $i < 2; $i++) {
        $len = ord($der[$pos + 1]);
        $int = substr($der, $pos + 2, $len);
        $out .= str_pad(ltrim($int, "\0"), 32, "\0", STR_PAD_LEFT);
        $pos += 2 + $len;
    }
    return $out;
}

/** Заголовок Authorization: vapid t=JWT, k=ключ — для сервера уведомлений адреса $endpoint. */
function push_vapid_header($endpoint) {
    $v = push_vapid();
    $u = parse_url($endpoint);
    $claims = ['aud' => $u['scheme'] . '://' . $u['host'] . (isset($u['port']) ? ':' . $u['port'] : ''), 'exp' => time() + 12 * 3600,
               'sub' => defined('PUSH_CONTACT') ? PUSH_CONTACT : 'mailto:support@rteam.info'];
    $data = push_b64(json_encode(['typ' => 'JWT', 'alg' => 'ES256'])) . '.' . push_b64(json_encode($claims, JSON_UNESCAPED_SLASHES));
    openssl_sign($data, $der, $v['pem'], OPENSSL_ALGO_SHA256);
    return 'vapid t=' . $data . '.' . push_b64(push_der_to_raw($der)) . ', k=' . $v['public'];
}

/** Зашифровать сообщение для устройства (RFC 8291, aes128gcm). Возвращает тело запроса. */
function push_encrypt($payload, $p256dh, $auth) {
    $ua_public = push_unb64($p256dh);
    $secret = push_unb64($auth);
    if (strlen($ua_public) !== 65 || $ua_public[0] !== "\x04" || strlen($secret) < 16) throw new RuntimeException('bad subscription keys');
    $peer = push_public_key($ua_public);
    if (!$peer) throw new RuntimeException('bad subscription key');
    $local = push_new_key();
    $as_public = push_raw_public($local);
    $shared = openssl_pkey_derive($peer, $local, 32);
    if ($shared === false || strlen($shared) !== 32) throw new RuntimeException('ecdh failed');

    $prk_key = hash_hmac('sha256', $shared, $secret, true);
    $ikm = hash_hmac('sha256', "WebPush: info\0" . $ua_public . $as_public . "\x01", $prk_key, true);
    $salt = random_bytes(16);
    $prk = hash_hmac('sha256', $ikm, $salt, true);
    $cek = substr(hash_hmac('sha256', "Content-Encoding: aes128gcm\0\x01", $prk, true), 0, 16);
    $nonce = substr(hash_hmac('sha256', "Content-Encoding: nonce\0\x01", $prk, true), 0, 12);
    $tag = '';
    $cipher = openssl_encrypt($payload . "\x02", 'aes-128-gcm', $cek, OPENSSL_RAW_DATA, $nonce, $tag, '', 16);
    if ($cipher === false) throw new RuntimeException('encrypt failed');
    return $salt . pack('N', 4096) . chr(65) . $as_public . $cipher . $tag;
}

// ---------------------------------------------------------------- подписки
function push_subs() { return load_json('push_subs.json', []); }

function push_sub_id($endpoint) { return substr(hash('sha256', (string)$endpoint), 0, 20); }

/** Проверить подписку из браузера: {endpoint, keys: {p256dh, auth}}. */
function push_valid_sub($sub) {
    if (!is_array($sub) || empty($sub['endpoint']) || !is_string($sub['endpoint'])) return null;
    $endpoint = $sub['endpoint'];
    // только https-адреса серверов уведомлений браузеров (не свой сайт и не локальная сеть)
    $u = parse_url($endpoint);
    if (($u['scheme'] ?? '') !== 'https' || empty($u['host']) || strlen($endpoint) > 1000) {
        if (!getenv('PUSH_TEST_HTTP') || !in_array($u['scheme'] ?? '', ['http', 'https'], true)) return null;
    }
    $host = strtolower($u['host']);
    if (!getenv('PUSH_TEST_HTTP') && (filter_var($host, FILTER_VALIDATE_IP) || $host === 'localhost')) return null;
    $p = (string)($sub['keys']['p256dh'] ?? '');
    $a = (string)($sub['keys']['auth'] ?? '');
    if (strlen(push_unb64($p)) !== 65 || strlen(push_unb64($a)) < 16) return null;
    return ['endpoint' => $endpoint, 'p256dh' => $p, 'auth' => $a];
}

/** Сохранить устройство. $extra: login, kind (user/admin), events, back (адрес админки), ua. */
function push_save_sub($sub, array $extra) {
    $id = push_sub_id($sub['endpoint']);
    update_json('push_subs.json', function (&$subs) use ($id, $sub, $extra) {
        $old = $subs[$id] ?? [];
        $subs[$id] = array_merge($old, $sub, $extra, ['id' => $id, 'created' => $old['created'] ?? time(), 'seen' => time(), 'fails' => 0]);
        if (count($subs) > PUSH_MAX_SUBS) {   // самые старые неактивные — прочь
            uasort($subs, function ($a, $b) { return ($a['seen'] ?? 0) <=> ($b['seen'] ?? 0); });
            $subs = array_slice($subs, count($subs) - PUSH_MAX_SUBS, null, true);
        }
    });
    return $id;
}

function push_delete($ids) {
    $ids = (array)$ids;
    if (!$ids) return;
    update_json('push_subs.json', function (&$subs) use ($ids) { foreach ($ids as $id) unset($subs[$id]); });
}

/** Устройства по условию: ['kind' => 'user'|'admin', 'login' => …, 'event' => событие для админов]. */
function push_find(array $where) {
    $out = [];
    foreach (push_subs() as $id => $s) {
        if (isset($where['kind']) && ($s['kind'] ?? 'user') !== $where['kind']) continue;
        if (isset($where['login']) && strcasecmp((string)($s['login'] ?? ''), (string)$where['login']) !== 0) continue;
        if (isset($where['event']) && !in_array($where['event'], $s['events'] ?? array_keys(PUSH_ADMIN_EVENTS), true)) continue;
        if (isset($where['id']) && $id !== $where['id']) continue;
        $out[$id] = $s;
    }
    return $out;
}

/**
 * Отправить уведомление на устройства (параллельно, пачками). $msg: title, body, url, tag, icon.
 * Возвращает ['sent' => n, 'failed' => n, 'removed' => n]. Устройства, от которых браузер отказался (404/410), удаляются.
 */
function push_send(array $subs, array $msg, $ttl = 86400) {
    $res = ['sent' => 0, 'failed' => 0, 'removed' => 0];
    if (!$subs || !push_ready()) { $res['failed'] = count($subs); return $res; }
    $payload = json_encode(array_filter([
        'title' => mb_substr((string)($msg['title'] ?? 'Rai'), 0, 80), 'body' => mb_substr((string)($msg['body'] ?? ''), 0, 300),
        'url' => (string)($msg['url'] ?? ''), 'tag' => (string)($msg['tag'] ?? ''), 'icon' => (string)($msg['icon'] ?? ''),
    ], 'strlen'), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $gone = [];
    $failed = [];
    $ok = [];
    foreach (array_chunk($subs, 40, true) as $chunk) {
        $mh = curl_multi_init();
        $handles = [];
        foreach ($chunk as $id => $s) {
            try {
                $body = push_encrypt($payload, $s['p256dh'], $s['auth']);
                $auth = push_vapid_header($s['endpoint']);
            } catch (Throwable $e) {
                $gone[] = $id;   // испорченная подписка
                continue;
            }
            $headers = ['Content-Type: application/octet-stream', 'Content-Encoding: aes128gcm', 'TTL: ' . (int)$ttl,
                        'Urgency: ' . ($msg['urgency'] ?? 'normal'), 'Authorization: ' . $auth];
            // одинаковая «тема» — новое уведомление заменяет старое, если устройство было не в сети
            if (!empty($msg['tag']) && preg_match('/^[A-Za-z0-9_-]{1,32}$/', $msg['tag'])) $headers[] = 'Topic: ' . $msg['tag'];
            $ch = curl_init($s['endpoint']);
            curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $body, CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 10, CURLOPT_HTTPHEADER => $headers]);
            curl_multi_add_handle($mh, $ch);
            $handles[$id] = $ch;
        }
        do {
            $status = curl_multi_exec($mh, $running);
            if ($running) curl_multi_select($mh, 1);
        } while ($running && $status === CURLM_OK);
        foreach ($handles as $id => $ch) {
            $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            if ($code >= 200 && $code < 300) { $res['sent']++; $ok[] = $id; }
            elseif ($code === 404 || $code === 410) { $gone[] = $id; }
            else { $res['failed']++; $failed[] = $id; }
            curl_multi_remove_handle($mh, $ch);
            curl_close($ch);
        }
        curl_multi_close($mh);
    }
    $res['removed'] = count($gone);
    if ($gone || $failed || $ok) {
        update_json('push_subs.json', function (&$all) use ($gone, $failed, $ok) {
            foreach ($gone as $id) unset($all[$id]);
            foreach ($failed as $id) {
                if (!isset($all[$id])) continue;
                $all[$id]['fails'] = ($all[$id]['fails'] ?? 0) + 1;
                if ($all[$id]['fails'] >= 10) unset($all[$id]);   // 10 неудач подряд — устройство больше не отвечает
            }
            foreach ($ok as $id) if (isset($all[$id])) { $all[$id]['fails'] = 0; $all[$id]['last_ok'] = time(); }
        });
    }
    return $res;
}

/** Записать рассылку в журнал (для админ-панели). */
function push_log(array $entry) {
    update_json('push_log.json', function (&$log) use ($entry) {
        $log[] = $entry + ['time' => time()];
        $log = array_slice($log, -200);
    });
}

/**
 * Уведомить админов о событии (нарушение, оплата, новый пользователь) — после ответа посетителю, чтобы его не задерживать.
 * $path — куда вести в админ-панели (например «?tab=rai_rules»): к адресу админки, сохранённому на устройстве.
 */
function push_admins($event, $title, $body, $path = '') {
    if (!push_ready()) return;
    register_shutdown_function(function () use ($event, $title, $body, $path) {
        if (function_exists('fastcgi_finish_request')) @fastcgi_finish_request();
        $subs = push_find(['kind' => 'admin', 'event' => $event]);
        // у каждого устройства — свой адрес админки: отправляем группами по адресу
        $groups = [];
        foreach ($subs as $id => $s) $groups[(string)($s['back'] ?? '')][$id] = $s;
        foreach ($groups as $back => $list) {
            push_send($list, ['title' => $title, 'body' => $body, 'url' => $back !== '' ? $back . $path : '', 'tag' => 'rai-' . $event]);
        }
    });
}

/** Уведомить пользователя (все его устройства) — тоже после ответа. */
function push_user_later($login, array $msg) {
    if (!push_ready() || !$login) return;
    register_shutdown_function(function () use ($login, $msg) {
        if (function_exists('fastcgi_finish_request')) @fastcgi_finish_request();
        $subs = push_find(['kind' => 'user', 'login' => $login]);
        if ($subs) push_send($subs, $msg);
    });
}

/** Подпись ссылки для устройства админа: админ-панель (у неё есть ADMIN_API_KEY) выдаёт её на 1 час. */
function push_admin_token_ok($exp, $back, $token) {
    if (!defined('ADMIN_API_KEY') || strlen(ADMIN_API_KEY) < 32 || strpos(ADMIN_API_KEY, 'ВСТАВЬТЕ') === 0) return false;
    $exp = (int)$exp;
    if ($exp < time() || $exp > time() + 3600 + 60) return false;
    return is_string($token) && hash_equals(hash_hmac('sha256', 'push-admin|' . $exp . '|' . $back, ADMIN_API_KEY), $token);
}
