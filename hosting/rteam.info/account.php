<?php
/* Личный кабинет: профиль, пароль, Google, сервисы, выход и удаление аккаунта. */
require __DIR__ . '/config.php';
$user = require_user();
$csrf = csrf_token();
$flash = $_SESSION['flash'] ?? null;
unset($_SESSION['flash']);
$oks = ['profile' => 'Профиль сохранён.', 'password' => 'Пароль изменён.', 'unlinked' => 'Google отвязан.', 'google' => 'Google привязан к аккаунту.'];
$errors = [
    'email' => 'Похоже, почта написана с ошибкой.', 'email_taken' => 'Эта почта уже у другого аккаунта.',
    'current' => 'Текущий пароль неверный.', 'password' => 'Новый пароль должен быть не короче 8 символов.',
    'need_password' => 'Сначала задайте пароль, иначе вы не сможете войти без Google.',
    'confirm' => 'Для удаления впишите свой логин точно.', 'too_many' => 'Слишком много попыток. Подождите немного.',
    'google_taken' => 'Этот Google уже привязан к другому аккаунту.',
];
$ok = $flash ?: ($oks[$_GET['ok'] ?? ''] ?? null);
$error = $errors[$_GET['error'] ?? ''] ?? null;
page_head('Личный кабинет — Rteam', $user);
?>
<main class="account">
  <section class="panel profile-head">
    <?= avatar_html($user, 'ava big') ?>
    <div>
      <h1><?= h($user['name'] ?: $user['login']) ?></h1>
      <p class="muted">@<?= h($user['login']) ?><?= $user['email'] ? ' · ' . h($user['email']) : '' ?> · с нами с <?= date('d.m.Y', $user['created']) ?></p>
    </div>
    <form method="post" action="auth.php" class="logout">
      <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="logout">
      <button class="btn ghost" type="submit">Выйти</button>
    </form>
  </section>
  <?php if ($ok): ?><p class="okmsg" role="status"><?= h($ok) ?></p><?php endif; ?>
  <?php if ($error): ?><p class="error" role="alert"><?= h($error) ?></p><?php endif; ?>

  <section class="cards" aria-label="Ваши сервисы">
    <a class="card" href="<?= h(RAI_URL) ?>"><span class="tag">Чат</span><h2>Rai</h2><p>Спросить, перевести, нарисовать, сделать презентацию.</p><span class="go">Открыть →</span></a>
    <a class="card" href="<?= h(RAI_CODE_URL) ?>"><span class="tag">Код</span><h2>Rai Code</h2><p>Писать, запускать и исправлять программы с ИИ.</p><span class="go">Открыть →</span></a>
    <a class="card" href="<?= h(STUDIO_URL) ?>/sso_start.php"><span class="tag">Сайты</span><h2>AI Studio</h2><p>Ваш сайт: aistudio.rteam.info/sites/<?= h($user['login']) ?>/ и API-ключи.</p><span class="go">Войти →</span></a>
  </section>

  <div class="grid2">
    <section class="panel" aria-labelledby="h-prof">
      <h2 id="h-prof">Профиль</h2>
      <form method="post" action="auth.php" class="form">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="profile">
        <label class="field">Имя<input name="name" maxlength="60" value="<?= h($user['name']) ?>" autocomplete="name"></label>
        <label class="field">Почта<input name="email" type="email" value="<?= h($user['email']) ?>" autocomplete="email"></label>
        <button class="btn" type="submit">Сохранить</button>
      </form>
    </section>

    <section class="panel" aria-labelledby="h-pass">
      <h2 id="h-pass"><?= empty($user['password']) ? 'Задать пароль' : 'Сменить пароль' ?></h2>
      <?php if (empty($user['password'])): ?><p class="muted small">Вы входите через Google. С паролем сможете входить и по логину <b><?= h($user['login']) ?></b>.</p><?php endif; ?>
      <form method="post" action="auth.php" class="form">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="password">
        <input type="text" name="username" value="<?= h($user['login']) ?>" autocomplete="username" hidden>
        <?php if (!empty($user['password'])): ?>
          <label class="field">Текущий пароль<input name="current" type="password" required autocomplete="current-password"></label>
        <?php endif; ?>
        <label class="field">Новый пароль (от 8 символов)<input name="new" type="password" minlength="8" required autocomplete="new-password"></label>
        <button class="btn" type="submit">Сохранить пароль</button>
      </form>
    </section>

    <section class="panel" aria-labelledby="h-google">
      <h2 id="h-google">Google</h2>
      <?php if (!empty($user['google_id'])): ?>
        <p class="muted small">Google привязан: можно входить кнопкой «Войти через Google».</p>
        <form method="post" action="auth.php">
          <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="unlink_google">
          <button class="btn ghost" type="submit">Отвязать Google</button>
        </form>
      <?php else: ?>
        <p class="muted small">Привяжите Google, чтобы входить в один клик.</p>
        <a class="btn google" href="google_start.php?link=1">Привязать Google</a>
      <?php endif; ?>
    </section>

    <section class="panel danger" aria-labelledby="h-del">
      <h2 id="h-del">Удалить аккаунт</h2>
      <p class="muted small">Аккаунт Rteam удалится. Сайт в AI Studio удаляется в самой студии.</p>
      <form method="post" action="auth.php" class="form">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="delete">
        <label class="field"><span>Впишите логин <b><?= h($user['login']) ?></b> для подтверждения</span><input name="confirm" autocomplete="off" required></label>
        <button class="btn danger" type="submit">Удалить навсегда</button>
      </form>
    </section>
  </div>
</main>
<?php page_foot();
