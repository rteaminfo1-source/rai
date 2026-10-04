<?php
session_start();

function load_json($file, $default) {
    if (!file_exists($file)) file_put_contents($file, json_encode($default, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    $data = json_decode(file_get_contents($file), true);
    return $data ?: $default;
}
function save_json($file, $data) {
    file_put_contents($file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

require_once __DIR__ . '/_roles.php'; // IP, баны и ИИ поддержки (общий файл с admin.php)

$settings = load_json("settings.json", []);
$accent = preg_match('/^#[0-9a-fA-F]{3,8}$/', $settings["accent"] ?? "") ? $settings["accent"] : "#ff2a2a";
$is_ajax = isset($_GET['ajax_html_ticket']) || isset($_GET['ajax_client_ticket_list']) || isset($_POST['is_ajax']);

/* IP посетителя: сохраняется в тикете и каждом ответе клиента — в админ-панели
   рядом с сообщением видно, откуда оно пришло, и этот IP можно забанить.
   Забаненный IP (вкладка «Баны» в админ-панели) писать в поддержку не может. */
$client_ip = rt_client_ip();
$ip_ban = rt_active_ban($client_ip);
if ($ip_ban) {
    http_response_code(403);
    if ($is_ajax) {
        header('Content-Type: application/json');
        echo json_encode(["html" => "", "status" => "Закрыт", "error" => "banned"]);
        exit;
    }
    $ban_until = (int)($ip_ban["expires"] ?? 0) === 0 ? "навсегда" : "до " . date("d.m.Y H:i", (int)$ip_ban["expires"]);
    ?><!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Доступ ограничен — RTeam</title>
    <style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:radial-gradient(700px 400px at 50% 0%,rgba(239,68,68,.16),transparent 70%),#07070b;color:#ececf2;font-family:Inter,"Segoe UI",system-ui,Arial,sans-serif;padding:20px;box-sizing:border-box}
    .box{max-width:460px;padding:30px;border-radius:20px;text-align:center;border:1px solid transparent;background:linear-gradient(180deg,rgba(23,23,33,.95),rgba(13,13,20,.95)) padding-box,linear-gradient(180deg,rgba(239,68,68,.55),rgba(239,68,68,.08)) border-box;box-shadow:0 30px 60px -30px rgba(0,0,0,.9)}
    .ico{width:64px;height:64px;margin:0 auto 14px;border-radius:18px;display:grid;place-items:center;font-size:30px;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.35)}
    h1{font-size:21px;margin:0 0 10px}p{color:#b4b4c3;line-height:1.55;margin:6px 0}b{color:#fff}</style></head>
    <body><div class="box"><div class="ico">🚫</div><h1>Поддержка недоступна</h1><p>Ваш IP-адрес заблокирован администрацией <?=htmlspecialchars($ban_until)?>.</p><p><b>Причина:</b> <?=htmlspecialchars($ip_ban["reason"] ?? "Нарушение правил")?></p></div></body></html><?php
    exit;
}

/* Вход на сайте (login.php) действует и в поддержке — второй раз вводить пароль не нужно */
if (empty($_SESSION["client_user"]) && !empty($_SESSION["user"])) {
    $site_users = load_json("users.json", []);
    if (isset($site_users[$_SESSION["user"]])) $_SESSION["client_user"] = $_SESSION["user"];
}
$client = $_SESSION["client_user"] ?? null;

/* ============================================================
   Тикеты
   ============================================================ */

const SUP_PENDING_TTL = 300; // ИИ, не ответивший за 5 минут, больше не ждём — тикет остаётся администратору

function sup_idx($tickets, $id, $client) {
    if (!$client) return null;
    foreach ($tickets as $k => $t) {
        if ((string)($t["id"] ?? "") === (string)$id && ($t["client"] ?? null) === $client) return $k;
    }
    return null;
}

function sup_status($s) {
    $map = [
        "Открыт"                 => ["Открыт", "st-wait"],
        "Ожидает ответа клиента" => ["Есть ответ", "st-ok"],
        "Ждёт администратора"    => ["Ждёт администратора", "st-view"],
        "Закрыт"                 => ["Закрыт", "st-off"],
    ];
    return $map[$s] ?? [$s, "st-wait"];
}

function sup_ai_pending($t) {
    return !empty($t["ai_pending"]) && time() - (int)$t["ai_pending"] < SUP_PENDING_TTL;
}

function sup_initial($name) {
    return htmlspecialchars(mb_strtoupper(mb_substr(trim((string)$name) ?: "R", 0, 1)));
}

/* Одно сообщение чата (страница и AJAX рисуют одинаково) */
function sup_render_reply($r) {
    $date = htmlspecialchars($r["date"] ?? "");
    $text = nl2br(htmlspecialchars((string)($r["text"] ?? "")));
    if (!empty($r["is_system"])) {
        return '<div class="sys"><span>' . $text . '</span><time>' . $date . '</time></div>';
    }
    $photo = "";
    if (!empty($r["photo"])) {
        $src = htmlspecialchars($r["photo"]);
        $photo = '<a class="b-photo" href="' . $src . '" target="_blank" rel="noopener"><img src="' . $src . '" alt="Фото" loading="lazy"></a>';
    }
    if (!empty($r["is_ai"])) {
        $cls = "ai";
        $who = '<span class="ava ai-ava">✨</span><b>Rai</b><span class="tag tag-ai">ИИ-помощник</span>';
    } elseif ($r["is_admin"] ?? true) {
        $cls = "staff";
        $name = (string)($r["employee"] ?? "Поддержка");
        $who = '<span class="ava">' . sup_initial($name) . '</span><b>' . htmlspecialchars($name) . '</b><span class="tag">RTeam</span>';
    } else {
        $cls = "me";
        $who = '<b>Вы</b>';
    }
    return '<div class="msg ' . $cls . '"><div class="bubble"><div class="b-head">' . $who . '<time>' . $date . '</time></div>'
         . '<div class="b-text">' . $text . '</div>' . $photo . '</div></div>';
}

function sup_render_list($tickets, $client, $active_id) {
    $mine = $client ? array_filter($tickets, fn($t) => ($t["client"] ?? null) === $client) : [];
    if (!$mine) return '<div class="list-empty">Обращений пока нет.<br>Создайте первое — ответим сразу.</div>';
    $html = "";
    foreach (array_reverse($mine) as $t) {
        [$label, $cls] = sup_status($t["status"] ?? "Открыт");
        $id = htmlspecialchars((string)$t["id"]);
        $reps = (array)($t["replies"] ?? []);
        $last = $reps ? end($reps) : null;
        $preview = $last ? (!empty($last["is_ai"]) ? "Rai: " : (($last["is_admin"] ?? true) && empty($last["is_system"]) ? "Поддержка: " : "")) . ($last["text"] ?? "") : ($t["description"] ?? "");
        $preview = mb_strimwidth(preg_replace('/\s+/u', ' ', (string)$preview), 0, 70, "…");
        $html .= '<a href="?ticket_id=' . urlencode((string)$t["id"]) . '" class="t-item' . ((string)$active_id === (string)$t["id"] ? ' active' : '') . '">'
               . '<div class="t-top"><span class="t-title">' . htmlspecialchars($t["topic"] ?? "") . '</span><span class="t-date">' . htmlspecialchars(substr((string)($t["date"] ?? ""), 5, 11)) . '</span></div>'
               . '<div class="t-prev">' . htmlspecialchars($preview) . '</div>'
               . '<div class="t-meta"><span>#' . $id . '</span><span class="status ' . $cls . '">' . htmlspecialchars($label) . '</span></div></a>';
    }
    return $html;
}

/* Ответ нейросети сохраняется в тикет. Нейросеть — на GitHub (rai-support.js и model.json)
   и работает в браузере клиента; страница только передаёт ей переписку и сохраняет ответ.
   Ответ принимается, только если тикет его ждёт (ai_pending): один ответ на каждое сообщение клиента. */
function sup_ai_save($id, $client, $settings, $text, $handoff, $source, $n, $close = false) {
    return rt_tickets_update(function (&$tickets) use ($id, $client, $settings, $text, $handoff, $source, $n, $close) {
        $k = sup_idx($tickets, $id, $client);
        if ($k === null) return ["ok" => false, "reason" => "gone"];
        $t = &$tickets[$k];
        if (!sup_ai_pending($t) || !rt_ticket_ai_on($t, $settings)) { unset($t["ai_pending"]); return ["ok" => false, "reason" => "taken"]; }
        $now = date("Y-m-d H:i:s");
        $add = [["text" => $text, "photo" => null, "employee" => RT_AI_NAME, "date" => $now,
                 "is_admin" => true, "is_ai" => true, "ai_source" => $source]];
        if ($close) {
            // Клиент написал, что вопрос решён / попросил закрыть — Rai закрывает тикет сам
            $add[] = ["text" => "Rai закрыл тикет: клиент подтвердил, что вопрос решён.", "employee" => "Система",
                      "date" => $now, "is_admin" => true, "is_system" => true];
            $t["status"] = "Закрыт";
            $t["closed"] = ["by" => "ai", "date" => $now];
            $handoff = false;
        } elseif ($handoff) {
            $add[] = ["text" => "ИИ передал тикет администратору. Дальше вам ответит сотрудник RTeam.", "employee" => "Система",
                      "date" => $now, "is_admin" => true, "is_system" => true];
            $t["ai"] = false;
            $t["handoff"] = ["by" => "ai", "date" => $now, "reason" => $source];
            $t["status"] = "Ждёт администратора";
        } else {
            $t["status"] = "Ожидает ответа клиента";
        }
        unset($t["ai_error"]);
        // Ответ ставим сразу после сообщений, на которые он отвечает
        $n = max(0, min((int)$n, count($t["replies"] ?? [])));
        array_splice($t["replies"], $n, 0, $add);
        // Клиент успел дописать ещё — нейросеть ответит и на это
        $again = false;
        if (!$handoff && !$close) foreach (array_slice($t["replies"], $n + count($add)) as $r) if (!($r["is_admin"] ?? true)) $again = true;
        if ($again) { $t["ai_pending"] = time(); $t["status"] = "Открыт"; } else unset($t["ai_pending"]);
        return ["ok" => true, "handoff" => $handoff, "again" => $again, "closed" => $close];
    });
}

/* ---------- AJAX: сообщения тикета ---------- */
if (isset($_GET['ajax_html_ticket'])) {
    header('Content-Type: application/json');
    header('Cache-Control: no-store');
    $tickets_data = load_json("tickets.json", []);
    $k = sup_idx($tickets_data, $_GET['ajax_html_ticket'], $client);
    if ($k === null) { echo json_encode(["html" => "", "status" => "Закрыт", "error" => "not_found"]); exit; }
    $t = $tickets_data[$k];
    $html = "";
    foreach ($t["replies"] ?? [] as $reply) $html .= sup_render_reply($reply);
    [$label, $cls] = sup_status($t["status"]);
    echo json_encode([
        "html" => $html, "status" => $t["status"], "status_label" => $label, "status_class" => $cls,
        "ai_on" => rt_ticket_ai_on($t, $settings), "ai_ready" => rt_support_ai_ready($settings),
        "ai_pending" => sup_ai_pending($t) && rt_ticket_ai_on($t, $settings),
    ] + rt_ticket_ai_payload($t), JSON_UNESCAPED_UNICODE);
    exit;
}

/* ---------- AJAX: список тикетов слева ---------- */
if (isset($_GET['ajax_client_ticket_list'])) {
    header('Content-Type: application/json');
    header('Cache-Control: no-store');
    echo json_encode(["html" => sup_render_list(load_json("tickets.json", []), $client, $_GET['active_id'] ?? null)], JSON_UNESCAPED_UNICODE);
    exit;
}

/* ---------- AJAX: ответ нейросети из браузера ---------- */
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["ai_reply"])) {
    header('Content-Type: application/json');
    $text = trim((string)($_POST["text"] ?? ""));
    $source = preg_replace('/[^a-z0-9_:\-]/i', '', (string)($_POST["source"] ?? ""));
    if (!$client || $text === "") { echo json_encode(["ok" => false]); exit; }
    echo json_encode(sup_ai_save((string)($_POST["id"] ?? ""), $client, $settings, mb_substr($text, 0, 4000),
                                 ($_POST["handoff"] ?? "") === "1", mb_substr($source, 0, 40), (int)($_POST["n"] ?? 0),
                                 ($_POST["close"] ?? "") === "1"));
    exit;
}
/* Нейросеть не загрузилась (GitHub недоступен и т.п.): тикет остаётся администратору */
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["ai_fail"])) {
    header('Content-Type: application/json');
    $id = (string)($_POST["id"] ?? "");
    $err = mb_substr(trim((string)($_POST["error"] ?? "")), 0, 200);
    if ($client) rt_tickets_update(function (&$tickets) use ($id, $client, $err) {
        $k = sup_idx($tickets, $id, $client);
        if ($k === null || empty($tickets[$k]["ai_pending"])) return;
        unset($tickets[$k]["ai_pending"]);
        $tickets[$k]["ai_error"] = ["date" => date("Y-m-d H:i:s"), "text" => "нейросеть не загрузилась у клиента" . ($err !== "" ? ": $err" : "")];
    });
    echo json_encode(["ok" => true]);
    exit;
}

/* ---------- Вход и регистрация ---------- */
$error = "";
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["auth_action"])) {
    $users = load_json("users.json", []);
    $login = trim($_POST["login"] ?? "");
    $pass = trim($_POST["password"] ?? "");

    if ($_POST["auth_action"] === "register") {
        if ($login === "" || $pass === "") $error = "Заполните логин и пароль.";
        elseif (mb_strlen($login) < 3 || mb_strlen($login) > 32) $error = "Логин — от 3 до 32 символов.";
        elseif (isset($users[$login])) $error = "Такой логин уже занят.";
        elseif (mb_strlen($pass) < 6) $error = "Пароль — не короче 6 символов.";
        else {
            $users[$login] = ["password" => $pass, "role" => "Пользователь"];
            rt_track_ip($users[$login], $client_ip);
            save_json("users.json", $users);
            $_SESSION["client_user"] = $login;
        }
    } elseif ($_POST["auth_action"] === "login") {
        if (isset($users[$login]) && ($users[$login]["password"] ?? null) === $pass) {
            $_SESSION["client_user"] = $login;
            rt_track_ip($users[$login], $client_ip);
            save_json("users.json", $users);
        } else {
            $error = "Неверный логин или пароль.";
        }
    }
    if ($error === "") { header("Location: support.php"); exit; }
}

if (isset($_GET["logout"])) { unset($_SESSION["client_user"]); header("Location: support.php"); exit; }

/* ---------- Новый тикет ---------- */
if ($client && $_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["create_ticket"])) {
    $topic = ($_POST["topic"] ?? "") === "other" ? trim($_POST["custom_topic"] ?? "") : trim($_POST["topic"] ?? "");
    $desc = trim($_POST["description"] ?? "");
    if ($topic === "" || $desc === "") {
        $error = "Выберите тему и опишите вопрос.";
    } else {
        $photo_path = rt_save_image_upload($_FILES["photo"] ?? [], "");
        $ai_on = rt_support_ai_ready($settings);
        $ticket = [
            "id" => 0, "client" => $client, "topic" => mb_substr($topic, 0, 100),
            "description" => mb_substr($desc, 0, 5000), "photo" => $photo_path, "status" => "Открыт",
            "date" => date("Y-m-d H:i:s"), "replies" => [], "pinned_photo" => false,
            "ip" => $client_ip,
        ];
        if ($ai_on) $ticket["ai_pending"] = time(); // ИИ ответит, как только откроется страница тикета
        $new_id = rt_tickets_update(function (&$tickets) use ($ticket) {
            // Номер тикета — время создания; два тикета в одну секунду получают разные номера
            $ids = array_flip(array_map(fn($t) => (string)($t["id"] ?? ""), $tickets));
            $ticket["id"] = time();
            while (isset($ids[(string)$ticket["id"]])) $ticket["id"]++;
            $tickets[] = $ticket;
            return $ticket["id"];
        });
        header("Location: support.php" . ($new_id ? "?ticket_id=" . $new_id : "")); exit;
    }
}

/* ---------- Ответ клиента ---------- */
if ($client && $_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["reply_ticket"])) {
    $id = (string)($_POST["id"] ?? "");
    $text = trim($_POST["reply_text"] ?? "");
    $photo = rt_save_image_upload($_FILES["reply_photo"] ?? [], "reply_");
    $res = ["ok" => false];
    if ($text !== "" || $photo) {
        $res = rt_tickets_update(function (&$tickets) use ($id, $client, $text, $photo, $client_ip, $settings) {
            $k = sup_idx($tickets, $id, $client);
            if ($k === null || ($tickets[$k]["status"] ?? "") === "Закрыт") return ["ok" => false];
            $t = &$tickets[$k];
            $t["replies"][] = [
                "text" => mb_substr($text !== "" ? $text : "📷 Фото", 0, 5000), "photo" => $photo,
                "author" => $client, "date" => date("Y-m-d H:i:s"), "is_admin" => false, "ip" => $client_ip,
            ];
            $t["last_ip"] = $client_ip;
            $ai = rt_ticket_ai_on($t, $settings);
            if ($ai) { $t["ai_pending"] = time(); $t["status"] = "Открыт"; }
            elseif (($t["status"] ?? "") !== "Ждёт администратора") $t["status"] = "Открыт";
            return ["ok" => true, "ai" => $ai];
        }) ?: ["ok" => false];
    }
    if (isset($_POST["is_ajax"])) { header('Content-Type: application/json'); echo json_encode($res); exit; }
    header("Location: support.php?ticket_id=" . urlencode($id)); exit;
}

/* ---------- «Позвать администратора»: ИИ отключается, отвечает человек ---------- */
if ($client && $_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["call_admin"])) {
    $id = (string)($_POST["id"] ?? "");
    $res = rt_tickets_update(function (&$tickets) use ($id, $client) {
        $k = sup_idx($tickets, $id, $client);
        if ($k === null || ($tickets[$k]["status"] ?? "") === "Закрыт") return ["ok" => false];
        $t = &$tickets[$k];
        if (($t["ai"] ?? true) === false) return ["ok" => true];
        $now = date("Y-m-d H:i:s");
        $t["ai"] = false;
        unset($t["ai_pending"]);
        $t["handoff"] = ["by" => "client", "date" => $now];
        $t["status"] = "Ждёт администратора";
        $t["replies"][] = ["text" => "Вы позвали администратора. ИИ отключён — дальше вам ответит сотрудник RTeam.",
                           "employee" => "Система", "date" => $now, "is_admin" => true, "is_system" => true];
        return ["ok" => true];
    }) ?: ["ok" => false];
    if (isset($_POST["is_ajax"])) { header('Content-Type: application/json'); echo json_encode($res); exit; }
    header("Location: support.php?ticket_id=" . urlencode($id)); exit;
}

$tickets = load_json("tickets.json", []);
$active_ticket_id = $_GET["ticket_id"] ?? null;
$is_new_ticket = isset($_GET["new_ticket"]) || ($client && isset($_POST["create_ticket"]));
$ai_ready = rt_support_ai_ready($settings);

$current_ticket = null;
if ($client && $active_ticket_id !== null) {
    $k = sup_idx($tickets, $active_ticket_id, $client);
    if ($k !== null) $current_ticket = $tickets[$k];
}
$my_count = $client ? count(array_filter($tickets, fn($t) => ($t["client"] ?? null) === $client)) : 0;

$topics = [
    "Багги"                     => ["🐞", "Баги и ошибки", "Что-то не работает на сайте"],
    "Подписка или платёж"       => ["💳", "Подписка или платёж", "Оплата, возврат, чек"],
    "Апеляция Rteamvisuals"     => ["⚖️", "Апелляция Rteamvisuals", "Обжаловать решение"],
    "Тех вопрос Rteamvisuals"   => ["🛠️", "Тех. вопрос Rteamvisuals", "Как что-то сделать"],
    "Багги/Ошибки Rteamvisuals" => ["🎨", "Ошибки Rteamvisuals", "Баги в Rteamvisuals"],
    "Вопросы по Дневнику"       => ["📒", "Дневник", "Электронный журнал школы"],
    // Rai — ИИ-ассистент на rai.rteam.info
    "Rai: ответы и ошибки"      => ["🤖", "Rai: ответы и ошибки", "Не отвечает, ошибается, не грузится"],
    "Rai: аккаунт и чаты"       => ["👤", "Rai: аккаунт и чаты", "Вход, Google, пропали чаты"],
    "Rai: нейросеть"            => ["🧠", "Rai: нейросеть", "Модели Qwen в браузере"],
    "Rai: Code"                 => ["💻", "Rai Code", "Запуск и проверка кода"],
    "Rai: Слайды"               => ["📽️", "Rai: Слайды", "Презентации, PowerPoint"],
    "AI Studio"                 => ["🎛️", "AI Studio", "Сайты в aistudio.rteam.info"],
    "other"                     => ["✏️", "Другое", "Своя тема"],
];
/* Перед какими темами показать заголовок группы */
$topic_groups = ["Багги" => "RTeam · rteam.info", "Rai: ответы и ошибки" => "Rai · rai.rteam.info", "other" => ""];
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Поддержка — RTeam</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
    --accent: <?=htmlspecialchars($accent)?>;
    --bg: #07070b; --text: #ececf2; --soft: #b4b4c3; --muted: #747487;
    --line: rgba(255,255,255,.07); --line-2: rgba(255,255,255,.12);
    --ok: #22c55e; --warn: #f59e0b; --danger: #ef4444; --info: #3b82f6; --ai: #a78bfa;
    --font: "Inter", "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
    --top: 64px;
}
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; color: var(--text); font-family: var(--font); font-size: 14px; line-height: 1.55; letter-spacing: -.006em; -webkit-font-smoothing: antialiased;
    background: var(--bg);
    background: radial-gradient(1100px 600px at 105% -10%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 60%),
                radial-gradient(900px 500px at -15% 110%, rgba(120,90,255,.08), transparent 60%), var(--bg);
    background-attachment: fixed; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image: radial-gradient(rgba(255,255,255,.045) 1px, transparent 1px); background-size: 24px 24px;
    -webkit-mask-image: linear-gradient(180deg, #000, transparent 65%); mask-image: linear-gradient(180deg, #000, transparent 65%); }
a { color: color-mix(in srgb, var(--accent) 70%, #fff); text-decoration: none; }
::selection { background: color-mix(in srgb, var(--accent) 45%, transparent); }

/* Верхняя панель */
.top { position: sticky; top: 0; z-index: 40; height: var(--top); display: flex; align-items: center; gap: 12px; padding: 0 24px;
    background: rgba(8,8,12,.62); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border-bottom: 1px solid var(--line); }
.brand { display: flex; align-items: center; gap: 10px; color: #fff; font-weight: 800; letter-spacing: .06em; }
.brand-logo { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; color: #fff;
    background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 50%, #6b0000)); box-shadow: 0 6px 18px color-mix(in srgb, var(--accent) 40%, transparent); }
.brand small { display: block; font-size: 11px; font-weight: 600; letter-spacing: .02em; color: var(--muted); }
.top-links { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.me-chip { display: inline-flex; align-items: center; gap: 8px; padding: 4px 12px 4px 4px; border-radius: 999px; border: 1px solid var(--line-2); background: rgba(255,255,255,.04); color: #fff; font-weight: 600; font-size: 13px; }
.me-chip .ava { width: 26px; height: 26px; font-size: 12px; }

/* Карточки */
.card { border: 1px solid transparent; border-radius: 18px;
    background: linear-gradient(180deg, rgba(23,23,33,.92), rgba(13,13,20,.92)) padding-box,
                linear-gradient(180deg, rgba(255,255,255,.11), rgba(255,255,255,.025) 60%, rgba(255,255,255,.05)) border-box;
    box-shadow: 0 1px 0 rgba(255,255,255,.04) inset, 0 18px 40px -26px rgba(0,0,0,.8); }

/* Кнопки */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 16px; border-radius: 11px; border: 1px solid transparent;
    font: inherit; font-weight: 700; font-size: 14px; color: #fff; cursor: pointer; text-decoration: none !important; white-space: nowrap;
    background: linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 75%, #000));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.25), 0 8px 22px -8px color-mix(in srgb, var(--accent) 70%, transparent);
    transition: transform .12s, filter .15s, background .15s; }
.btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
.btn:disabled { opacity: .55; cursor: default; transform: none; filter: none; }
.btn-ghost { background: rgba(255,255,255,.04); border-color: var(--line-2); color: var(--text); box-shadow: none; }
.btn-ghost:hover { background: rgba(255,255,255,.08); }
.btn-human { background: rgba(245,158,11,.1); border-color: rgba(245,158,11,.45); color: #fcd34d; box-shadow: none; }
.btn-human:hover { background: rgba(245,158,11,.18); }
.btn-sm { padding: 7px 12px; font-size: 13px; border-radius: 10px; }
.btn-block { width: 100%; }

/* Поля */
input, textarea, select { width: 100%; padding: 11px 13px; border-radius: 11px; border: 1px solid rgba(255,255,255,.1); background: rgba(6,6,10,.7); color: #fff; font: inherit; font-size: 14px; transition: border-color .15s, box-shadow .15s; }
input:focus, textarea:focus { outline: none; border-color: color-mix(in srgb, var(--accent) 70%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent); }
label.lbl { display: block; font-size: 12.5px; color: var(--soft); margin: 16px 0 7px; font-weight: 600; }

/* Статусы */
.status { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 700; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--line-2); white-space: nowrap; }
.status::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.st-ok { color: #6ee7a0; border-color: rgba(34,197,94,.35); background: rgba(34,197,94,.1); }
.st-view { color: #fcc56b; border-color: rgba(245,158,11,.35); background: rgba(245,158,11,.1); }
.st-wait { color: #8bb8ff; border-color: rgba(59,130,246,.35); background: rgba(59,130,246,.1); }
.st-off { color: var(--muted); background: rgba(255,255,255,.03); }

/* Аватары */
.ava { width: 30px; height: 30px; border-radius: 50%; flex: none; display: inline-grid; place-items: center; font-size: 13px; font-weight: 800; color: #fff;
    background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 40%, #000)); }
.ai-ava { background: linear-gradient(135deg, #8b5cf6, #ec4899); box-shadow: 0 0 16px rgba(167,139,250,.45); font-size: 14px; }

/* ===== Вход ===== */
.auth { position: relative; z-index: 1; min-height: calc(100vh - var(--top)); display: grid; place-items: center; padding: 30px 16px; }
.auth-box { width: 100%; max-width: 900px; display: grid; grid-template-columns: 1.05fr 1fr; overflow: hidden; }
.auth-side { padding: 36px; position: relative; border-right: 1px solid var(--line);
    background: radial-gradient(500px 260px at 0% 0%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 70%),
                radial-gradient(400px 260px at 100% 100%, rgba(139,92,246,.18), transparent 70%); }
.auth-side h1 { font-size: 30px; line-height: 1.15; letter-spacing: -.03em; margin: 18px 0 10px; }
.auth-side p { color: var(--soft); margin: 0 0 22px; }
.perks { list-style: none; padding: 0; margin: 0; display: grid; gap: 12px; }
.perks li { display: flex; gap: 12px; align-items: flex-start; color: var(--soft); font-size: 13.5px; }
.perks .p-ico { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; flex: none; background: rgba(255,255,255,.05); border: 1px solid var(--line); font-size: 16px; }
.perks b { color: #fff; display: block; }
.auth-form { padding: 36px; }
.auth-form h2 { margin: 0 0 4px; font-size: 20px; }
.auth-form .sub { color: var(--muted); margin: 0 0 18px; font-size: 13px; }
.auth-err { margin-bottom: 14px; padding: 10px 13px; border-radius: 11px; color: #ffb4b4; background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.35); font-size: 13px; }
.auth-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
.auth-note { margin-top: 16px; font-size: 12.5px; color: var(--muted); }
@media (max-width: 760px) { .auth-box { grid-template-columns: 1fr; } .auth-side { border-right: 0; border-bottom: 1px solid var(--line); padding: 26px; } .auth-form { padding: 26px; } .auth-side h1 { font-size: 24px; } }

/* ===== Приложение ===== */
.app { position: relative; z-index: 1; display: grid; grid-template-columns: 330px 1fr; gap: 16px; max-width: 1280px; margin: 0 auto; padding: 16px;
    height: calc(100vh - var(--top)); height: calc(100dvh - var(--top)); }
.side { display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.side-head { padding: 16px; border-bottom: 1px solid var(--line); display: grid; gap: 10px; }
.side-title { display: flex; align-items: center; justify-content: space-between; font-weight: 700; color: #fff; }
.side-title span { color: var(--muted); font-weight: 600; font-size: 12.5px; }
.search { position: relative; }
.search input { padding-left: 36px; font-size: 13.5px; }
.search::before { content: "⌕"; position: absolute; left: 13px; top: 50%; transform: translateY(-52%); color: var(--muted); font-size: 17px; }
.t-list { flex: 1; overflow-y: auto; padding: 8px; scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.12) transparent; }
.t-item { display: block; padding: 12px 13px; border-radius: 13px; color: var(--soft); border: 1px solid transparent; transition: background .15s, border-color .15s; margin-bottom: 4px; }
.t-item:hover { background: rgba(255,255,255,.04); }
.t-item.active { background: color-mix(in srgb, var(--accent) 12%, transparent); border-color: color-mix(in srgb, var(--accent) 35%, transparent); }
.t-top { display: flex; align-items: center; gap: 8px; justify-content: space-between; }
.t-title { font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.t-prev { font-size: 12.5px; color: var(--muted); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.t-date { flex: none; font-size: 11px; color: var(--muted); }
.t-meta { display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; color: var(--muted); margin-top: 8px; }
.list-empty { text-align: center; color: var(--muted); padding: 30px 14px; font-size: 13px; line-height: 1.6; }

.main { display: flex; flex-direction: column; min-height: 0; min-width: 0; overflow: hidden; }

/* Шапка чата */
.chat-head { display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.chat-head .back { display: none; }
.ch-info { flex: 1; min-width: 200px; }
.ch-info h2 { margin: 0; font-size: 17px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ch-sub { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 4px; color: var(--muted); font-size: 12.5px; }
.who-chip { display: inline-flex; align-items: center; gap: 7px; padding: 4px 11px 4px 5px; border-radius: 999px; font-size: 12.5px; font-weight: 600; border: 1px solid var(--line-2); background: rgba(255,255,255,.04); color: var(--soft); }
.who-chip .ava { width: 22px; height: 22px; font-size: 11px; }
.who-chip.ai { color: #ddd6fe; border-color: rgba(167,139,250,.4); background: rgba(139,92,246,.1); }
.who-chip.human { color: #fde68a; border-color: rgba(245,158,11,.4); background: rgba(245,158,11,.08); }

/* Сообщения */
.chat { flex: 1; overflow-y: auto; padding: 22px 20px 10px; display: flex; flex-direction: column; gap: 14px; scroll-behavior: smooth;
    scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.12) transparent; }
#repliesContainer { display: flex; flex-direction: column; gap: 14px; }
.msg { display: flex; animation: pop .25s ease both; }
@keyframes pop { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.msg.me { justify-content: flex-end; }
.bubble { max-width: min(76%, 640px); padding: 11px 15px 12px; border-radius: 16px; line-height: 1.5; word-wrap: break-word; overflow-wrap: anywhere; }
.msg.me .bubble { background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 30%, #15151f), color-mix(in srgb, var(--accent) 18%, #101018));
    border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent); border-bottom-right-radius: 5px; }
.msg.staff .bubble { background: rgba(255,255,255,.045); border: 1px solid var(--line-2); border-bottom-left-radius: 5px; }
.msg.ai .bubble { border: 1px solid transparent; border-bottom-left-radius: 5px;
    background: linear-gradient(180deg, rgba(30,24,48,.96), rgba(20,17,32,.96)) padding-box, linear-gradient(135deg, rgba(167,139,250,.75), rgba(236,72,153,.45)) border-box;
    box-shadow: 0 10px 30px -18px rgba(139,92,246,.6); }
.b-head { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; margin-bottom: 6px; font-size: 12.5px; color: #fff; }
.b-head b, .b-head .tag, .b-head time { white-space: nowrap; }
.b-head time { margin-left: auto; padding-left: 10px; color: var(--muted); font-size: 11px; font-weight: 500; }
.b-head .ava { width: 22px; height: 22px; font-size: 11px; }
.msg.me .b-head { justify-content: flex-end; }
.msg.me .b-head time { margin-left: 0; order: -1; padding: 0 6px 0 0; }
.tag { font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px; color: var(--soft); background: rgba(255,255,255,.07); border: 1px solid var(--line); }
.tag-ai { color: #e9d5ff; background: rgba(139,92,246,.2); border-color: rgba(167,139,250,.35); }
.b-text { color: #eee; font-size: 14px; }
.b-photo { display: block; margin-top: 10px; }
.b-photo img { max-width: 100%; max-height: 240px; border-radius: 11px; border: 1px solid var(--line-2); display: block; }
.pin { display: inline-block; margin-top: 8px; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; color: #fff; background: var(--accent); }
.sys { align-self: center; text-align: center; max-width: 520px; font-size: 12.5px; color: #fcd34d; padding: 7px 14px; border-radius: 999px;
    background: rgba(245,158,11,.08); border: 1px dashed rgba(245,158,11,.35); animation: pop .25s ease both; }
.sys time { display: block; font-size: 10.5px; color: var(--muted); }

/* Rai печатает… */
.typing { display: none; align-items: center; gap: 10px; padding: 0 20px 10px; color: #c4b5fd; font-size: 12.5px; }
.typing.on { display: flex; }
.dots { display: inline-flex; gap: 4px; padding: 10px 13px; border-radius: 14px; border-bottom-left-radius: 5px; background: rgba(139,92,246,.12); border: 1px solid rgba(167,139,250,.3); }
.dots i { width: 6px; height: 6px; border-radius: 50%; background: #c4b5fd; animation: blink 1.2s infinite both; }
.dots i:nth-child(2) { animation-delay: .2s; } .dots i:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 80%, 100% { opacity: .25; transform: translateY(0); } 40% { opacity: 1; transform: translateY(-3px); } }

/* Поле ввода */
.composer { padding: 12px 14px 14px; border-top: 1px solid var(--line); }
.composer-row { display: flex; gap: 8px; align-items: flex-end; padding: 6px; border-radius: 15px; background: rgba(6,6,10,.7); border: 1px solid rgba(255,255,255,.1); transition: border-color .15s, box-shadow .15s; }
.composer-row:focus-within { border-color: color-mix(in srgb, var(--accent) 60%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent); }
.composer textarea { border: 0; background: transparent; box-shadow: none !important; resize: none; min-height: 40px; max-height: 160px; padding: 9px 6px; line-height: 1.45; }
.icon-btn { width: 40px; height: 40px; flex: none; border-radius: 11px; display: grid; place-items: center; cursor: pointer; font-size: 17px; color: var(--soft); background: rgba(255,255,255,.04); border: 1px solid var(--line); transition: background .15s; }
.icon-btn:hover { background: rgba(255,255,255,.09); color: #fff; }
.send { width: 40px; height: 40px; padding: 0; flex: none; border-radius: 11px; font-size: 17px; }
.attach-chip { display: none; align-items: center; gap: 8px; margin: 0 0 8px; padding: 6px 8px 6px 6px; border-radius: 11px; background: rgba(255,255,255,.04); border: 1px solid var(--line); font-size: 12.5px; color: var(--soft); width: fit-content; max-width: 100%; }
.attach-chip.on { display: inline-flex; }
.attach-chip img { width: 34px; height: 34px; object-fit: cover; border-radius: 7px; }
.attach-chip button { border: 0; background: transparent; color: var(--muted); cursor: pointer; font-size: 15px; }
.composer-hint { display: flex; justify-content: space-between; gap: 10px; margin-top: 7px; font-size: 11.5px; color: var(--muted); }
.closed-note { margin: 12px 14px 14px; padding: 12px 14px; border-radius: 13px; text-align: center; color: var(--muted); background: rgba(255,255,255,.03); border: 1px dashed var(--line-2); }

/* Пустой экран и новый тикет */
.pad { flex: 1; overflow-y: auto; padding: 30px; }
.welcome { max-width: 640px; margin: auto; text-align: center; padding: 30px 0; }
.welcome .big { width: 74px; height: 74px; margin: 0 auto 16px; border-radius: 22px; display: grid; place-items: center; font-size: 34px;
    background: linear-gradient(135deg, #8b5cf6, #ec4899); box-shadow: 0 18px 40px -14px rgba(139,92,246,.7); }
.welcome h2 { font-size: 24px; margin: 0 0 8px; letter-spacing: -.02em; }
.welcome p { color: var(--soft); margin: 0 auto 22px; max-width: 480px; }
.quick { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-top: 24px; text-align: left; }
.quick a { padding: 13px 14px; border-radius: 14px; border: 1px solid var(--line); background: rgba(255,255,255,.03); color: var(--soft); font-size: 13px; transition: border-color .15s, background .15s, transform .15s; }
.quick a:hover { border-color: color-mix(in srgb, var(--accent) 45%, transparent); background: color-mix(in srgb, var(--accent) 8%, transparent); transform: translateY(-2px); }
.quick b { display: block; color: #fff; margin-top: 4px; }
.new-wrap { max-width: 720px; margin: 0 auto; }
.new-wrap h2 { margin: 0 0 4px; font-size: 22px; letter-spacing: -.02em; }
.new-wrap .sub { color: var(--muted); margin: 0 0 6px; }
.topics { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
.topic { position: relative; }
.topics-head { grid-column: 1 / -1; margin: 6px 0 -2px; color: var(--muted); font-size: 11.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.topics-head:first-child { margin-top: 0; }
.topic input { position: absolute; opacity: 0; pointer-events: none; }
.topic > span { display: flex; gap: 11px; align-items: center; height: 100%; padding: 12px 13px; border-radius: 13px; cursor: pointer; border: 1px solid var(--line); background: rgba(255,255,255,.03); transition: border-color .15s, background .15s; }
.topic > span:hover { border-color: var(--line-2); background: rgba(255,255,255,.05); }
.topic em { font-style: normal; font-size: 20px; width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; flex: none; background: rgba(255,255,255,.05); }
.topic b { display: block; color: #fff; font-size: 13.5px; }
.topic small { color: var(--muted); font-size: 12px; }
.topic input:checked + span { border-color: color-mix(in srgb, var(--accent) 65%, transparent); background: color-mix(in srgb, var(--accent) 12%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent); }
.topic input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }
.drop { display: flex; align-items: center; gap: 14px; padding: 16px; border-radius: 14px; border: 1px dashed var(--line-2); background: rgba(255,255,255,.02); cursor: pointer; color: var(--soft); transition: border-color .15s, background .15s; }
.drop:hover, .drop.over { border-color: color-mix(in srgb, var(--accent) 55%, transparent); background: color-mix(in srgb, var(--accent) 6%, transparent); }
.drop .d-ico { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; font-size: 20px; background: rgba(255,255,255,.05); flex: none; overflow: hidden; }
.drop .d-ico img { width: 100%; height: 100%; object-fit: cover; }
.drop small { display: block; color: var(--muted); }
.ai-note { display: flex; gap: 12px; align-items: center; margin-top: 18px; padding: 12px 14px; border-radius: 13px; font-size: 13px; color: #ddd6fe; background: rgba(139,92,246,.08); border: 1px solid rgba(167,139,250,.3); }
.form-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
.back-m { display: none; }

/* Уведомления */
#toasts { position: fixed; right: 20px; bottom: 20px; z-index: 99; display: flex; flex-direction: column; gap: 10px; max-width: min(420px, calc(100vw - 40px)); }
.toast { padding: 13px 18px; border-radius: 12px; background: rgba(20,20,29,.97); border: 1px solid var(--line-2); border-left: 4px solid var(--info); box-shadow: 0 20px 50px -20px rgba(0,0,0,.9); animation: pop .3s ease both; transition: opacity .4s; }
.toast.ok { border-left-color: var(--ok); } .toast.err { border-left-color: var(--danger); } .toast.warn { border-left-color: var(--warn); }

@media (max-width: 860px) {
    .top { padding: 0 14px; }
    .brand small, .hide-m { display: none; }
    .app { grid-template-columns: 1fr; padding: 10px; }
    .app.has-ticket .side, .app.has-form .side { display: none; }
    .app:not(.has-ticket):not(.has-form) .main { display: none; }
    .chat-head .back, .back-m { display: inline-flex; }
    .bubble { max-width: 88%; }
    .pad { padding: 20px 16px; }
    .topics { grid-template-columns: 1fr 1fr; gap: 8px; }
    .topic > span { padding: 10px; gap: 9px; }
    .topic em { width: 30px; height: 30px; font-size: 17px; }
    .topic small { display: none; }
    .topic b { font-size: 13px; line-height: 1.3; }
    .form-actions .btn { flex: 1; }
    .me-chip { max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; scroll-behavior: auto !important; } }
</style>
</head>
<body>

<header class="top">
    <a class="brand" href="index.php"><span class="brand-logo">R</span><span>RTEAM<small>Центр поддержки</small></span></a>
    <div class="top-links">
        <a class="btn btn-ghost btn-sm hide-m" href="index.php">← На сайт</a>
        <?php if ($client): ?>
            <a class="btn btn-ghost btn-sm hide-m" href="cabinet.php">Кабинет</a>
            <span class="me-chip"><span class="ava"><?=sup_initial($client)?></span><?=htmlspecialchars($client)?></span>
            <a class="btn btn-ghost btn-sm" href="?logout=1" title="Выйти из поддержки">Выйти</a>
        <?php endif; ?>
    </div>
</header>

<?php if (!$client): ?>
<main class="auth">
    <div class="auth-box card">
        <div class="auth-side">
            <span class="brand-logo" style="width:46px;height:46px;border-radius:14px;font-size:20px;font-weight:800;">R</span>
            <h1>Поддержка RTeam</h1>
            <p>Задайте вопрос о сайте, проектах, заявках или оплате — поможем разобраться.</p>
            <ul class="perks">
                <?php if ($ai_ready): ?>
                <li><span class="p-ico">✨</span><div><b>Ответ сразу</b>ИИ-помощник Rai отвечает круглосуточно и знает, как устроен сайт.</div></li>
                <li><span class="p-ico">🙋</span><div><b>Живой сотрудник</b>Кнопка «Позвать администратора» — и дальше отвечает человек.</div></li>
                <?php else: ?>
                <li><span class="p-ico">💬</span><div><b>Чат с поддержкой</b>Сотрудники отвечают прямо в тикете, обычно в течение дня.</div></li>
                <?php endif; ?>
                <li><span class="p-ico">📷</span><div><b>Скриншоты</b>Прикрепите фото — так проблему найдут быстрее.</div></li>
                <li><span class="p-ico">🔒</span><div><b>Мы не спрашиваем пароль</b>Никогда не сообщайте его никому, даже сотрудникам.</div></li>
            </ul>
        </div>
        <form class="auth-form" method="POST" autocomplete="on">
            <h2>Вход в поддержку</h2>
            <p class="sub">Тот же логин и пароль, что и на сайте rteam.info</p>
            <?php if ($error): ?><div class="auth-err"><?=htmlspecialchars($error)?></div><?php endif; ?>
            <label class="lbl" for="login">Логин</label>
            <input id="login" type="text" name="login" value="<?=htmlspecialchars($_POST["login"] ?? "")?>" autocomplete="username" required>
            <label class="lbl" for="password">Пароль</label>
            <input id="password" type="password" name="password" autocomplete="current-password" required>
            <div class="auth-btns">
                <button type="submit" name="auth_action" value="login" class="btn">Войти</button>
                <button type="submit" name="auth_action" value="register" class="btn btn-ghost">Регистрация</button>
            </div>
            <p class="auth-note">Нет аккаунта? Введите новый логин и пароль (от 6 символов) и нажмите «Регистрация».</p>
        </form>
    </div>
</main>
<?php else: ?>
<main class="app<?= $current_ticket ? ' has-ticket' : ($is_new_ticket ? ' has-form' : '') ?>">

    <!-- Список обращений -->
    <aside class="side card">
        <div class="side-head">
            <div class="side-title">Мои обращения <span><?=$my_count?></span></div>
            <a href="?new_ticket=1" class="btn btn-block">＋ Новое обращение</a>
            <?php if ($my_count > 4): ?><div class="search"><input type="search" id="tSearch" placeholder="Поиск по обращениям" oninput="filterList()"></div><?php endif; ?>
        </div>
        <div class="t-list" id="ticketSidebarList"><?=sup_render_list($tickets, $client, $active_ticket_id)?></div>
    </aside>

    <section class="main card">
    <?php if ($is_new_ticket): ?>
        <div class="pad">
            <form class="new-wrap" method="POST" enctype="multipart/form-data" id="newForm">
                <input type="hidden" name="create_ticket" value="1">
                <a class="btn btn-ghost btn-sm back-m" href="support.php" style="margin-bottom:14px;">← Назад</a>
                <h2>Новое обращение</h2>
                <p class="sub">Выберите тему и опишите вопрос — чем подробнее, тем быстрее ответ.</p>
                <?php if ($error): ?><div class="auth-err" style="margin-top:12px;"><?=htmlspecialchars($error)?></div><?php endif; ?>

                <label class="lbl">Тема</label>
                <div class="topics">
                    <?php $sel = (string)($_POST["topic"] ?? ($_GET["topic"] ?? "")); /* помощник Rai открывает форму с темой и текстом */ foreach ($topics as $val => [$ico, $name, $hint]): ?>
                    <?php if (isset($topic_groups[$val]) && $topic_groups[$val] !== ""): ?><div class="topics-head"><?=htmlspecialchars($topic_groups[$val])?></div><?php endif; ?>
                    <label class="topic"><input type="radio" name="topic" value="<?=htmlspecialchars($val)?>" <?= $sel === $val ? "checked" : "" ?> required onchange="toggleTopic()">
                        <span><em><?=$ico?></em><span><b><?=htmlspecialchars($name)?></b><small><?=htmlspecialchars($hint)?></small></span></span></label>
                    <?php endforeach; ?>
                </div>
                <div id="customTopicWrap" style="display:<?= $sel === "other" ? "block" : "none" ?>;">
                    <label class="lbl" for="customTopic">Своя тема</label>
                    <input type="text" name="custom_topic" id="customTopic" maxlength="100" placeholder="Коротко: о чём вопрос" value="<?=htmlspecialchars($_POST["custom_topic"] ?? "")?>">
                </div>

                <label class="lbl" for="desc">Сообщение</label>
                <textarea name="description" id="desc" rows="6" maxlength="5000" placeholder="Что случилось? На какой странице? Что вы уже пробовали?" required><?=htmlspecialchars(mb_substr((string)($_POST["description"] ?? ($_GET["text"] ?? "")), 0, 5000))?></textarea>

                <label class="lbl">Скриншот (необязательно)</label>
                <label class="drop" id="drop">
                    <span class="d-ico" id="dropIco">📷</span>
                    <span><b id="dropName" style="color:#fff;">Перетащите картинку или нажмите</b><small>JPG, PNG, GIF или WEBP до 8 МБ</small></span>
                    <input type="file" name="photo" id="photoInput" accept="image/png,image/jpeg,image/gif,image/webp" hidden>
                </label>

                <?php if ($ai_ready): ?>
                <div class="ai-note"><span class="ava ai-ava">✨</span><div>Первым ответит <b>Rai</b> — ИИ-помощник поддержки. Если нужен человек, в чате будет кнопка «Позвать администратора».</div></div>
                <?php endif; ?>

                <div class="form-actions">
                    <button type="submit" class="btn" id="newSubmit">Отправить обращение</button>
                    <a class="btn btn-ghost" href="support.php">Отмена</a>
                </div>
            </form>
        </div>

    <?php elseif ($current_ticket):
        [$st_label, $st_class] = sup_status($current_ticket["status"]);
        $ai_on = rt_ticket_ai_on($current_ticket, $settings);
        $closed = $current_ticket["status"] === "Закрыт"; ?>
        <div class="chat-head">
            <a class="btn btn-ghost btn-sm back" href="support.php">←</a>
            <div class="ch-info">
                <h2><?=htmlspecialchars($current_ticket['topic'])?></h2>
                <div class="ch-sub">
                    <span>#<?=htmlspecialchars((string)$current_ticket['id'])?> · <?=htmlspecialchars(substr((string)$current_ticket['date'], 0, 16))?></span>
                    <span class="status <?=$st_class?>" id="header_status"><?=htmlspecialchars($st_label)?></span>
                </div>
            </div>
            <span class="who-chip ai" id="whoAi" style="<?= $ai_on ? '' : 'display:none' ?>"><span class="ava ai-ava">✨</span>Отвечает Rai · ИИ</span>
            <span class="who-chip human" id="whoHuman" style="<?= (!$ai_on && $ai_ready && !$closed) ? '' : 'display:none' ?>"><span class="ava">🛡</span>Отвечает администратор</span>
            <button type="button" class="btn btn-human btn-sm" id="callAdmin" style="<?= $ai_on ? '' : 'display:none' ?>" onclick="callAdmin()">🙋 Позвать администратора</button>
        </div>

        <div class="chat" id="chatHistory">
            <div class="msg me"><div class="bubble">
                <div class="b-head"><b>Вы</b><time><?=htmlspecialchars($current_ticket['date'])?></time></div>
                <div class="b-text"><?=nl2br(htmlspecialchars($current_ticket['description']))?></div>
                <?php if (!empty($current_ticket["photo"])): ?>
                    <a class="b-photo" href="<?=htmlspecialchars($current_ticket["photo"])?>" target="_blank" rel="noopener"><img src="<?=htmlspecialchars($current_ticket["photo"])?>" alt="Фото"></a>
                    <?php if (!empty($current_ticket["pinned_photo"])): ?><span class="pin">📌 Закреплено поддержкой</span><?php endif; ?>
                <?php endif; ?>
            </div></div>
            <div id="repliesContainer"><?php foreach ($current_ticket["replies"] as $reply) echo sup_render_reply($reply); ?></div>
        </div>
        <div class="typing" id="typing"><span class="ava ai-ava">✨</span><span class="dots"><i></i><i></i><i></i></span>Rai печатает…</div>

        <form class="composer" id="replyForm" method="POST" enctype="multipart/form-data" style="<?= $closed ? 'display:none' : '' ?>">
            <input type="hidden" name="reply_ticket" value="1">
            <input type="hidden" name="id" value="<?=htmlspecialchars((string)$current_ticket['id'])?>">
            <input type="hidden" name="is_ajax" value="1">
            <div class="attach-chip" id="attachChip"><img id="attachImg" alt=""><span id="attachName"></span><button type="button" onclick="clearAttach()" title="Убрать">✕</button></div>
            <div class="composer-row">
                <label class="icon-btn" title="Прикрепить картинку">📎<input type="file" name="reply_photo" id="replyPhoto" accept="image/png,image/jpeg,image/gif,image/webp" hidden></label>
                <textarea name="reply_text" id="replyText" rows="1" maxlength="5000" placeholder="Напишите сообщение…"></textarea>
                <button type="submit" class="btn send" id="sendBtn" title="Отправить">➤</button>
            </div>
            <div class="composer-hint"><span>Enter — отправить, Shift+Enter — новая строка</span><span class="hide-m">Пароль никому не сообщайте 🔒</span></div>
        </form>
        <div class="closed-note" id="closedNote" style="<?= $closed ? '' : 'display:none' ?>">Тикет закрыт. Если вопрос остался — <a href="?new_ticket=1">создайте новое обращение</a>.</div>

    <?php elseif ($active_ticket_id !== null): ?>
        <div class="pad"><div class="welcome"><div class="big" style="background:rgba(239,68,68,.15);box-shadow:none;">🔎</div><h2>Тикет не найден</h2><p>Возможно, он принадлежит другому аккаунту.</p><a class="btn" href="support.php">К обращениям</a></div></div>

    <?php else: ?>
        <div class="pad"><div class="welcome">
            <div class="big"><?= $ai_ready ? "✨" : "💬" ?></div>
            <h2>Здравствуйте, <?=htmlspecialchars($client)?>!</h2>
            <p><?= $ai_ready ? "Я — Rai, ИИ-помощник поддержки RTeam. Отвечаю сразу и в любое время. Нужен человек — позову администратора." : "Опишите вопрос — сотрудник поддержки ответит прямо здесь." ?></p>
            <a class="btn" href="?new_ticket=1">＋ Новое обращение</a>
            <div class="quick">
                <a href="?new_ticket=1"><span>🧑‍💻</span><b>Как попасть в команду</b>Заявка и направления</a>
                <a href="?new_ticket=1"><span>🤖</span><b>Код из Telegram</b>Вход и привязка бота</a>
                <a href="?new_ticket=1"><span>💳</span><b>Оплата</b>Подписка и возвраты</a>
                <a href="?new_ticket=1"><span>🐞</span><b>Ошибка на сайте</b>Что-то не работает</a>
            </div>
        </div></div>
    <?php endif; ?>
    </section>
</main>
<?php endif; ?>

<div id="toasts"></div>
<script>
function toast(text, type) {
    const t = document.createElement('div'); t.className = 'toast ' + (type || ''); t.textContent = text;
    document.getElementById('toasts').appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 450); }, 5000);
}
function filterList() {
    const q = (document.getElementById('tSearch')?.value || '').toLowerCase();
    document.querySelectorAll('#ticketSidebarList .t-item').forEach(a => a.style.display = a.textContent.toLowerCase().includes(q) ? '' : 'none');
}
function toggleTopic() {
    const other = document.querySelector('input[name="topic"][value="other"]');
    const wrap = document.getElementById('customTopicWrap');
    if (!other || !wrap) return;
    wrap.style.display = other.checked ? 'block' : 'none';
    document.getElementById('customTopic').required = other.checked;
}
function previewFile(file, onUrl) {
    if (!file) return;
    const r = new FileReader(); r.onload = e => onUrl(e.target.result); r.readAsDataURL(file);
}

/* Новое обращение: картинка перетаскиванием */
(function () {
    const drop = document.getElementById('drop'), input = document.getElementById('photoInput');
    if (!drop) return;
    toggleTopic();
    const show = () => {
        const f = input.files[0]; if (!f) return;
        document.getElementById('dropName').textContent = f.name;
        previewFile(f, url => document.getElementById('dropIco').innerHTML = '<img src="' + url + '" alt="">');
    };
    input.addEventListener('change', show);
    ['dragenter', 'dragover'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.add('over'); }));
    ['dragleave', 'drop'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.remove('over'); }));
    drop.addEventListener('drop', ev => { if (ev.dataTransfer.files.length) { input.files = ev.dataTransfer.files; show(); } });
    document.getElementById('newForm').addEventListener('submit', () => { const b = document.getElementById('newSubmit'); b.disabled = true; b.textContent = 'Отправляем…'; });
})();

<?php if ($client && $current_ticket): ?>
/* ===== Чат тикета ===== */
<?=rt_support_ai_loader_js()?>
const AI_SRC = <?=json_encode(rt_support_ai_src($settings))?>, AI_SEARCH = <?=json_encode(rt_support_ai_search($settings))?>;
const ticketId = <?=json_encode((string)$current_ticket['id'])?>;
const chatHist = document.getElementById('chatHistory');
const replyForm = document.getElementById('replyForm');
const replyText = document.getElementById('replyText');
const replyPhoto = document.getElementById('replyPhoto');
const typing = document.getElementById('typing');
let lastHtml = document.getElementById('repliesContainer').innerHTML;
let lastSidebarHtml = document.getElementById('ticketSidebarList').innerHTML;
let aiBusy = false, aiTried = 0, aiPending = <?=json_encode(sup_ai_pending($current_ticket) && rt_ticket_ai_on($current_ticket, $settings))?>;

const nearBottom = () => chatHist.scrollHeight - chatHist.scrollTop - chatHist.clientHeight < 140;
chatHist.scrollTop = chatHist.scrollHeight;

function setTyping(on) {
    const stick = nearBottom();
    typing.classList.toggle('on', on);
    if (stick) chatHist.scrollTop = chatHist.scrollHeight;
}

function applyState(d) {
    const st = document.getElementById('header_status');
    st.textContent = d.status_label; st.className = 'status ' + d.status_class;
    const closed = d.status === 'Закрыт';
    document.getElementById('whoAi').style.display = d.ai_on ? '' : 'none';
    document.getElementById('callAdmin').style.display = d.ai_on ? '' : 'none';
    document.getElementById('whoHuman').style.display = (!d.ai_on && d.ai_ready && !closed) ? '' : 'none';
    replyForm.style.display = closed ? 'none' : '';
    document.getElementById('closedNote').style.display = closed ? '' : 'none';
    aiPending = !!d.ai_pending;
    setTyping(aiPending);
}

async function loadMessages() {
    try {
        const r = await fetch('?ajax_html_ticket=' + encodeURIComponent(ticketId), { cache: 'no-store' });
        const d = await r.json();
        if (d.html !== lastHtml) {
            const stick = nearBottom();
            document.getElementById('repliesContainer').innerHTML = d.html;
            lastHtml = d.html;
            if (stick) chatHist.scrollTop = chatHist.scrollHeight;
        }
        if (d.status_label) applyState(d);
        // ИИ должен ответить, а запрос ещё никто не отправил (например, тикет только что создан)
        if (aiPending && !aiBusy && Date.now() - aiTried > 15000) runAI();
    } catch (e) {}
    try {
        const r = await fetch('?ajax_client_ticket_list=1&active_id=' + encodeURIComponent(ticketId), { cache: 'no-store' });
        const d = await r.json();
        if (d.html !== lastSidebarHtml) { document.getElementById('ticketSidebarList').innerHTML = d.html; lastSidebarHtml = d.html; filterList(); }
    } catch (e) {}
}

/* Ответ нейросети: она загружается с GitHub и думает прямо здесь, в браузере */
async function runAI() {
    aiBusy = true; aiTried = Date.now(); setTyping(true);
    let d = {};
    try {
        const st = await (await fetch('?ajax_html_ticket=' + encodeURIComponent(ticketId), { cache: 'no-store' })).json();
        if (!st.ai_pending) { aiBusy = false; return loadMessages(); }
        try {
            const Rai = await RaiLoader(AI_SRC);
            const [r] = await Promise.all([
                Rai.reply(st.ai_message, { history: st.ai_history, topic: st.topic, mode: 'client', searchUrl: AI_SEARCH }),
                new Promise(ok => setTimeout(ok, 700)),   // «Rai печатает…» хотя бы мгновение
            ]);
            const fd = new FormData();
            fd.append('ai_reply', '1'); fd.append('id', ticketId); fd.append('n', st.n);
            fd.append('text', r.reply); fd.append('handoff', r.handoff ? '1' : '0'); fd.append('source', r.source); fd.append('close', r.close ? '1' : '0');
            d = await (await fetch('support.php', { method: 'POST', body: fd })).json();
            if (d.handoff) toast('Rai передал вопрос администратору.', 'warn');
            if (d.closed) toast('Тикет закрыт ✅ Спасибо за обращение!', 'ok');
        } catch (e) {
            const fd = new FormData(); fd.append('ai_fail', '1'); fd.append('id', ticketId); fd.append('error', String(e && e.message || e));
            await fetch('support.php', { method: 'POST', body: fd });
            toast('ИИ сейчас недоступен — вам ответит администратор.', 'warn');
        }
    } catch (e) {}
    aiBusy = false;
    if (d.again) return runAI();
    await loadMessages();
}

async function callAdmin() {
    const b = document.getElementById('callAdmin'); b.disabled = true;
    const fd = new FormData(); fd.append('call_admin', '1'); fd.append('id', ticketId); fd.append('is_ajax', '1');
    try {
        const d = await (await fetch('support.php', { method: 'POST', body: fd })).json();
        if (d.ok) toast('Администратор получил ваш тикет. ИИ отключён.', 'ok');
    } catch (e) { toast('Не получилось — попробуйте ещё раз.', 'err'); }
    b.disabled = false;
    loadMessages();
}

/* Поле ввода: растёт по тексту, Enter отправляет */
const grow = () => { replyText.style.height = 'auto'; replyText.style.height = Math.min(replyText.scrollHeight, 160) + 'px'; };
replyText.addEventListener('input', grow);
replyText.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); replyForm.requestSubmit(); } });
replyPhoto.addEventListener('change', () => {
    const f = replyPhoto.files[0]; if (!f) return clearAttach();
    document.getElementById('attachName').textContent = f.name;
    previewFile(f, url => document.getElementById('attachImg').src = url);
    document.getElementById('attachChip').classList.add('on');
});
function clearAttach() { replyPhoto.value = ''; document.getElementById('attachChip').classList.remove('on'); }

replyForm.addEventListener('submit', async e => {
    e.preventDefault();
    if (!replyText.value.trim() && !replyPhoto.files.length) return replyText.focus();
    const btn = document.getElementById('sendBtn'); btn.disabled = true;
    try {
        const d = await (await fetch('support.php', { method: 'POST', body: new FormData(replyForm) })).json();
        if (!d.ok) toast('Сообщение не отправлено. Обновите страницу.', 'err');
        else { replyText.value = ''; grow(); clearAttach(); }
        await loadMessages();
        if (d.ai) runAI();
    } catch (err) { toast('Нет связи с сервером.', 'err'); }
    btn.disabled = false; replyText.focus();
});

setInterval(loadMessages, 2500);
if (aiPending) runAI();
<?php endif; ?>
</script>
</body>
</html>
