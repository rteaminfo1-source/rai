<?php
/* AI Studio Rteam — главная: что это, вход и регистрация. */
require __DIR__ . '/config.php';
if (current_user()) redirect('studio.php');

$errors = [
    'sso' => 'Не получилось войти: ссылка устарела. Нажмите «Войти» ещё раз.',
    'sso_off' => 'Вход ещё не настроен: впишите одинаковый SSO_SECRET в config.php студии и сайта rai.rteam.info.',
    'csrf' => 'Страница устарела — попробуйте ещё раз.',
];
$error = $errors[$_GET['error'] ?? ''] ?? null;
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Studio Rteam</title>
<meta name="description" content="Опишите сайт словами — ИИ соберёт его и опубликует. API-ключи и хостинг для проектов Rteam.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;700;800&family=Onest:wght@400;500;600;700&family=JetBrains+Mono&display=swap">
<meta name="theme-color" content="#07070b">
<?php include __DIR__ . '/assets/style.php'; ?>
</head>
<body>
<header class="topbar">
  <a class="brand" href="index.php"><i>✦</i>AI <span>Studio</span></a>
  <nav>
    <a href="<?= h(RAI_URL) ?>">Rai — основной ИИ</a>
    <a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>
  </nav>
</header>

<main class="landing">
  <section>
    <span class="badge fade"><b>ИИ</b> Сайт по описанию — за минуту</span>
    <h1 class="fade d1">Опишите сайт — <span class="grad-text">ИИ</span> его соберёт</h1>
    <p class="lead fade d2">AI Studio от Rteam: напишите словами, какой сайт нужен, и ИИ студии создаст его, поправит по вашим
      просьбам и опубликует по адресу <span class="mono">aistudio.rteam.info/sites/ваше-имя/</span>.</p>
    <ol class="steps fade d3">
      <li>Войдите аккаунтом Rai — логин станет адресом вашего сайта.</li>
      <li>Напишите, например: «сайт кофейни «Зерно» в тёмных тонах с меню, отзывами и контактами».</li>
      <li>Попросите поправить: «добавь раздел цены», «сделай синим», «переименуй в …».</li>
      <li>Нажмите «Опубликовать». Нужен API — получите ключ в студии.</li>
    </ol>
    <p class="muted fade d3">Вопросы задавайте основному ИИ — <a href="<?= h(RAI_URL) ?>">Rai</a>, он встроен и в студию.
      Исходный код — на <a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>.</p>
  </section>

  <section class="panel sso fade d2" aria-label="Вход">
    <h2>Вход в студию</h2>
    <p class="muted" style="margin:0">Один аккаунт для Rai и AI Studio. Логин аккаунта станет адресом вашего сайта.</p>
    <?php if ($error): ?><p class="error"><?= h($error) ?></p><?php endif; ?>
    <a class="btn" href="sso_start.php">Войти через аккаунт Rai →</a>
    <a class="btn ghost" href="<?= h(ACCOUNT_URL) ?>/login.php?tab=register">Создать аккаунт в Rai</a>
    <p class="muted" style="margin:0;font-size:13px">Можно войти и через Google — на странице входа Rai.</p>
  </section>
</main>
<footer class="foot"><span>© <?= date('Y') ?> Rteam</span><a href="<?= h(RAI_URL) ?>">rai.rteam.info</a><a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a></footer>
</body>
</html>
