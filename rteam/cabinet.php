<?php
require __DIR__ . '/config.php';

/* =========================================================
   ЛИЧНЫЙ КАБИНЕТ RTEAM
   - Просмотр и редактирование своего профиля
   - Привязка Google-аккаунта
   - Привязка Telegram-бота (2FA / уведомления)
   - Смена пароля
   - Мои заявки
   - Достижения (Золотой билет, Игра в кальмара)
   - Публичный просмотр чужого профиля: cabinet.php?u=login
   ========================================================= */

$users        = load_json("users.json", []);
$settings     = load_json("settings.json", []);
$applications = load_json("applications.json", []);
$squid_game   = load_json("squid_game.json", ["paused" => false, "progress" => []]);

$me       = $_SESSION["user"] ?? null;
$my_role  = $_SESSION["role"] ?? null;

$view_login = isset($_GET["u"]) && trim($_GET["u"]) !== "" ? trim($_GET["u"]) : null;
$is_own     = ($view_login === null) || ($me !== null && $view_login === $me);

if ($view_login !== null && !$is_own) {
    // Публичный просмотр чужого профиля
    $target_login = $view_login;
    if (!isset($users[$target_login])) {
        http_response_code(404);
        ?>
        <!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
        <title>Профиль не найден — RTeam</title>
        <style>body{background:#07040f;color:#ece7fb;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}</style>
        </head><body><div><h2>Пользователь не найден</h2><p><a href="index.php" style="color:#9b5cff;">← На главную</a></p></div></body></html>
        <?php
        exit;
    }
} else {
    if (!$me) { header("Location: login.php"); exit; }
    $target_login = $me;
}

$target = $users[$target_login];
$error   = "";
$success = "";

// Сообщения от google_callback.php после попытки привязки Google
if ($is_own && $me) {
    if (isset($_GET["google_linked"])) {
        $success = "Google-аккаунт успешно привязан.";
        $target = $users[$me]; // подтянуть свежие данные после привязки
    } elseif (($_GET["google_error"] ?? "") === "already_linked") {
        $error = "Этот Google-аккаунт уже привязан к другому пользователю RTeam.";
    }
}

/* ---------------------------------------------------------
   Обработка POST-действий (только для владельца профиля)
--------------------------------------------------------- */
if ($is_own && $me && isset($_POST["action"])) {
    $action = $_POST["action"];

    // --- Обновление основной информации профиля ---
    if ($action === "update_profile") {
        $bio     = trim($_POST["bio"] ?? "");
        $discord = trim($_POST["discord"] ?? "");
        $avatar  = trim($_POST["avatar"] ?? "");

        if ($avatar !== "" && !preg_match('~^https?://~i', $avatar)) {
            $error = "Ссылка на аватар должна начинаться с http:// или https://";
        } elseif (mb_strlen($bio) > 500) {
            $error = "Описание «о себе» не должно превышать 500 символов.";
        } else {
            $users[$me]["bio"]     = $bio;
            $users[$me]["discord"] = $discord;
            $users[$me]["avatar"]  = $avatar;
            save_json("users.json", $users);
            rteam_log("profile", "Обновлён профиль: $me");
            $success = "Профиль обновлён.";
            $target = $users[$me];
        }
    }

    // --- Золотой статус (доступно только обладателям билета) ---
    if ($action === "update_golden_status" && !empty($users[$me]["golden"])) {
        $status = trim($_POST["golden_status"] ?? "");
        if (mb_strlen($status) > 60) {
            $error = "Статус слишком длинный (максимум 60 символов).";
        } else {
            $users[$me]["golden_status"] = $status;
            save_json("users.json", $users);
            $success = "Статус обновлён.";
            $target = $users[$me];
        }
    }

    // --- Смена пароля ---
    if ($action === "change_password") {
        $current = trim($_POST["current_password"] ?? "");
        $new1    = trim($_POST["new_password"] ?? "");
        $new2    = trim($_POST["new_password2"] ?? "");

        if (!isset($users[$me]["password"]) || $users[$me]["password"] !== $current) {
            $error = "Текущий пароль указан неверно.";
        } elseif (strlen($new1) < 6) {
            $error = "Новый пароль должен быть не короче 6 символов.";
        } elseif ($new1 !== $new2) {
            $error = "Новые пароли не совпадают.";
        } else {
            $users[$me]["password"] = $new1;
            save_json("users.json", $users);
            rteam_log("security", "Смена пароля: $me");
            $success = "Пароль успешно изменён.";
            $target = $users[$me];
        }
    }

    // --- Отвязать Google ---
    if ($action === "unlink_google") {
        unset($users[$me]["google_id"], $users[$me]["google_email"], $users[$me]["google_name"], $users[$me]["google_avatar"]);
        save_json("users.json", $users);
        rteam_log("profile", "Отвязан Google: $me");
        $success = "Google-аккаунт отвязан.";
        $target = $users[$me];
    }

    // --- Сгенерировать код привязки Telegram-бота ---
    if ($action === "generate_tg_code") {
        $tg_codes = load_json("tg_link_codes.json", []);
        // Убираем старые коды этого пользователя
        foreach ($tg_codes as $c => $info) {
            if (($info["login"] ?? "") === $me) unset($tg_codes[$c]);
        }
        $code = strtoupper(substr(bin2hex(random_bytes(4)), 0, 6));
        $tg_codes[$code] = ["login" => $me, "expires" => time() + 900];
        save_json("tg_link_codes.json", $tg_codes);
        $_SESSION["tg_link_code"] = $code;
        $success = "Код для привязки бота создан.";
    }

    // --- Отвязать Telegram ---
    if ($action === "unlink_telegram") {
        unset($users[$me]["tg_id"], $users[$me]["tg_username"]);
        save_json("users.json", $users);
        rteam_log("profile", "Отвязан Telegram: $me");
        $success = "Telegram отвязан. 2FA для входа отключена, пока не будет привязан новый аккаунт.";
        $target = $users[$me];
    }
}

/* ---------------------------------------------------------
   Внешний эндпоинт: бот дергает эту страницу, чтобы завершить
   привязку Telegram после того, как пользователь в чате бота
   ввёл команду вида "/link КОД".
   Запрос: POST cabinet.php?action=complete_tg_link
     secret   = bot_token (settings.json -> bot_token)
     code     = код, показанный пользователю в кабинете
     chat_id  = chat_id пользователя в Telegram
     username = @username пользователя в Telegram (необязательно)
--------------------------------------------------------- */
if (isset($_GET["action"]) && $_GET["action"] === "complete_tg_link") {
    header("Content-Type: application/json; charset=utf-8");
    $secret   = $_POST["secret"] ?? "";
    $code     = strtoupper(trim($_POST["code"] ?? ""));
    $chat_id  = trim($_POST["chat_id"] ?? "");
    $username = trim($_POST["username"] ?? "");

    if (empty($settings["bot_token"]) || !hash_equals((string)$settings["bot_token"], (string)$secret)) {
        echo json_encode(["ok" => false, "error" => "bad_secret"]);
        exit;
    }
    $tg_codes = load_json("tg_link_codes.json", []);
    if (!isset($tg_codes[$code]) || $tg_codes[$code]["expires"] < time()) {
        echo json_encode(["ok" => false, "error" => "invalid_or_expired_code"]);
        exit;
    }
    $login = $tg_codes[$code]["login"];
    if (!isset($users[$login])) {
        echo json_encode(["ok" => false, "error" => "user_not_found"]);
        exit;
    }
    $users[$login]["tg_id"]       = $chat_id;
    $users[$login]["tg_username"] = $username;
    save_json("users.json", $users);
    unset($tg_codes[$code]);
    save_json("tg_link_codes.json", $tg_codes);
    rteam_log("profile", "Telegram привязан через бота: $login");
    echo json_encode(["ok" => true]);
    exit;
}

$accent   = $settings["accent"] ?? "#9b5cff";
$is_admin_viewer = $me && in_array($my_role, ["Главный разработчик", "Администратор", "Главный Администратор", "Тестер", "Главный Тестер", "Кодер", "Главный Кодер", "Руководитель"]);

$my_apps = [];
if ($is_own) {
    foreach ($applications as $a) {
        $a_login = $a["login"] ?? $a["user"] ?? null;
        if ($a_login === $me || (isset($a["email"]) && isset($target["email"]) && $a["email"] === $target["email"])) {
            $my_apps[] = $a;
        }
    }
}

$my_squid = $squid_game["progress"][$target_login] ?? ["season" => 0, "completed" => false];

$tg_link_code = $_SESSION["tg_link_code"] ?? null;
$bot_username = $settings["bot_username"] ?? "RteamBot";
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= $is_own ? "Мой профиль" : htmlspecialchars($target_login) ?> — RTeam</title>
<style>
:root {
    --accent: <?=htmlspecialchars($accent)?>;
    --accent-2: #d946ef;
    --accent-3: #6d28d9;
    --bg: #07040f;
    --card: #14101f;
    --card-2: #1b1430;
    --border: rgba(155, 92, 255, .28);
    --text: #ece7fb;
    --soft: #ada2cc;
    --grad: linear-gradient(135deg, var(--accent-3), var(--accent) 55%, var(--accent-2));
}
* { box-sizing: border-box; }
body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
}
a { color: var(--accent-2); text-decoration: none; }
.top-bar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 28px; border-bottom: 1px solid var(--border);
    background: rgba(255,255,255,.02);
}
.top-bar .logo { font-weight: 800; letter-spacing: 1px; color: var(--accent); }
.top-bar a.back { color: var(--soft); font-size: 14px; }
.top-bar a.back:hover { color: var(--text); }

.wrap { max-width: 980px; margin: 0 auto; padding: 32px 20px 60px; }

.profile-head {
    display: flex; gap: 22px; align-items: center;
    background: linear-gradient(135deg, var(--card), var(--card-2));
    border: 1px solid var(--border); border-radius: 18px;
    padding: 26px; margin-bottom: 26px;
    flex-wrap: wrap;
}
.avatar {
    width: 84px; height: 84px; border-radius: 50%;
    background: var(--grad); color: #fff; font-size: 34px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; flex-shrink: 0;
    box-shadow: 0 0 22px rgba(155,92,255,.35);
}
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.profile-head h1 { margin: 0 0 4px; font-size: 26px; }
.role-chip {
    display: inline-block; font-size: 12px; padding: 3px 10px; border-radius: 999px;
    border: 1px solid var(--border); color: var(--soft); margin-right: 6px;
}
.badge-golden {
    display: inline-block; margin-top: 8px; font-size: 12px; font-weight: 700;
    background: linear-gradient(135deg,#ffe066,#d4a017); color: #3a2a00;
    padding: 3px 12px; border-radius: 999px; box-shadow: 0 0 12px rgba(255,215,0,.4);
}
.bio { color: var(--soft); margin-top: 10px; max-width: 560px; font-size: 14px; line-height: 1.5; }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }

.card {
    background: var(--card); border: 1px solid var(--border); border-radius: 16px;
    padding: 22px;
}
.card h3 { margin: 0 0 6px; font-size: 17px; }
.card .desc { color: var(--soft); font-size: 13px; margin-bottom: 16px; line-height: 1.5; }

label.field-label { display: block; font-size: 12px; color: var(--soft); margin: 12px 0 4px; }
input, textarea, select {
    width: 100%; padding: 10px 12px; border-radius: 10px;
    border: 1px solid var(--border); background: rgba(255,255,255,.03); color: var(--text);
    font-size: 14px; font-family: inherit;
}
textarea { resize: vertical; min-height: 70px; }
input:focus, textarea:focus, select:focus { outline: none; border-color: var(--accent-2); }

.btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    margin-top: 14px; padding: 10px 18px; border-radius: 10px; border: none;
    background: var(--grad); color: #fff; font-weight: 600; font-size: 14px;
    cursor: pointer; text-decoration: none;
}
.btn:hover { filter: brightness(1.08); }
.btn-ghost { background: rgba(255,255,255,.04); border: 1px solid var(--border); color: var(--text); }
.btn-danger { background: linear-gradient(135deg,#7f1d1d,#dc2626); }
.btn-block { width: 100%; }
.btn-sm { padding: 7px 12px; font-size: 12.5px; margin-top: 8px; }

.status-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 4px; }
.status-pill {
    font-size: 12px; padding: 3px 10px; border-radius: 999px;
    background: rgba(155,92,255,.15); border: 1px solid var(--border); color: var(--soft);
}
.status-pill.on { background: rgba(52,168,83,.15); border-color: rgba(52,168,83,.4); color: #6ee7a0; }

.error-box, .success-box {
    padding: 10px 14px; border-radius: 10px; font-size: 13.5px; margin-bottom: 16px;
}
.error-box { background: rgba(220,38,38,.12); border: 1px solid rgba(220,38,38,.4); color: #ff9c9c; }
.success-box { background: rgba(52,168,83,.12); border: 1px solid rgba(52,168,83,.4); color: #8ff0ac; }

.code-box {
    font-family: 'Courier New', monospace; font-size: 26px; letter-spacing: 6px;
    text-align: center; padding: 14px; border-radius: 12px;
    background: rgba(155,92,255,.1); border: 1px dashed var(--accent-2); margin: 12px 0;
}
.instructions { font-size: 13px; color: var(--soft); line-height: 1.6; }
.instructions b { color: var(--text); }

.apps-list { list-style: none; padding: 0; margin: 0; }
.apps-list li {
    padding: 10px 0; border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; gap: 10px; font-size: 13.5px;
}
.apps-list li:last-child { border-bottom: none; }
.muted { color: var(--soft); font-size: 13.5px; }

.season-track { display: flex; gap: 8px; margin-top: 6px; }
.season-dot {
    flex: 1; height: 8px; border-radius: 6px; background: rgba(255,255,255,.08);
}
.season-dot.done { background: var(--grad); }

.full-width { grid-column: 1 / -1; }
</style>
</head>
<body>

<div class="top-bar">
    <div class="logo">RTEAM</div>
    <a href="index.php" class="back">← На главную</a>
</div>

<div class="wrap">

    <?php if ($error): ?><div class="error-box"><?=htmlspecialchars($error)?></div><?php endif; ?>
    <?php if ($success): ?><div class="success-box"><?=htmlspecialchars($success)?></div><?php endif; ?>

    <div class="profile-head">
        <div class="avatar">
            <?php if (!empty($target["avatar"])): ?>
                <img src="<?=htmlspecialchars($target["avatar"])?>" alt="">
            <?php else: ?>
                <?=strtoupper(mb_substr($target_login,0,1))?>
            <?php endif; ?>
        </div>
        <div>
            <h1><?=htmlspecialchars($target_login)?><?= $is_own ? " (Вы)" : "" ?></h1>
            <span class="role-chip"><?=htmlspecialchars($target["role"] ?? "Пользователь")?></span>
            <?php if (!empty($target["golden"])): ?>
                <div><span class="badge-golden">🎫 <?=htmlspecialchars($target["golden_title"] ?? "Золотой билет RTeam")?></span></div>
                <?php if (!empty($target["golden_status"])): ?>
                    <div class="bio">«<?=htmlspecialchars($target["golden_status"])?>»</div>
                <?php endif; ?>
            <?php endif; ?>
            <?php if (!empty($target["bio"])): ?>
                <p class="bio"><?=nl2br(htmlspecialchars($target["bio"]))?></p>
            <?php endif; ?>
            <?php if (!empty($target["discord"])): ?>
                <p class="muted">Discord: <b><?=htmlspecialchars($target["discord"])?></b></p>
            <?php endif; ?>
        </div>
    </div>

    <?php if (!$is_own): ?>
        <!-- ==================== ПУБЛИЧНЫЙ ПРОСМОТР ==================== -->
        <div class="grid">
            <div class="card">
                <h3>🏆 Достижения</h3>
                <p class="desc">Прогресс пользователя в испытаниях RTeam.</p>
                <div class="status-row">
                    <span>Игра в кальмара</span>
                    <span class="status-pill <?= !empty($my_squid["completed"]) ? "on" : "" ?>">
                        <?= !empty($my_squid["completed"]) ? "Пройдена ✅" : "Сезон " . (int)($my_squid["season"] ?? 0) . " из 3" ?>
                    </span>
                </div>
                <div class="season-track">
                    <?php for ($s=1; $s<=3; $s++): ?>
                        <div class="season-dot <?= ($my_squid["season"] ?? 0) >= $s ? "done" : "" ?>"></div>
                    <?php endfor; ?>
                </div>
            </div>
            <div class="card">
                <h3>ℹ️ Об аккаунте</h3>
                <p class="desc">Публичная информация, видимая всем посетителям сайта.</p>
                <p class="muted">Роль: <b><?=htmlspecialchars($target["role"] ?? "Пользователь")?></b></p>
                <?php if (!empty($target["golden"])): ?>
                    <p class="muted">Статус: обладатель «Золотого билета RTeam» 🎫</p>
                <?php endif; ?>
            </div>
        </div>

    <?php else: ?>
        <!-- ==================== СОБСТВЕННЫЙ КАБИНЕТ ==================== -->
        <div class="grid">

            <!-- О себе -->
            <div class="card full-width">
                <h3>✏️ О себе</h3>
                <p class="desc">Эта информация видна другим пользователям на вашей странице профиля.</p>
                <form method="POST">
                    <input type="hidden" name="action" value="update_profile">
                    <label class="field-label">Ссылка на аватар (URL картинки)</label>
                    <input type="text" name="avatar" value="<?=htmlspecialchars($target["avatar"] ?? "")?>" placeholder="https://...">
                    <label class="field-label">О себе</label>
                    <textarea name="bio" maxlength="500" placeholder="Пара слов о себе..."><?=htmlspecialchars($target["bio"] ?? "")?></textarea>
                    <label class="field-label">Discord (никнейм или тег)</label>
                    <input type="text" name="discord" value="<?=htmlspecialchars($target["discord"] ?? "")?>" placeholder="username">
                    <button class="btn">Сохранить</button>
                </form>
            </div>

            <?php if (!empty($target["golden"])): ?>
            <!-- Золотой статус -->
            <div class="card full-width">
                <h3>🎫 Золотой билет</h3>
                <p class="desc">Придумайте короткую подпись-статус, которая будет отображаться под вашим золотым бейджем.</p>
                <form method="POST">
                    <input type="hidden" name="action" value="update_golden_status">
                    <label class="field-label">Статус (до 60 символов)</label>
                    <input type="text" name="golden_status" maxlength="60" value="<?=htmlspecialchars($target["golden_status"] ?? "")?>" placeholder="Например: легенда RTeam">
                    <button class="btn btn-sm">Обновить статус</button>
                </form>
            </div>
            <?php endif; ?>

            <!-- Google -->
            <div class="card">
                <h3>🔗 Google-аккаунт</h3>
                <p class="desc">Привяжите Google для быстрого входа в один клик — без пароля.</p>
                <?php if (!empty($target["google_id"])): ?>
                    <div class="status-row">
                        <span class="status-pill on">Привязан ✅</span>
                    </div>
                    <p class="muted">
                        <?= !empty($target["google_avatar"]) ? '<img src="'.htmlspecialchars($target["google_avatar"]).'" style="width:20px;height:20px;border-radius:50%;vertical-align:middle;margin-right:6px;">' : '' ?>
                        <?=htmlspecialchars($target["google_name"] ?? "")?>
                        <?php if (!empty($target["google_email"])): ?><br><?=htmlspecialchars($target["google_email"])?><?php endif; ?>
                    </p>
                    <form method="POST" onsubmit="return confirm('Отвязать Google-аккаунт?');">
                        <input type="hidden" name="action" value="unlink_google">
                        <button class="btn btn-ghost btn-sm">Отвязать Google</button>
                    </form>
                <?php else: ?>
                    <div class="status-row"><span class="status-pill">Не привязан</span></div>
                    <a href="google_start.php?mode=link" class="btn btn-block">Привязать Google</a>
                <?php endif; ?>
            </div>

            <!-- Telegram -->
            <div class="card">
                <h3>🤖 Telegram-бот</h3>
                <p class="desc">Нужен для получения кода 2FA при входе (для администраторов) и уведомлений.</p>
                <?php if (!empty($target["tg_id"])): ?>
                    <div class="status-row"><span class="status-pill on">Привязан ✅</span></div>
                    <?php if (!empty($target["tg_username"])): ?>
                        <p class="muted">Аккаунт: <b>@<?=htmlspecialchars($target["tg_username"])?></b></p>
                    <?php endif; ?>
                    <form method="POST" onsubmit="return confirm('Отвязать Telegram? Если у вас админ-роль, вход с 2FA станет недоступен, пока не привяжете новый аккаунт.');">
                        <input type="hidden" name="action" value="unlink_telegram">
                        <button class="btn btn-ghost btn-sm">Отвязать Telegram</button>
                    </form>
                <?php else: ?>
                    <div class="status-row"><span class="status-pill">Не привязан</span></div>
                    <?php if ($tg_link_code): ?>
                        <div class="code-box"><?=htmlspecialchars($tg_link_code)?></div>
                        <p class="instructions">
                            1. Откройте бота <b>@<?=htmlspecialchars($bot_username)?></b> в Telegram.<br>
                            2. Отправьте ему команду: <b>/link <?=htmlspecialchars($tg_link_code)?></b><br>
                            3. Код действует 15 минут. Как только бот подтвердит привязку — обновите эту страницу.
                        </p>
                    <?php endif; ?>
                    <form method="POST">
                        <input type="hidden" name="action" value="generate_tg_code">
                        <button class="btn btn-block"><?= $tg_link_code ? "Сгенерировать новый код" : "Привязать Telegram" ?></button>
                    </form>
                <?php endif; ?>
            </div>

            <!-- Смена пароля -->
            <div class="card">
                <h3>🔒 Безопасность</h3>
                <p class="desc">Смена пароля от аккаунта.</p>
                <form method="POST">
                    <input type="hidden" name="action" value="change_password">
                    <label class="field-label">Текущий пароль</label>
                    <input type="password" name="current_password" required>
                    <label class="field-label">Новый пароль</label>
                    <input type="password" name="new_password" required>
                    <label class="field-label">Повторите новый пароль</label>
                    <input type="password" name="new_password2" required>
                    <button class="btn btn-block">Сменить пароль</button>
                </form>
            </div>

            <!-- Достижения -->
            <div class="card">
                <h3>🏆 Достижения</h3>
                <p class="desc">Ваш прогресс в испытаниях RTeam.</p>
                <div class="status-row">
                    <span>Игра в кальмара</span>
                    <span class="status-pill <?= !empty($my_squid["completed"]) ? "on" : "" ?>">
                        <?= !empty($my_squid["completed"]) ? "Пройдена ✅" : "Сезон " . (int)($my_squid["season"] ?? 0) . " из 3" ?>
                    </span>
                </div>
                <div class="season-track">
                    <?php for ($s=1; $s<=3; $s++): ?>
                        <div class="season-dot <?= ($my_squid["season"] ?? 0) >= $s ? "done" : "" ?>"></div>
                    <?php endfor; ?>
                </div>
                <?php if (empty($target["golden"])): ?>
                    <p class="muted" style="margin-top:12px;">Пройдите все 3 сезона, чтобы попасть в претенденты на 🎫 Золотой билет RTeam.</p>
                <?php endif; ?>
            </div>

            <!-- Заявки -->
            <div class="card full-width">
                <h3>📨 Мои заявки</h3>
                <p class="desc">История заявок, поданных с этого аккаунта.</p>
                <?php if (!$my_apps): ?>
                    <p class="muted">Вы ещё не подавали заявок.</p>
                    <a href="index.php#join" class="btn btn-sm">Подать заявку</a>
                <?php else: ?>
                    <ul class="apps-list">
                        <?php foreach (array_reverse($my_apps) as $a): ?>
                            <li>
                                <span><?=htmlspecialchars($a["type"] ?? "Заявка")?></span>
                                <span class="muted"><?=htmlspecialchars($a["date"] ?? $a["time"] ?? "")?></span>
                                <span class="status-pill <?= ($a["status"] ?? "") === "Принята" ? "on" : "" ?>">
                                    <?=htmlspecialchars($a["status"] ?? "На рассмотрении")?>
                                </span>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                    <a href="index.php#join" class="btn btn-ghost btn-sm">Подать ещё одну заявку</a>
                <?php endif; ?>
            </div>

            <!-- Аккаунт -->
            <div class="card full-width">
                <h3>⚙️ Аккаунт</h3>
                <div class="status-row"><span class="muted">Логин</span><b><?=htmlspecialchars($me)?></b></div>
                <div class="status-row"><span class="muted">Роль</span><b><?=htmlspecialchars($target["role"] ?? "Пользователь")?></b></div>
                <a href="?logout=1" style="text-decoration:none;">
                    <button type="button" class="btn btn-danger btn-sm" onclick="location.href='index.php?logout=1'">Выйти из аккаунта</button>
                </a>
            </div>

        </div>
    <?php endif; ?>

</div>
</body>
</html>
<?php if ($is_own) unset($_SESSION["tg_link_code"]); ?>
