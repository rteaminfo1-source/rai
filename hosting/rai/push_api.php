<?php
/*
 * Подписка на push-уведомления Rai (страница чата и страница push_admin.php для админов).
 *   GET                                   — {ok, ready, key}: открытый ключ сайта для pushManager.subscribe()
 *   POST {action: "subscribe", subscription}           — это устройство пользователя (заголовок X-CSRF-Token из me.php)
 *   POST {action: "unsubscribe", endpoint}             — отписать устройство
 *   POST {action: "test", endpoint}                    — проверочное уведомление на это устройство
 *   POST {action: "admin_subscribe", subscription, exp, back, t, events}  — устройство админа (подписанная ссылка из админки)
 */
require __DIR__ . '/config.php';
require __DIR__ . '/moderation.php';
require __DIR__ . '/push.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    $ready = push_ready();
    json_out(['ok' => true, 'ready' => $ready, 'key' => $ready ? push_vapid()['public'] : null]);
}
if (!push_ready()) json_out(['ok' => false, 'error' => 'На хостинге нет openssl или curl — уведомления не работают.'], 503);

$in = json_decode((string)file_get_contents('php://input'), true);
if (!is_array($in)) json_out(['ok' => false, 'error' => 'bad request'], 400);
$action = (string)($in['action'] ?? '');
$ua = mb_substr((string)($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 160);

/** Коротко, что за устройство: «Chrome · Windows». */
function push_device_name($ua) {
    $b = preg_match('/YaBrowser/i', $ua) ? 'Яндекс Браузер' : (preg_match('/Edg\//', $ua) ? 'Edge' : (preg_match('/OPR\//', $ua) ? 'Opera' :
         (preg_match('/Firefox/i', $ua) ? 'Firefox' : (preg_match('/Chrome/i', $ua) ? 'Chrome' : (preg_match('/Safari/i', $ua) ? 'Safari' : 'Браузер')))));
    $os = preg_match('/Android/i', $ua) ? 'Android' : (preg_match('/iPhone|iPad/i', $ua) ? 'iPhone' : (preg_match('/Windows/i', $ua) ? 'Windows' :
          (preg_match('/Mac OS/i', $ua) ? 'macOS' : (preg_match('/Linux/i', $ua) ? 'Linux' : ''))));
    return $b . ($os ? ' · ' . $os : '');
}

switch ($action) {
    case 'subscribe':
        if (!csrf_ok()) json_out(['ok' => false, 'error' => 'Страница устарела — обновите её.'], 403);
        if (rate_limited('push_sub:' . client_ip(), 30, 3600)) json_out(['ok' => false, 'error' => 'Слишком часто.'], 429);
        $sub = push_valid_sub($in['subscription'] ?? null);
        if (!$sub) json_out(['ok' => false, 'error' => 'Браузер прислал неправильную подписку.'], 400);
        $user = current_user();
        $id = push_save_sub($sub, ['kind' => 'user', 'login' => $user['login'] ?? null, 'ua' => $ua, 'device' => push_device_name($ua)]);
        json_out(['ok' => true, 'id' => $id]);

    case 'unsubscribe':
        $id = push_sub_id((string)($in['endpoint'] ?? ''));
        push_delete([$id]);
        json_out(['ok' => true]);

    case 'test':
        if (rate_limited('push_test:' . client_ip(), 6, 3600)) json_out(['ok' => false, 'error' => 'Проверка — не чаще 6 раз в час.'], 429);
        $id = push_sub_id((string)($in['endpoint'] ?? ''));
        $subs = push_find(['id' => $id]);
        if (!$subs) json_out(['ok' => false, 'error' => 'Это устройство не подписано.'], 404);
        $admin = (reset($subs)['kind'] ?? '') === 'admin';
        $r = push_send($subs, ['title' => $admin ? '✅ Уведомления админ-панели работают' : '✅ Уведомления Rai работают',
                               'body' => $admin ? 'Сюда будут приходить нарушения, оплаты и новые пользователи.' : 'Сюда будут приходить ответы Rai и новости.',
                               'url' => $admin ? (string)(reset($subs)['back'] ?? '') : 'chat.html', 'tag' => 'rai-test']);
        json_out(['ok' => $r['sent'] > 0, 'result' => $r, 'error' => $r['sent'] ? null : 'Сервер уведомлений браузера не принял сообщение.']);

    case 'admin_subscribe':
        $back = (string)($in['back'] ?? '');
        if (!preg_match('~^https?://[^\s"<>]+$~', $back) || strlen($back) > 300) json_out(['ok' => false, 'error' => 'Неверный адрес админ-панели.'], 400);
        if (!push_admin_token_ok($in['exp'] ?? 0, $back, $in['t'] ?? '')) {
            json_out(['ok' => false, 'error' => 'Ссылка устарела — откройте её заново из админ-панели (вкладка «Rai: уведомления»).'], 403);
        }
        $sub = push_valid_sub($in['subscription'] ?? null);
        if (!$sub) json_out(['ok' => false, 'error' => 'Браузер прислал неправильную подписку.'], 400);
        $events = array_values(array_intersect(array_keys(PUSH_ADMIN_EVENTS), array_map('strval', (array)($in['events'] ?? []))));
        if (!$events) $events = array_keys(PUSH_ADMIN_EVENTS);
        $id = push_save_sub($sub, ['kind' => 'admin', 'login' => null, 'back' => $back, 'events' => $events, 'ua' => $ua,
                                   'device' => push_device_name($ua), 'admin' => mb_substr((string)($in['admin'] ?? ''), 0, 40)]);
        json_out(['ok' => true, 'id' => $id, 'events' => $events]);

    default:
        json_out(['ok' => false, 'error' => 'unknown action'], 400);
}
