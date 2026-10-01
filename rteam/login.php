<?php
require __DIR__ . '/config.php';
require_once __DIR__ . '/_roles.php'; // роли и права (общий файл с admin.php)

$users    = load_json("users.json", []);
$settings = load_json("settings.json", []);
$error    = "";
$info     = "";

// Страницу входа не кэшируем: иначе хостинг или браузер может показать
// старую форму логина вместо формы кода из бота
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Pragma: no-cache");

if (!empty($_SESSION["user"])) {
    header("Location: index.php");
    exit;
}

/* ВХОД С КОДОМ ИЗ TELEGRAM-БОТА
   Шаг 1: логин и пароль верны → бот присылает код, открывается форма кода.
   Шаг 2: вводим код → вход.
   Логин передаётся вместе с формой кода, а срок кода и число попыток хранятся
   на сервере (2fa_pending.json), поэтому второй шаг не зависит от сессии:
   если хостинг потеряет сессию между шагами, вход всё равно сработает.
   Код живёт 10 минут, на ввод — 5 попыток, потом нужно снова ввести пароль. */
const RT_2FA_TTL = 600;
const RT_2FA_TRIES = 5;

function rteam_2fa_forget($login) {
    $codes = load_json("2fa_codes.json", []);
    $pending = load_json("2fa_pending.json", []);
    if ($login !== "") { unset($codes[$login], $pending[$login]); }
    save_json("2fa_codes.json", $codes);
    save_json("2fa_pending.json", $pending);
    unset($_SESSION["pending_2fa_user"], $_SESSION["pending_2fa_role"], $_SESSION["pending_2fa_time"], $_SESSION["pending_2fa_tries"]);
}
function rteam_2fa_url($login) {
    return "login.php?step=2fa&u=" . urlencode($login);
}

/* Для кого сейчас открыта форма кода */
$pending_login = (string)($_SESSION["pending_2fa_user"] ?? "");
if ($pending_login === "" && ($_GET["step"] ?? "") === "2fa") $pending_login = trim((string)($_GET["u"] ?? ""));
if (isset($_POST["action"]) && in_array($_POST["action"], ["verify_2fa", "cancel_2fa"], true) && trim($_POST["login"] ?? "") !== "") {
    $pending_login = trim($_POST["login"]);
}

/* ОТМЕНА 2FA ВХОДА */
if (isset($_POST["action"]) && $_POST["action"] === "cancel_2fa") {
    rteam_2fa_forget($pending_login);
    header("Location: login.php");
    exit;
}

/* ПОДТВЕРЖДЕНИЕ 2FA КОДА ОТ БОТА */
if (isset($_POST["action"]) && $_POST["action"] === "verify_2fa") {
    $code_input = preg_replace('/\D+/', '', (string)($_POST["code"] ?? "")); // только цифры: пробелы и т.п. не мешают
    $login   = $pending_login;
    $codes   = load_json("2fa_codes.json", []);
    $pending = load_json("2fa_pending.json", []);
    $p       = $pending[$login] ?? null;

    if ($login === "" || !isset($users[$login]) || !isset($codes[$login])) {
        rteam_2fa_forget($login);
        $error = "Запрос кода не найден (возможно, код уже использован). Введите логин и пароль ещё раз.";
    } elseif ($p !== null && time() - (int)($p["time"] ?? 0) > RT_2FA_TTL) {
        rteam_2fa_forget($login);
        $error = "Код устарел. Введите логин и пароль ещё раз — бот пришлёт новый.";
    } elseif (hash_equals((string)$codes[$login], $code_input)) {
        rteam_2fa_forget($login);
        rteam_login_user($login, $users[$login]["role"] ?? "Пользователь");
        rt_track_login_ip($login); // IP входа — для банов в админ-панели
        rteam_log("login", "Вход (2FA Бот): $login");
        header("Location: " . rteam_post_login_redirect());
        exit;
    } else {
        $tries = (int)($p["tries"] ?? 0) + 1;
        if ($tries >= RT_2FA_TRIES) {
            rteam_2fa_forget($login);
            $error = "Слишком много неверных попыток. Введите логин и пароль ещё раз — бот пришлёт новый код.";
        } else {
            $pending[$login] = ["time" => (int)($p["time"] ?? time()), "tries" => $tries];
            save_json("2fa_pending.json", $pending);
            $error = "Неверный код. Введите последний код, который прислал бот. Осталось попыток: " . (RT_2FA_TRIES - $tries) . ".";
        }
    }
}

/* ВХОД (ПЕРВЫЙ ЭТАП: ЛОГИН/ПАРОЛЬ) */
if (isset($_POST["action"]) && $_POST["action"] === "login") {
    $login = trim($_POST["login"] ?? "");
    $pass  = trim($_POST["password"] ?? "");

    if (isset($users[$login]) && isset($users[$login]["password"]) && $users[$login]["password"] === $pass) {
        $role = $users[$login]["role"] ?? "Пользователь";

        // Код из Telegram-бота спрашиваем у тех, кто входит в админ-панель
        // (включая стажёров), но только если Telegram привязан к аккаунту
        // и бот настроен. Без привязки — обычный вход по паролю.
        $is_panel_role = rt_is_staff($role, $login) || in_array($role, rteam_admin_roles());
        $tg_linked     = !empty($users[$login]["tg_id"]) && !empty($settings["bot_token"]);

        if ($is_panel_role && $tg_linked) {
            $code = (string)random_int(100000, 999999);

            $codes = load_json("2fa_codes.json", []);
            $codes[$login] = $code;
            save_json("2fa_codes.json", $codes);
            $pending = load_json("2fa_pending.json", []);
            $pending[$login] = ["time" => time(), "tries" => 0];
            save_json("2fa_pending.json", $pending);

            $_SESSION["pending_2fa_user"] = $login;
            $_SESSION["pending_2fa_role"] = $role;

            $url = "https://api.telegram.org/bot" . $settings["bot_token"] . "/sendMessage";
            $data = ['chat_id' => $users[$login]["tg_id"], 'text' => "🔐 Ваш одноразовый код для входа в панель Rteam:\n\n<b>$code</b>\n\nКод действует 10 минут.", 'parse_mode' => 'HTML'];
            $ch = curl_init($url); curl_setopt($ch, CURLOPT_POST, 1); curl_setopt($ch, CURLOPT_POSTFIELDS, $data); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_setopt($ch, CURLOPT_TIMEOUT, 10); curl_exec($ch); curl_close($ch);
            header("Location: " . rteam_2fa_url($login));
            exit;
        } else {
            rteam_login_user($login, $role);
            rt_track_login_ip($login); // IP входа — для банов в админ-панели
            rteam_log("login", "Вход: $login");
            header("Location: " . rteam_post_login_redirect());
            exit;
        }
    } else {
        $error = "Неверный логин или пароль.";
    }
}

if (isset($_GET["registered"])) $info = "Регистрация прошла успешно — теперь войдите в аккаунт.";
if (isset($_GET["google_new"])) $info = "Мы создали аккаунт через Google и уже вошли вас в систему.";
if (isset($_GET["oauth_error"])) $error = "Не удалось войти через Google. Попробуйте ещё раз.";

// Форму кода показываем, только если для этого логина действительно ждём код
$pending_codes = load_json("2fa_codes.json", []);
$pending_2fa = $pending_login !== "" && isset($pending_codes[$pending_login]);
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход в аккаунт — RTeam</title>
<?php require __DIR__ . '/partials/auth_theme.php'; ?>
</head>
<body>
<div class="auth-shell">
    <div class="auth-side">
        <div>
            <div class="auth-logo">RTEAM</div>
            <h2>Рады видеть<br>вас снова</h2>
            <p>Войдите, чтобы отслеживать заявки, участвовать в розыгрышах и открывать эксклюзивные фишки сайта.</p>
            <ul>
                <li>Быстрый вход через Google</li>
                <li>Код 2FA из Telegram — если бот привязан</li>
                <li>Единый вход RTeam для других проектов</li>
            </ul>
        </div>
        <a href="index.php" class="auth-back">← На главную</a>
    </div>

    <div class="auth-main">
        <div class="auth-tabs">
            <span class="auth-tab active">Вход</span>
            <a href="register.php" class="auth-tab">Регистрация</a>
        </div>

        <?php if ($pending_2fa): ?>
            <h1 class="auth-title">Код подтверждения</h1>
            <p class="auth-subtitle">🔐 К вашему аккаунту привязан Telegram, поэтому для входа в админ-панель нужен код — бот уже прислал его. Не пришёл? Напишите боту команду <b>/code</b>. Код действует 10 минут.</p>
            <?php if ($error): ?><div class="error-box"><?=htmlspecialchars($error)?></div><?php endif; ?>
            <p class="auth-subtitle" style="margin-top:-6px;">Вход для: <b><?=htmlspecialchars($pending_login)?></b></p>
            <form method="POST" action="<?=htmlspecialchars(rteam_2fa_url($pending_login))?>">
                <input type="hidden" name="action" value="verify_2fa">
                <input type="hidden" name="login" value="<?=htmlspecialchars($pending_login)?>">
                <label class="field-label">Код из бота</label>
                <input type="text" name="code" class="otp-input" placeholder="000000" required autocomplete="one-time-code" inputmode="numeric" maxlength="12" autofocus>
                <button class="btn">Подтвердить вход</button>
            </form>
            <form method="POST" action="login.php">
                <input type="hidden" name="action" value="cancel_2fa">
                <input type="hidden" name="login" value="<?=htmlspecialchars($pending_login)?>">
                <button class="btn btn-google" style="margin-top:10px;">Отменить и выйти</button>
            </form>
        <?php else: ?>
            <h1 class="auth-title">Вход в аккаунт</h1>
            <p class="auth-subtitle">Введите логин и пароль, либо продолжите через Google.</p>
            <?php if ($error): ?><div class="error-box"><?=htmlspecialchars($error)?></div><?php endif; ?>
            <?php if ($info): ?><div class="info-box"><?=htmlspecialchars($info)?></div><?php endif; ?>

            <form method="POST">
                <input type="hidden" name="action" value="login">
                <label class="field-label">Логин</label>
                <input type="text" name="login" placeholder="Ваш логин" required>
                <label class="field-label">Пароль</label>
                <input type="password" name="password" placeholder="Ваш пароль" required>
                <button class="btn">Войти</button>
            </form>

            <div class="divider"><span>или</span></div>
            <a href="google_start.php?mode=login" class="btn btn-google">
                <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.9v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.17.29-1.7V4.97H.9A9 9 0 0 0 0 9c0 1.45.35 2.83.9 4.03l3.05-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .9 4.97l3.05 2.33C4.66 5.17 6.65 3.58 9 3.58z"/></svg>
                Войти через Google
            </a>
            <a href="register.php" class="muted-link">Ещё нет аккаунта? Зарегистрироваться</a>
        <?php endif; ?>
    </div>
</div>
</body>
</html>
