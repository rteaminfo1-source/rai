<?php
require __DIR__ . '/config.php';
require_once __DIR__ . '/_roles.php'; // настройки входа через Discord

$users = load_json("users.json", []);
$settings = load_json("settings.json", []);
$discord_on = rt_discord_login_ready($settings);
$error = "";

if (!empty($_SESSION["user"])) {
    header("Location: index.php");
    exit;
}

if (!rteam_storage_writable()) {
    $error = "Сервер не может записывать данные (users.json). Обратитесь к администратору хостинга: нужны права на запись в папку сайта.";
}

if (empty($error) && isset($_POST["action"]) && $_POST["action"] === "register") {
    $login = trim($_POST["login"] ?? "");
    $pass  = trim($_POST["password"] ?? "");
    $pass2 = trim($_POST["password2"] ?? "");

    if ($login === "" || $pass === "") {
        $error = "Заполните все поля.";
    } elseif (!preg_match('/^[a-zA-Z0-9_\.]{3,32}$/', $login)) {
        $error = "Логин: 3–32 символа, только латиница, цифры, «_» и «.».";
    } elseif (strlen($pass) < 6) {
        $error = "Пароль должен быть не короче 6 символов.";
    } elseif ($pass !== $pass2) {
        $error = "Пароли не совпадают.";
    } elseif (isset($users[$login])) {
        $error = "Такой логин уже занят.";
    } else {
        $users[$login] = [
            "password" => $pass,
            "role"     => "Пользователь",
        ];
        save_json("users.json", $users);
        rteam_log("register", "Регистрация: $login");
        header("Location: login.php?registered=1");
        exit;
    }
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Регистрация — RTeam</title>
<?php require __DIR__ . '/partials/auth_theme.php'; ?>
<style>
.btn-discord { background: #5865F2 !important; color: #fff !important; border-color: #5865F2 !important; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; text-decoration: none; }
.btn-discord:hover { filter: brightness(1.08); }
</style>
</head>
<body>
<div class="auth-shell">
    <div class="auth-side">
        <div>
            <div class="auth-logo">RTEAM</div>
            <h2>Присоединяйтесь<br>к команде</h2>
            <p>Создайте аккаунт, чтобы подавать заявки в команду, участвовать в розыгрышах и открывать «Золотой билет RTeam».</p>
            <ul>
                <li>Регистрация за 15 секунд</li>
                <li>Или один клик через Google<?= $discord_on ? " или Discord" : "" ?></li>
                <li>Единый вход RTeam для других проектов</li>
            </ul>
        </div>
        <a href="index.php" class="auth-back">← На главную</a>
    </div>

    <div class="auth-main">
        <div class="auth-tabs">
            <a href="login.php" class="auth-tab">Вход</a>
            <span class="auth-tab active">Регистрация</span>
        </div>

        <h1 class="auth-title">Создать аккаунт</h1>
        <p class="auth-subtitle">Придумайте логин и пароль, либо зарегистрируйтесь через Google<?= $discord_on ? " или Discord" : "" ?> в один клик.</p>
        <?php if ($error): ?><div class="error-box"><?=htmlspecialchars($error)?></div><?php endif; ?>

        <a href="google_start.php?mode=register" class="btn btn-google">
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.9v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.17.29-1.7V4.97H.9A9 9 0 0 0 0 9c0 1.45.35 2.83.9 4.03l3.05-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .9 4.97l3.05 2.33C4.66 5.17 6.65 3.58 9 3.58z"/></svg>
            Зарегистрироваться через Google
        </a>
        <?php if ($discord_on): ?>
        <a href="discord_auth.php?mode=register" class="btn btn-discord">
            <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M20.32 4.37A19.8 19.8 0 0 0 15.4 2.84a.07.07 0 0 0-.08.04c-.21.38-.45.87-.61 1.25a18.3 18.3 0 0 0-5.49 0 12.6 12.6 0 0 0-.62-1.25.08.08 0 0 0-.08-.04 19.7 19.7 0 0 0-4.92 1.53.07.07 0 0 0-.03.03C.53 9.05-.32 13.58.1 18.06a.08.08 0 0 0 .03.05 19.9 19.9 0 0 0 6 3.03.08.08 0 0 0 .08-.03c.46-.63.87-1.3 1.23-1.99a.08.08 0 0 0-.04-.1 13.1 13.1 0 0 1-1.87-.9.08.08 0 0 1-.01-.12l.37-.29a.07.07 0 0 1 .08-.01c3.93 1.79 8.18 1.79 12.06 0a.07.07 0 0 1 .08 0l.37.3a.08.08 0 0 1 0 .12c-.6.35-1.22.65-1.87.89a.08.08 0 0 0-.04.11c.36.7.77 1.36 1.23 1.99a.08.08 0 0 0 .08.03 19.8 19.8 0 0 0 6-3.03.08.08 0 0 0 .04-.05c.5-5.18-.84-9.67-3.55-13.66a.06.06 0 0 0-.03-.03zM8.02 15.33c-1.18 0-2.16-1.09-2.16-2.42s.96-2.42 2.16-2.42c1.21 0 2.18 1.1 2.16 2.42 0 1.33-.96 2.42-2.16 2.42zm7.97 0c-1.18 0-2.15-1.09-2.15-2.42s.95-2.42 2.15-2.42c1.21 0 2.18 1.1 2.16 2.42 0 1.33-.95 2.42-2.16 2.42z"/></svg>
            Зарегистрироваться через Discord
        </a>
        <?php endif; ?>
        <div class="divider"><span>или через логин и пароль</span></div>

        <form method="POST">
            <input type="hidden" name="action" value="register">
            <label class="field-label">Логин</label>
            <input type="text" name="login" placeholder="Латиница, цифры, «_», «.»" required>
            <label class="field-label">Пароль</label>
            <input type="password" name="password" placeholder="Минимум 6 символов" required>
            <label class="field-label">Повторите пароль</label>
            <input type="password" name="password2" placeholder="Ещё раз пароль" required>
            <button class="btn">Зарегистрироваться</button>
        </form>
        <a href="login.php" class="muted-link">Уже есть аккаунт? Войти</a>
    </div>
</div>
</body>
</html>