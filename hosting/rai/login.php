<?php
/* Вход и регистрация в аккаунт Rai: логин и пароль или Google. Аккаунт подходит и для AI Studio. */
require __DIR__ . '/config.php';

// Куда вернуться после входа: из ссылки, а после ошибки входа — из сессии
$next = safe_next($_GET['next'] ?? (isset($_GET['error']) || isset($_GET['tab']) ? ($_SESSION['next'] ?? './') : './'));
if (current_user()) redirect($next);
$_SESSION['next'] = $next;  // понадобится и после входа через Google

$tab = ($_GET['tab'] ?? '') === 'register' ? 'register' : 'login';
$errors = [
    'login' => 'Неверный логин или пароль.', 'google_only' => 'Этот аккаунт создан через Google — войдите кнопкой Google.',
    'username' => 'Логин: 3–20 символов — латинские буквы (маленькие), цифры и дефис.',
    'password' => 'Пароль должен быть не короче 8 символов.', 'email' => 'Похоже, почта написана с ошибкой.',
    'taken' => 'Этот логин уже занят — выберите другой.', 'email_taken' => 'Эта почта уже зарегистрирована — войдите.',
    'too_many' => 'Слишком много попыток. Подождите пару минут.', 'csrf' => 'Страница устарела — попробуйте ещё раз.',
    'google' => 'Google не подтвердил вход. Попробуйте ещё раз.', 'google_cancel' => 'Вход через Google отменён.',
    'google_off' => 'Вход через Google ещё не настроен: впишите секрет в config.php на хостинге.',
    'deleted' => 'Аккаунт удалён.', 'sso' => 'Сначала войдите в аккаунт Rai.',
    'banned' => 'Аккаунт заблокирован за нарушение правил Rai. Если это ошибка — напишите в поддержку.',
];
$error = $errors[$_GET['error'] ?? ''] ?? null;
$sso = strpos($next, 'sso.php') === 0;
$csrf = csrf_token();
page_head($tab === 'register' ? 'Регистрация — Rai' : 'Вход — Rai');
?>
<main class="auth">
  <section class="panel" aria-label="Вход и регистрация">
    <h1><?= $tab === 'register' ? 'Регистрация' : 'Вход в Rai' ?></h1>
    <?php if ($sso): ?><p class="muted">После входа вы вернётесь в AI Studio.</p><?php endif; ?>
    <div class="tabs" role="tablist">
      <a role="tab" href="?tab=login" aria-selected="<?= $tab === 'login' ? 'true' : 'false' ?>">Вход</a>
      <a role="tab" href="?tab=register" aria-selected="<?= $tab === 'register' ? 'true' : 'false' ?>">Регистрация</a>
    </div>
    <a class="btn google" href="google_start.php">
      <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.7 6c4.5-4.2 6.9-10.3 6.9-17.7z"/><path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.7-6c-2.2 1.5-5 2.3-8.2 2.3-6.2 0-11.5-4.1-13.4-9.9l-7.9 6.1C6.6 42.6 14.6 48 24 48z"/></svg>
      <?= $tab === 'register' ? 'Регистрация через Google' : 'Войти через Google' ?></a>
    <div class="or">или</div>
    <?php if ($error): ?><p class="error" role="alert"><?= h($error) ?></p><?php endif; ?>
    <?php if ($tab === 'login'): ?>
      <form method="post" action="auth.php" class="form">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="login">
        <label class="field">Логин или почта<input name="login" autocomplete="username" required></label>
        <label class="field">Пароль<input name="password" type="password" autocomplete="current-password" required></label>
        <button class="btn" type="submit">Войти</button>
      </form>
      <p class="muted small">Нет аккаунта? <a href="?tab=register">Зарегистрируйтесь</a> — это бесплатно.</p>
    <?php else: ?>
      <form method="post" action="auth.php" class="form">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="register">
        <label class="field">Логин
          <input name="login" required minlength="3" maxlength="20" pattern="[a-z0-9][a-z0-9\-]{1,18}[a-z0-9]"
                 title="Маленькие латинские буквы, цифры и дефис" autocomplete="username" placeholder="например, artem">
          <small>Он же — адрес вашего сайта в AI Studio: aistudio.rteam.info/sites/логин/</small></label>
        <label class="field">Как вас зовут<input name="name" maxlength="60" autocomplete="name"></label>
        <label class="field">Почта (необязательно)<input name="email" type="email" autocomplete="email"></label>
        <label class="field">Пароль (от 8 символов)<input name="password" type="password" minlength="8" required autocomplete="new-password"></label>
        <button class="btn" type="submit">Создать аккаунт</button>
        <p class="muted small">Регистрируясь, вы принимаете <a href="terms.php">Пользовательское соглашение</a>,
          <a href="rules.php">Правила</a> и <a href="privacy.php">Политику конфиденциальности</a>.</p>
      </form>
      <p class="muted small">Уже есть аккаунт? <a href="?tab=login">Войдите</a>.</p>
    <?php endif; ?>
  </section>
</main>
<?php page_foot();
