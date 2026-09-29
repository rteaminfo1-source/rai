<?php
/* AI Studio Rteam — главная: что это, вход и регистрация. */
require __DIR__ . '/config.php';
if (current_user()) redirect('studio.php');

$tab = ($_GET['tab'] ?? '') === 'register' ? 'register' : 'login';
$errors = [
    'login' => 'Неверный логин или пароль.', 'google_only' => 'Этот аккаунт создан через Google — войдите кнопкой Google.',
    'username' => 'Имя: 3–20 символов — латинские буквы, цифры и дефис. Оно станет адресом вашего сайта.',
    'password' => 'Пароль должен быть не короче 8 символов.', 'email' => 'Похоже, почта написана с ошибкой.',
    'taken' => 'Это имя уже занято — выберите другое.', 'email_taken' => 'Эта почта уже зарегистрирована.',
    'too_many' => 'Слишком много попыток. Подождите пару минут.', 'csrf' => 'Страница устарела — попробуйте ещё раз.',
    'google' => 'Google не подтвердил вход. Попробуйте ещё раз.', 'google_cancel' => 'Вход через Google отменён.',
    'google_off' => 'Вход через Google ещё не настроен: вставьте секрет в config.php.',
];
$error = $errors[$_GET['error'] ?? ''] ?? null;
$csrf = csrf_token();
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Studio Rteam</title>
<meta name="description" content="Опишите сайт словами — ИИ соберёт его и опубликует. API-ключи и хостинг для проектов Rteam.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@700;800&family=Onest:wght@400;500;600&family=JetBrains+Mono&display=swap">
<link rel="stylesheet" href="assets/studio.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="index.php">AI <span>Studio</span></a>
  <nav>
    <a href="<?= h(RAI_URL) ?>">Rai — основной ИИ</a>
    <a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>
  </nav>
</header>

<main class="landing">
  <section>
    <h1>Опишите сайт — <span>ИИ</span> его соберёт</h1>
    <p class="lead">AI Studio от Rteam: напишите словами, какой сайт нужен, и ИИ студии создаст его, поправит по вашим
      просьбам и опубликует по адресу <span class="mono">aistudio.rteam.info/sites/ваше-имя/</span>.</p>
    <ol class="steps">
      <li>Зарегистрируйтесь — имя станет адресом вашего сайта.</li>
      <li>Напишите, например: «сайт кофейни «Зерно» в тёмных тонах с меню, отзывами и контактами».</li>
      <li>Попросите поправить: «добавь раздел цены», «сделай синим», «переименуй в …».</li>
      <li>Нажмите «Опубликовать». Нужен API — получите ключ в студии.</li>
    </ol>
    <p class="muted">Вопросы задавайте основному ИИ — <a href="<?= h(RAI_URL) ?>">Rai</a>, он встроен и в студию.
      Исходный код — на <a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>.</p>
  </section>

  <section class="panel" aria-label="Вход и регистрация">
    <div class="tabs">
      <a href="?tab=login" class="<?= $tab === 'login' ? 'on' : '' ?>">Вход</a>
      <a href="?tab=register" class="<?= $tab === 'register' ? 'on' : '' ?>">Регистрация</a>
    </div>
    <a class="btn google" href="google_start.php">
      <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.6 5.4 2.7 13.3l7.9 6.1C12.5 13.6 17.8 9.5 24 9.5z"/><path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.7 6c4.5-4.2 6.9-10.3 6.9-17.7z"/><path fill="#FBBC05" d="M10.6 28.6c-.5-1.4-.8-3-.8-4.6s.3-3.2.8-4.6l-7.9-6.1C1 16.6 0 20.2 0 24s1 7.4 2.7 10.7l7.9-6.1z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.7-6c-2.2 1.5-5 2.3-8.2 2.3-6.2 0-11.5-4.1-13.4-9.9l-7.9 6.1C6.6 42.6 14.6 48 24 48z"/></svg>
      Войти через Google</a>
    <div class="or">или</div>
    <?php if ($error): ?><p class="error"><?= h($error) ?></p><?php endif; ?>
    <?php if ($tab === 'login'): ?>
      <form method="post" action="auth.php" class="panel" style="padding:0;border:0;background:none">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="login">
        <label class="field">Имя или почта<input name="login" autocomplete="username" required></label>
        <label class="field">Пароль<input name="password" type="password" autocomplete="current-password" required></label>
        <button class="btn" type="submit">Войти</button>
      </form>
    <?php else: ?>
      <form method="post" action="auth.php" class="panel" style="padding:0;border:0;background:none">
        <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="register">
        <label class="field">Имя пользователя (адрес сайта)
          <input name="username" required minlength="3" maxlength="20" pattern="[a-z0-9][a-z0-9\-]{1,18}[a-z0-9]"
                 title="Латинские буквы в нижнем регистре, цифры и дефис" autocomplete="username" placeholder="например, artem"></label>
        <label class="field">Как вас зовут<input name="name" maxlength="60" autocomplete="name"></label>
        <label class="field">Почта (необязательно)<input name="email" type="email" autocomplete="email"></label>
        <label class="field">Пароль (от 8 символов)<input name="password" type="password" minlength="8" required autocomplete="new-password"></label>
        <button class="btn" type="submit">Зарегистрироваться</button>
      </form>
    <?php endif; ?>
  </section>
</main>
<footer class="foot"><span>© <?= date('Y') ?> Rteam</span><a href="<?= h(RAI_URL) ?>">rai.rteam.info</a><a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a></footer>
</body>
</html>
