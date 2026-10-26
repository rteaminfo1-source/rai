<?php
/*
 * Купить подписку: форма с главной (тариф и срок) → заказ → страница оплаты Platega.
 * Подписка включается, когда Platega пришлёт уведомление (pay_callback.php) или покупатель вернётся (pay_return.php).
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';
require __DIR__ . '/stars.php';

$plan = (string)($_REQUEST['plan'] ?? '');
$months = (int)($_REQUEST['months'] ?? 1);
if (!in_array($plan, PAID_PLANS, true)) redirect('./#pricing');
if (!isset(PLAN_PERIODS[$months])) $months = 1;

$user = current_user();
if (!$user) {
    // после входа вернёмся сюда же с тем же тарифом
    redirect('login.php?tab=register&next=' . rawurlencode('pay.php?plan=' . $plan . '&months=' . $months . (!empty($_REQUEST['promo']) ? '&promo=' . rawurlencode((string)$_REQUEST['promo']) : '')));
}

$p = plans()[$plan];
$promo = promo_code($_REQUEST['promo'] ?? '');
$offer = plan_offer($plan, $months, $promo);
$amount = $offer['price'];
$stars = stars_ready() ? (int)$offer['stars'] : 0;   // звёзды — от цены со скидкой, + комиссия Telegram
$error = null;

// Оплата звёздами Telegram: создаём заказ и уводим пользователя в бота (оплата идёт в Telegram).
if (($_GET['stars'] ?? '') === '1') {
    if (!$stars) {
        $error = 'Этот тариф пока нельзя оплатить звёздами Telegram.';
    } elseif ($promo !== '' && $offer['promo_error'] && !$offer['promo']) {
        $error = $offer['promo_error'];
    } elseif (rate_limited('stars:' . $user['login'], 15, 600)) {
        $error = 'Слишком много попыток. Подождите пару минут.';
    } else {
        $link = stars_link($user['login'], $plan, $months, (string)($offer['promo'] ?? ''));
        if ($link) redirect($link);
        $error = 'Не удалось создать оплату звёздами. Попробуйте ещё раз.';
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_ok()) {
        $error = 'Страница устарела — нажмите «Оплатить» ещё раз.';
    } elseif (rate_limited('pay:' . $user['login'], 10, 600)) {
        $error = 'Слишком много попыток оплаты. Подождите несколько минут.';
    } elseif (!platega_ready()) {
        $error = 'Оплата скоро заработает: владелец сайта ещё не подключил Platega. Напишите в поддержку — подписку можно выдать вручную.';
    } elseif ($promo !== '' && $offer['promo_error'] && !$offer['promo']) {
        $error = $offer['promo_error'];
    } else {
        $id = 'r' . date('ymd') . strtoupper(bin2hex(random_bytes(5)));
        $order = [
            'id' => $id, 'login' => $user['login'], 'plan' => $plan, 'months' => $months, 'amount' => $amount,
            'base' => $offer['base'], 'discount' => $offer['percent'], 'promo' => $offer['promo'],
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
        <?php $o = plan_offer($plan, $m, $promo); ?>
        <a role="radio" aria-checked="<?= $m === $months ? 'true' : 'false' ?>" href="?plan=<?= h($plan) ?>&amp;months=<?= $m ?><?= $promo !== '' ? '&amp;promo=' . h(rawurlencode($promo)) : '' ?>">
          <b><?= $m >= 12 ? '12 месяцев' : '1 месяц' ?></b><span><?php if ($o['percent']): ?><s><?= rub($o['base']) ?></s> <?php endif; ?><?= rub($o['price']) ?><?= $m >= 12 ? ' · −' . YEAR_DISCOUNT . '%' : '' ?></span></a>
      <?php endforeach; ?>
    </div>
    <?php if ($current['key'] !== 'free'): ?>
      <p class="muted small">Сейчас у вас «<?= h(plans()[$current['key']]['name']) ?>» <?= until_text($current['until']) ?>.
        <?= $current['key'] === $plan ? 'Оплата продлит подписку с этой даты.' : 'Новый тариф начнёт действовать сразу после оплаты.' ?></p>
    <?php endif; ?>
    <?php if ($offer['percent']): ?>
      <p class="sale-note">🏷 <b><?= h($offer['title']) ?>: −<?= (int)$offer['percent'] ?>%</b><?= !empty($offer['until']) ? ' · до ' . h(ru_date($offer['until'])) : '' ?>
        <span class="muted small">Без скидки — <s><?= rub($offer['base']) ?></s></span></p>
    <?php endif; ?>
    <form method="get" class="promo-form">
      <input type="hidden" name="plan" value="<?= h($plan) ?>"><input type="hidden" name="months" value="<?= $months ?>">
      <input type="text" name="promo" value="<?= h($promo) ?>" placeholder="Промокод" maxlength="32" autocomplete="off" aria-label="Промокод">
      <button class="btn small ghost" type="submit">Применить</button>
    </form>
    <?php if ($promo !== '' && $offer['promo_error']): ?><p class="error small"><?= h($offer['promo_error']) ?></p><?php endif; ?>
    <?php if ($error): ?><p class="error" role="alert"><?= h($error) ?></p><?php endif; ?>
    <form method="post" class="form">
      <input type="hidden" name="csrf" value="<?= h($csrf) ?>">
      <input type="hidden" name="plan" value="<?= h($plan) ?>"><input type="hidden" name="months" value="<?= $months ?>">
      <input type="hidden" name="promo" value="<?= h($offer['promo'] ?? '') ?>">
      <button class="btn big" type="submit">Оплатить <?= rub($amount) ?></button>
    </form>
    <?php if ($stars > 0): ?>
      <p class="muted small" style="text-align:center;margin:14px 0 8px">— или —</p>
      <a class="btn big stars-btn" href="?plan=<?= h($plan) ?>&amp;months=<?= $months ?>&amp;stars=1<?= !empty($offer['promo']) ? '&amp;promo=' . h(rawurlencode($offer['promo'])) : '' ?>"
         style="display:block;text-align:center;background:linear-gradient(135deg,#2aabee,#229ed9);border-color:#229ed9;color:#fff">
        Оплатить Telegram Stars · <?= (int)$stars ?> ⭐<?php if ($offer['percent'] && $offer['stars_base'] > $stars): ?> <s style="opacity:.7"><?= (int)$offer['stars_base'] ?> ⭐</s><?php endif; ?></a>
      <p class="muted small stars-note">⭐ При оплате звёздами к цене добавляется <b><?= stars_commission() ?>% — это комиссия Telegram</b>:
        <?= rub($amount) ?> + <?= stars_commission() ?>% = <?= rub($offer['stars_rub']) ?> ≈ <b><?= (int)$stars ?> ⭐</b>
        (1 ⭐ ≈ <?= h(str_replace('.', ',', (string)stars_rate())) ?> ₽).<?= $offer['percent'] ? ' Скидка −' . (int)$offer['percent'] . '% действует и при оплате звёздами.' : ' Скидки и промокоды действуют и при оплате звёздами.' ?>
        Откроется Telegram (@<?= h(stars_bot_username()) ?>), подписка включится сразу после оплаты.</p>
    <?php endif; ?>
    <p class="muted small">Оплата через Platega: СБП, банковские карты. Аккаунт: <b><?= h($user['login']) ?></b>.
      Подписка включится сразу после оплаты. <a href="./#pricing">Все тарифы</a></p>
  </section>
</main>
<?php page_foot();
