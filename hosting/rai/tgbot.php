<?php
/*
 * Телеграм-бот оплаты Rai звёздами (Telegram Stars). Это вебхук: Telegram шлёт сюда обновления.
 *
 * Настройка (один раз):
 *   1) @BotFather → создать бота → взять токен → вписать в config.php (TELEGRAM_BOT_TOKEN) и имя бота (TELEGRAM_BOT_USERNAME).
 *   2) Открыть в браузере: https://rai.rteam.info/tgbot.php?action=setwebhook&key=ВАШ_ADMIN_API_KEY
 *      (поставит вебхук на этот файл с секретным заголовком — чужие запросы бот игнорирует).
 *   3) Готово. На сайте у тарифов появится кнопка «Оплатить Telegram Stars».
 * Проверка: https://rai.rteam.info/tgbot.php?action=info&key=ВАШ_ADMIN_API_KEY
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';
require __DIR__ . '/stars.php';

// ----- служебные GET-команды для владельца сайта (поставить/проверить вебхук) -----
if (($_GET['action'] ?? '') !== '') {
    header('Content-Type: application/json; charset=utf-8');
    $key = (string)($_GET['key'] ?? '');
    if (!hash_equals((string)ADMIN_API_KEY, $key)) { http_response_code(403); echo json_encode(['ok' => false, 'error' => 'bad key']); exit; }
    if (!stars_ready()) { echo json_encode(['ok' => false, 'error' => 'TELEGRAM_BOT_TOKEN не вписан в config.php']); exit; }
    if ($_GET['action'] === 'setwebhook') {
        $url = SITE_URL . '/tgbot.php';
        echo json_encode(tg_api('setWebhook', [
            'url' => $url, 'secret_token' => TELEGRAM_WEBHOOK_SECRET,
            'allowed_updates' => ['message', 'pre_checkout_query', 'callback_query'],
            'drop_pending_updates' => true,
        ]), JSON_UNESCAPED_UNICODE);
        exit;
    }
    if ($_GET['action'] === 'info') { echo json_encode(tg_api('getWebhookInfo'), JSON_UNESCAPED_UNICODE); exit; }
    if ($_GET['action'] === 'delete') { echo json_encode(tg_api('deleteWebhook', ['drop_pending_updates' => true]), JSON_UNESCAPED_UNICODE); exit; }
    http_response_code(404); echo json_encode(['ok' => false]); exit;
}

// ----- приём обновлений от Telegram -----
function ok200() { http_response_code(200); header('Content-Type: text/plain'); echo 'ok'; exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') ok200();
if (!stars_ready()) ok200();
// Защита: Telegram присылает наш секрет в заголовке. Чужой запрос без него — игнор.
$got = (string)($_SERVER['HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN'] ?? '');
if (!hash_equals((string)TELEGRAM_WEBHOOK_SECRET, $got)) ok200();

$update = json_decode((string)file_get_contents('php://input'), true);
if (!is_array($update)) ok200();

$site = rtrim(SITE_URL, '/');

/** Текст с ценами в звёздах и ссылкой на сайт. */
function stars_help_text($site) {
    $lines = ["<b>Rai</b> — оплата подписки звёздами Telegram ⭐", ""];
    foreach (PAID_PLANS as $key) {
        $p = plans()[$key];
        $m = plan_stars($key, 1);
        $y = plan_stars($key, 12);
        if ($m > 0) $lines[] = "• <b>" . htmlspecialchars($p['name']) . "</b> — {$m}⭐ / месяц, {$y}⭐ / год";
    }
    $sale = sale_active();
    if ($sale) $lines[] = "\n🏷 Сейчас акция «" . htmlspecialchars((string)($sale['title'] ?: 'Скидка')) . "»: −" . (int)$sale['percent'] . "% — цены выше уже со скидкой.";
    $lines[] = "";
    $lines[] = "В цену в звёздах входит " . stars_commission() . "% — комиссия Telegram (1 ⭐ ≈ " . str_replace('.', ',', (string)stars_rate()) . " ₽). "
             . "Промокоды с сайта тоже действуют.";
    $lines[] = "";
    $lines[] = "Чтобы купить, откройте тариф на сайте и нажмите «Оплатить Telegram Stars» — я сразу выставлю счёт.";
    $lines[] = $site;
    return implode("\n", $lines);
}

// --- предварительная проверка платежа (нужно ответить за 10 секунд) ---
if (isset($update['pre_checkout_query'])) {
    $q = $update['pre_checkout_query'];
    $order = stars_order($q['invoice_payload'] ?? '');
    $okPay = $order && ($order['status'] ?? '') !== 'paid' && (int)($q['total_amount'] ?? 0) === (int)($order['stars'] ?? -1);
    tg_api('answerPreCheckoutQuery', $okPay
        ? ['pre_checkout_query_id' => $q['id'], 'ok' => true]
        : ['pre_checkout_query_id' => $q['id'], 'ok' => false, 'error_message' => 'Счёт устарел. Откройте оплату на сайте заново.']);
    ok200();
}

$msg = $update['message'] ?? null;
if (!$msg) ok200();
$chat_id = $msg['chat']['id'] ?? null;
if ($chat_id === null) ok200();
$from = $msg['from']['id'] ?? '';

// --- успешная оплата: выдаём подписку ---
if (isset($msg['successful_payment'])) {
    $sp = $msg['successful_payment'];
    $id = (string)($sp['invoice_payload'] ?? '');
    $charge = (string)($sp['telegram_payment_charge_id'] ?? '');
    $order = stars_order($id);
    $granted = $order ? stars_grant($id, $charge, (string)$from) : false;
    if ($order) {
        $p = plans()[$order['plan']];
        $period = (int)$order['months'] >= 12 ? 'год' : 'месяц';
        $text = $granted
            ? "✅ Оплата получена! Подписка <b>Rai " . htmlspecialchars($p['name']) . "</b> на {$period} активна.\n\n"
              . "Откройте Rai тем же аккаунтом — всё уже работает:\n" . $site
            : "Оплата получена, подписка уже была активна — спасибо!";
    } else {
        $text = "Оплата получена. Если подписка не включилась за пару минут — напишите в поддержку, всё поправим.";
    }
    tg_api('sendMessage', ['chat_id' => $chat_id, 'text' => $text, 'parse_mode' => 'HTML', 'disable_web_page_preview' => true]);
    ok200();
}

// --- команды и /start ---
$text = trim((string)($msg['text'] ?? ''));
if (strpos($text, '/start') === 0) {
    $payload = trim((string)substr($text, 6));
    $order = $payload !== '' ? stars_order($payload) : null;
    if ($order && ($order['status'] ?? '') !== 'paid') {
        // выставляем счёт в звёздах
        $p = plans()[$order['plan']];
        $period = (int)$order['months'] >= 12 ? '12 месяцев' : '1 месяц';
        $r = tg_api('sendInvoice', [
            'chat_id' => $chat_id,
            'title' => 'Rai ' . $p['name'] . ' · ' . $period,
            'description' => 'Подписка Rai ' . $p['name'] . ' на ' . $period . ' для аккаунта ' . $order['login'] . '.'
                . (!empty($order['discount']) ? ' Скидка −' . (int)$order['discount'] . '%' . (!empty($order['promo']) ? ' (промокод ' . $order['promo'] . ')' : '') . '.' : '')
                . ' Включает ' . (int)($order['commission'] ?? stars_commission()) . '% комиссии Telegram.',
            'payload' => $order['id'],
            'provider_token' => '',               // для Telegram Stars — пусто
            'currency' => 'XTR',
            'prices' => [['label' => 'Rai ' . $p['name'] . ' (' . $period . ')', 'amount' => (int)$order['stars']]],
        ]);
        if (!$r || empty($r['ok'])) {
            tg_api('sendMessage', ['chat_id' => $chat_id, 'text' => 'Не получилось выставить счёт. Откройте оплату на сайте заново: ' . $site]);
        }
    } elseif ($order && ($order['status'] ?? '') === 'paid') {
        tg_api('sendMessage', ['chat_id' => $chat_id, 'text' => 'Этот счёт уже оплачен ✅ Подписка активна.']);
    } else {
        tg_api('sendMessage', ['chat_id' => $chat_id, 'text' => stars_help_text($site), 'parse_mode' => 'HTML', 'disable_web_page_preview' => true]);
    }
    ok200();
}

if ($text === '/help' || $text === '/paysupport') {
    $t = $text === '/paysupport'
        ? "Оплата звёздами Telegram. Если звёзды списались, а подписка не включилась — напишите нам, пришлите дату и тариф, всё поправим."
        : stars_help_text($site);
    tg_api('sendMessage', ['chat_id' => $chat_id, 'text' => $t, 'parse_mode' => 'HTML', 'disable_web_page_preview' => true]);
    ok200();
}

// на любое другое сообщение — подсказка
tg_api('sendMessage', ['chat_id' => $chat_id, 'text' => stars_help_text($site), 'parse_mode' => 'HTML', 'disable_web_page_preview' => true]);
ok200();
