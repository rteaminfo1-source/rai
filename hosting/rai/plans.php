<?php
/*
 * Тарифы Rai, подписки и лимиты нейросети.
 *
 * Тариф хранится у пользователя в users.json: plan (plus | premium | ultra), plan_until (до какого момента).
 * Цены, лимиты и названия можно менять из админ-панели (вкладка «Rai») — они сохраняются в data/plans.php.
 * Подключается после config.php.
 */

// Тарифы по умолчанию. neuro_day — сообщений нейросети в день (0 — без ограничений).
// models — какие модели Rai Нейро доступны: fast (Лайт), normal (Стандарт), strong (Про), max (Макс), coder (Код).
const PLAN_DEFAULTS = [
    'free' => [
        'name' => 'Старт', 'price' => 0, 'neuro_day' => 15, 'think' => false, 'models' => ['fast', 'normal'],
        'tagline' => 'Чтобы познакомиться',
        'features' => ['15 сообщений нейросети в день', 'Модели Лайт и Стандарт', 'Движок Rai без ограничений: погода, курсы, перевод, код, презентации', 'Чаты в аккаунте на всех устройствах'],
    ],
    'plus' => [
        'name' => 'Плюс', 'price' => 249, 'neuro_day' => 150, 'think' => true, 'models' => ['fast', 'normal', 'strong'],
        'tagline' => 'Для учёбы и каждого дня',
        'features' => ['150 сообщений нейросети в день', 'Модель Про — умнее и точнее', 'Режим «Думать глубже» для сложных задач', 'Разбор соцсетей и сайтов нейросетью'],
    ],
    'premium' => [
        'name' => 'Премиум', 'price' => 599, 'neuro_day' => 600, 'think' => true, 'models' => ['fast', 'normal', 'strong', 'max', 'coder'],
        'tagline' => 'Для работы и кода', 'popular' => true,
        'features' => ['600 сообщений нейросети в день', 'Все модели: Макс (9B) и Код (7B)', 'Rai Code с самой сильной моделью для программ', 'Приоритетная поддержка'],
    ],
    'ultra' => [
        'name' => 'Ультра', 'price' => 1290, 'neuro_day' => 0, 'think' => true, 'models' => ['fast', 'normal', 'strong', 'max', 'coder'],
        'tagline' => 'Без ограничений',
        'features' => ['Нейросеть без лимита', 'Все модели и режимы', 'Ранний доступ к новым моделям и функциям', 'Личная поддержка команды Rteam'],
    ],
];
const PAID_PLANS = ['plus', 'premium', 'ultra'];
const GUEST_NEURO_DAY = 5;                 // без входа — столько сообщений в день (по IP)
const YEAR_DISCOUNT = 25;                  // скидка за год, %
const PLAN_PERIODS = [1 => 'месяц', 12 => 'год'];

/** Тарифы с учётом изменений из админ-панели. */
function plans() {
    static $cache = null;
    if ($cache !== null) return $cache;
    $over = load_json('plans.json', []);
    $out = PLAN_DEFAULTS;
    foreach ($out as $key => &$plan) {
        foreach (['name', 'price', 'neuro_day', 'tagline'] as $f) {
            if (isset($over[$key][$f]) && $over[$key][$f] !== '') $plan[$f] = $over[$key][$f];
        }
        if (isset($over[$key]['features']) && is_array($over[$key]['features'])) $plan['features'] = $over[$key]['features'];
        $plan['price'] = max(0, (int)$plan['price']);
        $plan['neuro_day'] = max(0, (int)$plan['neuro_day']);
    }
    unset($plan);
    return $cache = $out;
}

function plan_price($key, $months) {
    $price = plans()[$key]['price'] * $months;
    if ($months >= 12) $price = (int)round($price * (100 - YEAR_DISCOUNT) / 100);
    return $price;
}

function rub($n) { return number_format((int)$n, 0, ',', ' ') . ' ₽'; }

/** Действующий тариф пользователя: ['key', 'until'] (free — без срока). Просроченная подписка = free. */
function user_plan($user) {
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
            $u['plan_until'] = $from + (int)$days * 86400;
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
    $limit = $user ? $p['neuro_day'] : GUEST_NEURO_DAY;
    $used = usage_get(usage_key($user));
    return [
        'guest' => !$user,
        'plan' => $plan['key'], 'plan_name' => $p['name'], 'until' => $plan['until'] ?: null,
        'limit' => $limit, 'used' => $used, 'left' => $limit > 0 ? max(0, $limit - $used) : null,
        'models' => $user ? $p['models'] : PLAN_DEFAULTS['free']['models'],
        'think' => $user ? (bool)$p['think'] : false,
        'unlock' => model_unlocks(),
        'pricing' => './#pricing',
    ];
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
function platega_ready() {
    return PLATEGA_MERCHANT_ID !== '' && strpos(PLATEGA_MERCHANT_ID, 'ВСТАВЬТЕ') !== 0
        && PLATEGA_SECRET !== '' && strpos(PLATEGA_SECRET, 'ВСТАВЬТЕ') !== 0;
}

/** Запрос к API Platega. Возвращает [код ответа, данные]. */
function platega_request($method, $path, $body = null) {
    $url = rtrim(PLATEGA_API, '/') . $path;
    $headers = ['X-MerchantId: ' . PLATEGA_MERCHANT_ID, 'X-Secret: ' . PLATEGA_SECRET,
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
    if ((int)PLATEGA_METHOD > 0) {  // заданный способ (2 — СБП, 11 — карты…)
        $body['paymentMethod'] = (int)PLATEGA_METHOD;
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
        sub_log('payment', $activated['login'], $activated['plan'], 30 * (int)$activated['months'], 'Platega · ' . rub($activated['amount']));
    }
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
