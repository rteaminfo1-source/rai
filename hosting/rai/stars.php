<?php
/*
 * Оплата подписок Rai звёздами Telegram (Telegram Stars, валюта XTR).
 * Здесь — вспомогательные функции; сам бот (вебхук) — в tgbot.php.
 *
 * Как это работает:
 *   1) На сайте пользователь (вошедший в аккаунт) жмёт «Оплатить Telegram Stars» → открывается ссылка
 *      https://t.me/БОТ?start=<id>. Перед этим сайт создаёт заказ (stars_order_create) с коротким id.
 *   2) Бот по этому id выставляет счёт в звёздах (sendInvoice, currency=XTR).
 *   3) Пользователь платит в Telegram → бот ловит successful_payment → выдаёт подписку (set_subscription).
 * Секреты в ссылке не передаются — только короткий id заказа; всё остальное хранится на сайте в data/stars.json.
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/plans.php';

function stars_token() {
    // defined() — на случай, если TELEGRAM_* ещё не добавили в config.php: тогда оплата звёздами просто выключена
    $t = defined('TELEGRAM_BOT_TOKEN') ? (string)TELEGRAM_BOT_TOKEN : '';
    return (strpos($t, 'ВСТАВЬТЕ') === 0 || $t === '') ? '' : $t;
}

/** Подключена ли оплата звёздами (вписан ли токен бота). */
function stars_ready() { return stars_token() !== ''; }

function stars_bot_username() {
    return ltrim(defined('TELEGRAM_BOT_USERNAME') ? (string)TELEGRAM_BOT_USERNAME : '', '@') ?: 'RaiPayBot';
}

/** Вызов Telegram Bot API. Возвращает массив ответа или null. */
function tg_api($method, $params = []) {
    $token = stars_token();
    if ($token === '') return null;
    $url = 'https://api.telegram.org/bot' . $token . '/' . $method;
    $json = json_encode($params, JSON_UNESCAPED_UNICODE);
    $raw = null;
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true, CURLOPT_POSTFIELDS => $json,
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_TIMEOUT => 20,
        ]);
        $raw = curl_exec($ch);
        curl_close($ch);
    } else {
        $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => "Content-Type: application/json\r\n",
            'content' => $json, 'timeout' => 20, 'ignore_errors' => true]]);
        $raw = @file_get_contents($url, false, $ctx);
    }
    $data = json_decode((string)$raw, true);
    return is_array($data) ? $data : null;
}

// ------------------------------------------------------------------ заказы (data/stars.json)

function stars_price_for($plan, $months, $promo = '') { return plan_stars($plan, $months, $promo); }

/**
 * Создать заказ на оплату звёздами. Возвращает короткий id (его кладём в ссылку ?start=<id>).
 * Цена — от итоговой цены в рублях (скидка за год, акция, промокод) + комиссия Telegram.
 */
function stars_order_create($login, $plan, $months, $promo = '') {
    $plan = (string)$plan;
    $months = (int)$months >= 12 ? 12 : 1;
    if (!in_array($plan, PAID_PLANS, true)) return null;
    $offer = plan_offer($plan, $months, $promo);
    $stars = (int)$offer['stars'];
    if ($stars <= 0) return null;
    $id = bin2hex(random_bytes(8));   // 16 символов [0-9a-f] — помещается в Telegram start (≤64, разрешённые символы)
    $extra = ['rub' => (int)$offer['price'], 'base' => (int)$offer['base'], 'discount' => (int)$offer['percent'],
              'promo' => $offer['promo'], 'commission' => stars_commission(), 'rate' => stars_rate()];
    update_json('stars.json', function (&$all) use ($id, $login, $plan, $months, $stars, $extra) {
        // чистим старые незавершённые заказы (старше суток)
        foreach ($all as $k => $o) {
            if (($o['status'] ?? '') !== 'paid' && (int)($o['created'] ?? 0) < time() - 86400) unset($all[$k]);
        }
        $all[$id] = ['id' => $id, 'login' => (string)$login, 'plan' => $plan, 'months' => $months,
                     'stars' => $stars, 'status' => 'new', 'created' => time()] + $extra;
    });
    return $id;
}

function stars_order($id) {
    $id = preg_replace('/[^0-9a-f]/', '', (string)$id);
    if ($id === '') return null;
    $all = load_json('stars.json', []);
    return $all[$id] ?? null;
}

/** Ссылка в Telegram, которая откроет бота и начнёт оплату выбранного тарифа. */
function stars_link($login, $plan, $months, $promo = '') {
    if (!stars_ready()) return null;
    $id = stars_order_create($login, $plan, $months, $promo);
    if (!$id) return null;
    return 'https://t.me/' . stars_bot_username() . '?start=' . $id;
}

/**
 * Зачислить оплату звёздами по заказу (вызывается ботом на successful_payment).
 * Защита от повторной выдачи — по telegram_payment_charge_id. Возвращает true, если подписка выдана сейчас.
 */
function stars_grant($id, $charge_id, $tg_user = '') {
    $done = false;
    update_json('stars.json', function (&$all) use ($id, $charge_id, $tg_user, &$done) {
        $o = $all[$id] ?? null;
        if (!$o) return;
        if (($o['status'] ?? '') === 'paid') return;             // уже зачислено — второй раз не начисляем
        $all[$id]['status'] = 'paid';
        $all[$id]['charge'] = (string)$charge_id;
        $all[$id]['tg_user'] = (string)$tg_user;
        $all[$id]['paid_at'] = time();
        $done = true;
    });
    if (!$done) return false;
    $o = stars_order($id);
    $days = plan_days($o['months']);
    $note = 'Telegram Stars · ' . $o['stars'] . '⭐' . (!empty($o['discount']) ? ' · скидка −' . (int)$o['discount'] . '%' : '')
          . (!empty($o['promo']) ? ' · промокод ' . $o['promo'] : '') . ' · заказ ' . $id . ($tg_user ? ' · tg ' . $tg_user : '');
    set_subscription($o['login'], $o['plan'], $days, 'telegram-stars', $note);
    if (!empty($o['promo'])) promo_used($o['promo']);   // промокод засчитан, как и при оплате картой
    sub_log('stars', $o['login'], $o['plan'], $days, $note);
    return true;
}
