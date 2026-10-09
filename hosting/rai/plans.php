<?php
/*
 * Тарифы Rai, подписки и лимиты нейросети.
 *
 * Тариф хранится у пользователя в users.json: plan (plus | premium | ultra), plan_until (до какого момента).
 * Цены, лимиты и названия можно менять из админ-панели (вкладка «Rai») — они сохраняются в data/plans.php.
 * Подключается после config.php.
 */

// Тарифы по умолчанию. neuro_day — сообщений нейросети в день (0 — без ограничений).
// tokens_day — дневной лимит токенов своего движка Rai (0 — бесконечно); видно в чате внизу (⚡).
// models — какие модели внешней нейросети доступны (если её подключили): fast, normal, strong, max, coder.
// levels — уровни размышления своего движка Rai (выбор внизу чата): low, medium, high, extra, code, ultra.
const PLAN_DEFAULTS = [
    'free' => [
        'name' => 'Старт', 'price' => 0, 'neuro_day' => 15, 'tokens_day' => 100000, 'think' => false, 'models' => ['fast', 'normal'],
        'levels' => ['low', 'medium', 'high'],
        'tagline' => 'Чтобы познакомиться',
        'features' => ['Rai думает сам: уровни Low, Medium и High', '100 000 токенов в день', 'Поиск и чтение сайтов, ответы со ссылками', 'Погода, курсы, перевод, код, презентации — без ограничений', 'Чаты в аккаунте на всех устройствах'],
    ],
    'plus' => [
        'name' => 'Плюс', 'price' => 249, 'neuro_day' => 150, 'tokens_day' => 1000000, 'think' => true, 'models' => ['fast', 'normal', 'strong'],
        'levels' => ['low', 'medium', 'high', 'extra', 'code'],
        'tagline' => 'Для учёбы и каждого дня',
        'features' => ['Уровни Extra и Code: глубже ищет, сам пишет и проверяет программы', '1 000 000 токенов в день', 'Разбор тем по разделам статей', 'Разбор соцсетей и сайтов'],
    ],
    'premium' => [
        'name' => 'Премиум', 'price' => 599, 'neuro_day' => 600, 'tokens_day' => 3000000, 'think' => true, 'models' => ['fast', 'normal', 'strong', 'max', 'coder'],
        'levels' => ['low', 'medium', 'high', 'extra', 'code', 'ultra'],
        'tagline' => 'Для работы и кода', 'popular' => true,
        'features' => ['Все уровни, включая Ultra: максимум источников и сверка', '3 000 000 токенов в день', 'Rai Code: программы с проверкой запуском', 'Приоритетная поддержка'],
    ],
    'ultra' => [
        'name' => 'Ультра', 'price' => 1290, 'neuro_day' => 0, 'tokens_day' => 0, 'think' => true, 'models' => ['fast', 'normal', 'strong', 'max', 'coder'],
        'levels' => ['low', 'medium', 'high', 'extra', 'code', 'ultra'],
        'tagline' => 'Без ограничений',
        'features' => ['Все уровни размышления без ограничений', 'Токены без ограничений — бесконечно', 'Ранний доступ к новым функциям', 'Личная поддержка команды Rteam'],
    ],
];
const PAID_PLANS = ['plus', 'premium', 'ultra'];
const GUEST_NEURO_DAY = 5;                 // без входа — столько сообщений в день (по IP); меняется в админке
const GUEST_TOKENS_DAY = 30000;            // без входа — столько токенов движка Rai в день
const YEAR_DISCOUNT = 25;                  // скидка за год, %
const PLAN_PERIODS = [1 => 'месяц', 12 => 'год'];
const PLAN_FOREVER = 4102444800;           // 1 января 2100 — подписка «навсегда» (выдаётся в админ-панели)
// Особые роли (ставятся в админ-панели): значок у имени и полный доступ (как «Ультра») навсегда
const USER_ROLES = [
    'creator' => ['name' => 'Создатель', 'icon' => '👑'],
    'developer' => ['name' => 'Разработчик', 'icon' => '🛠'],
];

function user_role($user) {
    $r = is_array($user) ? (string)($user['role'] ?? '') : '';
    return isset(USER_ROLES[$r]) ? $r : null;
}

/** Роль для страниц: {key, name, icon} или null. */
function user_role_public($user) {
    $r = user_role($user);
    return $r ? ['key' => $r] + USER_ROLES[$r] : null;
}

function plan_is_forever($until) { return (int)$until >= PLAN_FOREVER - 365 * 86400; }

/** «навсегда» или «до 5 октября 2026». */
function until_text($until) { return plan_is_forever($until) ? 'навсегда' : 'до ' . ru_date($until); }

/** Тарифы с учётом изменений из админ-панели. */
function plans() {
    static $cache = null;
    if ($cache !== null) return $cache;
    $over = load_json('plans.json', []);
    $out = PLAN_DEFAULTS;
    foreach ($out as $key => &$plan) {
        foreach (['name', 'price', 'neuro_day', 'tokens_day', 'tagline'] as $f) {
            if (isset($over[$key][$f]) && $over[$key][$f] !== '') $plan[$f] = $over[$key][$f];
        }
        if (isset($over[$key]['features']) && is_array($over[$key]['features'])) $plan['features'] = $over[$key]['features'];
        $plan['price'] = max(0, (int)$plan['price']);
        $plan['neuro_day'] = max(0, (int)$plan['neuro_day']);
        $plan['tokens_day'] = max(0, (int)($plan['tokens_day'] ?? 0));
    }
    unset($plan);
    return $cache = $out;
}

/** Без входа — сколько сообщений нейросети в день (из админки или GUEST_NEURO_DAY). */
function guest_limit() {
    $over = load_json('plans.json', []);
    return isset($over['guest']['neuro_day']) ? max(0, (int)$over['guest']['neuro_day']) : GUEST_NEURO_DAY;
}

function plan_price($key, $months) {
    $price = plans()[$key]['price'] * $months;
    if ($months >= 12) $price = (int)round($price * (100 - YEAR_DISCOUNT) / 100);
    return $price;
}

// ====================================================================== скидки и промокоды (админ-панель → «Rai: скидки»)
// data/discounts.php: {"sale": {percent, plans: [], title, until}, "promos": {"КОД": {percent, plans: [], until, uses_max, used, note}}}
// Акция действует сама для всех; промокод вводят при оплате. Скидки не складываются — берётся бо́льшая.

function discounts() {
    $d = load_json('discounts.json', []);
    return ['sale' => is_array($d['sale'] ?? null) ? $d['sale'] : null, 'promos' => is_array($d['promos'] ?? null) ? $d['promos'] : []];
}

function discount_fits($d, $plan) { return empty($d['plans']) || in_array($plan, (array)$d['plans'], true); }

/** Акция, которая действует сейчас (или null). */
function sale_active() {
    $s = discounts()['sale'];
    if (!$s || (int)($s['percent'] ?? 0) <= 0) return null;
    if (!empty($s['until']) && (int)$s['until'] < time()) return null;
    return $s;
}

function promo_code($code) { return strtoupper(preg_replace('/[^A-Za-z0-9А-Яа-яЁё_-]/u', '', mb_substr(trim((string)$code), 0, 32))); }

/** Проверить промокод для тарифа: [данные промокода | null, ошибка | null]. */
function promo_check($code, $plan) {
    $code = promo_code($code);
    if ($code === '') return [null, null];
    $p = discounts()['promos'][mb_strtoupper($code)] ?? null;
    if (!$p) return [null, 'Такого промокода нет.'];
    if (!empty($p['until']) && (int)$p['until'] < time()) return [null, 'Срок промокода закончился.'];
    if (!empty($p['uses_max']) && (int)($p['used'] ?? 0) >= (int)$p['uses_max']) return [null, 'Промокод уже использовали максимальное число раз.'];
    if (!discount_fits($p, $plan)) return [null, 'Промокод не действует для этого тарифа.'];
    return [['code' => mb_strtoupper($code)] + $p, null];
}

/**
 * Цена с учётом акции и промокода: base (без скидок), price (к оплате), percent, reason (sale | promo | ''), title,
 * promo (код, если применён), promo_error (почему код не подошёл).
 */
function plan_offer($plan, $months, $promo = '') {
    $base = plan_price($plan, $months);
    $out = ['base' => $base, 'price' => $base, 'percent' => 0, 'reason' => '', 'title' => '', 'until' => null, 'promo' => null, 'promo_error' => null];
    if ($base <= 0) return $out;   // бесплатный тариф
    $sale = sale_active();
    if ($sale && discount_fits($sale, $plan)) {
        $out = array_merge($out, ['percent' => (int)$sale['percent'], 'reason' => 'sale', 'title' => (string)($sale['title'] ?? 'Скидка'), 'until' => $sale['until'] ?? null]);
    }
    list($p, $err) = promo_check($promo, $plan);
    $out['promo_error'] = $err;
    if ($p && (int)$p['percent'] > $out['percent']) {
        $out = array_merge($out, ['percent' => (int)$p['percent'], 'reason' => 'promo', 'title' => 'Промокод ' . $p['code'], 'until' => $p['until'] ?? null, 'promo' => $p['code']]);
    } elseif ($p) {
        $out['promo_error'] = 'Акция уже даёт скидку больше, чем этот промокод.';
    }
    if ($out['percent'] > 0) $out['price'] = max(1, (int)round($base * (100 - min(95, $out['percent'])) / 100));
    return $out;
}

/** Промокод использован (после оплаты). */
function promo_used($code) {
    $code = promo_code($code);
    if ($code === '') return;
    update_json('discounts.json', function (&$d) use ($code) {
        $code = mb_strtoupper($code);
        if (isset($d['promos'][$code])) $d['promos'][$code]['used'] = (int)($d['promos'][$code]['used'] ?? 0) + 1;
    });
}

function rub($n) { return number_format((int)$n, 0, ',', ' ') . ' ₽'; }

/** Действующий тариф пользователя: ['key', 'until'] (free — без срока). Просроченная подписка = free. */
function user_plan($user) {
    if (user_role($user)) return ['key' => 'ultra', 'until' => PLAN_FOREVER, 'role' => user_role($user)];   // создатель, разработчик
    $key = $user['plan'] ?? 'free';
    $until = (int)($user['plan_until'] ?? 0);
    if (!in_array($key, PAID_PLANS, true) || $until <= time()) return ['key' => 'free', 'until' => 0];
    return ['key' => $key, 'until' => $until];
}

/**
 * Выдать или продлить подписку. Тот же тариф — продлевается от текущей даты окончания,
 * другой — начинается сейчас. $days = 0 — снять подписку.
 */
function set_subscription($login, $plan, $days, $source, $note = '') {
    return update_json('users.json', function (&$users) use ($login, $plan, $days, $source, $note) {
        if (!isset($users[$login])) return null;
        $u = &$users[$login];
        if ($days <= 0 || !in_array($plan, PAID_PLANS, true)) {
            $u['plan'] = 'free';
            $u['plan_until'] = 0;
        } else {
            $current = user_plan($u);
            $from = $current['key'] === $plan ? max(time(), $current['until']) : time();
            $u['plan'] = $plan;
            $u['plan_until'] = $days >= 36500 ? PLAN_FOREVER : min(PLAN_FOREVER, $from + (int)$days * 86400);
        }
        $u['plan_source'] = $source;
        $u['plan_note'] = mb_substr((string)$note, 0, 200);
        return $u;
    });
}

// ====================================================================== сколько нейросети уже потрачено сегодня
function usage_day() { return date('Y-m-d'); }

function usage_key($user) {
    return $user ? 'u:' . $user['login'] : 'g:' . substr(hash('sha256', client_ip() . '|' . SSO_SECRET), 0, 24);
}

function usage_get($key) {
    $day = load_json('usage/' . usage_day() . '.json', []);
    return (int)($day[$key] ?? 0);
}

/** Засчитать одно сообщение, если лимит позволяет. Возвращает [разрешено, использовано]. */
function usage_take($key, $limit) {
    $name = 'usage/' . usage_day() . '.json';
    $result = update_json($name, function (&$day) use ($key, $limit) {
        $used = (int)($day[$key] ?? 0);
        if ($limit > 0 && $used >= $limit) return [false, $used];
        $day[$key] = $used + 1;
        return [true, $used + 1];
    });
    // старые дни не храним (оставляем неделю для статистики)
    if (mt_rand(1, 50) === 1) {
        foreach (glob(DATA_DIR . '/usage/*.php') ?: [] as $file) {
            if (preg_match('/(\d{4}-\d{2}-\d{2})/', $file, $m) && strtotime($m[1]) < time() - 7 * 86400) @unlink($file);
        }
    }
    return $result;
}

/** Всё о лимитах для страницы чата. */
function limits_state($user) {
    $plan = $user ? user_plan($user) : ['key' => 'free', 'until' => 0];
    $p = plans()[$plan['key']];
    $limit = $user ? $p['neuro_day'] : guest_limit();
    $used = usage_get(usage_key($user));
    return [
        'guest' => !$user,
        'plan' => $plan['key'], 'plan_name' => $p['name'], 'until' => $plan['until'] ?: null,
        'limit' => $limit, 'used' => $used, 'left' => $limit > 0 ? max(0, $limit - $used) : null,
        'tokens_day' => $user ? (int)($p['tokens_day'] ?? 0) : GUEST_TOKENS_DAY,   // лимит токенов движка Rai по подписке (0 — ∞)
        'models' => $user ? $p['models'] : PLAN_DEFAULTS['free']['models'],
        'think' => $user ? (bool)$p['think'] : false,
        'unlock' => model_unlocks(),
        'levels' => $user ? ($p['levels'] ?? PLAN_DEFAULTS['free']['levels']) : PLAN_DEFAULTS['free']['levels'],
        'level_unlock' => level_unlocks(),
        'pricing' => './#pricing',
    ];
}

/** Для каждого уровня размышления — самый дешёвый тариф, где он есть: {"extra": "Плюс", "ultra": "Премиум"}. */
function level_unlocks() {
    $out = [];
    $paid = array_intersect_key(plans(), array_flip(PAID_PLANS));
    uasort($paid, function ($a, $b) { return $a['price'] <=> $b['price']; });
    foreach ($paid as $p) foreach (($p['levels'] ?? []) as $l) if (!isset($out[$l])) $out[$l] = $p['name'];
    return $out;
}

/** Для каждой модели — самый дешёвый тариф, где она есть: {"strong": "Плюс", "max": "Премиум", …}. */
function model_unlocks() {
    $out = [];
    $paid = array_intersect_key(plans(), array_flip(PAID_PLANS));
    uasort($paid, function ($a, $b) { return $a['price'] <=> $b['price']; });
    foreach ($paid as $p) foreach ($p['models'] as $m) if (!isset($out[$m])) $out[$m] = $p['name'];
    return $out;
}

// ====================================================================== оплата через Platega
// Ключи Platega: из config.php, а если там ещё заглушки — из админ-панели (data/platega.php, из браузера не читается).
function platega_conf() {
    static $conf = null;
    if ($conf !== null) return $conf;
    $filled = function ($v) { return $v !== '' && strpos((string)$v, 'ВСТАВЬТЕ') !== 0; };
    if ($filled(PLATEGA_MERCHANT_ID) && $filled(PLATEGA_SECRET)) {
        return $conf = ['id' => PLATEGA_MERCHANT_ID, 'secret' => PLATEGA_SECRET, 'method' => (int)PLATEGA_METHOD, 'source' => 'config'];
    }
    $saved = load_json('platega.json', []);
    if (!empty($saved['id']) && !empty($saved['secret'])) {
        return $conf = ['id' => (string)$saved['id'], 'secret' => (string)$saved['secret'], 'method' => (int)($saved['method'] ?? 0), 'source' => 'admin'];
    }
    return $conf = ['id' => '', 'secret' => '', 'method' => 0, 'source' => null];
}

function platega_ready() { return platega_conf()['source'] !== null; }

/** Запрос к API Platega. Возвращает [код ответа, данные]. */
function platega_request($method, $path, $body = null) {
    $url = rtrim(PLATEGA_API, '/') . $path;
    $c = platega_conf();
    $headers = ['X-MerchantId: ' . $c['id'], 'X-Secret: ' . $c['secret'],
                'Content-Type: application/json', 'Accept: application/json'];
    $payload = $body === null ? null : json_encode($body, JSON_UNESCAPED_UNICODE);
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_HTTPHEADER => $headers, CURLOPT_RETURNTRANSFER => true,
                                CURLOPT_CONNECTTIMEOUT => 8, CURLOPT_TIMEOUT => 20]);
        if ($payload !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        $raw = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
    } else {
        $ctx = stream_context_create(['http' => ['method' => $method, 'header' => implode("\r\n", $headers),
                                                 'content' => (string)$payload, 'timeout' => 20, 'ignore_errors' => true]]);
        $raw = @file_get_contents($url, false, $ctx);
        $code = isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m) ? (int)$m[1] : 0;
    }
    $data = json_decode((string)$raw, true);
    return [$code, is_array($data) ? $data : []];
}

/** Создать платёж: ссылка на страницу оплаты Platega или null и текст ошибки. */
function platega_create($order) {
    $body = [
        'paymentDetails' => ['amount' => (float)$order['amount'], 'currency' => 'RUB'],
        'description' => $order['title'],
        'return' => SITE_URL . '/pay_return.php?order=' . rawurlencode($order['id']),
        'failedUrl' => SITE_URL . '/pay_return.php?order=' . rawurlencode($order['id']) . '&failed=1',
        'payload' => $order['id'],
        'metadata' => ['userId' => $order['login']],
    ];
    $method = platega_conf()['method'];
    if ($method > 0) {  // заданный способ (2 — СБП, 11 — карты…)
        $body['paymentMethod'] = $method;
        list($code, $data) = platega_request('POST', '/transaction/process', $body);
    } else {                         // покупатель сам выбирает способ на странице Platega
        list($code, $data) = platega_request('POST', '/v2/transaction/process', $body);
    }
    $link = $data['url'] ?? ($data['redirect'] ?? null);
    if ($code >= 200 && $code < 300 && $link && !empty($data['transactionId'])) {
        return [$link, (string)$data['transactionId'], null];
    }
    return [null, null, $data['message'] ?? ('Platega ответила кодом ' . $code)];
}

/** Статус платежа в Platega: CONFIRMED, PENDING, CANCELED… и сумма. */
function platega_status($transaction_id) {
    list($code, $data) = platega_request('GET', '/transaction/' . rawurlencode($transaction_id));
    if ($code < 200 || $code >= 300) return [null, null];
    $amount = $data['paymentDetails']['amount'] ?? ($data['amount'] ?? null);
    return [strtoupper((string)($data['status'] ?? '')), $amount === null ? null : (float)$amount];
}

/**
 * Отметить заказ оплаченным и включить подписку — ровно один раз, сколько бы раз ни пришло уведомление.
 * Возвращает заказ.
 */
function order_confirm($order_id, $paid_amount) {
    $activated = null;
    $order = update_json('orders.json', function (&$orders) use ($order_id, $paid_amount, &$activated) {
        if (!isset($orders[$order_id])) return null;
        $o = &$orders[$order_id];
        if ($o['status'] === 'paid') return $o;
        if ($paid_amount !== null && $paid_amount + 0.01 < (float)$o['amount']) {
            $o['status'] = 'underpaid';
            return $o;
        }
        $o['status'] = 'paid';
        $o['paid_at'] = time();
        $activated = $o;
        return $o;
    });
    if ($activated) {
        set_subscription($activated['login'], $activated['plan'], 30 * (int)$activated['months'], 'platega',
                         'Оплата ' . rub($activated['amount']) . ', заказ ' . $activated['id']);
        sub_log('payment', $activated['login'], $activated['plan'], 30 * (int)$activated['months'], 'Platega · ' . rub($activated['amount'])
                . (!empty($activated['discount']) ? ' (скидка ' . (int)$activated['discount'] . '%' . (!empty($activated['promo']) ? ', промокод ' . $activated['promo'] : '') . ')' : ''));
        if (!empty($activated['promo'])) promo_used($activated['promo']);
        // уведомления: админам — «пришла оплата», покупателю — «тариф включён» (push.php, после ответа Platega)
        require_once __DIR__ . '/push.php';
        $plan = plans()[$activated['plan']]['name'] ?? $activated['plan'];
        $months = (int)$activated['months'];
        push_admins('payments', '💳 Оплата Rai: ' . rub($activated['amount']), '@' . $activated['login'] . ' — тариф «' . $plan . '» на ' . $months . ' мес.', '?tab=rai');
        $until = user_plan(users()[$activated['login']] ?? [])['until'] ?? 0;
        push_user_later($activated['login'], ['title' => '✅ Оплата прошла', 'url' => 'chat.html', 'tag' => 'rai-plan',
            'body' => 'Тариф «' . $plan . '» включён' . ($until ? ' до ' . date('d.m.Y', $until) : '') . '. Спасибо, что вы с Rai!']);
    }
    return $order;
}

/** Спросить у Platega статус заказа и, если оплачен, включить подписку. Возвращает заказ. */
function order_check($order_id) {
    $order = load_json('orders.json', [])[$order_id] ?? null;
    if (!$order || $order['status'] === 'paid' || empty($order['transaction']) || !platega_ready()) return $order;
    list($status, $amount) = platega_status($order['transaction']);
    if ($status === 'CONFIRMED') return order_confirm($order['id'], $amount);
    if (in_array($status, ['CANCELED', 'CANCELLED', 'FAILED', 'EXPIRED'], true)) return order_update($order['id'], ['status' => 'canceled']);
    return $order;
}

function order_update($order_id, $fields) {
    return update_json('orders.json', function (&$orders) use ($order_id, $fields) {
        if (!isset($orders[$order_id])) return null;
        $orders[$order_id] = array_merge($orders[$order_id], $fields);
        return $orders[$order_id];
    });
}

/** Журнал подписок (видно в админ-панели). */
function sub_log($type, $login, $plan, $days, $note, $by = '') {
    update_json('sub_log.json', function (&$log) use ($type, $login, $plan, $days, $note, $by) {
        $log[] = ['time' => time(), 'type' => $type, 'login' => $login, 'plan' => $plan, 'days' => (int)$days,
                  'note' => mb_substr((string)$note, 0, 200), 'by' => $by];
        if (count($log) > 2000) $log = array_slice($log, -2000);
    });
}

/** Дата по-русски: 3 октября 2026. */
function ru_date($ts) {
    $m = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    return date('j', $ts) . ' ' . $m[(int)date('n', $ts) - 1] . ' ' . date('Y', $ts);
}
