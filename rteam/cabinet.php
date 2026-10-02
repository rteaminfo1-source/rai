<?php
require __DIR__ . '/config.php';
require_once __DIR__ . '/_roles.php'; // роли и права (общий файл с admin.php)

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
// Роль берём из users.json: смена роли в админ-панели видна сразу, без перевхода
if ($me && isset($users[$me]) && is_array($users[$me])) {
    $my_role = $users[$me]["role"] ?? "Пользователь";
    $_SESSION["role"] = $my_role;
}

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
        $success = "Telegram отвязан. Теперь вход на сайт — просто по паролю, без кода из бота.";
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

$accent   = preg_match('/^#[0-9a-fA-F]{3,8}$/', $settings["accent"] ?? "") ? $settings["accent"] : "#ff2a2a";
$is_admin_viewer = $me && rt_is_staff($my_role, $me);

// Роль с направлением стажёра, например «Стажёр · Кодер»
$target_role_info  = rt_role_info($target["role"] ?? "Пользователь") ?? ["icon" => "👤", "color" => "#718096", "desc" => ""];
$target_role_label = rt_role_label($target["role"] ?? "Пользователь", $target["direction"] ?? "");
$target_is_staff   = rt_is_staff($target["role"] ?? "Пользователь", $target_login);
$role_color        = $target_role_info["color"] ?? $accent;

// Мои заявки: по логину, который админ-панель записывает при решении,
// по логину в заявке или по нику/email из ответов
$my_apps = [];
if ($is_own) {
    foreach ($applications as $a) {
        $a_login = $a["account"] ?? $a["login"] ?? $a["user"] ?? rt_app_account($a, $users);
        if ($a_login === $me) $my_apps[] = $a;
    }
}
$app_status_names = ["new" => "На рассмотрении", "viewed" => "Просмотрена", "resolved_accept" => "Принята", "resolved_decline" => "Отклонена"];
$app_status_class = ["new" => "st-wait", "viewed" => "st-view", "resolved_accept" => "st-ok", "resolved_decline" => "st-no", "Принята" => "st-ok"];

$my_squid = $squid_game["progress"][$target_login] ?? ["season" => 0, "completed" => false];
$squid_season = (int)($my_squid["season"] ?? 0);

$tg_link_code = $_SESSION["tg_link_code"] ?? null;
$bot_username = $settings["bot_username"] ?? "RteamBot";
$has_google   = !empty($target["google_id"]);
$has_tg       = !empty($target["tg_id"]);
$initial      = mb_strtoupper(mb_substr($target_login, 0, 1));
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= $is_own ? "Мой профиль" : htmlspecialchars($target_login) ?> — RTeam</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {
    --accent: <?=htmlspecialchars($accent)?>;
    --rc: <?=htmlspecialchars($role_color)?>;
    --bg: #07070b; --text: #ececf2; --soft: #b4b4c3; --muted: #747487;
    --line: rgba(255,255,255,.07); --line-2: rgba(255,255,255,.12);
    --ok: #22c55e; --warn: #f59e0b; --danger: #ef4444; --info: #3b82f6;
    --font: "Inter", "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
    --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; min-height: 100vh; color: var(--text); font-family: var(--font); font-size: 14px; line-height: 1.55; letter-spacing: -.006em; -webkit-font-smoothing: antialiased;
    background: var(--bg);
    background: radial-gradient(1100px 600px at 105% -10%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 60%),
                radial-gradient(900px 500px at -15% 110%, rgba(90,90,255,.07), transparent 60%), var(--bg);
    background-attachment: fixed; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image: radial-gradient(rgba(255,255,255,.045) 1px, transparent 1px); background-size: 24px 24px;
    -webkit-mask-image: linear-gradient(180deg, #000, transparent 65%); mask-image: linear-gradient(180deg, #000, transparent 65%); }
a { color: color-mix(in srgb, var(--accent) 70%, #fff); text-decoration: none; }
a:hover { text-decoration: underline; }
::selection { background: color-mix(in srgb, var(--accent) 45%, transparent); }

/* Верхняя панель */
.top { position: sticky; top: 0; z-index: 40; display: flex; align-items: center; gap: 12px; padding: 14px 28px;
    background: rgba(8,8,12,.62); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border-bottom: 1px solid var(--line); }
.brand { display: flex; align-items: center; gap: 10px; color: #fff; font-weight: 800; letter-spacing: .08em; }
.brand:hover { text-decoration: none; }
.brand-logo { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; color: #fff;
    background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 50%, #6b0000)); box-shadow: 0 6px 18px color-mix(in srgb, var(--accent) 40%, transparent); }
.top-links { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }

.wrap { position: relative; z-index: 1; max-width: 1080px; margin: 0 auto; padding: 26px 20px 70px; }

/* Стеклянные карточки */
.card, .hero, .stat {
    border: 1px solid transparent; border-radius: 18px;
    background: linear-gradient(180deg, rgba(23,23,33,.92), rgba(13,13,20,.92)) padding-box,
                linear-gradient(180deg, rgba(255,255,255,.11), rgba(255,255,255,.025) 60%, rgba(255,255,255,.05)) border-box;
    box-shadow: 0 1px 0 rgba(255,255,255,.04) inset, 0 18px 40px -26px rgba(0,0,0,.8);
}
.card { padding: 22px; }
.card h3 { margin: 0 0 4px; font-size: 16px; color: #fff; display: flex; align-items: center; gap: 8px; }
.card .desc { color: var(--soft); font-size: 13px; margin: 0 0 16px; }
.card.gold { background: linear-gradient(160deg, rgba(40,31,6,.95), rgba(16,16,23,.95) 60%) padding-box, linear-gradient(135deg, #b8901e, rgba(120,90,10,.25)) border-box; }
.card.gold h3 { color: #ffd76a; }

@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.wrap > * { animation: rise .4s cubic-bezier(.2,.7,.2,1) both; }
.grid > * { animation: rise .45s cubic-bezier(.2,.7,.2,1) both; }
.grid > *:nth-child(2) { animation-delay: .04s; } .grid > *:nth-child(3) { animation-delay: .08s; } .grid > *:nth-child(4) { animation-delay: .12s; } .grid > *:nth-child(n+5) { animation-delay: .16s; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

/* Шапка профиля */
.hero { position: relative; overflow: hidden; padding: 0; }
.hero-cover { height: 130px; background:
    radial-gradient(500px 160px at 20% 120%, color-mix(in srgb, var(--rc) 55%, transparent), transparent 70%),
    radial-gradient(500px 200px at 90% -20%, color-mix(in srgb, var(--accent) 45%, transparent), transparent 70%),
    linear-gradient(135deg, rgba(255,255,255,.04), rgba(255,255,255,0));
    border-bottom: 1px solid var(--line); }
.hero-body { display: flex; gap: 22px; align-items: flex-end; flex-wrap: wrap; padding: 0 26px 24px; margin-top: -54px; }
.avatar { width: 112px; height: 112px; border-radius: 50%; flex: none; display: grid; place-items: center; overflow: hidden;
    font-size: 44px; font-weight: 800; color: #fff; background: linear-gradient(135deg, var(--rc), color-mix(in srgb, var(--rc) 40%, #000));
    border: 4px solid #0e0e15; box-shadow: 0 0 0 2px color-mix(in srgb, var(--rc) 55%, transparent), 0 12px 30px -10px rgba(0,0,0,.8); }
.avatar img { width: 100%; height: 100%; object-fit: cover; }
.hero-info { flex: 1; min-width: 240px; padding-top: 60px; }
.hero-info h1 { margin: 0; font-size: 28px; letter-spacing: -.02em; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.you { font-size: 12px; font-weight: 600; color: var(--muted); border: 1px solid var(--line-2); border-radius: 999px; padding: 2px 10px; }
.tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.bio { color: var(--soft); margin: 12px 0 0; max-width: 640px; }
.role-badge { --rc: #718096; display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 700; white-space: nowrap;
    color: color-mix(in srgb, var(--rc) 80%, #fff); background: color-mix(in srgb, var(--rc) 15%, transparent); border: 1px solid color-mix(in srgb, var(--rc) 40%, transparent); }
.owner-badge { --rc: #f6c445; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px; font-size: 12.5px; color: var(--soft); background: rgba(255,255,255,.04); border: 1px solid var(--line); }
.chip.on { color: #c9f7d8; background: rgba(34,197,94,.1); border-color: rgba(34,197,94,.35); }
.badge-golden { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 999px; font-size: 12.5px; font-weight: 800;
    background: linear-gradient(135deg, #ffe066, #d4a017); color: #3a2a00; box-shadow: 0 0 14px rgba(255,215,0,.35); }
.golden-quote { color: #ffd76a; font-style: italic; margin-top: 8px; }

/* Мини-статистика */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 16px; }
.stat { padding: 14px 16px; }
.stat .s-ico { font-size: 18px; }
.stat .s-num { font-size: 22px; font-weight: 800; color: #fff; margin-top: 4px; letter-spacing: -.02em; }
.stat .s-lbl { color: var(--muted); font-size: 12.5px; }

/* Навигация по разделам */
.subnav { position: sticky; top: 64px; z-index: 30; display: flex; gap: 6px; overflow-x: auto; margin: 18px 0 4px; padding: 6px; border-radius: 14px;
    background: rgba(14,14,21,.75); backdrop-filter: blur(12px); border: 1px solid var(--line); scrollbar-width: none; }
.subnav::-webkit-scrollbar { display: none; }
.subnav a { flex: none; padding: 8px 14px; border-radius: 10px; color: var(--soft); font-weight: 600; font-size: 13px; white-space: nowrap; }
.subnav a:hover, .subnav a.active { background: color-mix(in srgb, var(--accent) 16%, transparent); color: #fff; text-decoration: none; }

.section-title { display: flex; align-items: center; gap: 10px; margin: 30px 0 12px; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: var(--soft); scroll-margin-top: 130px; }
.section-title::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, var(--line-2), transparent); }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.full { grid-column: 1 / -1; }
@media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }

/* Формы */
label.field-label { display: block; font-size: 12.5px; color: var(--soft); margin: 14px 0 6px; font-weight: 500; }
label.field-label:first-of-type { margin-top: 0; }
input, textarea, select { width: 100%; padding: 11px 13px; border-radius: 11px; border: 1px solid rgba(255,255,255,.1); background: rgba(6,6,10,.7); color: #fff; font: inherit; font-size: 14px; transition: border-color .15s, box-shadow .15s; }
input:hover, textarea:hover { border-color: rgba(255,255,255,.18); }
input:focus, textarea:focus, select:focus { outline: none; border-color: color-mix(in srgb, var(--accent) 70%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent); }
textarea { resize: vertical; min-height: 90px; }
.field-row { display: flex; gap: 10px; align-items: center; }
.field-row > input { flex: 1; }
.hint { font-size: 12px; color: var(--muted); margin-top: 6px; display: flex; justify-content: space-between; gap: 10px; }
.avatar-preview { width: 44px; height: 44px; border-radius: 50%; flex: none; overflow: hidden; display: grid; place-items: center; font-weight: 800; color: #fff;
    background: linear-gradient(135deg, var(--rc), color-mix(in srgb, var(--rc) 40%, #000)); border: 1px solid var(--line-2); }
.avatar-preview img { width: 100%; height: 100%; object-fit: cover; }
.pass-wrap { position: relative; }
.pass-wrap input { padding-right: 44px; }
.pass-eye { position: absolute; right: 6px; top: 50%; transform: translateY(-50%); width: 32px; height: 32px; border: 0; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; font-size: 15px; }
.pass-eye:hover { color: #fff; background: rgba(255,255,255,.06); }
.meter { height: 6px; border-radius: 999px; background: rgba(255,255,255,.06); overflow: hidden; margin-top: 8px; }
.meter span { display: block; height: 100%; width: 0; border-radius: 999px; transition: width .25s, background .25s; }

/* Кнопки */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; margin-top: 16px; padding: 11px 18px; border-radius: 11px; border: 1px solid transparent;
    font: inherit; font-weight: 700; font-size: 14px; color: #fff; cursor: pointer; text-decoration: none !important; white-space: nowrap;
    background: linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 75%, #000));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.25), 0 8px 22px -8px color-mix(in srgb, var(--accent) 70%, transparent);
    transition: transform .12s, filter .15s; }
.btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
.btn-ghost { background: rgba(255,255,255,.04); border-color: var(--line-2); color: var(--text); box-shadow: none; }
.btn-danger { background: transparent; border-color: rgba(239,68,68,.4); color: #ff9b9b; box-shadow: none; }
.btn-danger:hover { background: rgba(239,68,68,.1); }
.btn-google { background: #fff; color: #1f1f1f; box-shadow: 0 8px 22px -10px rgba(255,255,255,.35); }
.btn-tg { background: linear-gradient(180deg, #2aabee, #1c8ad0); box-shadow: 0 8px 22px -10px rgba(42,171,238,.6); }
.btn-gold { background: linear-gradient(135deg, #ffe066, #d4a017); color: #3a2a00; box-shadow: 0 8px 22px -10px rgba(255,215,0,.6); }
.btn-sm { padding: 8px 13px; font-size: 13px; margin-top: 12px; }
.btn-block { width: 100%; }
.top .btn { margin-top: 0; padding: 8px 14px; font-size: 13px; }

/* Статусы */
.status { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 700; padding: 4px 11px; border-radius: 999px; border: 1px solid var(--line-2); color: var(--soft); background: rgba(255,255,255,.04); }
.status::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.status.on, .st-ok { color: #6ee7a0; border-color: rgba(34,197,94,.35); background: rgba(34,197,94,.1); }
.st-no { color: #ff9b9b; border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.1); }
.st-view { color: #fcc56b; border-color: rgba(245,158,11,.35); background: rgba(245,158,11,.1); }
.st-wait { color: #8bb8ff; border-color: rgba(59,130,246,.35); background: rgba(59,130,246,.1); }
.link-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.link-icon { width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center; font-size: 22px; flex: none; background: rgba(255,255,255,.05); border: 1px solid var(--line); }
.link-who { display: flex; align-items: center; gap: 10px; margin-top: 12px; padding: 10px 12px; border-radius: 12px; background: rgba(255,255,255,.03); border: 1px solid var(--line); color: var(--soft); }
.link-who img { width: 26px; height: 26px; border-radius: 50%; }

/* Код привязки Telegram */
.code-box { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 14px 0 6px; padding: 14px 16px; border-radius: 14px;
    background: rgba(42,171,238,.08); border: 1px dashed rgba(42,171,238,.6); }
.code-box code { font-family: var(--mono); font-size: 26px; font-weight: 700; letter-spacing: .25em; color: #fff; }
.steps { list-style: none; counter-reset: s; padding: 0; margin: 12px 0 0; }
.steps li { counter-increment: s; display: flex; gap: 10px; align-items: flex-start; padding: 6px 0; color: var(--soft); font-size: 13.5px; }
.steps li::before { content: counter(s); flex: none; width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center; font-size: 12px; font-weight: 800; color: #fff; background: rgba(42,171,238,.35); }
.steps b { color: #fff; }
kbd { font-family: var(--mono); font-size: 12px; padding: 1px 6px; border-radius: 6px; border: 1px solid var(--line-2); border-bottom-width: 2px; background: rgba(255,255,255,.04); color: #fff; }

/* Достижения */
.seasons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 14px; }
.season { padding: 12px; border-radius: 13px; text-align: center; border: 1px solid var(--line); background: rgba(255,255,255,.03); color: var(--muted); }
.season .s-ico { font-size: 24px; filter: grayscale(1); opacity: .5; }
.season.done { border-color: color-mix(in srgb, #ff2fa0 55%, transparent); background: rgba(255,47,160,.09); color: #ffd0ea; }
.season.done .s-ico { filter: none; opacity: 1; }
.season .s-name { font-size: 12px; font-weight: 600; margin-top: 4px; }

/* Заявки */
.apps { list-style: none; padding: 0; margin: 0; }
.apps li { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); }
.apps li:last-child { border-bottom: 0; }
.apps .a-ico { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; background: rgba(255,255,255,.05); border: 1px solid var(--line); flex: none; }
.apps .a-main { flex: 1; min-width: 0; }
.apps .a-title { font-weight: 700; color: #fff; }
.apps .a-date { color: var(--muted); font-size: 12.5px; }
.empty { text-align: center; color: var(--muted); padding: 22px 10px; border: 1px dashed var(--line-2); border-radius: 14px; }
.kv { display: flex; justify-content: space-between; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.kv:last-of-type { border-bottom: 0; }
.kv span { color: var(--muted); }
.kv b { color: #fff; text-align: right; }

/* Уведомления */
#toasts { position: fixed; right: 20px; bottom: 20px; z-index: 99; display: flex; flex-direction: column; gap: 10px; max-width: min(420px, calc(100vw - 40px)); }
.toast { padding: 13px 18px; border-radius: 12px; background: rgba(20,20,29,.97); border: 1px solid var(--line-2); border-left: 4px solid var(--info); box-shadow: 0 20px 50px -20px rgba(0,0,0,.9); animation: slide .35s ease both; transition: opacity .4s; }
.toast.ok { border-left-color: var(--ok); } .toast.err { border-left-color: var(--danger); font-weight: 600; }
@keyframes slide { from { opacity: 0; transform: translateX(110%); } to { opacity: 1; transform: none; } }

@media (max-width: 640px) {
    .top { padding: 12px 16px; }
    .top-links .hide-sm { display: none; }
    .wrap { padding: 18px 14px 60px; }
    .hero-body { padding: 0 18px 20px; justify-content: center; text-align: center; }
    .hero-info { padding-top: 0; }
    .hero-info h1, .tags { justify-content: center; }
    .bio { margin-left: auto; margin-right: auto; }
    .subnav { top: 60px; }
}
</style>
</head>
<body>

<div id="toasts"></div>

<header class="top">
    <a class="brand" href="index.php"><span class="brand-logo">R</span>RTEAM</a>
    <div class="top-links">
        <a class="btn btn-ghost hide-sm" href="index.php">← На главную</a>
        <?php if ($is_admin_viewer): ?><a class="btn" href="admin.php">🛠 Админ‑панель</a><?php endif; ?>
        <?php if ($me && !$is_own): ?><a class="btn btn-ghost" href="cabinet.php">👤 Мой профиль</a><?php endif; ?>
        <?php if ($is_own): ?><a class="btn btn-ghost" href="index.php?logout=1" title="Выйти">⎋<span class="hide-sm"> Выйти</span></a><?php endif; ?>
    </div>
</header>

<main class="wrap">

    <!-- ШАПКА ПРОФИЛЯ -->
    <section class="hero">
        <div class="hero-cover"></div>
        <div class="hero-body">
            <div class="avatar"><?php if (!empty($target["avatar"])): ?><img src="<?=htmlspecialchars($target["avatar"])?>" alt=""><?php else: ?><?=htmlspecialchars($initial)?><?php endif; ?></div>
            <div class="hero-info">
                <h1><?=htmlspecialchars($target_login)?><?php if ($is_own): ?><span class="you">это вы</span><?php endif; ?></h1>
                <div class="tags">
                    <?=rt_role_badge($target["role"] ?? "Пользователь", $target["direction"] ?? "", $target_login)?>
                    <?php if (!empty($target["golden"])): ?><span class="badge-golden">🎫 <?=htmlspecialchars($target["golden_title"] ?? "Золотой билет RTeam")?></span><?php endif; ?>
                    <?php if (!empty($target["discord"])): ?><span class="chip">💬 <?=htmlspecialchars($target["discord"])?></span><?php endif; ?>
                </div>
                <?php if (!empty($target["golden"]) && !empty($target["golden_status"])): ?><div class="golden-quote">«<?=htmlspecialchars($target["golden_status"])?>»</div><?php endif; ?>
                <?php if (!empty($target["bio"])): ?><p class="bio"><?=nl2br(htmlspecialchars($target["bio"]))?></p><?php elseif ($is_own): ?><p class="bio" style="color:var(--muted);">Расскажите о себе — блок «О себе» ниже.</p><?php endif; ?>
            </div>
        </div>
    </section>

    <div class="stats">
        <div class="stat"><div class="s-ico"><?=$target_role_info["icon"]?></div><div class="s-num" style="font-size:16px; margin-top:8px;"><?=htmlspecialchars($target_role_label)?></div><div class="s-lbl">роль на сайте</div></div>
        <div class="stat"><div class="s-ico">🦑</div><div class="s-num"><?= !empty($my_squid["completed"]) ? "✓" : $squid_season . "/3" ?></div><div class="s-lbl">Игра в кальмара</div></div>
        <?php if ($is_own): ?>
            <div class="stat"><div class="s-ico">📨</div><div class="s-num"><?=count($my_apps)?></div><div class="s-lbl">заявок подано</div></div>
            <div class="stat"><div class="s-ico">🔐</div><div class="s-num" style="font-size:16px; margin-top:8px;"><?= ($has_google ? "Google" : "") . ($has_google && $has_tg ? " + " : "") . ($has_tg ? "Telegram" : "") ?: "—" ?></div><div class="s-lbl">привязки</div></div>
        <?php else: ?>
            <div class="stat"><div class="s-ico">🎫</div><div class="s-num"><?= !empty($target["golden"]) ? "Есть" : "—" ?></div><div class="s-lbl">золотой билет</div></div>
        <?php endif; ?>
    </div>

    <?php if (!$is_own): ?>
        <!-- ==================== ПУБЛИЧНЫЙ ПРОСМОТР ==================== -->
        <div class="section-title">Достижения</div>
        <div class="grid">
            <div class="card">
                <h3>🦑 Игра в кальмара</h3>
                <p class="desc">Прогресс в испытаниях RTeam.</p>
                <div class="seasons">
                    <?php foreach ([["🚦", "Красный свет"], ["🍪", "Дальгона"], ["🌉", "Стеклянный мост"]] as $si => [$sico, $sname]): ?>
                        <div class="season<?= $squid_season > $si ? " done" : "" ?>"><div class="s-ico"><?=$sico?></div><div class="s-name"><?=$sname?></div></div>
                    <?php endforeach; ?>
                </div>
            </div>
            <div class="card<?= !empty($target["golden"]) ? " gold" : "" ?>">
                <h3>ℹ️ Об аккаунте</h3>
                <p class="desc">Публичная информация, видимая всем посетителям сайта.</p>
                <div class="kv"><span>Роль</span><b><?=$target_role_info["icon"]?> <?=htmlspecialchars($target_role_label)?></b></div>
                <div class="kv"><span>Золотой билет</span><b><?= !empty($target["golden"]) ? "🎫 Есть" : "Нет" ?></b></div>
                <?php if (!empty($target["discord"])): ?><div class="kv"><span>Discord</span><b><?=htmlspecialchars($target["discord"])?></b></div><?php endif; ?>
            </div>
        </div>

    <?php else: ?>
        <!-- ==================== СОБСТВЕННЫЙ КАБИНЕТ ==================== -->
        <nav class="subnav">
            <a href="#profile">✏️ Профиль</a>
            <a href="#links">🔗 Привязки</a>
            <a href="#security">🔒 Безопасность</a>
            <a href="#apps">📨 Заявки</a>
            <a href="#achievements">🏆 Достижения</a>
            <a href="#account">⚙️ Аккаунт</a>
        </nav>

        <div class="section-title" id="profile">Профиль</div>
        <div class="grid">
            <div class="card <?= !empty($target["golden"]) ? "" : "full" ?>">
                <h3>✏️ О себе</h3>
                <p class="desc">Эта информация видна другим на вашей странице профиля.</p>
                <form method="POST" action="cabinet.php#profile">
                    <input type="hidden" name="action" value="update_profile">
                    <label class="field-label">Аватар — ссылка на картинку</label>
                    <div class="field-row">
                        <div class="avatar-preview" id="avPrev"><?php if (!empty($target["avatar"])): ?><img src="<?=htmlspecialchars($target["avatar"])?>" alt=""><?php else: ?><?=htmlspecialchars($initial)?><?php endif; ?></div>
                        <input type="text" name="avatar" id="avInput" value="<?=htmlspecialchars($target["avatar"] ?? "")?>" placeholder="https://...">
                    </div>
                    <label class="field-label">О себе</label>
                    <textarea name="bio" id="bioInput" maxlength="500" placeholder="Пара слов о себе..."><?=htmlspecialchars($target["bio"] ?? "")?></textarea>
                    <div class="hint"><span>Видно всем на странице профиля</span><span id="bioCount">0/500</span></div>
                    <label class="field-label">Discord</label>
                    <input type="text" name="discord" value="<?=htmlspecialchars($target["discord"] ?? "")?>" placeholder="username">
                    <button class="btn">💾 Сохранить</button>
                </form>
            </div>

            <?php if (!empty($target["golden"])): ?>
            <div class="card gold">
                <h3>🎫 Золотой билет</h3>
                <p class="desc" style="color:#d8c38a;">Короткая подпись-статус под вашим золотым бейджем.</p>
                <form method="POST" action="cabinet.php#profile">
                    <input type="hidden" name="action" value="update_golden_status">
                    <label class="field-label" style="color:#d8c38a;">Статус (до 60 символов)</label>
                    <input type="text" name="golden_status" maxlength="60" value="<?=htmlspecialchars($target["golden_status"] ?? "")?>" placeholder="Например: легенда RTeam">
                    <button class="btn btn-gold btn-block">Обновить статус</button>
                </form>
                <a href="profile.php" class="btn btn-ghost btn-sm btn-block">Открыть золотой профиль →</a>
            </div>
            <?php endif; ?>
        </div>

        <div class="section-title" id="links">Привязки</div>
        <div class="grid">
            <!-- Google -->
            <div class="card">
                <div class="link-head">
                    <div style="display:flex; gap:12px; align-items:center;"><div class="link-icon"><svg width="22" height="22" viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.88 2.7-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.9v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.66 9c0-.59.1-1.17.29-1.7V4.97H.9A9 9 0 0 0 0 9c0 1.45.35 2.83.9 4.03l3.05-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .9 4.97l3.05 2.33C4.66 5.17 6.65 3.58 9 3.58z"/></svg></div>
                    <div><h3 style="margin:0;">Google</h3><div style="color:var(--muted); font-size:12.5px;">Вход в один клик, без пароля</div></div></div>
                    <span class="status <?=$has_google ? "on" : ""?>"><?=$has_google ? "Привязан" : "Не привязан"?></span>
                </div>
                <?php if ($has_google): ?>
                    <div class="link-who"><?php if (!empty($target["google_avatar"])): ?><img src="<?=htmlspecialchars($target["google_avatar"])?>" alt=""><?php endif; ?><div><b style="color:#fff;"><?=htmlspecialchars($target["google_name"] ?? "")?></b><?php if (!empty($target["google_email"])): ?><br><span style="font-size:12.5px;"><?=htmlspecialchars($target["google_email"])?></span><?php endif; ?></div></div>
                    <form method="POST" action="cabinet.php#links" onsubmit="return confirm('Отвязать Google-аккаунт?');">
                        <input type="hidden" name="action" value="unlink_google">
                        <button class="btn btn-danger btn-sm">Отвязать Google</button>
                    </form>
                <?php else: ?>
                    <a href="google_start.php?mode=link" class="btn btn-google btn-block">Привязать Google</a>
                <?php endif; ?>
            </div>

            <!-- Telegram -->
            <div class="card">
                <div class="link-head">
                    <div style="display:flex; gap:12px; align-items:center;"><div class="link-icon" style="background:rgba(42,171,238,.12);"><svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="#2AABEE" d="M21.9 4.3 18.7 19.4c-.2 1.1-.9 1.3-1.8.8l-4.9-3.6-2.4 2.3c-.3.3-.5.5-1 .5l.3-5 9.2-8.3c.4-.4-.1-.6-.6-.2L6.1 13 1.2 11.5c-1.1-.3-1.1-1.1.2-1.6L20.5 2.6c.9-.3 1.7.2 1.4 1.7z"/></svg></div>
                    <div><h3 style="margin:0;">Telegram-бот</h3><div style="color:var(--muted); font-size:12.5px;">Уведомления и код входа</div></div></div>
                    <span class="status <?=$has_tg ? "on" : ""?>"><?=$has_tg ? "Привязан" : "Не привязан"?></span>
                </div>
                <?php if ($has_tg): ?>
                    <div class="link-who">🤖 <div><?php if (!empty($target["tg_username"])): ?><b style="color:#fff;">@<?=htmlspecialchars($target["tg_username"])?></b><br><?php endif; ?><span style="font-size:12.5px;"><?= $target_is_staff ? "🔐 Вход в админ-панель защищён кодом из бота" : "Бот присылает уведомления" ?></span></div></div>
                    <form method="POST" action="cabinet.php#links" onsubmit="return confirm('Отвязать Telegram? Код из бота при входе больше спрашиваться не будет — только пароль.');">
                        <input type="hidden" name="action" value="unlink_telegram">
                        <button class="btn btn-danger btn-sm">Отвязать Telegram</button>
                    </form>
                <?php else: ?>
                    <p class="desc" style="margin:12px 0 0;">Необязательно. Если привязать<?= $target_is_staff ? "" : " и потом попасть в команду" ?>, при входе в админ-панель бот будет присылать код подтверждения (2FA) — это защитит аккаунт, даже если пароль узнают.</p>
                    <?php if ($tg_link_code): ?>
                        <div class="code-box"><code id="tgCode"><?=htmlspecialchars($tg_link_code)?></code><button type="button" class="btn btn-ghost btn-sm" style="margin:0;" onclick="copyText('/link <?=htmlspecialchars($tg_link_code)?>', this)">📋 Копировать</button></div>
                        <ol class="steps">
                            <li><span>Откройте бота <a href="https://t.me/<?=htmlspecialchars(rawurlencode($bot_username))?>" target="_blank" rel="noopener"><b>@<?=htmlspecialchars($bot_username)?></b></a> в Telegram.</span></li>
                            <li><span>Отправьте ему: <kbd>/link <?=htmlspecialchars($tg_link_code)?></kbd></span></li>
                            <li><span>Код действует 15 минут. После ответа бота обновите эту страницу.</span></li>
                        </ol>
                    <?php endif; ?>
                    <form method="POST" action="cabinet.php#links">
                        <input type="hidden" name="action" value="generate_tg_code">
                        <button class="btn btn-tg btn-block"><?= $tg_link_code ? "🔄 Новый код" : "Привязать Telegram" ?></button>
                    </form>
                <?php endif; ?>
            </div>
        </div>

        <div class="section-title" id="security">Безопасность</div>
        <div class="grid">
            <div class="card">
                <h3>🔒 Смена пароля</h3>
                <p class="desc">Не короче 6 символов. Лучше длинный и с цифрами.</p>
                <form method="POST" action="cabinet.php#security">
                    <input type="hidden" name="action" value="change_password">
                    <label class="field-label">Текущий пароль</label>
                    <div class="pass-wrap"><input type="password" name="current_password" required autocomplete="current-password"><button type="button" class="pass-eye" onclick="togglePass(this)" aria-label="Показать пароль">👁</button></div>
                    <label class="field-label">Новый пароль</label>
                    <div class="pass-wrap"><input type="password" name="new_password" id="newPass" required autocomplete="new-password"><button type="button" class="pass-eye" onclick="togglePass(this)" aria-label="Показать пароль">👁</button></div>
                    <div class="meter"><span id="passMeter"></span></div>
                    <div class="hint"><span id="passHint">Введите новый пароль</span></div>
                    <label class="field-label">Повторите новый пароль</label>
                    <div class="pass-wrap"><input type="password" name="new_password2" id="newPass2" required autocomplete="new-password"><button type="button" class="pass-eye" onclick="togglePass(this)" aria-label="Показать пароль">👁</button></div>
                    <div class="hint"><span id="passMatch"></span></div>
                    <button class="btn btn-block">Сменить пароль</button>
                </form>
            </div>
            <div class="card">
                <h3>🛡️ Защита входа</h3>
                <p class="desc">Как сейчас защищён ваш аккаунт.</p>
                <div class="kv"><span>Пароль</span><b>✓ установлен</b></div>
                <div class="kv"><span>Вход через Google</span><b><?=$has_google ? "✓ включён" : "—"?></b></div>
                <div class="kv"><span>Telegram</span><b><?=$has_tg ? "✓ привязан" : "—"?></b></div>
                <?php if ($target_is_staff): ?>
                    <div class="kv"><span>Вход в админ-панель</span><b><?=$has_tg ? "пароль + код 🔐" : "только пароль"?></b></div>
                    <?php if (!$has_tg): ?><a href="#links" class="btn btn-tg btn-sm btn-block">Включить код из Telegram</a><?php endif; ?>
                <?php endif; ?>
            </div>
        </div>

        <div class="section-title" id="apps">Заявки</div>
        <div class="card">
            <?php if (!$my_apps): ?>
                <div class="empty">Вы ещё не подавали заявок в команду.<br><a href="index.php#join" class="btn btn-sm">Подать заявку</a></div>
            <?php else: ?>
                <ul class="apps">
                    <?php foreach (array_reverse($my_apps) as $a): $a_st = $a["status"] ?? "new"; ?>
                        <li>
                            <div class="a-ico"><?= mb_stripos($a["type"] ?? "", "админ") !== false ? "🛡️" : "👥" ?></div>
                            <div class="a-main">
                                <div class="a-title">Заявка «<?=htmlspecialchars($a["type"] ?? "Заявка")?>»</div>
                                <div class="a-date"><?=htmlspecialchars($a["date"] ?? $a["time"] ?? "")?><?php if ($a_st === "resolved_accept" && !empty($a["direction"])): ?> · стажёр, направление «<?=htmlspecialchars($a["direction"])?>»<?php endif; ?><?php if (!empty($a["comment"])): ?> · «<?=htmlspecialchars($a["comment"])?>»<?php endif; ?></div>
                            </div>
                            <span class="status <?=$app_status_class[$a_st] ?? ""?>"><?=htmlspecialchars($app_status_names[$a_st] ?? $a_st)?></span>
                        </li>
                    <?php endforeach; ?>
                </ul>
                <a href="index.php#join" class="btn btn-ghost btn-sm">Подать ещё одну заявку</a>
            <?php endif; ?>
        </div>

        <div class="section-title" id="achievements">Достижения</div>
        <div class="grid">
            <div class="card">
                <h3>🦑 Игра в кальмара</h3>
                <p class="desc"><?= !empty($my_squid["completed"]) ? "Все три сезона пройдены — вы в претендентах на золотой билет!" : "Пройдите все 3 сезона, чтобы попасть в претенденты на 🎫 Золотой билет RTeam." ?></p>
                <div class="seasons">
                    <?php foreach ([["🚦", "Красный свет"], ["🍪", "Дальгона"], ["🌉", "Стеклянный мост"]] as $si => [$sico, $sname]): ?>
                        <div class="season<?= $squid_season > $si ? " done" : "" ?>"><div class="s-ico"><?=$sico?></div><div class="s-name"><?=$sname?></div></div>
                    <?php endforeach; ?>
                </div>
            </div>
            <div class="card<?= !empty($target["golden"]) ? " gold" : "" ?>">
                <h3>🎫 Золотой билет</h3>
                <?php if (!empty($target["golden"])): ?>
                    <p class="desc" style="color:#d8c38a;">У вас есть «<?=htmlspecialchars($target["golden_title"] ?? "Золотой билет RTeam")?>» — премиальный профиль и личный чат с сотрудником.</p>
                    <a href="profile.php" class="btn btn-gold btn-sm">Открыть золотой профиль</a>
                <?php else: ?>
                    <p class="desc">Билет выдаётся победителям розыгрышей и испытаний: золотой профиль, отметка в рейтинге и личный чат с командой.</p>
                    <div class="empty" style="padding:16px;">Пока нет — всё впереди ✨</div>
                <?php endif; ?>
            </div>
        </div>

        <div class="section-title" id="account">Аккаунт</div>
        <div class="card">
            <div class="kv"><span>Логин</span><b><?=htmlspecialchars($me)?></b></div>
            <div class="kv"><span>Роль</span><b><?=$target_role_info["icon"]?> <?=htmlspecialchars($target_role_label)?></b></div>
            <?php if (!empty($target["email"])): ?><div class="kv"><span>Email</span><b><?=htmlspecialchars($target["email"])?></b></div><?php endif; ?>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <?php if ($target_is_staff): ?><a href="admin.php" class="btn btn-sm">🛠 Открыть админ-панель</a><?php endif; ?>
                <a href="cabinet.php?u=<?=urlencode($me)?>" class="btn btn-ghost btn-sm">👁 Как видят мой профиль</a>
                <a href="index.php?logout=1" class="btn btn-danger btn-sm">⎋ Выйти из аккаунта</a>
            </div>
        </div>
    <?php endif; ?>

</main>

<script>
function toast(text, type) {
    const t = document.createElement('div'); t.className = 'toast ' + (type || ''); t.textContent = text;
    document.getElementById('toasts').appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 450); }, 5000);
}
<?php if ($error): ?>toast(<?=json_encode($error, JSON_UNESCAPED_UNICODE)?>, 'err');<?php endif; ?>
<?php if ($success): ?>toast(<?=json_encode($success, JSON_UNESCAPED_UNICODE)?>, 'ok');<?php endif; ?>

function copyText(text, btn) {
    const done = () => { const o = btn.textContent; btn.textContent = '✓ Скопировано'; setTimeout(() => btn.textContent = o, 1600); };
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, () => prompt('Скопируйте:', text));
    else prompt('Скопируйте:', text);
}
function togglePass(btn) {
    const i = btn.previousElementSibling; const show = i.type === 'password';
    i.type = show ? 'text' : 'password'; btn.textContent = show ? '🙈' : '👁';
}
(function () {
    // Живой предпросмотр аватара и счётчик «о себе»
    const av = document.getElementById('avInput'), prev = document.getElementById('avPrev');
    if (av && prev) av.addEventListener('input', () => {
        const v = av.value.trim();
        if (/^https?:\/\//i.test(v)) { prev.innerHTML = ''; const img = new Image(); img.src = v; img.alt = ''; img.onerror = () => { prev.textContent = '?'; }; prev.appendChild(img); }
        else prev.textContent = <?=json_encode($initial, JSON_UNESCAPED_UNICODE)?>;
    });
    const bio = document.getElementById('bioInput'), cnt = document.getElementById('bioCount');
    if (bio && cnt) { const upd = () => cnt.textContent = bio.value.length + '/500'; bio.addEventListener('input', upd); upd(); }

    // Надёжность нового пароля и совпадение
    const p1 = document.getElementById('newPass'), p2 = document.getElementById('newPass2');
    const meter = document.getElementById('passMeter'), hint = document.getElementById('passHint'), match = document.getElementById('passMatch');
    function check() {
        if (!p1) return;
        const v = p1.value; let s = 0;
        if (v.length >= 6) s++; if (v.length >= 10) s++; if (/[0-9]/.test(v) && /[a-zа-я]/i.test(v)) s++; if (/[^a-zа-я0-9]/i.test(v) || /[A-ZА-Я]/.test(v) && /[a-zа-я]/.test(v)) s++;
        const lv = [["", "Введите новый пароль", "0%"], ["#ef4444", "Слабый", "25%"], ["#f59e0b", "Средний", "50%"], ["#84cc16", "Хороший", "75%"], ["#22c55e", "Надёжный", "100%"]][v ? Math.max(1, s) : 0];
        meter.style.width = lv[2]; meter.style.background = lv[0]; hint.textContent = v && v.length < 6 ? "Слишком короткий — нужно от 6 символов" : lv[1];
        if (p2.value) { match.textContent = p1.value === p2.value ? "✓ Пароли совпадают" : "✕ Пароли не совпадают"; match.style.color = p1.value === p2.value ? "#6ee7a0" : "#ff9b9b"; } else match.textContent = "";
    }
    if (p1) { p1.addEventListener('input', check); p2.addEventListener('input', check); }

    // Подсветка текущего раздела в навигации
    const links = [...document.querySelectorAll('.subnav a')];
    if (links.length && 'IntersectionObserver' in window) {
        const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) links.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#' + e.target.id)); }), { rootMargin: '-40% 0px -55% 0px' });
        links.forEach(a => { const t = document.querySelector(a.getAttribute('href')); if (t) io.observe(t); });
    }
})();
</script>
<?= rt_rai_widget($settings ?? [], $me ?? null) /* помощник Rai: кнопка ✨, нейросеть с GitHub */ ?>
</body>
</html>
<?php if ($is_own) unset($_SESSION["tg_link_code"]); ?>
