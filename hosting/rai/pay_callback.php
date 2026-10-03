<?php
/*
 * Уведомление Platega об оплате (callback). Адрес укажите в кабинете Platega:
 *   https://rai.rteam.info/pay_callback.php
 * Platega присылает свои X-MerchantId и X-Secret — сверяем их, затем ещё раз спрашиваем статус платежа у API
 * (подделать уведомление без ключа нельзя, а сумма и статус берутся из самой Platega).
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';

function done($code, $text) {
    http_response_code($code);
    header('Content-Type: text/plain; charset=utf-8');
    echo $text;
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') done(405, 'POST only');
if (!platega_ready()) done(503, 'not configured');

$merchant = (string)($_SERVER['HTTP_X_MERCHANTID'] ?? '');
$secret = (string)($_SERVER['HTTP_X_SECRET'] ?? '');
if (!hash_equals((string)PLATEGA_MERCHANT_ID, $merchant) || !hash_equals((string)PLATEGA_SECRET, $secret)) done(401, 'bad credentials');

$data = json_decode((string)file_get_contents('php://input'), true);
if (!is_array($data)) done(400, 'bad json');
$transaction = (string)($data['id'] ?? ($data['transactionId'] ?? ''));
$order_id = (string)($data['payload'] ?? '');

$orders = load_json('orders.json', []);
$order = $orders[$order_id] ?? null;
if (!$order) {  // payload потерялся — ищем по номеру платежа
    foreach ($orders as $o) if ($transaction !== '' && ($o['transaction'] ?? '') === $transaction) { $order = $o; break; }
}
if (!$order) done(200, 'unknown order');  // 200 — чтобы Platega не повторяла чужие уведомления
if (!empty($order['transaction']) && $transaction !== '' && $order['transaction'] !== $transaction) done(400, 'transaction mismatch');

// Статус и сумму берём из API (а не только из тела уведомления)
list($status, $amount) = platega_status($order['transaction'] ?: $transaction);
if ($status === null) $status = strtoupper((string)($data['status'] ?? ''));
if ($amount === null && isset($data['amount'])) $amount = (float)$data['amount'];

if ($status === 'CONFIRMED') {
    $result = order_confirm($order['id'], $amount);
    done(200, $result && $result['status'] === 'paid' ? 'OK' : 'amount mismatch');
}
if (in_array($status, ['CANCELED', 'CANCELLED', 'FAILED', 'EXPIRED'], true) && $order['status'] !== 'paid') {
    order_update($order['id'], ['status' => 'canceled']);
} elseif ($status === 'CHARGEBACKED' && $order['status'] === 'paid') {
    order_update($order['id'], ['status' => 'refunded']);
    set_subscription($order['login'], 'free', 0, 'platega', 'Возврат платежа ' . $order['id']);
    sub_log('refund', $order['login'], $order['plan'], 0, 'Возврат в Platega · заказ ' . $order['id']);
}
done(200, 'OK');
