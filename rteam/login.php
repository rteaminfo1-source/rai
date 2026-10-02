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

/* ВХОД С КОДОМ ИЗ TELEGRAM- ИЛИ DISCORD-БОТА
   Шаг 1: логин и пароль верны → бот присылает код (в Telegram или Discord — что привязано;
   если привязаны оба, пользователь выбирает в кабинете, а на странице кода можно прислать в другое место),
   открывается форма кода.
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
if (isset($_POST["action"]) && in_array($_POST["action"], ["verify_2fa", "cancel_2fa", "resend_2fa"], true) && trim($_POST["login"] ?? "") !== "") {
    $pending_login = trim($_POST["login"]);
}

/* ПРИСЛАТЬ КОД ЕЩЁ РАЗ (туда же или в другое место). Не чаще раза в 20 секунд и не больше 5 раз */
if (isset($_POST["action"]) && $_POST["action"] === "resend_2fa" && $pending_login !== "") {
    $codes   = load_json("2fa_codes.json", []);
    $pending = load_json("2fa_pending.json", []);
    $p       = $pending[$pending_login] ?? null;
    $u       = $users[$pending_login] ?? null;
    $via     = (string)($_POST["via"] ?? "");
    if (!$u || !isset($codes[$pending_login]) || !$p) {
        $error = "Запрос кода не найден. Введите логин и пароль ещё раз.";
    } elseif (!in_array($via, rt_2fa_channels($u, $settings), true)) {
        $error = "Сюда код прислать нельзя.";
    } elseif (time() - (int)($p["sent"] ?? 0) < 20) {
        $error = "Код только что отправлен. Подождите немного перед повтором.";
    } elseif ((int)($p["resends"] ?? 0) >= 5) {
        $error = "Слишком много повторов. Отмените вход и введите пароль ещё раз.";
    } elseif (rt_2fa_deliver($u, $settings, $via, $codes[$pending_login])) {
        $pending[$pending_login] = array_merge($p, ["via" => $via, "sent" => time(), "resends" => (int)($p["resends"] ?? 0) + 1, "failed" => false]);
        save_json("2fa_pending.json", $pending);
        $info = "Код отправлен в " . rt_2fa_label($via) . ".";
    } else {
        $pending[$pending_login] = array_merge($p, ["sent" => time(), "resends" => (int)($p["resends"] ?? 0) + 1]);
        save_json("2fa_pending.json", $pending);
        $error = "Не удалось отправить код в " . rt_2fa_label($via) . ($via === "ds" ? ": бот не может написать вам в ЛС. Проверьте, что вы на сервере RTeam и ЛС открыты." : ". Попробуйте ещё раз.");
    }
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
            $pending[$login] = array_merge((array)$p, ["time" => (int)($p["time"] ?? time()), "tries" => $tries]);
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

        // Код из бота спрашиваем у тех, кто входит в админ-панель (включая стажёров),
        // но только если к аккаунту привязан Telegram или Discord и бот настроен.
        // Без привязки — обычный вход по паролю.
        $is_panel_role = rt_is_staff($role, $login) || in_array($role, rteam_admin_roles());

        if ($is_panel_role && rt_2fa_channels($users[$login], $settings)) {
            rt_2fa_begin($login, $role, $users[$login], $settings);
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
if (isset($_GET["discord_hint"])) $info = "Войдите в аккаунт, а потом в кабинете нажмите «Привязать Discord». Или войдите через Discord — если аккаунта ещё нет, мы его создадим.";
$ds_errors = [
    "denied" => "Вход через Discord отменён.",
    "off"    => "Вход через Discord пока не настроен.",
    "state"  => "Ссылка входа через Discord устарела. Нажмите кнопку ещё раз.",
    "failed" => "Не удалось войти через Discord. Попробуйте ещё раз.",
];
if (isset($_GET["discord_error"])) $error = $ds_errors[$_GET["discord_error"]] ?? $ds_errors["failed"];
$discord_on = rt_discord_login_ready($settings);

// Форму кода показываем, только если для этого логина действительно ждём код
$pending_codes = load_json("2fa_codes.json", []);
$pending_2fa = $pending_login !== "" && isset($pending_codes[$pending_login]);
$p2 = $pending_2fa ? (load_json("2fa_pending.json", [])[$pending_login] ?? []) : [];
$via_now = (string)($p2["via"] ?? "tg");
$via_all = $pending_2fa && isset($users[$pending_login]) ? rt_2fa_channels($users[$pending_login], $settings) : [];
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход в аккаунт — RTeam</title>
<?php require __DIR__ . '/partials/auth_theme.php'; ?>
<style>
.btn-discord { background: #5865F2 !important; color: #fff !important; border-color: #5865F2 !important; margin-top: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; text-decoration: none; }
.btn-discord:hover { filter: brightness(1.08); }
.resend-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.resend-row form { flex: 1; min-width: 150px; margin: 0; }
.resend-row .btn-resend { width: 100%; margin-top: 0; }
</style>
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
                <li>Код 2FA из Telegram или Discord — если бот привязан</li>
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
            <?php if (!empty($p2["failed"])): ?>
                <p class="auth-subtitle">🔐 Для входа в админ-панель нужен код из бота, но отправить его не получилось. Нажмите «Прислать ещё раз» ниже.</p>
            <?php elseif ($via_now === "ds"): ?>
                <p class="auth-subtitle">🔐 К вашему аккаунту привязан Discord, поэтому для входа в админ-панель нужен код — бот RTeam уже прислал его вам в <b>личные сообщения Discord</b>. Код действует 10 минут.</p>
            <?php else: ?>
                <p class="auth-subtitle">🔐 К вашему аккаунту привязан Telegram, поэтому для входа в админ-панель нужен код — бот уже прислал его. Не пришёл? Напишите боту команду <b>/code</b>. Код действует 10 минут.</p>
            <?php endif; ?>
            <?php if ($error): ?><div class="error-box"><?=htmlspecialchars($error)?></div><?php endif; ?>
            <?php if ($info): ?><div class="info-box"><?=htmlspecialchars($info)?></div><?php endif; ?>
            <p class="auth-subtitle" style="margin-top:-6px;">Вход для: <b><?=htmlspecialchars($pending_login)?></b></p>
            <form method="POST" action="<?=htmlspecialchars(rteam_2fa_url($pending_login))?>">
                <input type="hidden" name="action" value="verify_2fa">
                <input type="hidden" name="login" value="<?=htmlspecialchars($pending_login)?>">
                <label class="field-label">Код из бота</label>
                <input type="text" name="code" class="otp-input" placeholder="000000" required autocomplete="one-time-code" inputmode="numeric" maxlength="12" autofocus>
                <button class="btn">Подтвердить вход</button>
            </form>
            <?php if ($via_all): ?>
            <div class="resend-row">
                <?php foreach ($via_all as $v): ?>
                <form method="POST" action="<?=htmlspecialchars(rteam_2fa_url($pending_login))?>">
                    <input type="hidden" name="action" value="resend_2fa">
                    <input type="hidden" name="login" value="<?=htmlspecialchars($pending_login)?>">
                    <input type="hidden" name="via" value="<?=$v?>">
                    <button class="btn btn-google btn-resend" type="submit"><?= $v === $via_now ? "🔁 Прислать ещё раз" : ($v === "ds" ? "💬 Прислать в Discord" : "✈️ Прислать в Telegram") ?></button>
                </form>
                <?php endforeach; ?>
            </div>
            <?php endif; ?>
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
            <?php if ($discord_on): ?>
            <a href="discord_auth.php?mode=login" class="btn btn-discord">
                <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M20.32 4.37A19.8 19.8 0 0 0 15.4 2.84a.07.07 0 0 0-.08.04c-.21.38-.45.87-.61 1.25a18.3 18.3 0 0 0-5.49 0 12.6 12.6 0 0 0-.62-1.25.08.08 0 0 0-.08-.04 19.7 19.7 0 0 0-4.92 1.53.07.07 0 0 0-.03.03C.53 9.05-.32 13.58.1 18.06a.08.08 0 0 0 .03.05 19.9 19.9 0 0 0 6 3.03.08.08 0 0 0 .08-.03c.46-.63.87-1.3 1.23-1.99a.08.08 0 0 0-.04-.1 13.1 13.1 0 0 1-1.87-.9.08.08 0 0 1-.01-.12l.37-.29a.07.07 0 0 1 .08-.01c3.93 1.79 8.18 1.79 12.06 0a.07.07 0 0 1 .08 0l.37.3a.08.08 0 0 1 0 .12c-.6.35-1.22.65-1.87.89a.08.08 0 0 0-.04.11c.36.7.77 1.36 1.23 1.99a.08.08 0 0 0 .08.03 19.8 19.8 0 0 0 6-3.03.08.08 0 0 0 .04-.05c.5-5.18-.84-9.67-3.55-13.66a.06.06 0 0 0-.03-.03zM8.02 15.33c-1.18 0-2.16-1.09-2.16-2.42s.96-2.42 2.16-2.42c1.21 0 2.18 1.1 2.16 2.42 0 1.33-.96 2.42-2.16 2.42zm7.97 0c-1.18 0-2.15-1.09-2.15-2.42s.95-2.42 2.15-2.42c1.21 0 2.18 1.1 2.16 2.42 0 1.33-.95 2.42-2.16 2.42z"/></svg>
                Войти через Discord
            </a>
            <?php endif; ?>
            <a href="register.php" class="muted-link">Ещё нет аккаунта? Зарегистрироваться</a>
        <?php endif; ?>
    </div>
</div>
<?= rt_rai_widget($settings ?? [], null) /* помощник Rai: кнопка ✨, нейросеть с GitHub */ ?>
</body>
</html>
