<?php
/*
 * Купить подписку: форма с главной (тариф и срок) → заказ → страница оплаты Platega.
 * Подписка включается, когда Platega пришлёт уведомление (pay_callback.php) или покупатель вернётся (pay_return.php).
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';

$plan = (string)($_REQUEST['plan'] ?? '');
$months = (int)($_REQUEST['months'] ?? 1);
if (!in_array($plan, PAID_PLANS, true)) redirect('./#pricing');
if (!isset(PLAN_PERIODS[$months])) $months = 1;

$user = current_user();
if (!$user) {
    // после входа вернёмся сюда же с тем же тарифом
    redirect('login.php?tab=register&next=' . rawurlencode('pay.php?plan=' . $plan . '&months=' . $months));
}

$p = plans()[$plan];
$amount = plan_price($plan, $months);
$error = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_ok()) {
        $error = 'Страница устарела — нажмите «Оплатить» ещё раз.';
    } elseif (rate_limited('pay:' . $user['login'], 10, 600)) {
        $error = 'Слишком много попыток оплаты. Подождите несколько минут.';
    } elseif (!platega_ready()) {
        $error = 'Оплата скоро заработает: владелец сайта ещё не подключил Platega. Напишите в поддержку — подписку можно выдать вручную.';
    } else {
        $id = 'r' . date('ymd') . strtoupper(bin2hex(random_bytes(5)));
        $order = [
            'id' => $id, 'login' => $user['login'], 'plan' => $plan, 'months' => $months, 'amount' => $amount,
            'title' => 'Rai ' . $p['name'] . ' — ' . ($months >= 12 ? '12 месяцев' : '1 месяц') . ' (' . $user['login'] . ')',
            'status' => 'new', 'created' => time(), 'transaction' => null,
        ];
        update_json('orders.json', function (&$orders) use ($order) {
            $orders[$order['id']] = $order;
            if (count($orders) > 5000) $orders = array_slice($orders, -5000, null, true);
        });
        list($link, $transaction, $fail) = platega_create($order);
        if ($link) {
            order_update($id, ['status' => 'pending', 'transaction' => $transaction]);
            $_SESSION['last_order'] = $id;
            redirect($link);
        }
        order_update($id, ['status' => 'error', 'error' => mb_substr((string)$fail, 0, 300)]);
        $error = 'Не удалось создать платёж: ' . $fail . '. Попробуйте ещё раз чуть позже.';
    }
}

$current = user_plan($user);
$csrf = csrf_token();
page_head('Оплата — Rai ' . $p['name'], $user);
?>
<main class="auth pay">
  <section class="panel">
    <span class="tag">Подписка</span>
    <h1>Rai <?= h($p['name']) ?></h1>
    <p class="muted"><?= h($p['tagline']) ?></p>
    <ul class="checks">
      <?php foreach ($p['features'] as $f): ?><li><?= h($f) ?></li><?php endforeach; ?>
    </ul>
    <div class="periods" role="radiogroup" aria-label="Срок">
      <?php foreach (PLAN_PERIODS as $m => $label): ?>
        <a role="radio" aria-checked="<?= $m === $months ? 'true' : 'false' ?>" href="?plan=<?= h($plan) ?>&amp;months=<?= $m ?>">
          <b><?= $m >= 12 ? '12 месяцев' : '1 месяц' ?></b><span><?= rub(plan_price($plan, $m)) ?><?= $m >= 12 ? ' · −' . YEAR_DISCOUNT . '%' : '' ?></span></a>
      <?php endforeach; ?>
    </div>
    <?php if ($current['key'] !== 'free'): ?>
      <p class="muted small">Сейчас у вас «<?= h(plans()[$current['key']]['name']) ?>» до <?= ru_date($current['until']) ?>.
        <?= $current['key'] === $plan ? 'Оплата продлит подписку с этой даты.' : 'Новый тариф начнёт действовать сразу после оплаты.' ?></p>
    <?php endif; ?>
    <?php if ($error): ?><p class="error" role="alert"><?= h($error) ?></p><?php endif; ?>
    <form method="post" class="form">
      <input type="hidden" name="csrf" value="<?= h($csrf) ?>">
      <input type="hidden" name="plan" value="<?= h($plan) ?>"><input type="hidden" name="months" value="<?= $months ?>">
      <button class="btn big" type="submit">Оплатить <?= rub($amount) ?></button>
    </form>
    <p class="muted small">Оплата через Platega: СБП, банковские карты. Аккаунт: <b><?= h($user['login']) ?></b>.
      Подписка включится сразу после оплаты. <a href="./#pricing">Все тарифы</a></p>
  </section>
</main>
<?php page_foot();
