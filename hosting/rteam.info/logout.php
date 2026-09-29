<?php
/* Выход по ссылке (с подтверждением формой — чтобы чужой сайт не мог разлогинить по картинке). */
require __DIR__ . '/config.php';
$user = current_user();
if (!$user) redirect('index.php');
page_head('Выход — Rteam', $user);
?>
<main class="auth"><section class="panel">
  <h1>Выйти из аккаунта?</h1>
  <form method="post" action="auth.php" class="row">
    <input type="hidden" name="csrf" value="<?= h(csrf_token()) ?>"><input type="hidden" name="action" value="logout">
    <button class="btn" type="submit">Выйти</button><a class="btn ghost" href="account.php">Отмена</a>
  </form>
</section></main>
<?php page_foot();
