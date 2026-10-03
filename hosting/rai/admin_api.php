<?php
/*
 * API для админ-панели (admin.php, вкладка «Rai»): статистика, поиск пользователя, выдача и снятие подписки,
 * тарифы и платежи. Принимает только подписанные запросы:
 *   POST, тело JSON {"action": "...", "nonce": "...", ...}
 *   X-Rai-Time: unix-время, X-Rai-Signature: hex(HMAC-SHA256(время + "\n" + тело, ADMIN_API_KEY))
 * Запрос старше 5 минут или с уже использованным nonce отклоняется.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';

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
        json_out(['ok' => true,
            'users' => count($users), 'new_week' => count(array_filter($users, function ($u) { return ($u['created'] ?? 0) > time() - 7 * 86400; })),
            'by_plan' => $by_plan, 'subscribers' => array_sum($by_plan), 'mrr' => $mrr,
            'revenue_total' => $sum($paid), 'revenue_month' => $sum(array_filter($paid, function ($o) use ($month_start) { return ($o['paid_at'] ?? 0) >= $month_start; })),
            'neuro_today' => array_sum($usage), 'neuro_people_today' => count($usage),
            'subs' => array_slice($subs, 0, 300), 'orders' => $recent,
            'log' => array_slice(array_reverse(load_json('sub_log.json', [])), 0, 50),
            'plans' => plans(), 'platega' => platega_ready(), 'guest_limit' => GUEST_NEURO_DAY]);

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

    case 'plans_reset':
        save_json('plans.json', []);
        sub_log('plans', '', '', 0, 'Тарифы сброшены к стандартным', $by);
        json_out(['ok' => true]);

    default:
        json_out(['ok' => false, 'error' => 'unknown action'], 400);
}
