<?php
/*
 * Сюда Platega возвращает покупателя после оплаты. Если уведомление ещё не пришло — сами спрашиваем статус
 * у Platega и включаем подписку (так всё работает, даже если адрес уведомлений в кабинете не указан).
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';

$user = require_user();
$id = (string)($_GET['order'] ?? ($_SESSION['last_order'] ?? ''));
$order = load_json('orders.json', [])[$id] ?? null;
if (!$order || $order['login'] !== $user['login']) redirect('./#pricing');

$order = order_check($order['id']);
$user = current_user();
$plan = user_plan($user);
$p = plans()[$order['plan']];
$paid = $order['status'] === 'paid';
$wait = !$paid && in_array($order['status'], ['new', 'pending'], true) && empty($_GET['failed']);
page_head($paid ? 'Оплата прошла — Rai' : 'Оплата — Rai', $user);
?>
<main class="auth pay">
  <section class="panel result <?= $paid ? 'ok' : ($wait ? 'wait' : 'fail') ?>">
    <div class="result-icon" aria-hidden="true"><?= $paid ? '✓' : ($wait ? '…' : '!') ?></div>
    <?php if ($paid): ?>
      <h1>Rai <?= h($p['name']) ?> подключён</h1>
      <p>Спасибо! Подписка действует <b><?= until_text($plan['until']) ?></b>.
        <?= $p['neuro_day'] ? 'Нейросеть: ' . $p['neuro_day'] . ' сообщений в день.' : 'Нейросеть — без ограничений.' ?></p>
      <a class="btn big" href="<?= CHAT_URL ?>">Открыть Rai</a>
    <?php elseif ($wait): ?>
      <h1>Ждём подтверждение оплаты</h1>
      <p class="muted">Обычно это несколько секунд. Страница обновится сама.</p>
      <script>setTimeout(() => location.reload(), 5000);</script>
      <a class="btn ghost" href="<?= CHAT_URL ?>">Вернуться в Rai</a>
    <?php else: ?>
      <h1>Оплата не прошла</h1>
      <p class="muted">Деньги не списаны. Можно попробовать ещё раз или выбрать другой способ.</p>
      <a class="btn big" href="pay.php?plan=<?= h($order['plan']) ?>&amp;months=<?= (int)$order['months'] ?>">Попробовать снова</a>
    <?php endif; ?>
    <p class="muted small">Заказ <?= h($order['id']) ?> · <?= rub($order['amount']) ?></p>
  </section>
</main>
<?php page_foot();
