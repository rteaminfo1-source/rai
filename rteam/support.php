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

// --- AJAX API: Получение сообщений без перезагрузки ---
if (isset($_GET['ajax_html_ticket'])) {
    header('Content-Type: application/json');
    $id = $_GET['ajax_html_ticket'];
    $tickets_data = load_json("tickets.json", []);
    $html = ""; $status = "Закрыт";
    
    foreach ($tickets_data as $t) {
        if ((string)$t['id'] === (string)$id && $t['client'] === ($_SESSION['client_user'] ?? '')) {
            $status = $t['status'];
            foreach ($t["replies"] as $reply) {
                $is_admin_reply = $reply["is_admin"] ?? true;
                $bubbleClass = $is_admin_reply ? 'admin' : 'client';
                $author = $is_admin_reply ? htmlspecialchars($reply["employee"]) . ' (Rteam)' : 'Вы';
                
                $html .= '<div class="bubble ' . $bubbleClass . '">';
                $html .= '<div class="b-meta">' . $author . ' <span style="color:#777; font-weight:normal; font-size:10px;">('.$reply["date"].')</span></div>';
                $html .= nl2br(htmlspecialchars($reply["text"]));
                if (!empty($reply["photo"])) {
                    $html .= '<div style="margin-top:8px;"><img src="'.htmlspecialchars($reply["photo"]).'" style="max-height:150px; border-radius:6px; border:1px solid #333;"></div>';
                }
                $html .= '</div>';
            }
            break;
        }
    }
    echo json_encode(["html" => $html, "status" => $status]);
    exit;
}

// --- AJAX API: Обновление списка тикетов слева ---
if (isset($_GET['ajax_client_ticket_list'])) {
    header('Content-Type: application/json');
    $tickets_data = load_json("tickets.json", []);
    $html = "";
    $active_id = $_GET['active_id'] ?? null;
    $client = $_SESSION['client_user'] ?? '';
    
    $my_tickets = array_filter($tickets_data, fn($t) => $t["client"] === $client);
    if (!$my_tickets) {
        $html = '<div style="padding: 20px; text-align: center; color: #777; font-size: 13px;">У вас пока нет тикетов.</div>';
    } else {
        foreach (array_reverse($my_tickets) as $t) {
            $statusColor = $t['status'] === 'Открыт' ? '#1f9d55' : ($t['status'] === 'Закрыт' ? '#777' : '#d97706');
            $activeClass = ($active_id == $t['id']) ? 'active' : '';
            $html .= '<a href="?ticket_id='.$t['id'].'" class="ticket-item '.$activeClass.'">';
            $html .= '<div class="t-title">'.htmlspecialchars($t['topic']).'</div>';
            $html .= '<div class="t-meta"><span>#'.$t['id'].'</span><span class="t-status" id="sidebar_status_'.$t['id'].'" style="background: '.$statusColor.'">'.$t['status'].'</span></div></a>';
        }
    }
    echo json_encode(["html" => $html]);
    exit;
}
// -----------------------------------------------------

$users = load_json("users.json", []);
$tickets = load_json("tickets.json", []);

// Авторизация
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["auth_action"])) {
    $login = trim($_POST["login"] ?? "");
    $pass = trim($_POST["password"] ?? "");
    
    if ($_POST["auth_action"] === "register") {
        if ($login !== "" && $pass !== "" && !isset($users[$login])) {
            $users[$login] = ["password" => $pass, "role" => "Пользователь"];
            save_json("users.json", $users);
            $_SESSION["client_user"] = $login;
        } else {
            $error = "Логин занят или поля пусты!";
        }
    } elseif ($_POST["auth_action"] === "login") {
        if (isset($users[$login]) && $users[$login]["password"] === $pass) {
            $_SESSION["client_user"] = $login;
        } else {
            $error = "Неверный логин или пароль!";
        }
    }
    header("Location: support.php"); exit;
}

if (isset($_GET["logout"])) { unset($_SESSION["client_user"]); header("Location: support.php"); exit; }

// Создание тикета
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["create_ticket"])) {
    $topic = $_POST["topic"] === "other" ? trim($_POST["custom_topic"]) : $_POST["topic"];
    $desc = trim($_POST["description"] ?? "");
    $photo_path = null;

    if (!empty($_FILES["photo"]["name"]) && $_FILES["photo"]["error"] === 0) {
        $dir = "support_uploads/";
        if (!is_dir($dir)) mkdir($dir, 0777, true);
        $safe_name = time() . "_" . basename($_FILES["photo"]["name"]);
        if (move_uploaded_file($_FILES["photo"]["tmp_name"], $dir . $safe_name)) $photo_path = $dir . $safe_name;
    }

    $new_id = time();
    $tickets[] = [
        "id" => $new_id, "client" => $_SESSION["client_user"], "topic" => $topic,
        "description" => $desc, "photo" => $photo_path, "status" => "Открыт",
        "date" => date("Y-m-d H:i:s"), "replies" => [], "pinned_photo" => false
    ];
    save_json("tickets.json", $tickets);
    header("Location: support.php?ticket_id=" . $new_id); exit;
}

// Ответ клиента в тикете (с поддержкой загрузки фото)
if ($_SERVER["REQUEST_METHOD"] === "POST" && isset($_POST["reply_ticket"])) {
    $id = $_POST["id"];
    
    // Обработка фото прикрепленного к сообщению
    $reply_photo_path = null;
    if (!empty($_FILES["reply_photo"]["name"]) && $_FILES["reply_photo"]["error"] === 0) {
        $dir = "support_uploads/";
        if (!is_dir($dir)) mkdir($dir, 0777, true);
        $safe_name = time() . "_reply_" . rand(100,999) . "_" . basename($_FILES["reply_photo"]["name"]);
        if (move_uploaded_file($_FILES["reply_photo"]["tmp_name"], $dir . $safe_name)) {
            $reply_photo_path = $dir . $safe_name;
        }
    }

    foreach ($tickets as &$t) {
        if ((string)$t["id"] === (string)$id && $t["client"] === $_SESSION["client_user"]) {
            $t["replies"][] = [
                "text" => trim($_POST["reply_text"]), 
                "photo" => $reply_photo_path,
                "author" => $_SESSION["client_user"], 
                "date" => date("Y-m-d H:i:s"), 
                "is_admin" => false
            ];
            $t["status"] = "Открыт";
            break;
        }
    }
    save_json("tickets.json", $tickets);
    
    // Если запрос пришел через AJAX, просто завершаем скрипт, чтобы не перезагружать страницу
    if (isset($_POST["is_ajax"])) exit;
    
    header("Location: support.php?ticket_id=" . $id); exit;
}

$client = $_SESSION["client_user"] ?? null;
$active_ticket_id = $_GET["ticket_id"] ?? null;
$is_new_ticket = isset($_GET["new_ticket"]);
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Поддержка — Rteam</title>
    <style>
        body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #050509; color: #eee; height: 100vh; display: flex; flex-direction: column; }
        .header { padding: 15px 20px; background: #101018; border-bottom: 1px solid #2a0000; display: flex; justify-content: space-between; align-items: center; }
        h1 { color: #ff2a2a; text-shadow: 0 0 12px #ff000066; margin: 0; font-size: 24px; }
        .wrap { display: flex; flex: 1; overflow: hidden; max-width: 1200px; margin: 0 auto; width: 100%; }
        
        .auth-card { background: #101018; border: 1px solid #2a0000; padding: 20px; border-radius: 10px; width: 100%; max-width: 400px; margin: auto; }
        
        .sidebar { width: 300px; background: #0a0a0f; border-right: 1px solid #2a0000; display: flex; flex-direction: column; }
        .sidebar-btn { display: block; padding: 15px; text-align: center; background: #ff2a2a; color: #fff; text-decoration: none; font-weight: bold; border-bottom: 1px solid #2a0000; }
        .sidebar-btn:hover { background: #c53030; }
        
        #ticketSidebarList { flex: 1; overflow-y: auto; }
        
        .ticket-item { padding: 15px; border-bottom: 1px solid #222; text-decoration: none; color: #ccc; display: block; transition: 0.2s; }
        .ticket-item:hover { background: #1a0a0a; }
        .ticket-item.active { background: #1a0a0a; border-left: 4px solid #ff2a2a; color: #fff; }
        .t-title { font-weight: bold; margin-bottom: 5px; color: #ff7777; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .t-meta { font-size: 11px; color: #777; display: flex; justify-content: space-between; }
        .t-status { padding: 2px 6px; border-radius: 4px; color: #fff; font-size: 10px; }
        
        .chat-area { flex: 1; display: flex; flex-direction: column; background: #050509; position: relative; }
        .chat-header { padding: 15px; border-bottom: 1px solid #2a0000; background: #101018; }
        .chat-history { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .chat-form { padding: 15px; border-top: 1px solid #2a0000; background: #101018; display: flex; gap: 10px; align-items: center; }
        
        #repliesContainer { display: flex; flex-direction: column; gap: 15px; }
        
        /* Пузыри чата для Клиента */
        .bubble { max-width: 75%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.4; }
        .bubble.client { background: #1a1a24; border: 1px solid #333; align-self: flex-end; border-bottom-right-radius: 2px; }
        .bubble.admin { background: #2a0a0a; border: 1px solid #ff2a2a; align-self: flex-start; border-bottom-left-radius: 2px; }
        .b-meta { font-size: 11px; font-weight: bold; margin-bottom: 5px; color: #ff7777; }
        
        input[type="text"], input[type="password"], select, textarea { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #333; background: #050509; color: #fff; box-sizing: border-box; }
        textarea { resize: none; margin-bottom: 12px; }
        .btn { padding: 10px 16px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; font-weight: bold; }
        .ok { background: #1f9d55; color: #fff; }
        .gray { background: #2d3748; color: #fff; }
        
        .file-upload-btn { background: #2d3748; padding: 10px; border-radius: 8px; cursor: pointer; font-size: 16px; border: 1px solid #333; display: flex; align-items: center; justify-content: center; }
        .file-upload-btn:hover { background: #3a475e; }
    </style>
    <script>
        function toggleTopic() {
            var sel = document.getElementById("topicSelect").value;
            document.getElementById("customTopic").style.display = (sel === "other") ? "block" : "none";
        }
    </script>
</head>
<body>

<div class="header">
    <h1>Rteam Support</h1>
    <?php if ($client): ?>
        <div><?=$client?> | <a href="?logout=1" style="color:#ff7777; text-decoration:none;">Выйти</a></div>
    <?php endif; ?>
</div>

<?php if (!$client): ?>
    <div style="display:flex; flex:1; align-items:center;">
        <div class="auth-card">
            <h2 style="margin-top:0; color:#ff2a2a; margin-bottom:15px;">Вход в поддержку</h2>
            <?php if (isset($error)) echo "<p style='color:#ff2a2a; font-size:13px;'>$error</p>"; ?>
            <form method="POST">
                <input style="margin-bottom:12px;" type="text" name="login" placeholder="Логин" required>
                <input style="margin-bottom:12px;" type="password" name="password" placeholder="Пароль" required>
                <div style="display:flex; gap:10px;">
                    <button type="submit" name="auth_action" value="login" class="btn gray" style="flex:1;">Войти</button>
                    <button type="submit" name="auth_action" value="register" class="btn ok" style="flex:1;">Регистрация</button>
                </div>
            </form>
        </div>
    </div>
<?php else: ?>
    <div class="wrap">
        <!-- БОКОВАЯ ПАНЕЛЬ -->
        <div class="sidebar">
            <a href="?new_ticket=1" class="sidebar-btn">+ Создать тикет</a>
            <div id="ticketSidebarList">
                <?php 
                $my_tickets = array_filter($tickets, fn($t) => $t["client"] === $client);
                if (!$my_tickets): ?>
                    <div style="padding: 20px; text-align: center; color: #777; font-size: 13px;">У вас пока нет тикетов.</div>
                <?php else: ?>
                    <?php foreach (array_reverse($my_tickets) as $t): ?>
                        <?php $statusColor = $t['status'] === 'Открыт' ? '#1f9d55' : ($t['status'] === 'Закрыт' ? '#777' : '#d97706'); ?>
                        <a href="?ticket_id=<?=$t['id']?>" class="ticket-item <?= ($active_ticket_id == $t['id']) ? 'active' : '' ?>">
                            <div class="t-title"><?=$t['topic']?></div>
                            <div class="t-meta">
                                <span>#<?=$t['id']?></span>
                                <span class="t-status" id="sidebar_status_<?=$t['id']?>" style="background: <?=$statusColor?>"><?=$t['status']?></span>
                            </div>
                        </a>
                    <?php endforeach; ?>
                <?php endif; ?>
            </div>
        </div>

        <!-- РАБОЧАЯ ОБЛАСТЬ -->
        <div class="chat-area">
            <?php if ($is_new_ticket): ?>
                <div style="padding: 20px; max-width: 600px; margin: auto; width: 100%;">
                    <h2 style="color:#ff2a2a;">Новое обращение</h2>
                    <form method="POST" enctype="multipart/form-data">
                        <input type="hidden" name="create_ticket" value="1">
                        <select name="topic" id="topicSelect" onchange="toggleTopic()" required style="margin-bottom:12px;">
                            <option value="" disabled selected>Выберите тему...</option>
                            <option value="Багги">Багги / Ошибки</option>
                            <option value="Подписка или платёж">Подписка или платёж</option>
							<option value="Апеляция Rteamvisuals">Апеляция Rteamvisuals</option>
							<option value="Тех вопрос Rteamvisuals">Тех вопрос Rteamvisuals</option>
							<option value="Багги/Ошибки Rteamvisuals">Багги/Ошибки Rteamvisuals</option>
							 <option value="Вопросы по Дневнику">Вопросы по Дневнику</option>
                            <option value="other">Другое (написать самому)</option>
                        </select>
                        <input type="text" name="custom_topic" id="customTopic" placeholder="Укажите вашу тему" style="display:none; margin-bottom:12px;">
                        <textarea name="description" placeholder="Подробно опишите проблему..." style="height: 120px;" required></textarea>
                        <label style="font-size:13px; color:#aaa; display:block; margin-bottom:5px;">Скриншот или фото (необязательно):</label>
                        <input type="file" name="photo" accept="image/*" style="width:100%; margin-bottom:12px;">
                        <button type="submit" class="btn ok" style="width: 100%;">Отправить</button>
                    </form>
                </div>

            <?php elseif ($active_ticket_id): ?>
                <?php
                $current_ticket = null;
                foreach ($tickets as $t) if ((string)$t["id"] === (string)$active_ticket_id && $t["client"] === $client) $current_ticket = $t;
                
                if ($current_ticket): ?>
                    <div class="chat-header">
                        <h3 style="margin:0; color:#fff;"><?=$current_ticket['topic']?></h3>
                        <div style="font-size: 12px; color: #aaa; margin-top: 4px;">Тикет #<?=$current_ticket['id']?> | Статус: <span id="header_status"><?=$current_ticket['status']?></span></div>
                    </div>
                    
                    <div class="chat-history" id="chatHistory">
                        <!-- Оригинальное сообщение -->
                        <div class="bubble client">
                            <div class="b-meta">Вы <span style="color:#777; font-weight:normal; font-size:10px;">(<?=$current_ticket['date']?>)</span></div>
                            <?=nl2br(htmlspecialchars($current_ticket['description']))?>
                            <?php if (!empty($current_ticket["photo"])): ?>
                                <div style="margin-top: 10px;">
                                    <?php if (!empty($current_ticket["pinned_photo"])): ?>
                                        <span style="background:#ff2a2a; color:#fff; padding:2px 6px; border-radius:4px; font-size:11px;">📌 Закреплено</span><br>
                                    <?php endif; ?>
                                    <img src="<?=$current_ticket["photo"]?>" style="max-width:250px; border-radius:8px; margin-top:5px; border:1px solid #333;">
                                </div>
                            <?php endif; ?>
                        </div>

                        <!-- Контейнер для AJAX ответов -->
                        <div id="repliesContainer">
                            <?php foreach ($current_ticket["replies"] as $reply): ?>
                                <?php $is_admin = $reply["is_admin"] ?? true; ?>
                                <div class="bubble <?= $is_admin ? 'admin' : 'client' ?>">
                                    <div class="b-meta"><?= $is_admin ? htmlspecialchars($reply["employee"]) . ' (Rteam)' : 'Вы' ?> <span style="color:#777; font-weight:normal; font-size:10px;">(<?=$reply["date"]?>)</span></div>
                                    <?=nl2br(htmlspecialchars($reply["text"]))?>
                                    <?php if (!empty($reply["photo"])): ?>
                                        <div style="margin-top: 8px;">
                                            <img src="<?=htmlspecialchars($reply["photo"])?>" style="max-height: 150px; border-radius: 6px; border: 1px solid #333;">
                                        </div>
                                    <?php endif; ?>
                                </div>
                            <?php endforeach; ?>
                        </div>
                    </div>
                    
                    <!-- Форма отправки с фото -->
                    <form class="chat-form" id="replyForm" method="POST" enctype="multipart/form-data">
                        <input type="hidden" name="reply_ticket" value="1">
                        <input type="hidden" name="id" value="<?=$current_ticket['id']?>">
                        <input type="hidden" name="is_ajax" value="1">
                        
                        <label class="file-upload-btn" title="Прикрепить фото">
                            📷 <input type="file" name="reply_photo" accept="image/*" style="display: none;">
                        </label>
                        <input type="text" name="reply_text" placeholder="Написать сообщение..." required style="margin:0; flex:1;">
                        <button type="submit" class="btn ok" style="margin:0; background:#ff2a2a;">Отправить</button>
                    </form>
                    
                    <script>
                        const chatHist = document.getElementById("chatHistory");
                        const replyForm = document.getElementById("replyForm");
                        let lastHtml = document.getElementById("repliesContainer").innerHTML;
                        let lastSidebarHtml = document.getElementById("ticketSidebarList").innerHTML;
                        const ticketId = "<?=$current_ticket['id']?>";

                        if(chatHist) chatHist.scrollTop = chatHist.scrollHeight;

                        if (replyForm) {
                            replyForm.addEventListener('submit', function(e) {
                                e.preventDefault();
                                fetch('', { method: 'POST', body: new FormData(this) })
                                .then(() => {
                                    this.reset();
                                    loadMessages(); 
                                });
                            });
                        }

                        function loadMessages() {
                            // Обновляем чат
                            fetch('?ajax_html_ticket=' + ticketId)
                            .then(r => r.json())
                            .then(data => {
                                if (data.html !== lastHtml) {
                                    document.getElementById('repliesContainer').innerHTML = data.html;
                                    lastHtml = data.html;
                                    chatHist.scrollTop = chatHist.scrollHeight;
                                }
                                if (data.status === 'Закрыт') {
                                    if (replyForm) replyForm.style.display = 'none';
                                    document.getElementById('header_status').innerText = 'Закрыт';
                                }
                            });
                            
                            // Обновляем левое меню
                            fetch('?ajax_client_ticket_list=1&active_id=' + ticketId)
                            .then(r => r.json())
                            .then(data => {
                                if (data.html !== lastSidebarHtml) {
                                    document.getElementById('ticketSidebarList').innerHTML = data.html;
                                    lastSidebarHtml = data.html;
                                }
                            });
                        }

                        setInterval(loadMessages, 2500);
                    </script>
                <?php else: ?>
                    <div style="padding: 20px; color: #ff2a2a;">Тикет не найден.</div>
                <?php endif; ?>
                
            <?php else: ?>
                <div style="display:flex; flex:1; align-items:center; justify-content:center; color:#777;">
                    Выберите тикет слева или создайте новый.
                </div>
            <?php endif; ?>
        </div>
    </div>
<?php endif; ?>

</body>
</html>