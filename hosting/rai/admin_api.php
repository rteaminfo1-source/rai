<?php
/*
 * API для админ-панели (admin.php, вкладки «Rai: подписки», «Rai: правила» и «Rai: уведомления»): статистика, поиск
 * пользователя, выдача и снятие подписки, тарифы и платежи; нарушения правил, блокировка и разблокировка;
 * push-уведомления: рассылка пользователям, устройства админов. Принимает только подписанные запросы:
 *   POST, тело JSON {"action": "...", "nonce": "...", ...}
 *   X-Rai-Time: unix-время, X-Rai-Signature: hex(HMAC-SHA256(время + "\n" + тело, ADMIN_API_KEY))
 * Запрос старше 5 минут или с уже использованным nonce отклоняется.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';
require __DIR__ . '/app.php';
require __DIR__ . '/moderation.php';
require __DIR__ . '/push.php';

function admin_ready() { return ADMIN_API_KEY !== '' && strpos(ADMIN_API_KEY, 'ВСТАВЬТЕ') !== 0 && strlen(ADMIN_API_KEY) >= 32; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') json_out(['ok' => false, 'error' => 'POST only'], 405);
if (!admin_ready()) json_out(['ok' => false, 'error' => 'ADMIN_API_KEY не задан в config.php на rai.rteam.info (нужно от 32 символов)'], 503);

$raw = (string)file_get_contents('php://input');
$time = (int)($_SERVER['HTTP_X_RAI_TIME'] ?? 0);
$sig = (string)($_SERVER['HTTP_X_RAI_SIGNATURE'] ?? '');
if (abs(time() - $time) > 300) json_out(['ok' => false, 'error' => 'Время запроса не совпадает (проверьте часы сервера)'], 401);
if (!hash_equals(hash_hmac('sha256', $time . "\n" . $raw, ADMIN_API_KEY), $sig)) {
    json_out(['ok' => false, 'error' => 'Неверная подпись: ключ в админке и в config.php должен быть одинаковым'], 401);
}
$req = json_decode($raw, true);
if (!is_array($req) || empty($req['nonce']) || !is_string($req['nonce'])) json_out(['ok' => false, 'error' => 'bad request'], 400);
$fresh = update_json('admin_nonces.json', function (&$seen) use ($req) {
    $now = time();
    foreach ($seen as $n => $t) if ($now - $t > 600) unset($seen[$n]);
    if (isset($seen[$req['nonce']])) return false;
    $seen[$req['nonce']] = $now;
    return true;
});
if (!$fresh) json_out(['ok' => false, 'error' => 'Повторный запрос'], 409);

$action = (string)($req['action'] ?? '');
$by = mb_substr((string)($req['admin'] ?? 'admin'), 0, 40);

function public_user($u) {
    $plan = user_plan($u);
    return [
        'login' => $u['login'], 'name' => $u['name'] ?? $u['login'], 'email' => $u['email'] ?? null,
        'created' => $u['created'] ?? null, 'last_login' => $u['last_login'] ?? null, 'google' => !empty($u['google_id']),
        'plan' => $plan['key'], 'plan_name' => plans()[$plan['key']]['name'], 'until' => $plan['until'] ?: null,
        'source' => $u['plan_source'] ?? null, 'note' => $u['plan_note'] ?? null,
        'neuro_today' => usage_get('u:' . $u['login']),
    ];
}

function find_login($q) {
    $q = strtolower(trim((string)$q));
    if ($q === '') return null;
    $users = users();
    if (isset($users[$q])) return $users[$q];
    foreach ($users as $u) if (strcasecmp((string)($u['email'] ?? ''), $q) === 0) return $u;
    return null;
}

switch ($action) {
    case 'ping':
        json_out(['ok' => true, 'site' => SITE_URL, 'platega' => platega_ready(), 'time' => time()]);

    case 'stats':
        $users = users();
        $by_plan = array_fill_keys(PAID_PLANS, 0);
        $mrr = 0;
        $subs = [];
        foreach ($users as $u) {
            $p = user_plan($u);
            if ($p['key'] === 'free') continue;
            $by_plan[$p['key']]++;
            $mrr += plans()[$p['key']]['price'];
            $subs[] = public_user($u);
        }
        usort($subs, function ($a, $b) { return $a['until'] <=> $b['until']; });
        $orders = array_values(load_json('orders.json', []));
        $paid = array_filter($orders, function ($o) { return $o['status'] === 'paid'; });
        $month_start = strtotime(date('Y-m-01'));
        $sum = function ($list) { return array_sum(array_map(function ($o) { return (int)$o['amount']; }, $list)); };
        $usage = load_json('usage/' . usage_day() . '.json', []);
        $recent = array_slice(array_reverse($orders), 0, 30);
        // графики: оплаты за 30 дней и сообщения нейросети за 7 дней
        $revenue_days = [];
        for ($i = 29; $i >= 0; $i--) $revenue_days[date('Y-m-d', strtotime("-$i days"))] = 0;
        foreach ($paid as $o) {
            $d = date('Y-m-d', (int)($o['paid_at'] ?? 0));
            if (isset($revenue_days[$d])) $revenue_days[$d] += (int)$o['amount'];
        }
        $neuro_days = [];
        for ($i = 6; $i >= 0; $i--) {
            $d = date('Y-m-d', strtotime("-$i days"));
            $neuro_days[$d] = array_sum(load_json('usage/' . $d . '.json', []));
        }
        $expiring = count(array_filter($subs, function ($u) { return $u['until'] && $u['until'] - time() < 3 * 86400; }));
        json_out(['ok' => true,
            'users' => count($users), 'new_week' => count(array_filter($users, function ($u) { return ($u['created'] ?? 0) > time() - 7 * 86400; })),
            'by_plan' => $by_plan, 'subscribers' => array_sum($by_plan), 'mrr' => $mrr,
            'revenue_total' => $sum($paid), 'revenue_month' => $sum(array_filter($paid, function ($o) use ($month_start) { return ($o['paid_at'] ?? 0) >= $month_start; })),
            'neuro_today' => array_sum($usage), 'neuro_people_today' => count($usage),
            'subs' => array_slice($subs, 0, 300), 'orders' => $recent,
            'log' => array_slice(array_reverse(load_json('sub_log.json', [])), 0, 50),
            'plans' => plans(), 'platega' => platega_ready(), 'platega_source' => platega_conf()['source'], 'guest_limit' => guest_limit(),
            'revenue_days' => $revenue_days, 'neuro_days' => $neuro_days, 'expiring' => $expiring,
            'downloads' => (load_json('downloads.json', [])['total'] ?? []), 'app_version' => app_version(),
            'pending' => count(array_filter($orders, function ($o) { return in_array($o['status'], ['new', 'pending'], true) && $o['created'] > time() - 3 * 86400; })),
            'violations_new' => count(array_filter(rai_violations(), function ($v) { return empty($v['seen']); }))]);

    case 'subs_all':  // для выгрузки в CSV
        $out = [];
        foreach (users() as $u) if (user_plan($u)['key'] !== 'free' || !empty($req['everyone'])) $out[] = public_user($u);
        json_out(['ok' => true, 'users' => $out]);

    case 'order_check':
        $order = order_check((string)($req['id'] ?? ''));
        if (!$order) json_out(['ok' => false, 'error' => 'Заказ не найден']);
        json_out(['ok' => true, 'order' => $order]);

    case 'platega_get':
        $c = platega_conf();
        json_out(['ok' => true, 'source' => $c['source'], 'method' => $c['method'],
                  'id' => $c['id'] !== '' ? substr($c['id'], 0, 4) . '…' . substr($c['id'], -4) : '',
                  'callback' => SITE_URL . '/pay_callback.php']);

    case 'platega_save':
        if (platega_conf()['source'] === 'config') json_out(['ok' => false, 'error' => 'Ключи Platega уже вписаны в config.php на rai.rteam.info — меняйте их там.']);
        $saved = load_json('platega.json', []);
        $id = trim((string)($req['id'] ?? ''));
        $secret = trim((string)($req['secret'] ?? ''));
        if ($id !== '') $saved['id'] = mb_substr($id, 0, 100);
        if ($secret !== '') $saved['secret'] = mb_substr($secret, 0, 300);
        if (isset($req['method'])) $saved['method'] = max(0, min(99, (int)$req['method']));
        if (!empty($req['clear'])) $saved = [];
        save_json('platega.json', $saved);
        sub_log('plans', '', '', 0, empty($req['clear']) ? 'Изменены ключи Platega' : 'Ключи Platega удалены', $by);
        json_out(['ok' => true, 'ready' => !empty($saved['id']) && !empty($saved['secret'])]);

    case 'user':
        $u = find_login($req['login'] ?? '');
        if (!$u) json_out(['ok' => false, 'error' => 'Пользователь «' . ($req['login'] ?? '') . '» на rai.rteam.info не найден']);
        json_out(['ok' => true, 'user' => public_user($u)]);

    case 'search':
        $q = mb_strtolower(trim((string)($req['q'] ?? '')));
        $out = [];
        foreach (users() as $u) {
            $hay = mb_strtolower($u['login'] . ' ' . ($u['name'] ?? '') . ' ' . ($u['email'] ?? ''));
            if ($q === '' || mb_strpos($hay, $q) !== false) $out[] = public_user($u);
            if (count($out) >= 50) break;
        }
        json_out(['ok' => true, 'users' => $out]);

    case 'grant':
        $u = find_login($req['login'] ?? '');
        if (!$u) json_out(['ok' => false, 'error' => 'Пользователь «' . ($req['login'] ?? '') . '» на rai.rteam.info не найден. Логин — как в кабинете Rai.']);
        $plan = (string)($req['plan'] ?? '');
        $days = (int)($req['days'] ?? 0);
        if (!in_array($plan, PAID_PLANS, true)) json_out(['ok' => false, 'error' => 'Неизвестный тариф']);
        if ($days < 1 || $days > 3660) json_out(['ok' => false, 'error' => 'Срок — от 1 до 3660 дней']);
        $note = (string)($req['note'] ?? '');
        set_subscription($u['login'], $plan, $days, 'admin', 'Выдал ' . $by . ($note !== '' ? ': ' . $note : ''));
        sub_log('grant', $u['login'], $plan, $days, $note, $by);
        json_out(['ok' => true, 'user' => public_user(users()[$u['login']])]);

    case 'revoke':
        $u = find_login($req['login'] ?? '');
        if (!$u) json_out(['ok' => false, 'error' => 'Пользователь не найден']);
        set_subscription($u['login'], 'free', 0, 'admin', 'Снял ' . $by);
        sub_log('revoke', $u['login'], 'free', 0, (string)($req['note'] ?? ''), $by);
        json_out(['ok' => true, 'user' => public_user(users()[$u['login']])]);

    case 'plans_save':
        $in = $req['plans'] ?? [];
        if (!is_array($in)) json_out(['ok' => false, 'error' => 'bad plans']);
        $saved = update_json('plans.json', function (&$over) use ($in) {
            if (isset($in['guest']['neuro_day'])) $over['guest']['neuro_day'] = max(0, min(1000, (int)$in['guest']['neuro_day']));
            foreach (PLAN_DEFAULTS as $key => $def) {
                if (!isset($in[$key]) || !is_array($in[$key])) continue;
                $row = $in[$key];
                if (isset($row['name']) && trim($row['name']) !== '') $over[$key]['name'] = mb_substr(trim($row['name']), 0, 30);
                if (isset($row['price']) && $key !== 'free') $over[$key]['price'] = max(1, min(1000000, (int)$row['price']));
                if (isset($row['neuro_day'])) $over[$key]['neuro_day'] = max(0, min(100000, (int)$row['neuro_day']));
                if (isset($row['tagline'])) $over[$key]['tagline'] = mb_substr(trim($row['tagline']), 0, 80);
                if (isset($row['features']) && is_array($row['features'])) {
                    $f = array_values(array_filter(array_map(function ($x) { return mb_substr(trim((string)$x), 0, 120); }, $row['features'])));
                    if ($f) $over[$key]['features'] = array_slice($f, 0, 8);
                }
            }
            return $over;
        });
        sub_log('plans', '', '', 0, 'Тарифы изменены', $by);
        json_out(['ok' => true, 'saved' => $saved]);

    // ---------------------------------------------------------------- правила: нарушения и блокировки
    case 'violations':
        $all = rai_violations();
        $per_login = [];
        $per_ip = [];
        foreach ($all as $v) {
            if (!empty($v['login'])) $per_login[$v['login']] = ($per_login[$v['login']] ?? 0) + 1;
            $per_ip[$v['ip'] ?? ''] = ($per_ip[$v['ip'] ?? ''] ?? 0) + 1;
        }
        $filter = (string)($req['filter'] ?? '');
        $list = array_reverse($all);
        if ($filter === 'new') $list = array_values(array_filter($list, function ($v) { return empty($v['seen']); }));
        $bans = rai_bans();
        foreach ($list as &$v) {
            $v['count'] = !empty($v['login']) ? ($per_login[$v['login']] ?? 1) : ($per_ip[$v['ip'] ?? ''] ?? 1);
            $v['banned'] = (bool)rai_ban_of($v['login'] ?? null, empty($v['login']) ? ($v['ip'] ?? null) : null);
        }
        unset($v);
        $by_cat = array_fill_keys(array_keys(RULE_LABELS), 0);
        foreach ($all as $v) if (isset($by_cat[$v['category']])) $by_cat[$v['category']]++;
        json_out(['ok' => true, 'items' => array_slice($list, 0, 300), 'total' => count($all),
                  'new' => count(array_filter($all, function ($v) { return empty($v['seen']); })),
                  'by_category' => $by_cat, 'labels' => RULE_LABELS, 'bans' => $bans, 'now' => time()]);

    case 'violations_seen':
        $ids = array_map('strval', (array)($req['ids'] ?? []));
        $all_seen = !empty($req['all']);
        update_json('violations.json', function (&$list) use ($ids, $all_seen) {
            foreach ($list as &$v) if ($all_seen || in_array($v['id'], $ids, true)) $v['seen'] = true;
        });
        json_out(['ok' => true]);

    case 'violations_delete':
        $ids = array_map('strval', (array)($req['ids'] ?? []));
        update_json('violations.json', function (&$list) use ($ids) {
            $list = array_values(array_filter($list, function ($v) use ($ids) { return !in_array($v['id'], $ids, true); }));
        });
        json_out(['ok' => true]);

    case 'ban':
        $login = strtolower(trim((string)($req['login'] ?? '')));
        $ip = trim((string)($req['ip'] ?? ''));
        if ($login === '' && $ip === '') json_out(['ok' => false, 'error' => 'Укажите логин или IP-адрес.'], 400);
        if ($login !== '' && !isset(users()[$login])) json_out(['ok' => false, 'error' => "Пользователь «{$login}» не найден."], 404);
        if ($ip !== '' && !filter_var($ip, FILTER_VALIDATE_IP)) json_out(['ok' => false, 'error' => 'Неверный IP-адрес.'], 400);
        $days = max(0, min(3650, (int)($req['days'] ?? 0)));
        $ban = ['reason' => mb_substr(trim((string)($req['reason'] ?? '')), 0, 200) ?: 'нарушение правил Rai',
                'until' => $days ? time() + $days * 86400 : 0, 'at' => time(), 'by' => $by];
        update_json('bans.json', function (&$b) use ($login, $ip, $ban) {
            $b += ['users' => [], 'ips' => []];
            if ($login !== '') $b['users'][$login] = $ban;
            if ($ip !== '') $b['ips'][$ip] = $ban;
        }, ['users' => [], 'ips' => []]);
        sub_log('ban', $login ?: $ip, '', $days, 'Блокировка: ' . $ban['reason'] . ($days ? " ({$days} дн.)" : ' (навсегда)'), $by);
        json_out(['ok' => true, 'ban' => $ban]);

    case 'unban':
        $login = strtolower(trim((string)($req['login'] ?? '')));
        $ip = trim((string)($req['ip'] ?? ''));
        update_json('bans.json', function (&$b) use ($login, $ip) {
            $b += ['users' => [], 'ips' => []];
            if ($login !== '') unset($b['users'][$login]);
            if ($ip !== '') unset($b['ips'][$ip]);
        }, ['users' => [], 'ips' => []]);
        sub_log('unban', $login ?: $ip, '', 0, 'Разблокировка', $by);
        json_out(['ok' => true]);

    // ---------------------------------------------------------------- push-уведомления
    case 'push_stats':
        $subs = push_subs();
        $users = $admins = [];
        $logins = [];
        foreach ($subs as $id => $sub) {
            if (($sub['kind'] ?? 'user') === 'admin') {
                $admins[] = ['id' => $id, 'device' => $sub['device'] ?? '', 'events' => $sub['events'] ?? [], 'created' => $sub['created'] ?? 0,
                             'last_ok' => $sub['last_ok'] ?? null, 'admin' => $sub['admin'] ?? '', 'back' => $sub['back'] ?? ''];
            } else {
                $users[] = $sub;
                if (!empty($sub['login'])) $logins[$sub['login']] = true;
            }
        }
        $week = count(array_filter($users, function ($u) { return ($u['created'] ?? 0) > time() - 7 * 86400; }));
        json_out(['ok' => true, 'ready' => push_ready(), 'devices' => count($users), 'people' => count($logins), 'new_week' => $week,
                  'admins' => $admins, 'events' => PUSH_ADMIN_EVENTS, 'log' => array_slice(array_reverse(load_json('push_log.json', [])), 0, 50)]);

    case 'push_send':
        if (!push_ready()) json_out(['ok' => false, 'error' => 'На хостинге rai.rteam.info нет openssl или curl — уведомления не работают.']);
        $title = trim(mb_substr((string)($req['title'] ?? ''), 0, 80));
        $body = trim(mb_substr((string)($req['body'] ?? ''), 0, 300));
        $url = trim((string)($req['url'] ?? '')) ?: 'chat.html';
        if ($title === '') json_out(['ok' => false, 'error' => 'Напишите заголовок уведомления.']);
        if (!preg_match('~^(https?://[^\s"<>]+|[A-Za-z0-9_./?=&#%-]+)$~', $url)) json_out(['ok' => false, 'error' => 'Неверная ссылка.']);
        $to = (string)($req['to'] ?? 'all');
        if ($to === 'login') {
            $u = find_login($req['login'] ?? '');
            if (!$u) json_out(['ok' => false, 'error' => 'Пользователь «' . ($req['login'] ?? '') . '» не найден.']);
            $targets = push_find(['kind' => 'user', 'login' => $u['login']]);
            $label = '@' . $u['login'];
            if (!$targets) json_out(['ok' => false, 'error' => "У @{$u['login']} уведомления не включены ни на одном устройстве."]);
        } else {
            $targets = push_find(['kind' => 'user']);
            $label = 'все';
            if (!$targets) json_out(['ok' => false, 'error' => 'Пока никто не включил уведомления.']);
        }
        @set_time_limit(300);
        $r = push_send($targets, ['title' => $title, 'body' => $body, 'url' => $url, 'tag' => 'rai-news-' . substr(md5($title . $body), 0, 8)]);
        push_log(['title' => $title, 'body' => $body, 'url' => $url, 'to' => $label, 'by' => $by] + $r);
        sub_log('push', $to === 'login' ? $label : '', '', 0, 'Уведомление «' . $title . '»: доставлено ' . $r['sent'] . ' из ' . count($targets), $by);
        json_out(['ok' => true, 'targets' => count($targets)] + $r);

    case 'push_device_delete':
        push_delete([(string)($req['id'] ?? '')]);
        json_out(['ok' => true]);

    case 'plans_reset':
        save_json('plans.json', []);
        sub_log('plans', '', '', 0, 'Тарифы сброшены к стандартным', $by);
        json_out(['ok' => true]);

    default:
        json_out(['ok' => false, 'error' => 'unknown action'], 400);
}
