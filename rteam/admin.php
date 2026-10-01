<?php
session_start();

require_once __DIR__ . '/_lib_db.php';

// Обычные load_json/save_json (для файлов вроде director_requests.json,
// заявок и т.д.) теперь просто используют безопасные lj_load/lj_save с
// блокировкой файла и атомарной записью — те же гарантии, что и у
// директорских данных, без дублирования кода.
function load_json($file, $default) {
    return lj_load($file, $default);
}
function save_json($file, $data) {
    return lj_save($file, $data);
}
function slugify_school($name) {
    $map = [
        'а'=>'a','б'=>'b','в'=>'v','г'=>'g','д'=>'d','е'=>'e','ё'=>'e','ж'=>'zh','з'=>'z','и'=>'i','й'=>'y',
        'к'=>'k','л'=>'l','м'=>'m','н'=>'n','о'=>'o','п'=>'p','р'=>'r','с'=>'s','т'=>'t','у'=>'u','ф'=>'f',
        'х'=>'h','ц'=>'c','ч'=>'ch','ш'=>'sh','щ'=>'sch','ъ'=>'','ы'=>'y','ь'=>'','э'=>'e','ю'=>'yu','я'=>'ya',
        'А'=>'A','Б'=>'B','В'=>'V','Г'=>'G','Д'=>'D','Е'=>'E','Ё'=>'E','Ж'=>'Zh','З'=>'Z','И'=>'I','Й'=>'Y',
        'К'=>'K','Л'=>'L','М'=>'M','Н'=>'N','О'=>'O','П'=>'P','Р'=>'R','С'=>'S','Т'=>'T','У'=>'U','Ф'=>'F',
        'Х'=>'H','Ц'=>'C','Ч'=>'Ch','Ш'=>'Sh','Щ'=>'Sch','Ъ'=>'','Ы'=>'Y','Ь'=>'','Э'=>'E','Ю'=>'Yu','Я'=>'Ya'
    ];
    $s = strtr($name, $map);
    $s = mb_strtolower($s);
    $s = preg_replace('/[^a-z0-9]+/', '-', $s);
    $s = trim($s, '-');
    if ($s === '') $s = 'school';
    return $s;
}
function unique_school_slug($base) {
    $slug = $base; $i = 2;
    while (dl_load_full($slug) !== null) { $slug = $base . '-' . $i; $i++; }
    return $slug;
}
// Имя файла страницы школы: сохраняем читаемое название школы (с кириллицей),
// убираем только опасные для файловой системы символы.
function safe_school_filename($name) {
    $s = trim($name);
    $s = preg_replace('/[\/\\\\\x00-\x1f"\'<>|:*?]/u', '', $s);
    $s = preg_replace('/\s+/u', '_', $s);
    if ($s === '') $s = 'school';
    return $s;
}
// Копирует dairy.html и универсальный шаблон сайта-визитки школы
// (school_site_template.html, должен лежать рядом с admin.php) в папку
// schools/<slug>/ — так у каждой школы получается свой адрес вида
// rteam.info/schools/<slug>/dairy.html (дневник) и
// rteam.info/schools/<slug>/index.html (визитка школы, редактируется
// из кабинета программиста). <slug> — это безопасная для URL версия
// названия школы, введённого в админке (уже используется везде в
// системе: database_<slug>.json, вход директора/программиста и т.д.).
function copy_school_journal($schoolName, $slug) {
    $dir = "schools/" . $slug;
    if (!is_dir($dir) && !@mkdir($dir, 0755, true)) return null;

    // dairy.html сам определяет свою школу по адресу страницы
    // (/schools/<slug>/dairy.html — распознаётся по пути, ?school=slug
    // не нужен), поэтому копия не требует НИКАКИХ подстановок в тексте —
    // просто копируем файл как есть, меняем только заголовок вкладки.
    // Из-за этого при будущих правках dairy.html копии школ не обновятся
    // сами — после изменения оригинала нажмите на вкладке "Директора"
    // кнопку "Обновить файлы всех школ" (или "Создать файл" для одной).
    $template = "dairy.html";
    if (!file_exists($template)) return null;
    $content = file_get_contents($template);
    if ($content === false) return null;
    if (preg_match('/<title>.*?<\/title>/su', $content)) {
        $content = preg_replace('/<title>.*?<\/title>/su', '<title>Электронный журнал — ' . htmlspecialchars($schoolName, ENT_QUOTES) . '</title>', $content, 1);
    }
    $target = $dir . '/dairy.html';
    $ok = @file_put_contents($target, $content);
    if ($ok === false) return null;

    // Шаблон сайта-визитки один и тот же для всех школ: он сам определяет
    // свой slug по адресной строке (/schools/<slug>/), поэтому его не нужно
    // ничем подставлять при копировании — просто копия файла как есть.
    // Файл index.html — это чистый шаблон без каких-либо данных внутри
    // (весь контент сайта хранится в MySQL, в поле site у школы), поэтому
    // его всегда можно спокойно перезаписать новой версией — это не сотрёт
    // ничего, что программист собрал в конструкторе.
    $siteTemplate = "school_site_template.html";
    if (file_exists($siteTemplate)) {
        @copy($siteTemplate, $dir . '/index.html');
    }

    return $target;
}
function formatBytes($bytes, $precision = 2) {
    $units = array('B', 'KB', 'MB', 'GB', 'TB');
    $bytes = max($bytes, 0);
    $pow = floor(($bytes ? log($bytes) : 0) / log(1024));
    $pow = min($pow, count($units) - 1);
    $bytes /= (1 << (10 * $pow));
    return round($bytes, $precision) . ' ' . $units[$pow];
}

// Каталог тематик сайта (раздел "Темы сайта" в админке).
// Ключ => [group, name, icon, field (подпись для текстового поля), placeholder]
function rteam_theme_catalog() {
    return [
        'tennis'           => ['group'=>'Спорт',    'name'=>'Теннис',                       'icon'=>'🎾', 'field'=>'Название турнира',        'placeholder'=>'Например: US Open 2026'],
        'football'         => ['group'=>'Спорт',    'name'=>'Футбол',                        'icon'=>'⚽', 'field'=>'Название турнира',        'placeholder'=>''],
        'basketball'       => ['group'=>'Спорт',    'name'=>'Баскетбол',                     'icon'=>'🏀', 'field'=>'Название турнира',        'placeholder'=>''],
        'hockey'           => ['group'=>'Спорт',    'name'=>'Хоккей',                        'icon'=>'🏒', 'field'=>'Название турнира',        'placeholder'=>''],
        'volleyball'       => ['group'=>'Спорт',    'name'=>'Волейбол',                      'icon'=>'🏐', 'field'=>'Название турнира',        'placeholder'=>''],
        'chess'            => ['group'=>'Спорт',    'name'=>'Шахматы',                       'icon'=>'♟️', 'field'=>'Название турнира',        'placeholder'=>''],
        'formula1'         => ['group'=>'Спорт',    'name'=>'Формула 1',                     'icon'=>'🏎️', 'field'=>'Название этапа',          'placeholder'=>''],
        'boxing'           => ['group'=>'Спорт',    'name'=>'Бокс',                          'icon'=>'🥊', 'field'=>'Название турнира / боя',  'placeholder'=>''],
        'olympics'         => ['group'=>'Спорт',    'name'=>'Олимпиада',                     'icon'=>'🏅', 'field'=>'Текст баннера',           'placeholder'=>''],
        'europa_league'    => ['group'=>'Спорт',    'name'=>'Лига Европы (футбол)',          'icon'=>'🏆', 'field'=>'Текст поздравления',      'placeholder'=>'Поздравляем с победой в Лиге Европы!'],
        'world_cup'        => ['group'=>'Спорт',    'name'=>'Чемпионат мира (футбол)',       'icon'=>'🌍', 'field'=>'Текст поздравления',      'placeholder'=>'С Чемпионатом мира по футболу!'],
        'gaming_day'       => ['group'=>'Спорт',    'name'=>'Киберспорт / игровой турнир',   'icon'=>'🎮', 'field'=>'Название турнира',        'placeholder'=>''],

        'new_year'         => ['group'=>'Праздники','name'=>'Новый год',                     'icon'=>'🎄', 'field'=>'Год',                     'placeholder'=>'Например: 2027'],
        'christmas'        => ['group'=>'Праздники','name'=>'Рождество',                     'icon'=>'🎅', 'field'=>'Текст (необязательно)',   'placeholder'=>''],
        'halloween'        => ['group'=>'Праздники','name'=>'Хэллоуин',                      'icon'=>'🎃', 'field'=>'Текст (необязательно)',   'placeholder'=>''],
        'valentine'        => ['group'=>'Праздники','name'=>'День св. Валентина',            'icon'=>'💘', 'field'=>'Текст (необязательно)',   'placeholder'=>''],
        'march8'           => ['group'=>'Праздники','name'=>'8 марта',                       'icon'=>'💐', 'field'=>'Текст поздравления',      'placeholder'=>''],
        'defender_day'     => ['group'=>'Праздники','name'=>'23 февраля',                    'icon'=>'🎖️', 'field'=>'Текст поздравления',      'placeholder'=>''],
        'easter'           => ['group'=>'Праздники','name'=>'Пасха',                         'icon'=>'🐣', 'field'=>'Текст (необязательно)',   'placeholder'=>''],
        'victory_day'      => ['group'=>'Праздники','name'=>'День Победы (9 мая)',           'icon'=>'🎆', 'field'=>'Текст поздравления',      'placeholder'=>''],
        'cosmonautics_day' => ['group'=>'Праздники','name'=>'День космонавтики',             'icon'=>'🚀', 'field'=>'Текст (необязательно)',   'placeholder'=>''],
        'graduation'       => ['group'=>'Праздники','name'=>'Выпускной',                     'icon'=>'🎓', 'field'=>'Текст (необязательно)',   'placeholder'=>''],

        'rteam_birthday'   => ['group'=>'RTeam',    'name'=>'День рождения RTeam',           'icon'=>'🎂', 'field'=>'Текст поздравления',      'placeholder'=>'RTeam исполняется 5 лет!'],
        'site_birthday'    => ['group'=>'RTeam',    'name'=>'День рождения сайта',           'icon'=>'🎉', 'field'=>'Текст поздравления',      'placeholder'=>''],
        'programmer_day'   => ['group'=>'RTeam',    'name'=>'День программиста',             'icon'=>'💻', 'field'=>'Текст (необязательно)',   'placeholder'=>''],

        'squid_game'       => ['group'=>'Игры',     'name'=>'Игра в кальмара',               'icon'=>'🦑', 'field'=>'Текст (необязательно)',   'placeholder'=>'Красный свет, зелёный свет...'],
    ];
}

// Функция рекурсивного удаления папки
function delete_directory($dir) {
    if (!file_exists($dir)) return true;
    if (!is_dir($dir)) return unlink($dir);
    foreach (scandir($dir) as $item) {
        if ($item == '.' || $item == '..') continue;
        if (!delete_directory($dir . DIRECTORY_SEPARATOR . $item)) return false;
    }
    return rmdir($dir);
}

// Функция сжатия изображений в WebP
function process_and_compress_image($file_info) {
    $dir = "uploads/icons/";
    if (!is_dir($dir)) mkdir($dir, 0755, true);
    $extension = strtolower(pathinfo($file_info['name'], PATHINFO_EXTENSION));
    $target_path = $dir . time() . "_" . uniqid() . ".webp";
    switch ($extension) {
        case 'jpeg': case 'jpg': $img = @imagecreatefromjpeg($file_info['tmp_name']); break;
        case 'png': $img = @imagecreatefrompng($file_info['tmp_name']); break;
        case 'webp': $img = @imagecreatefromwebp($file_info['tmp_name']); break;
        default: return "";
    }
    if (!$img) return "";
    $width = imagesx($img); $height = imagesy($img); $max_size = 200;
    if ($width > $max_size || $height > $max_size) {
        if ($width > $height) { $new_width = $max_size; $new_height = floor($height * ($max_size / $width)); } 
        else { $new_height = $max_size; $new_width = floor($width * ($max_size / $height)); }
        $tmp_img = imagecreatetruecolor($new_width, $new_height);
        imagealphablending($tmp_img, false); imagesavealpha($tmp_img, true);
        imagecopyresampled($tmp_img, $img, 0, 0, 0, 0, $new_width, $new_height, $width, $height);
        imagedestroy($img); $img = $tmp_img;
    }
    imagewebp($img, $target_path, 80); imagedestroy($img); return $target_path;
}

// ФУНКЦИЯ: Отрисовка HTML для ЗАЯВОК (AJAX)
function render_bot_tickets($tg_tickets, $banned_users) {
    $html = "";
    if (empty($tg_tickets)) return '<p style="color:#666;">Заявок пока нет.</p>';
    
    foreach ($tg_tickets as $ticket) {
        $is_new = ($ticket['status'] === 'new');
        $is_closed = ($ticket['status'] === 'closed');
        $is_banned = in_array((string)$ticket['user_id'], $banned_users) || in_array((int)$ticket['user_id'], $banned_users); 
        
        $badge_class = $is_new ? 'badge-new' : ($is_closed ? 'badge-dec' : 'badge-acc');
        $badge_text = $is_new ? 'Новая' : ($is_closed ? 'Закрыта' : 'Отвечено');
        $border_color = $is_new ? '#3182ce' : ($is_closed ? '#4a5568' : '#38a169');
        
        $html .= '<div class="card" style="border-left: 4px solid '.$border_color.'; '.($is_closed ? 'opacity: 0.6;' : '').'">';
        $html .= '<div class="meta" style="border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 10px;">';
        $html .= '<span class="badge '.$badge_class.'" style="float:right;">'.$badge_text.'</span>';
        if ($is_banned) $html .= '<span class="badge badge-dec" style="float:right; margin-right:5px; background:#c53030;">В МУТЕ 🔇</span>';
        $html .= '📅 ' . htmlspecialchars($ticket['date']) . ' | 👤 <b>' . htmlspecialchars($ticket['username']) . '</b> (ID: ' . $ticket['user_id'] . ')';
        $html .= '</div>';
        $html .= '<div style="font-size: 14px; margin-bottom: 15px; color: #eee; background: #050509; padding: 10px; border-radius: 6px; border: 1px solid #222;">';
        $html .= nl2br(htmlspecialchars($ticket['text']));
        $html .= '</div>';
        
        if (!$is_closed) {
            $html .= '<div style="background: #1a1a24; padding: 12px; border-radius: 8px; border: 1px solid #333;">';
            $placeholder = $is_new ? 'Написать ответ пользователю...' : 'Написать еще одно сообщение...';
            $html .= '<textarea id="reply_text_'.htmlspecialchars($ticket['id']).'" required placeholder="'.$placeholder.'" style="height: 60px; background: #050509; margin-bottom: 10px; width: 100%; box-sizing: border-box;"></textarea>';
            $html .= '<div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">';
            
            $html .= '<button class="btn blue" style="margin-top:0;" type="button" onclick="const t=document.getElementById(\'reply_text_'.htmlspecialchars($ticket['id']).'\').value; if(!t){alert(\'Введите текст ответа!\'); return;} sendBotAction(\'reply_tg_ticket\', \''.htmlspecialchars($ticket['user_id']).'\', \''.htmlspecialchars($ticket['id']).'\', t); document.getElementById(\'reply_text_'.htmlspecialchars($ticket['id']).'\').value=\'\';">Отправить ответ</button>';
            $html .= '<button class="btn gray" style="margin-top:0;" type="button" onclick="sendBotAction(\'close_tg_ticket\', \''.htmlspecialchars($ticket['user_id']).'\', \''.htmlspecialchars($ticket['id']).'\')">Закрыть диалог</button>';
            
            $html .= '<div style="flex:1; text-align:right; min-width: 150px;">';
            if ($is_banned) {
                $html .= '<button class="btn ok" style="margin-top:0;" type="button" onclick="sendBotAction(\'unban_bot_user\', \''.htmlspecialchars($ticket['user_id']).'\', \''.htmlspecialchars($ticket['id']).'\')">🔊 Снять Мут</button>';
            } else {
                $html .= '<button class="btn no" style="margin-top:0;" type="button" onclick="if(confirm(\'Запретить этому пользователю создавать заявки в боте?\')) sendBotAction(\'ban_bot_user\', \''.htmlspecialchars($ticket['user_id']).'\', \''.htmlspecialchars($ticket['id']).'\')">🔇 Выдать Мут</button>';
            }
            $html .= '</div></div></div>';
        }
        $html .= '</div>';
    }
    return $html;
}

// ФУНКЦИЯ: Отрисовка HTML для РОЗЫГРЫШЕЙ (AJAX)
function render_bot_giveaways_list($gws) {
    $html = "";
    if (empty($gws)) return '<p style="color:#666;">Розыгрышей пока нет.</p>';
    foreach (array_reverse($gws) as $gw) {
        $is_active = ($gw['status'] === 'active');
        $html .= '<div class="card" style="border-left: 4px solid '.($is_active ? '#e67e22' : '#777').'; '.(!$is_active ? 'opacity:0.7;' : '').'">';
        $html .= '<div style="float:right;"><span class="badge '.($is_active ? 'badge-warn' : 'badge-viewed').'">'.($is_active ? 'Активен' : 'Завершен').'</span></div>';
        $html .= '<h3 style="margin-top:0;">' . htmlspecialchars($gw['title']) . '</h3>';
        $html .= '<div class="meta" style="margin-bottom: 10px;">Кол-во победителей: <b>' . $gw['winners_count'] . '</b> | Текущих участников: <b style="color:#1f9d55;">' . count($gw['participants']) . '</b></div>';
        $html .= '<p style="font-size:13px; color:#ccc; background:#050509; padding:8px; border-radius:6px; border:1px solid #222;">' . nl2br(htmlspecialchars($gw['description'])) . '</p>';
        
        if ($is_active) {
            $html .= '<form class="ajax-bot-form" method="POST" style="margin-top:10px;" onsubmit="if(!confirm(\'Завершить розыгрыш и выбрать победителей?\')) return false;">
                        <input type="hidden" name="action" value="roll_bot_gw">
                        <input type="hidden" name="gw_id" value="'.$gw['id'].'">
                        <input type="hidden" name="is_ajax" value="1">
                        <button class="btn orange" type="submit">🎲 Подвести итоги</button>
                      </form>';
        } else {
            $win_mentions = [];
            foreach ($gw['winners'] as $w) { $win_mentions[] = "👤 <a href='tg://user?id=".$w."' style='color:#3182ce;'>".$w."</a>"; }
            $html .= '<div style="background:#1a1a24; padding:10px; border-radius:6px; margin:10px 0; border:1px solid #333; font-size:14px;">🏆 <b>Победители:</b><br> ' . (empty($win_mentions) ? 'Никто не участвовал' : implode(', ', $win_mentions)) . '</div>';
        }
        
        $html .= '<form class="ajax-bot-form" method="POST" style="margin-top:8px;" onsubmit="if(!confirm(\'Точно удалить этот розыгрыш из списка?\')) return false;">
                    <input type="hidden" name="action" value="del_bot_gw">
                    <input type="hidden" name="gw_id" value="'.$gw['id'].'">
                    <input type="hidden" name="is_ajax" value="1">
                    <button class="btn gray" type="submit">Удалить из списка</button>
                  </form>';
        $html .= '</div>';
    }
    return $html;
}

// --- API ДЛЯ ОБНОВЛЕНИЯ ВКЛАДКИ БОТА (AJAX JSON) ---
if (isset($_GET['ajax_bot_data'])) {
    header('Content-Type: application/json');
    $tg_tickets = load_json("bot_tickets.json", []);
    $banned_users = load_json("bot_banned.json", []);
    $gws = load_json("bot_giveaways.json", []);
    if (!is_array($banned_users)) $banned_users = [];
    
    echo json_encode([
        "tickets" => render_bot_tickets($tg_tickets, $banned_users),
        "giveaways" => render_bot_giveaways_list($gws)
    ]);
    exit;
}

$role = $_SESSION["role"] ?? "Гость";
$user = $_SESSION["user"] ?? "Гость";

$allowed_roles = ["Главный разработчик", "Администратор", "Главный Администратор", "Тестер", "Главный Тестер", "Кодер", "Главный Кодер", "Руководитель", "Разработчик"];
if (!in_array($role, $allowed_roles)) {
    echo "Доступ запрещён.";
    exit;
}

$is_leader = ($role === "Руководитель");

/* --- API ДЛЯ УВЕДОМЛЕНИЙ (AJAX) --- */
if (isset($_GET['ajax_check'])) {
    header('Content-Type: application/json');
    $last_time = (int)$_GET['last_time'];
    $new_msgs = [];
    $chat_data = load_json("chat.json", ["messages" => [], "pinned_id" => null]);
    foreach ($chat_data["messages"] as $m) {
        if (strtotime($m["time"]) > $last_time && $m["user"] !== $user) {
            $new_msgs[] = "Новое сообщение в чате от " . $m["user"];
        }
    }
    $new_fines = [];
    $fines = load_json("fines.json", []);
    foreach ($fines as $f) {
        if (strtotime($f["issue_date"]) > $last_time && $f["user"] === $user) {
            $new_fines[] = "ВНИМАНИЕ! Вам выписан новый штраф: " . $f["amount"] . " руб.";
        }
    }
    echo json_encode(["status" => "ok", "time" => time(), "msgs" => $new_msgs, "fines" => $new_fines]);
    exit;
}

/* --- API ДЛЯ ОБНОВЛЕНИЯ ЧАТА ТИКЕТА --- */
if (isset($_GET['ajax_html_ticket'])) {
    header('Content-Type: application/json');
    $id = $_GET['ajax_html_ticket'];
    $tickets_data = load_json("tickets.json", []);
    $html = ""; $status = "Закрыт";
    foreach ($tickets_data as $t) {
        if ((string)$t['id'] === (string)$id) {
            $status = $t['status'];
            foreach ($t["replies"] as $reply) {
                $is_admin_reply = $reply["is_admin"] ?? true;
                $bubbleClass = $is_admin_reply ? 'admin' : 'client';
                $author = $is_admin_reply ? htmlspecialchars($reply["employee"]) . ' (Rteam)' : 'Клиент: ' . htmlspecialchars($t['client']);
                $html .= '<div class="bubble ' . $bubbleClass . '">';
                $html .= '<div class="b-meta">' . $author . ' <span style="color:#777; font-weight:normal; font-size:10px;">('.$reply["date"].')</span></div>';
                $html .= nl2br(htmlspecialchars($reply["text"]));
                if (!empty($reply["photo"])) { $html .= '<div style="margin-top:8px;"><img src="'.htmlspecialchars($reply["photo"]).'" style="max-height:150px; border-radius:6px; border:1px solid #333;"></div>'; }
                $html .= '</div>';
            }
            break;
        }
    }
    echo json_encode(["html" => $html, "status" => $status]);
    exit;
}

/* --- API ДЛЯ ОБНОВЛЕНИЯ СПИСКА ТИКЕТОВ СЛЕВА --- */
if (isset($_GET['ajax_ticket_list'])) {
    header('Content-Type: application/json');
    $tickets_data = load_json("tickets.json", []);
    $html = "";
    $active_id = $_GET['active_id'] ?? null;
    if (!$tickets_data) {
        $html = '<div style="padding: 20px; color: #777; text-align: center; font-size: 13px;">Тикетов пока нет.</div>';
    } else {
        foreach (array_reverse($tickets_data) as $t) {
            $statusColor = $t['status'] === 'Открыт' ? '#1f9d55' : ($t['status'] === 'Закрыт' ? '#777' : '#d97706');
            $activeClass = ($active_id == $t['id']) ? 'active' : '';
            $html .= '<a href="?tab=support&ticket_id='.$t['id'].'" class="sup-ticket '.$activeClass.'">';
            $html .= '<div style="font-weight: bold; margin-bottom: 5px; color: #ff7777;">'.htmlspecialchars($t['topic']).'</div>';
            $html .= '<div style="font-size: 11px; color: #777; display: flex; justify-content: space-between;">';
            $html .= '<span>#'.$t['id'].' | '.htmlspecialchars($t['client']).'</span>';
            $html .= '<span id="sidebar_status_'.$t['id'].'" style="background: '.$statusColor.'; padding: 2px 6px; border-radius: 4px; color: #fff;">'.$t['status'].'</span>';
            $html .= '</div></a>';
        }
    }
    echo json_encode(["html" => $html]);
    exit;
}

/* --------------------------------- */
$tab = $_GET["tab"] ?? "apps";

$applications = load_json("applications.json", []);
$users        = load_json("users.json", []);
$leaks        = load_json("leaks.json", []);
$goals        = load_json("goals.json", []);
$fines        = load_json("fines.json", []);
$files_data   = load_json("files.json", []); 
$settings     = load_json("settings.json", ["site_name"=>"Rteam","accent"=>"#ff2a2a","neon"=>true,"animations"=>true,"recruit_open"=>true,"bot_token"=>""]);
$THEME_CATALOG = rteam_theme_catalog();
$theme_settings = load_json("theme.json", ["active" => "tennis", "enabled" => false, "text" => ""]);
if (!isset($THEME_CATALOG[$theme_settings["active"]])) $theme_settings["active"] = array_key_first($THEME_CATALOG);
$squid_game = load_json("squid_game.json", ["paused" => false, "progress" => []]);
$logs         = load_json("logs.json", []);
$messages     = load_json("messages.json", []);
$tickets      = load_json("tickets.json", []); 
$blog         = load_json("blog.json", []);
$questions    = load_json("questions.json", ["team" => ["Ник", "Email"],"admin" => ["Ник", "Email"]]);
$chat_data    = load_json("chat.json", ["messages" => [], "pinned_id" => null]);
$projects_data = load_json("projects.json", []);
$bans         = load_json("bans.json", []);
$geoblock_settings  = load_json("geoblock.json", ["enabled" => true, "countries" => ["UA", "PL", "LT", "LV", "EE"]]);
$blocked_attempts   = load_json("blocked_attempts.json", []);
$blacklist    = load_json("blacklist.json", []);
$bot_gws      = load_json("bot_giveaways.json", []);
$director_requests = load_json("director_requests.json", []);
$__migrationResult = dl_migrate_legacy_if_needed(); // разово переносит старые файловые данные в MySQL
$gold_chats   = load_json("gold_chats.json", []);
$gold_services = load_json("gold_services.json", []);

/* АВТОМАТИЧЕСКОЕ ИСКЛЮЧЕНИЕ ЗА НЕОПЛАЧЕННЫЕ ШТРАФЫ */
$users_changed = false;
foreach ($fines as &$fine) {
    if (empty($fine["paid"]) && time() - strtotime($fine["issue_date"]) >= 30 * 86400) {
        $fine_user = $fine["user"];
        if (isset($users[$fine_user]) && $users[$fine_user]["role"] !== "Пользователь") {
            $users[$fine_user]["role"] = "Пользователь";
            $users_changed = true;
            $logs[] = ["time" => date("Y-m-d H:i:s"),"type" => "fine_ban","msg"  => "Пользователь {$fine_user} автоматически исключен."];
        }
    }
}
unset($fine);
if ($users_changed) { save_json("users.json", $users); save_json("logs.json", $logs); }

/* ПОИСК И СОРТИРОВКА ДЛЯ ЗАЯВОК */
$search = trim($_GET["search"] ?? ""); $sort = $_GET["sort"] ?? "newest";
if ($tab === "apps") {
    if ($search !== "") {
        $s = mb_strtolower($search);
        $applications = array_filter($applications, function($app) use ($s) {
            $email = ""; $nick = "";
            foreach ($app["answers"] as $row) {
                if (mb_stripos($row["q"], "email") !== false) $email = $row["a"];
                if (mb_stripos($row["q"], "Ник") !== false) $nick = $row["a"];
            }
            return mb_strpos(mb_strtolower($email." ".$nick), $s) !== false;
        });
    }
    usort($applications, function($a, $b) use ($sort) {
        if ($sort === "oldest") return $a["id"] <=> $b["id"];
        if ($sort === "status") {
            $order = ["new" => 0, "viewed" => 1, "resolved_accept" => 2, "resolved_decline" => 3];
            $sa = $order[$a["status"] ?? "new"] ?? 99; $sb = $order[$b["status"] ?? "new"] ?? 99;
            if ($sa === $sb) return $b["id"] <=> $a["id"]; return $sa <=> $sb;
        }
        return $b["id"] <=> $a["id"];
    });
    if ($_SERVER["REQUEST_METHOD"] === "POST" && ($_POST["action"] ?? "") === "mark_viewed") {
        $id = $_POST["id"] ?? ""; $all = load_json("applications.json", []);
        foreach ($all as &$app) { if ((string)$app["id"] === (string)$id && ($app["status"] ?? "new") === "new") { $app["status"] = "viewed"; break; } } unset($app);
        save_json("applications.json", $all); header("Location: admin.php?tab=apps&search=".urlencode($search)."&sort=".urlencode($sort)); exit;
    }
}

/* POST ДЛЯ ОСТАЛЬНОГО */
if ($_SERVER["REQUEST_METHOD"] === "POST" && $tab !== "apps") {

    /* --- ДИРЕКТОРА ШКОЛ --- */
    if ($tab === "directors") {
        $action = $_POST["action"] ?? "";

        if ($action === "approve_request") {
            $id = $_POST["id"] ?? "";
            foreach ($director_requests as &$req) {
                if ((string)$req["id"] === (string)$id && ($req["status"] ?? "pending") === "pending") {
                    // Название школы и логин должны быть уникальны — иначе
                    // потом не получится однозначно найти школу по имени
                    // (именно так раньше ломался вход программиста).
                    if (dl_schoolname_taken($req["schoolName"])) {
                        $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "director_approve_fail", "msg" => "$user не смог одобрить заявку «{$req["schoolName"]}»: школа с таким названием уже существует."];
                        save_json("logs.json", $logs);
                        break;
                    }
                    $slugBase = slugify_school($req["schoolName"]);
                    $slug = unique_school_slug($slugBase);
                    $emptySchool = ["teachers" => [], "schedulers" => [], "quarterDates" => new stdClass(), "site" => ["title" => "", "blocks" => []], "studentAccounts" => [], "studentProfiles" => new stdClass(), "teacherProfiles" => new stdClass(), "remarks" => new stdClass(), "promoCodes" => new stdClass()];
                    $schoolFile = copy_school_journal($req["schoolName"], $slug);

                    dl_save_full([
                        "id" => uniqid(),
                        "schoolName" => $req["schoolName"],
                        "slug" => $slug,
                        "schoolFile" => $schoolFile,
                        "login" => $req["login"],
                        "password" => $req["password"],
                        "email" => $req["email"],
                        "fullName" => $req["fullName"] ?? "",
                        "phone" => $req["phone"] ?? "",
                        "data" => $emptySchool
                    ]);

                    $req["status"] = "approved";
                    $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "director_approve", "msg" => "$user одобрил заявку директора школы «{$req["schoolName"]}» (логин {$req["login"]})."];
                    save_json("logs.json", $logs);
                    break;
                }
            }
            unset($req);
            save_json("director_requests.json", $director_requests);
            header("Location: admin.php?tab=directors"); exit;
        }

        if ($action === "decline_request") {
            $id = $_POST["id"] ?? "";
            foreach ($director_requests as &$req) {
                if ((string)$req["id"] === (string)$id && ($req["status"] ?? "pending") === "pending") {
                    $req["status"] = "declined";
                    break;
                }
            }
            unset($req);
            save_json("director_requests.json", $director_requests);
            header("Location: admin.php?tab=directors"); exit;
        }

        if ($action === "delete_request") {
            $id = $_POST["id"] ?? "";
            $director_requests = array_values(array_filter($director_requests, fn($r) => (string)$r["id"] !== (string)$id));
            save_json("director_requests.json", $director_requests);
            header("Location: admin.php?tab=directors"); exit;
        }

        if ($action === "add_director") {
            $schoolName = trim($_POST["schoolName"] ?? "");
            $login = trim($_POST["login"] ?? "");
            $password = trim($_POST["password"] ?? "");
            $email = trim($_POST["email"] ?? "");
            $fullName = trim($_POST["fullName"] ?? "");
            if ($schoolName !== "" && $login !== "" && $password !== "" && !dl_schoolname_taken($schoolName) && !dl_login_taken($login)) {
                $slugBase = slugify_school($schoolName);
                $slug = unique_school_slug($slugBase);
                $emptySchool = ["teachers" => [], "schedulers" => [], "quarterDates" => new stdClass(), "site" => ["title" => "", "blocks" => []], "studentAccounts" => [], "studentProfiles" => new stdClass(), "teacherProfiles" => new stdClass(), "remarks" => new stdClass(), "promoCodes" => new stdClass()];
                $schoolFile = copy_school_journal($schoolName, $slug);
                dl_save_full([
                    "id" => uniqid(),
                    "schoolName" => $schoolName,
                    "slug" => $slug,
                    "schoolFile" => $schoolFile,
                    "login" => $login,
                    "password" => $password,
                    "email" => $email,
                    "fullName" => $fullName,
                    "phone" => "",
                    "data" => $emptySchool
                ]);
                $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "director_add", "msg" => "$user вручную создал аккаунт директора школы «{$schoolName}» (логин {$login})."];
                save_json("logs.json", $logs);
            }
            header("Location: admin.php?tab=directors"); exit;
        }

        if ($action === "reset_director_password") {
            $id = $_POST["id"] ?? ""; $slug = $_POST["slug"] ?? ""; $newPass = trim($_POST["password"] ?? "");
            if ($newPass !== "") {
                $d = dl_load_full($slug);
                if ($d && (string)$d["id"] === (string)$id) { $d["password"] = $newPass; dl_save_full($d); }
            }
            header("Location: admin.php?tab=directors"); exit;
        }

        if ($action === "regenerate_file") {
            $slug = $_POST["slug"] ?? "";
            $d = dl_load_full($slug);
            if ($d) {
                $newFile = copy_school_journal($d["schoolName"], $d["slug"]);
                if ($newFile) { $d["schoolFile"] = $newFile; dl_save_full($d); }
            }
            header("Location: admin.php?tab=directors"); exit;
        }

        // Пересоздаёт страницу-редирект dairy.html и сайт-визитку для школ
        // ПАЧКАМИ (по $batchSize за раз), а не всех разом — при большом числе
        // школ один проход по всем им в одном запросе просто не уложится в
        // лимит времени выполнения PHP-скрипта и оборвётся на середине.
        // Каждая ссылка "Дальше" обрабатывает следующую пачку и сама
        // подставляет offset для следующего шага, пока не дойдёт до конца.
        if ($action === "regenerate_all") {
            $batchSize = 300;
            $offset = (int)($_POST["offset"] ?? 0);
            $page = dl_list_index_page("", $offset, $batchSize);
            foreach ($page["rows"] as $row) {
                $d = dl_load_full($row["slug"]);
                if (!$d) continue;
                $newFile = copy_school_journal($d["schoolName"], $d["slug"]);
                if ($newFile) { $d["schoolFile"] = $newFile; dl_save_full($d); }
            }
            $nextOffset = $offset + $batchSize;
            if ($nextOffset < $page["total"]) {
                header("Location: admin.php?tab=directors&regen_offset=$nextOffset&regen_total={$page['total']}"); exit;
            }
            header("Location: admin.php?tab=directors&regen_done=1"); exit;
        }

        if ($action === "delete_director") {
            $slug = $_POST["slug"] ?? "";
            dl_delete($slug);
            header("Location: admin.php?tab=directors"); exit;
        }
    }

    /* --- БАНЫ --- */
    if ($tab === "bans") {
        if ($_POST["action"] === "add_ban") {
            $ip = trim($_POST["ip"] ?? ""); $duration = (int)($_POST["duration"] ?? 0); $reason = trim($_POST["reason"] ?? "Спам");
            if (!empty($ip)) {
                $expires = ($duration === 0) ? 0 : time() + ($duration * 3600);
                $bans[] = ["id" => time(), "ip" => $ip, "reason" => $reason, "expires" => $expires, "issued_by" => $user, "date" => date("Y-m-d H:i:s")];
                save_json("bans.json", $bans);
                $logs[] = ["time"=>date("Y-m-d H:i:s"), "type"=>"ban", "msg"=>"$user забанил IP: $ip. Причина: $reason"]; save_json("logs.json", $logs);
            }
            header("Location: admin.php?tab=bans"); exit;
        }
        if ($_POST["action"] === "unban") {
            $id = $_POST["id"]; $bans = array_filter($bans, fn($b) => (string)$b["id"] !== (string)$id); save_json("bans.json", array_values($bans)); header("Location: admin.php?tab=bans"); exit;
        }
        if ($_POST["action"] === "save_geoblock") {
            $codes = preg_split('/[\s,]+/', mb_strtoupper(trim($_POST["countries"] ?? "")), -1, PREG_SPLIT_NO_EMPTY);
            $codes = array_values(array_unique(array_filter($codes, fn($c) => preg_match('/^[A-Z]{2}$/', $c))));
            $geoblock_settings = ["enabled" => isset($_POST["enabled"]), "countries" => $codes];
            save_json("geoblock.json", $geoblock_settings);
            $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "geoblock", "msg" => "$user изменил гео-блокировку: " . (isset($_POST["enabled"]) ? "включена" : "выключена") . ", страны: " . implode(", ", $codes)];
            save_json("logs.json", $logs);
            header("Location: admin.php?tab=bans"); exit;
        }
        if ($_POST["action"] === "clear_blocked_attempts") {
            save_json("blocked_attempts.json", []);
            header("Location: admin.php?tab=bans"); exit;
        }
    }

    /* --- ЧЁРНЫЙ СПИСОК --- */
    if ($tab === "blacklist") {
        if ($_POST["action"] === "add_blacklist") {
            $identifier = trim($_POST["identifier"] ?? "");
            $ip         = trim($_POST["ip"] ?? "");
            $reason     = trim($_POST["reason"] ?? "");
            $date_added = trim($_POST["date_added"] ?? "") ?: date("Y-m-d");
            $ip_valid   = $ip !== "" && filter_var($ip, FILTER_VALIDATE_IP) !== false;
            if ($identifier !== "" || $ip !== "") {
                $entry = [
                    "id"         => (string)time() . rand(100, 999),
                    "identifier" => $identifier !== "" ? $identifier : $ip,
                    "ip"         => $ip,
                    "reason"     => $reason,
                    "date_added" => $date_added,
                    "added_by"   => $user,
                    "signed"     => false, "signed_by" => null, "signed_at" => null,
                    "released"   => false, "released_by" => null, "released_at" => null, "release_reason" => "",
                    "ip_ban_id"  => null,
                ];
                // Если указан валидный IP — он реально банится сразу, без отдельного подписания
                if ($ip_valid) {
                    $ban_id = time() . rand(100, 999);
                    $bans[] = ["id" => $ban_id, "ip" => $ip, "reason" => ($reason !== "" ? $reason : "Чёрный список"), "expires" => 0, "issued_by" => $user, "date" => date("Y-m-d H:i:s")];
                    save_json("bans.json", $bans);
                    $entry["ip_ban_id"] = $ban_id;
                    $entry["signed"]    = true;
                    $entry["signed_by"] = $user;
                    $entry["signed_at"] = date("Y-m-d H:i:s");
                }
                $blacklist[] = $entry;
                save_json("blacklist.json", $blacklist);
                $log_msg = "$user добавил в чёрный список: {$entry["identifier"]}";
                if ($ip_valid) $log_msg .= " (IP $ip забанен)";
                if ($reason !== "") $log_msg .= ". Причина: $reason";
                $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "blacklist", "msg" => $log_msg];
                save_json("logs.json", $logs);
            }
            header("Location: admin.php?tab=blacklist"); exit;
        }
        if ($_POST["action"] === "sign_blacklist") {
            $id = $_POST["id"] ?? "";
            foreach ($blacklist as &$bl) {
                if ((string)$bl["id"] === (string)$id && empty($bl["signed"])) {
                    $bl["signed"] = true; $bl["signed_by"] = $user; $bl["signed_at"] = date("Y-m-d H:i:s");
                    $ip_to_ban = trim($bl["ip"] ?? "");
                    if ($ip_to_ban === "" && filter_var($bl["identifier"], FILTER_VALIDATE_IP)) $ip_to_ban = $bl["identifier"];
                    if ($ip_to_ban !== "" && filter_var($ip_to_ban, FILTER_VALIDATE_IP)) {
                        $ban_id = time() . rand(100, 999);
                        $bans[] = ["id" => $ban_id, "ip" => $ip_to_ban, "reason" => (!empty($bl["reason"]) ? $bl["reason"] : "Чёрный список"), "expires" => 0, "issued_by" => $user, "date" => date("Y-m-d H:i:s")];
                        save_json("bans.json", $bans);
                        $bl["ip_ban_id"] = $ban_id;
                    }
                    $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "blacklist", "msg" => "$user подписал запись чёрного списка: {$bl["identifier"]}"];
                    save_json("logs.json", $logs);
                    break;
                }
            }
            unset($bl);
            save_json("blacklist.json", $blacklist);
            header("Location: admin.php?tab=blacklist"); exit;
        }
        if ($_POST["action"] === "release_blacklist") {
            $id = $_POST["id"] ?? ""; $reason = trim($_POST["release_reason"] ?? "");
            foreach ($blacklist as &$bl) {
                if ((string)$bl["id"] === (string)$id && !empty($bl["signed"]) && empty($bl["released"])) {
                    $bl["released"] = true; $bl["released_by"] = $user; $bl["released_at"] = date("Y-m-d H:i:s"); $bl["release_reason"] = $reason;
                    if (!empty($bl["ip_ban_id"])) {
                        $bans = array_values(array_filter($bans, fn($b) => (string)$b["id"] !== (string)$bl["ip_ban_id"]));
                        save_json("bans.json", $bans);
                    }
                    $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "blacklist", "msg" => "$user выпустил из чёрного списка: {$bl["identifier"]}. Причина: $reason"];
                    save_json("logs.json", $logs);
                    break;
                }
            }
            unset($bl);
            save_json("blacklist.json", $blacklist);
            header("Location: admin.php?tab=blacklist"); exit;
        }
        if ($_POST["action"] === "edit_blacklist") {
            $id = $_POST["id"] ?? "";
            $new_identifier = trim($_POST["identifier"] ?? "");
            $new_ip         = trim($_POST["ip"] ?? "");
            $new_reason     = trim($_POST["reason"] ?? "");
            $new_date       = trim($_POST["date_added"] ?? "");
            foreach ($blacklist as &$bl) {
                if ((string)$bl["id"] === (string)$id) {
                    $old_identifier = $bl["identifier"];
                    $old_ip         = trim($bl["ip"] ?? "");
                    if ($new_identifier !== "") $bl["identifier"] = $new_identifier;
                    $bl["ip"]     = $new_ip;
                    $bl["reason"] = $new_reason;
                    if ($new_date !== "") $bl["date_added"] = $new_date;

                    $new_ip_valid = $new_ip !== "" && filter_var($new_ip, FILTER_VALIDATE_IP) !== false;
                    $ip_changed   = $new_ip !== $old_ip;

                    if (empty($bl["released"])) {
                        if ($ip_changed) {
                            // IP поменялся или убран — снимаем старый реальный бан
                            if (!empty($bl["ip_ban_id"])) {
                                $bans = array_values(array_filter($bans, fn($b) => (string)$b["id"] !== (string)$bl["ip_ban_id"]));
                                $bl["ip_ban_id"] = null;
                            }
                            if ($new_ip_valid) {
                                $ban_id = time() . rand(100, 999);
                                $bans[] = ["id" => $ban_id, "ip" => $new_ip, "reason" => ($new_reason !== "" ? $new_reason : "Чёрный список"), "expires" => 0, "issued_by" => $user, "date" => date("Y-m-d H:i:s")];
                                $bl["ip_ban_id"] = $ban_id;
                                $bl["signed"] = true; $bl["signed_by"] = $user; $bl["signed_at"] = date("Y-m-d H:i:s");
                            }
                            save_json("bans.json", $bans);
                        } elseif (!empty($bl["ip_ban_id"]) && $new_reason !== "") {
                            // IP не менялся, но обновили причину — синхронизируем её с баном
                            foreach ($bans as &$b) {
                                if ((string)$b["id"] === (string)$bl["ip_ban_id"]) { $b["reason"] = $new_reason; break; }
                            }
                            unset($b);
                            save_json("bans.json", $bans);
                        }
                    }
                    $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "blacklist", "msg" => "$user отредактировал запись чёрного списка: $old_identifier -> {$bl["identifier"]}"];
                    save_json("logs.json", $logs);
                    break;
                }
            }
            unset($bl);
            save_json("blacklist.json", $blacklist);
            save_json("logs.json", $logs);
            header("Location: admin.php?tab=blacklist"); exit;
        }
        if ($_POST["action"] === "delete_blacklist") {
            $id = $_POST["id"] ?? "";
            foreach ($blacklist as $bl) {
                if ((string)$bl["id"] === (string)$id) {
                    if (!empty($bl["ip_ban_id"]) && empty($bl["released"])) {
                        $bans = array_values(array_filter($bans, fn($b) => (string)$b["id"] !== (string)$bl["ip_ban_id"]));
                        save_json("bans.json", $bans);
                    }
                    break;
                }
            }
            $blacklist = array_values(array_filter($blacklist, fn($bl) => (string)$bl["id"] !== (string)$id));
            save_json("blacklist.json", $blacklist);
            header("Location: admin.php?tab=blacklist"); exit;
        }
    }

    /* --- ПРОЕКТЫ --- */
    if ($tab === "projects") {
        if ($_POST["action"] === "add_project") {
            $title = trim($_POST["title"]); $desc = trim($_POST["description"]); $type = $_POST["type"]; $path = ""; $icon_path = "";
            if (isset($_FILES["icon"]) && $_FILES["icon"]['error'] === UPLOAD_ERR_OK) $icon_path = process_and_compress_image($_FILES["icon"]);
            if ($type === "link") $path = filter_var($_POST["link"], FILTER_SANITIZE_URL);
            elseif (in_array($type, ["file", "zip_view"]) && isset($_FILES["file"])) {
                $dir = "uploads/files/"; if (!is_dir($dir)) mkdir($dir, 0755, true);
                $path = $dir . time() . "_" . basename($_FILES["file"]["name"]); move_uploaded_file($_FILES["file"]["tmp_name"], $path);
            } elseif ($type === "site" && isset($_FILES["file"])) {
                $zip = new ZipArchive;
                if ($zip->open($_FILES["file"]["tmp_name"]) === TRUE) {
                    $site_dir = "uploads/sites/" . time() . "_" . uniqid() . "/"; if (!is_dir($site_dir)) mkdir($site_dir, 0755, true);
                    $zip->extractTo($site_dir); $zip->close(); $entry_point = $site_dir; 
                    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($site_dir));
                    foreach ($iterator as $file) { $filename = strtolower($file->getFilename()); if ($filename === 'index.html' || $filename === 'index.php') { $entry_point = str_replace("\\", "/", $file->getPathname()); break; } }
                    $path = $entry_point;
                }
            }
            if (!empty($title) && !empty($path)) { $projects_data[] = ["id" => time(),"title" => $title,"description" => $desc,"type" => $type,"path" => $path,"icon" => $icon_path,"hidden" => false]; save_json("projects.json", $projects_data); }
            header("Location: admin.php?tab=projects"); exit;
        }

        if ($_POST["action"] === "edit_project") {
            $id = $_POST["id"];
            foreach ($projects_data as &$p) {
                if ((string)$p["id"] === (string)$id) {
                    $p["title"] = trim($_POST["title"]); $p["description"] = trim($_POST["description"]);
                    if (isset($_FILES["icon"]) && $_FILES["icon"]['error'] === UPLOAD_ERR_OK) {
                        if (!empty($p["icon"]) && file_exists($p["icon"])) unlink($p["icon"]);
                        $p["icon"] = process_and_compress_image($_FILES["icon"]);
                    }
                    $type_changed = ($p["type"] !== $_POST["type"]); $file_uploaded = (isset($_FILES["file"]) && $_FILES["file"]['error'] === UPLOAD_ERR_OK);
                    if ($type_changed || $file_uploaded) {
                        if (in_array($p["type"], ["file", "zip_view"]) && file_exists($p["path"])) unlink($p["path"]);
                        if ($p["type"] === "site") { preg_match('/uploads\/sites\/[^\/]+\//', $p["path"] . '/', $matches); if (!empty($matches[0]) && is_dir($matches[0])) delete_directory($matches[0]); }
                        $p["type"] = $_POST["type"];
                        if ($p["type"] === "link") $p["path"] = filter_var($_POST["link"], FILTER_SANITIZE_URL);
                        elseif (in_array($p["type"], ["file", "zip_view"]) && $file_uploaded) {
                            $dir = "uploads/files/"; if (!is_dir($dir)) mkdir($dir, 0755, true); $p["path"] = $dir . time() . "_" . basename($_FILES["file"]["name"]); move_uploaded_file($_FILES["file"]["tmp_name"], $p["path"]);
                        } elseif ($p["type"] === "site" && $file_uploaded) {
                            $zip = new ZipArchive;
                            if ($zip->open($_FILES["file"]["tmp_name"]) === TRUE) {
                                $site_dir = "uploads/sites/" . time() . "_" . uniqid() . "/"; if (!is_dir($site_dir)) mkdir($site_dir, 0755, true);
                                $zip->extractTo($site_dir); $zip->close(); $entry_point = $site_dir; 
                                $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($site_dir));
                                foreach ($iterator as $file) { $filename = strtolower($file->getFilename()); if ($filename === 'index.html' || $filename === 'index.php') { $entry_point = str_replace("\\", "/", $file->getPathname()); break; } }
                                $p["path"] = $entry_point;
                            }
                        }
                    } elseif ($p["type"] === "link" && isset($_POST["link"])) { $p["path"] = filter_var($_POST["link"], FILTER_SANITIZE_URL); }
                    break;
                }
            } unset($p); save_json("projects.json", $projects_data); header("Location: admin.php?tab=projects"); exit;
        }
        
        if ($_POST["action"] === "toggle_project") { $id = $_POST["id"]; foreach ($projects_data as &$p) { if ((string)$p["id"] === (string)$id) { $p["hidden"] = !empty($p["hidden"]) ? false : true; break; } } unset($p); save_json("projects.json", $projects_data); header("Location: admin.php?tab=projects"); exit; }
        
        if ($_POST["action"] === "del_project") {
            $id = $_POST["id"]; $new = [];
            foreach ($projects_data as $p) {
                if ((string)$p["id"] === (string)$id) {
                    if (in_array($p["type"], ["file", "zip_view"]) && file_exists($p["path"])) unlink($p["path"]);
                    if ($p["type"] === "site") { preg_match('/uploads\/sites\/[^\/]+\//', $p["path"] . '/', $matches); if (!empty($matches[0]) && is_dir($matches[0])) delete_directory($matches[0]); }
                    if (!empty($p["icon"]) && file_exists($p["icon"])) unlink($p["icon"]); continue;
                } $new[] = $p;
            } $projects_data = $new; save_json("projects.json", $projects_data); header("Location: admin.php?tab=projects"); exit;
        }
    }

    /* --- ФАЙЛЫ --- */
    if ($tab === "files") {
        if ($_POST["action"] === "upload_file") {
            $target_dept = $_POST["department"] ?? "all"; $desc = trim($_POST["description"] ?? "");
            if (!empty($_FILES["team_file"]["name"]) && $_FILES["team_file"]["error"] === 0) {
                $dir = "team_files/"; if (!is_dir($dir)) mkdir($dir, 0777, true);
                $original_name = basename($_FILES["team_file"]["name"]);
                $safe_name = time() . "_" . preg_replace('/[^a-zA-Z0-9_.-]/', '_', $original_name);
                if (move_uploaded_file($_FILES["team_file"]["tmp_name"], $dir . $safe_name)) {
                    $files_data[] = ["id" => time(), "name" => $original_name, "path" => $dir . $safe_name, "size" => filesize($dir . $safe_name), "uploader" => $user, "department" => $target_dept, "desc" => $desc, "time" => date("Y-m-d H:i:s")];
                    save_json("files.json", $files_data); $logs[] = ["time"=>date("Y-m-d H:i:s"),"type"=>"file_upload","msg"=>"$user загрузил файл '$original_name'"]; save_json("logs.json", $logs);
                }
            }
            header("Location: admin.php?tab=files"); exit;
        }
        if ($_POST["action"] === "del_file") {
            $id = $_POST["id"];
            foreach ($files_data as $k => $f) { if ((string)$f["id"] === (string)$id) { if ($is_leader || $f["uploader"] === $user) { @unlink($f["path"]); unset($files_data[$k]); $logs[] = ["time"=>date("Y-m-d H:i:s"),"type"=>"file_del","msg"=>"$user удалил файл '".$f["name"]."'"]; } break; } }
            save_json("files.json", array_values($files_data)); save_json("logs.json", $logs); header("Location: admin.php?tab=files"); exit;
        }
    }

    /* --- ЧАТ --- */
    if ($tab === "chat") {
        if ($_POST["action"] === "send_chat_msg") {
            $text = trim($_POST["text"] ?? ""); $photo_path = null;
            if (!empty($_FILES["photo"]["name"]) && $_FILES["photo"]["error"] === 0) {
                $dir = "uploads/"; if (!is_dir($dir)) mkdir($dir, 0777, true);
                $ext = strtolower(pathinfo($_FILES["photo"]["name"], PATHINFO_EXTENSION));
                if (in_array($ext, ['jpg','jpeg','png','gif','webp'])) { $filename = $dir . time() . "_" . rand(1000,9999) . "." . $ext; if (move_uploaded_file($_FILES["photo"]["tmp_name"], $filename)) $photo_path = $filename; }
            }
            $poll = null; $poll_q = trim($_POST["poll_q"] ?? ""); $poll_opt_raw = trim($_POST["poll_opt"] ?? "");
            if ($poll_q !== "" && $poll_opt_raw !== "") {
                $opts = array_filter(array_map('trim', explode(",", $poll_opt_raw)));
                if (count($opts) > 1) { $votes = []; foreach ($opts as $o) $votes[$o] = []; $poll = ["question" => $poll_q, "votes" => $votes]; }
            }
            if ($text !== "" || $photo_path !== null || $poll !== null) {
                $chat_data["messages"][] = ["id" => time() . rand(100, 999), "user" => $user, "role" => $role, "time" => date("Y-m-d H:i:s"), "text" => $text, "photo" => $photo_path, "poll" => $poll];
                save_json("chat.json", $chat_data);
            }
            header("Location: admin.php?tab=chat"); exit;
        }
        if ($_POST["action"] === "pin_msg") { $chat_data["pinned_id"] = $_POST["id"]; save_json("chat.json", $chat_data); header("Location: admin.php?tab=chat"); exit; }
        if ($_POST["action"] === "unpin_msg") { $chat_data["pinned_id"] = null; save_json("chat.json", $chat_data); header("Location: admin.php?tab=chat"); exit; }
        if ($_POST["action"] === "vote_poll") {
            $msg_id = $_POST["msg_id"]; $selected_opt = $_POST["option"];
            foreach ($chat_data["messages"] as &$m) {
                if ((string)$m["id"] === (string)$msg_id && isset($m["poll"])) {
                    foreach ($m["poll"]["votes"] as $opt => &$voters) $voters = array_filter($voters, fn($v) => $v !== $user); unset($voters);
                    if (isset($m["poll"]["votes"][$selected_opt])) $m["poll"]["votes"][$selected_opt][] = $user; break;
                }
            } unset($m); save_json("chat.json", $chat_data); header("Location: admin.php?tab=chat"); exit;
        }
        if ($_POST["action"] === "del_chat_msg") {
            $msg_id = $_POST["id"]; $chat_data["messages"] = array_filter($chat_data["messages"], fn($m) => (string)$m["id"] !== (string)$msg_id);
            if ($chat_data["pinned_id"] === $msg_id) $chat_data["pinned_id"] = null;
            $chat_data["messages"] = array_values($chat_data["messages"]); save_json("chat.json", $chat_data); header("Location: admin.php?tab=chat"); exit;
        }
    }

    /* --- ЦЕЛИ И ШТРАФЫ --- */
    if ($_POST["action"] === "add_goal") {
        if (!$is_leader) die("Нет прав");
        $title = trim($_POST["title"] ?? ""); $desc = trim($_POST["description"] ?? ""); $date = trim($_POST["deadline_date"] ?? ""); $time = trim($_POST["deadline_time"] ?? ""); $assigned_to = trim($_POST["assigned_to"] ?? "all");
        if ($title !== "" && $date !== "" && $time !== "") { $goals[] = ["id" => time(), "title" => $title, "description" => $desc, "deadline" => $date . " " . $time . ":00", "assigned_to" => $assigned_to, "created_by" => $user, "created_at" => date("Y-m-d H:i:s")]; save_json("goals.json", $goals); }
        header("Location: admin.php?tab=goals"); exit;
    }
    if ($_POST["action"] === "del_goal") { if (!$is_leader) die("Нет прав"); $goals = array_filter($goals, fn($g) => (string)$g["id"] !== (string)$_POST["id"]); save_json("goals.json", array_values($goals)); header("Location: admin.php?tab=goals"); exit; }
    
    if ($_POST["action"] === "add_fine") {
        if (!$is_leader) die("Нет прав");
        $fine_user = trim($_POST["user"] ?? ""); $amount = (int)($_POST["amount"] ?? 0); $reason = trim($_POST["reason"] ?? "");
        if ($fine_user !== "" && $amount >= 10 && $reason !== "") { $fines[] = ["id" => time(), "user" => $fine_user, "amount" => $amount, "reason" => $reason, "issue_date" => date("Y-m-d H:i:s"), "issued_by" => $user, "paid" => false]; save_json("fines.json", $fines); }
        header("Location: admin.php?tab=fines"); exit;
    }
    if ($_POST["action"] === "pay_fine_manual") {
        if (!$is_leader) die("Нет прав");
        foreach ($fines as &$f) { if ((string)$f["id"] === (string)$_POST["id"]) { $f["paid"] = true; $f["paid_date"] = date("Y-m-d H:i:s"); break; } } unset($f);
        save_json("fines.json", $fines); header("Location: admin.php?tab=fines"); exit;
    }
    if ($_POST["action"] === "del_fine") { if (!$is_leader) die("Нет прав"); $fines = array_filter($fines, fn($f) => (string)$f["id"] !== (string)$_POST["id"]); save_json("fines.json", array_values($fines)); header("Location: admin.php?tab=fines"); exit; }

    /* --- СООБЩЕНИЯ И ТИКЕТЫ (САЙТ) --- */
    if ($tab === "messages" && $_POST["action"] === "reply_msg") {
        foreach ($messages as &$m) {
            if ((string)$m["id"] === (string)$_POST["id"]) {
                $m["reply"] = ["text" => trim($_POST["reply_text"]), "author" => $user, "role" => $role, "time" => date("Y-m-d H:i:s")];
                @mail($m["email"], "Ответ — Rteam", trim($_POST["reply_text"]), "From: team@rteam.info\r\nContent-Type: text/plain; charset=UTF-8\r\n"); break;
            }
        } unset($m); save_json("messages.json", $messages); header("Location: admin.php?tab=messages"); exit;
    }
    if ($_POST["action"] === "del_msg") { $messages = array_filter($messages, fn($m) => (string)$m["id"] !== (string)$_POST["id"]); save_json("messages.json", array_values($messages)); header("Location: admin.php?tab=messages"); exit; }

    if ($tab === "support") {
        if ($_POST["action"] === "reply_ticket") {
            $id = $_POST["id"]; $reply_photo_path = null;
            if (!empty($_FILES["reply_photo"]["name"]) && $_FILES["reply_photo"]["error"] === 0) {
                $dir = "support_uploads/"; if (!is_dir($dir)) mkdir($dir, 0777, true);
                $safe_name = time() . "_admin_" . rand(100,999) . "_" . basename($_FILES["reply_photo"]["name"]);
                if (move_uploaded_file($_FILES["reply_photo"]["tmp_name"], $dir . $safe_name)) $reply_photo_path = $dir . $safe_name;
            }
            foreach ($tickets as &$t) {
                if ((string)$t["id"] === (string)$id) {
                    $t["replies"][] = ["text" => trim($_POST["reply_text"]), "photo" => $reply_photo_path, "employee" => $user, "date" => date("Y-m-d H:i:s"), "is_admin" => true];
                    $t["status"] = "Ожидает ответа клиента"; break;
                }
            } save_json("tickets.json", $tickets);
            if (isset($_POST['is_ajax'])) exit; header("Location: admin.php?tab=support&ticket_id=" . $id); exit;
        }
        if ($_POST["action"] === "close_ticket") { $id = $_POST["id"]; foreach ($tickets as &$t) if ((string)$t["id"] === (string)$id) $t["status"] = "Закрыт"; save_json("tickets.json", $tickets); header("Location: admin.php?tab=support&ticket_id=" . $id); exit; }
        if ($_POST["action"] === "pin_photo") { $id = $_POST["id"]; foreach ($tickets as &$t) if ((string)$t["id"] === (string)$id) $t["pinned_photo"] = !empty($t["pinned_photo"]) ? false : true; save_json("tickets.json", $tickets); header("Location: admin.php?tab=support&ticket_id=" . $id); exit; }
    }

    /* --- БОТ TELEGRAM (АВТОНОМНАЯ AJAX СИСТЕМА, РОЗЫГРЫШИ И МУТЫ) --- */
    if ($tab === "bot") {
        
        // Массовая рассылка
        if ($_POST["action"] === "broadcast_tg") {
            $bot_token = $settings["bot_token"] ?? "";
            if (empty($bot_token)) { 
                if (isset($_POST['is_ajax'])) { echo "error"; exit; }
                echo "<script>alert('Нет токена!'); window.history.back();</script>"; exit; 
            }
            $bot_users = load_json("bot_users.json", []);
            $text = trim($_POST['broadcast_text']);
            $url = "https://api.telegram.org/bot" . $bot_token . "/sendMessage";
            
            foreach ($bot_users as $uid) {
                $data = ['chat_id' => $uid, 'text' => "📢 <b>Уведомление от RTeam:</b>\n\n" . $text, 'parse_mode' => 'HTML'];
                $ch = curl_init($url); curl_setopt($ch, CURLOPT_POST, 1); curl_setopt($ch, CURLOPT_POSTFIELDS, $data); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_exec($ch); curl_close($ch);
            }
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            echo "<script>alert('Рассылка завершена!'); window.history.back();</script>"; exit;
        }

        // Ответ в тикет
        if ($_POST["action"] === "reply_tg_ticket") {
            $bot_token = $settings["bot_token"] ?? "";
            if (empty($bot_token)) { 
                if (isset($_POST['is_ajax'])) { echo "error"; exit; }
                echo "<script>alert('Сначала укажите токен бота!'); window.history.back();</script>"; exit; 
            }
            $tg_tickets = load_json("bot_tickets.json", []); 
            $reply_text = trim($_POST['reply_text']); 
            $user_id = $_POST['user_id']; 
            $ticket_id = $_POST['ticket_id'];
            
            $url = "https://api.telegram.org/bot" . $bot_token . "/sendMessage";
            $message = "👨‍💻 <b>Ответ от поддержки RTeam:</b>\n\n" . $reply_text;
            $data = ['chat_id' => $user_id, 'text' => $message, 'parse_mode' => 'HTML'];
            $ch = curl_init($url); curl_setopt($ch, CURLOPT_POST, 1); curl_setopt($ch, CURLOPT_POSTFIELDS, $data); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_exec($ch); curl_close($ch);
            
            foreach ($tg_tickets as &$t) { if ((string)$t['id'] === (string)$ticket_id) { $t['status'] = 'answered'; break; } }
            save_json("bot_tickets.json", $tg_tickets); 
            
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }

        // Закрыть тикет
        if ($_POST["action"] === "close_tg_ticket") {
            $tg_tickets = load_json("bot_tickets.json", []);
            foreach ($tg_tickets as &$t) { if ((string)$t['id'] === (string)$_POST['ticket_id']) { $t['status'] = 'closed'; break; } }
            save_json("bot_tickets.json", $tg_tickets); 
            
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }

        // ВЫДАЧА И СНЯТИЕ МУТА В БОТЕ
        if ($_POST["action"] === "ban_bot_user") {
            $banned = load_json("bot_banned.json", []);
            if (!is_array($banned)) $banned = [];
            $uid = (string)$_POST["user_id"];
            if (!in_array($uid, $banned)) { $banned[] = $uid; save_json("bot_banned.json", $banned); }
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }
        
        if ($_POST["action"] === "unban_bot_user") {
            $banned = load_json("bot_banned.json", []);
            if (!is_array($banned)) $banned = [];
            $uid = (string)$_POST["user_id"];
            $banned = array_values(array_filter($banned, fn($id) => (string)$id !== $uid));
            save_json("bot_banned.json", $banned);
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }
        
        // --- УПРАВЛЕНИЕ РОЗЫГРЫШАМИ ---
        if ($_POST["action"] === "add_bot_gw") {
            $bot_gws = load_json("bot_giveaways.json", []);
            $bot_gws[] = [
                "id" => uniqid(),
                "title" => trim($_POST['title']),
                "description" => trim($_POST['description']),
                "winners_count" => (int)$_POST['winners_count'],
                "participants" => [],
                "winners" => [],
                "status" => "active"
            ];
            save_json("bot_giveaways.json", $bot_gws);
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }
        
        if ($_POST["action"] === "del_bot_gw") {
            $bot_gws = load_json("bot_giveaways.json", []);
            $bot_gws = array_values(array_filter($bot_gws, fn($g) => $g['id'] !== $_POST['gw_id']));
            save_json("bot_giveaways.json", $bot_gws);
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }
        
        if ($_POST["action"] === "roll_bot_gw") {
            $bot_gws = load_json("bot_giveaways.json", []);
            $bot_token = $settings["bot_token"] ?? "";
            
            foreach ($bot_gws as &$gw) {
                if ($gw['id'] === $_POST['gw_id'] && $gw['status'] === 'active') {
                    $gw['status'] = 'closed';
                    $participants = $gw['participants'];
                    $count = (int)$gw['winners_count'];
                    if ($count < 1) $count = 1;
                    
                    $winners = [];
                    if (!empty($participants)) {
                        shuffle($participants); // Перемешиваем случайным образом
                        $winners = array_slice($participants, 0, $count); // Берем X победителей
                    }
                    $gw['winners'] = $winners;
                    
                    // Рассылка с результатами
                    if (!empty($bot_token)) {
                        $win_text = empty($winners) ? "Участников не было 😔" : "🏆 <b>Победители (ID):</b>\n" . implode("\n", array_map(fn($w) => "👤 <a href='tg://user?id={$w}'>$w</a>", $winners));
                        $msg = "🎉 <b>РОЗЫГРЫШ ЗАВЕРШЁН!</b> 🎉\n\n<b>" . htmlspecialchars($gw['title']) . "</b>\n\n" . $win_text . "\n\nПоздравляем победителей! Спасибо всем за участие!";
                        
                        $bot_users = load_json("bot_users.json", []);
                        $url = "https://api.telegram.org/bot" . $bot_token . "/sendMessage";
                        foreach ($bot_users as $uid) {
                            $data = ['chat_id' => $uid, 'text' => $msg, 'parse_mode' => 'HTML'];
                            $ch = curl_init($url); curl_setopt($ch, CURLOPT_POST, 1); curl_setopt($ch, CURLOPT_POSTFIELDS, $data); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_exec($ch); curl_close($ch);
                        }
                    }
                    break;
                }
            }
            save_json("bot_giveaways.json", $bot_gws);
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }

        if ($_POST["action"] === "save_bot_token") {
            $settings["bot_token"] = trim($_POST["bot_token"]); save_json("settings.json", $settings); 
            if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
            header("Location: admin.php?tab=bot"); exit;
        }
    }

    /* --- ПРОЧЕЕ --- */
    if ($_POST["action"] === "save_recruit") { $settings["recruit_open"] = isset($_POST["recruit_open"]); save_json("settings.json", $settings); $questions = ["team" => array_values(array_filter(array_map("trim", explode("\n", $_POST["team_questions"])))), "admin" => array_values(array_filter(array_map("trim", explode("\n", $_POST["admin_questions"]))))]; save_json("questions.json", $questions); header("Location: admin.php?tab=recruit"); exit; }
    if ($_POST["action"] === "add_leak") { $leaks[] = ["id" => time(), "title" => trim($_POST["title"]), "content" => trim($_POST["content"]), "time" => date("Y-m-d H:i:s"), "hidden" => false]; save_json("leaks.json", $leaks); header("Location: admin.php?tab=leaks"); exit; }
    if ($_POST["action"] === "edit_leak") { foreach ($leaks as &$l) if ((string)$l["id"] === (string)$_POST["id"]) { $l["title"] = $_POST["title"]; $l["content"] = $_POST["content"]; break; } unset($l); save_json("leaks.json", $leaks); header("Location: admin.php?tab=leaks"); exit; }
    if ($_POST["action"] === "toggle_leak") { foreach ($leaks as &$l) if ((string)$l["id"] === (string)$_POST["id"]) $l["hidden"] = !$l["hidden"]; unset($l); save_json("leaks.json", $leaks); header("Location: admin.php?tab=leaks"); exit; }
    if ($_POST["action"] === "del_leak") { $leaks = array_filter($leaks, fn($l) => (string)$l["id"] !== (string)$_POST["id"]); save_json("leaks.json", array_values($leaks)); header("Location: admin.php?tab=leaks"); exit; }
    if ($_POST["action"] === "add_post") { $blog[] = ["id" => time(), "title" => trim($_POST["title"]), "content" => trim($_POST["content"]), "date" => date("Y-m-d H:i:s"), "hidden" => false]; save_json("blog.json", $blog); header("Location: admin.php?tab=blog"); exit; }
    if ($_POST["action"] === "edit_post") { foreach ($blog as &$p) if ((string)$p["id"] === (string)$_POST["id"]) { $p["title"] = $_POST["title"]; $p["content"] = $_POST["content"]; break; } unset($p); save_json("blog.json", $blog); header("Location: admin.php?tab=blog"); exit; }
    if ($_POST["action"] === "toggle_post") { foreach ($blog as &$p) if ((string)$p["id"] === (string)$_POST["id"]) $p["hidden"] = !$p["hidden"]; unset($p); save_json("blog.json", $blog); header("Location: admin.php?tab=blog"); exit; }
    if ($_POST["action"] === "del_post") { $blog = array_filter($blog, fn($p) => (string)$p["id"] !== (string)$_POST["id"]); save_json("blog.json", array_values($blog)); header("Location: admin.php?tab=blog"); exit; }
    if ($_POST["action"] === "add_user" && !isset($users[$_POST["login"]])) { $users[$_POST["login"]] = ["password"=>$_POST["password"],"role"=>$_POST["role"]]; save_json("users.json", $users); header("Location: admin.php?tab=users"); exit; }
    if ($_POST["action"] === "set_role" && isset($users[$_POST["login"]])) { $users[$_POST["login"]]["role"] = $_POST["role"]; save_json("users.json", $users); header("Location: admin.php?tab=users"); exit; }
    if ($_POST["action"] === "set_pass" && isset($users[$_POST["login"]])) { $users[$_POST["login"]]["password"] = $_POST["password"]; save_json("users.json", $users); header("Location: admin.php?tab=users"); exit; }
    if ($_POST["action"] === "del_user" && isset($users[$_POST["login"]]) && !in_array($_POST["login"], ["Roma_07b", "Petryha"])) { unset($users[$_POST["login"]]); save_json("users.json", $users); header("Location: admin.php?tab=users"); exit; }
    if ($_POST["action"] === "save_settings") { $settings["site_name"] = trim($_POST["site_name"]); $settings["accent"] = trim($_POST["accent"]); $settings["neon"] = isset($_POST["neon"]); $settings["animations"] = isset($_POST["animations"]); save_json("settings.json", $settings); header("Location: admin.php?tab=settings"); exit; }
    if ($_POST["action"] === "save_theme") {
        $cat = rteam_theme_catalog();
        $chosen = $_POST["theme_active"] ?? "";
        if (!isset($cat[$chosen])) $chosen = array_key_first($cat);
        $theme_settings["active"]  = $chosen;
        $theme_settings["enabled"] = isset($_POST["theme_enabled"]);
        $theme_settings["text"]    = trim($_POST["theme_text"] ?? "");
        save_json("theme.json", $theme_settings);
        header("Location: admin.php?tab=themes"); exit;
    }
    if ($_POST["action"] === "squid_set_paused") {
        $squid_game["paused"] = isset($_POST["squid_paused"]);
        save_json("squid_game.json", $squid_game);
        $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "squid_game", "msg" => "$user " . ($squid_game["paused"] ? "остановил" : "возобновил") . " «Игру в кальмара»."];
        save_json("logs.json", $logs);
        header("Location: admin.php?tab=themes"); exit;
    }
    if ($_POST["action"] === "squid_reset_user") {
        $sq_login = $_POST["login"] ?? "";
        if (isset($squid_game["progress"][$sq_login])) {
            unset($squid_game["progress"][$sq_login]);
            save_json("squid_game.json", $squid_game);
        }
        header("Location: admin.php?tab=themes"); exit;
    }
    if ($_POST["action"] === "add_to_team" && isset($users[$_POST["login"]])) { $users[$_POST["login"]]["role"] = $_POST["role"]; save_json("users.json", $users); header("Location: admin.php?tab=team"); exit; }
    if ($_POST["action"] === "change_team_role" && isset($users[$_POST["login"]])) { $users[$_POST["login"]]["role"] = $_POST["role"]; save_json("users.json", $users); header("Location: admin.php?tab=team"); exit; }
    if ($_POST["action"] === "remove_from_team" && isset($users[$_POST["login"]])) { $users[$_POST["login"]]["role"] = "Пользователь"; save_json("users.json", $users); header("Location: admin.php?tab=team"); exit; }

    /* --- ЗОЛОТОЙ БИЛЕТ RTEAM --- */
    if ($_POST["action"] === "grant_golden") {
        $login = trim($_POST["login"] ?? "");
        if ($login !== "" && isset($users[$login])) {
            $users[$login]["golden"] = true;
            $users[$login]["golden_title"] = trim($_POST["golden_title"] ?? "") !== "" ? trim($_POST["golden_title"]) : "Золотой билет RTeam";
            $users[$login]["golden_link"] = trim($_POST["golden_link"] ?? "");
            $users[$login]["golden_staff"] = trim($_POST["golden_staff"] ?? "");
            save_json("users.json", $users);
            if (!isset($gold_chats[$login])) $gold_chats[$login] = ["staff" => $users[$login]["golden_staff"], "messages" => []];
            else $gold_chats[$login]["staff"] = $users[$login]["golden_staff"];
            save_json("gold_chats.json", $gold_chats);
            $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "golden_ticket", "msg" => "$user выдал «Золотой билет RTeam» пользователю $login (сотрудник: {$users[$login]["golden_staff"]})."];
            save_json("logs.json", $logs);
        }
        header("Location: admin.php?tab=gold"); exit;
    }
    if ($_POST["action"] === "revoke_golden" && isset($users[$_POST["login"]])) {
        $login = $_POST["login"];
        $users[$login]["golden"] = false;
        save_json("users.json", $users);
        $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "golden_ticket", "msg" => "$user отозвал «Золотой билет RTeam» у пользователя $login."];
        save_json("logs.json", $logs);
        header("Location: admin.php?tab=gold"); exit;
    }
    if ($_POST["action"] === "gold_reply") {
        $login = trim($_POST["login"] ?? "");
        $text = trim($_POST["reply_text"] ?? "");
        if ($login !== "" && $text !== "" && isset($users[$login]) && !empty($users[$login]["golden"])) {
            if (!isset($gold_chats[$login])) $gold_chats[$login] = ["staff" => $users[$login]["golden_staff"] ?? "", "messages" => []];
            $gold_chats[$login]["messages"][] = ["id" => time() . rand(100, 999), "from" => "staff", "author" => $user, "role" => $role, "text" => $text, "time" => date("Y-m-d H:i:s")];
            save_json("gold_chats.json", $gold_chats);
        }
        if (isset($_POST['is_ajax'])) { echo "ok"; exit; }
        header("Location: admin.php?tab=gold&thread=".urlencode($login)); exit;
    }
    if ($_POST["action"] === "add_gold_service") {
        $name = trim($_POST["service_name"] ?? "");
        $link = trim($_POST["service_link"] ?? "");
        if ($name !== "") {
            $gold_services[] = ["id" => time() . rand(100, 999), "name" => $name, "link" => $link];
            save_json("gold_services.json", $gold_services);
            $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "golden_ticket", "msg" => "$user добавил платную услугу для держателей золотого билета: «$name»."];
            save_json("logs.json", $logs);
        }
        header("Location: admin.php?tab=gold"); exit;
    }
    if ($_POST["action"] === "edit_gold_service") {
        $sid = $_POST["service_id"] ?? "";
        foreach ($gold_services as &$svc) {
            if ($svc["id"] === $sid) {
                $svc["name"] = trim($_POST["service_name"] ?? $svc["name"]);
                $svc["link"] = trim($_POST["service_link"] ?? $svc["link"]);
                break;
            }
        }
        unset($svc);
        save_json("gold_services.json", $gold_services);
        $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "golden_ticket", "msg" => "$user изменил платную услугу для держателей золотого билета (id $sid)."];
        save_json("logs.json", $logs);
        header("Location: admin.php?tab=gold"); exit;
    }
    if ($_POST["action"] === "delete_gold_service") {
        $sid = $_POST["service_id"] ?? "";
        $gold_services = array_values(array_filter($gold_services, function($s) use ($sid) { return $s["id"] !== $sid; }));
        save_json("gold_services.json", $gold_services);
        $logs[] = ["time" => date("Y-m-d H:i:s"), "type" => "golden_ticket", "msg" => "$user удалил платную услугу для держателей золотого билета (id $sid)."];
        save_json("logs.json", $logs);
        header("Location: admin.php?tab=gold"); exit;
    }
}

$stats = [ "apps_total" => count($applications), "users_total" => count($users), "chat_total" => count($chat_data["messages"]), "files_total" => count($files_data), "goals_total" => count($goals), "fines_total" => count($fines), "bans_total" => count($bans), "msgs_total" => count($messages), "blog_total" => count($blog), "projects_total" => count($projects_data), "logs_total" => count($logs) ];

function render_chat_message($m, $is_pinned, $user, $is_leader) {
    global $chat_data;
    $html = '<div id="msg-' . $m["id"] . '" class="chat-msg ' . ($is_pinned ? 'highlight-pinned' : '') . '">';
    $html .= '<div class="chat-header"><div><span class="chat-author">' . htmlspecialchars($m["user"]) . '</span> <span class="chat-role">' . htmlspecialchars($m["role"]) . '</span></div><span class="chat-time">' . htmlspecialchars($m["time"]) . '</span></div>';
    if (!empty($m["text"])) $html .= '<div class="chat-text">' . nl2br(htmlspecialchars($m["text"])) . '</div>';
    if (!empty($m["photo"])) $html .= '<div class="chat-photo"><img src="' . htmlspecialchars($m["photo"]) . '" alt="photo"></div>';
    if (!empty($m["poll"])) {
        $html .= '<div class="chat-poll"><h4>📊 ' . htmlspecialchars($m["poll"]["question"]) . '</h4>';
        $total_votes = 0; foreach ($m["poll"]["votes"] as $opt => $voters) $total_votes += count($voters);
        foreach ($m["poll"]["votes"] as $opt => $voters) {
            $count = count($voters); $percent = $total_votes > 0 ? round(($count / $total_votes) * 100) : 0; $has_voted = in_array($user, $voters);
            $html .= '<div class="poll-option"><div>' . htmlspecialchars($opt) . ' <span style="font-size:11px;color:#777;">(' . $count . ' голосов, ' . $percent . '%)</span></div>';
            $html .= '<form method="POST" style="margin:0;"><input type="hidden" name="action" value="vote_poll"><input type="hidden" name="msg_id" value="' . $m["id"] . '"><input type="hidden" name="option" value="' . htmlspecialchars($opt) . '"><button class="btn ' . ($has_voted ? 'ok' : 'gray') . '" type="submit" style="padding:2px 8px;margin-top:0;">Голосовать</button></form></div>';
            $html .= '<div class="poll-bar-container"><div class="poll-bar" style="width:' . $percent . '%"></div></div>';
        } $html .= '</div>';
    }
    $html .= '<div class="chat-actions" style="margin-top:8px; display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end;">';
    if ($chat_data["pinned_id"] === $m["id"]) $html .= '<form method="POST" style="margin:0;"><input type="hidden" name="action" value="unpin_msg"><button class="btn gray" type="submit" style="padding:4px 8px;">Открепить</button></form>';
    else $html .= '<form method="POST" style="margin:0;"><input type="hidden" name="action" value="pin_msg"><input type="hidden" name="id" value="' . $m["id"] . '"><button class="btn blue" type="submit" style="padding:4px 8px;">Закрепить</button></form>';
    if ($m["user"] === $user || $is_leader || $_SESSION["role"] === "Главный разработчик") $html .= '<form method="POST" style="margin:0;"><input type="hidden" name="action" value="del_chat_msg"><input type="hidden" name="id" value="' . $m["id"] . '"><button class="btn no" type="submit" style="padding:4px 8px;">Удалить</button></form>';
    $html .= '</div></div>'; return $html;
}
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<link rel="icon" href="Favicon.Jpeg" type="image/jpeg">
<title>Админ — Rteam</title>
<style>
body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; background: #050509; color: #eee; }
.wrap { max-width: 1100px; margin: 30px auto; padding: 0 16px 40px; }
h1 { color: #ff2a2a; text-shadow: 0 0 12px #ff000066; margin-bottom: 10px; }
a { color:#ff7777; text-decoration:none; }
.tabs { display: flex; gap: 10px; margin: 10px 0 20px; flex-wrap: wrap; }
.tab { padding: 8px 14px; border-radius: 8px; background: #101018; border: 1px solid #2a0000; font-size: 14px; transition: background 0.3s; }
.tab:hover { background: #1a0a0a; }
.tab.active { background: #ff2a2a; color: #fff; box-shadow: 0 0 14px #ff000066; }
.card { background: #101018; border: 1px solid #2a0000; padding: 14px; border-radius: 10px; margin-top: 10px; }
.card h3 { margin: 0 0 6px; color: #ff2a2a; }
.meta { font-size: 13px; color: #aaa; margin-bottom: 6px; }
textarea, input[type="text"], input[type="password"], input[type="number"], input[type="date"], input[type="time"], select { width: 100%; padding: 8px; border-radius: 8px; border: 1px solid #333; background: #050509; color: #fff; resize: none; font-size: 13px; margin-top: 6px; box-sizing: border-box; }
textarea { height: 80px; }
.btn { display: inline-block; margin-top: 8px; padding: 7px 14px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight:bold; }
.ok { background:#1f9d55; color:#fff; }
.no { background:#c53030; color:#fff; }
.gray { background:#2d3748; color:#fff; }
.blue { background:#2b6cb0; color:#fff; }
.orange { background:#e67e22; color:#fff; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(120px,1fr)); gap: 10px; margin-top: 10px; }
.stat { background:#101018; border:1px solid #2a0000; border-radius:10px; padding:10px; text-align:center; font-size:13px; }
.stat b { font-size:18px; color:#ff2a2a; }
.badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; margin-left:6px; }
.badge-new { background:#2b6cb0; color:#fff; }
.badge-viewed { background:#b7791f; color:#fff; }
.badge-acc { background:#2f855a; color:#fff; }
.badge-dec { background:#c53030; color:#fff; }
.badge-warn { background:#dd6b20; color:#fff; }
.badge-gold { background:linear-gradient(135deg,#ffe066,#d4a017); color:#3a2a00; font-weight:bold; box-shadow:0 0 8px rgba(255,215,0,.5); }
.gold-card { background:linear-gradient(160deg,#1a1506,#101018 60%); border:1px solid #7a5c00; box-shadow: 0 0 14px rgba(212,160,23,.15) inset; }
.gold-card h3 { color:#ffd76a; }
.search-bar { display:flex; gap:8px; flex-wrap:wrap; margin:10px 0 16px; }
.search-bar input, .search-bar select { width:auto; }

/* Чат команды */
.chat-container { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; max-height: 600px; overflow-y: auto; padding-right: 8px; scroll-behavior: smooth; }
.chat-msg { background: #101018; border: 1px solid #2a0000; padding: 12px; border-radius: 10px; }
.chat-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 6px; margin-bottom: 8px; }
.chat-author { color: #ff2a2a; font-weight: bold; font-size: 15px; }
.chat-role { font-size: 11px; background: #333; padding: 3px 6px; border-radius: 4px; color: #ccc; margin-left: 8px; vertical-align: middle; }
.chat-time { font-size: 11px; color: #777; }
.chat-text { font-size: 14px; line-height: 1.5; white-space: pre-wrap; }
.chat-photo img { max-width: 100%; max-height: 350px; border-radius: 8px; margin-top: 10px; border: 1px solid #333; }
.chat-poll { margin-top: 12px; background: #050509; padding: 12px; border-radius: 8px; border: 1px solid #222; }
.poll-option { display: flex; align-items: center; justify-content: space-between; background: #1a1a24; padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; }
.poll-bar-container { width: 100%; background: #050509; height: 6px; border-radius: 3px; margin-top: 4px; overflow: hidden; margin-bottom: 8px; }
.poll-bar { height: 100%; background: #ff2a2a; transition: width 0.3s; }
.pinned-mini-bar { display: flex; align-items: center; background: #1a0a0a; border: 1px solid #ff2a2a; padding: 8px 12px; border-radius: 8px; color: #eee; position: sticky; top: 0; z-index: 10; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(255,0,0,0.2); }
.pinned-icon { font-size: 18px; margin-right: 12px; }
.pinned-content { flex: 1; overflow: hidden; }
.highlight-pinned { border-color: #ff2a2a; box-shadow: 0 0 10px rgba(255,42,42,0.15); }

#toast-container { position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; pointer-events: none; }
.toast { background: #101018; border-left: 4px solid #3182ce; color: #fff; padding: 15px 20px; border-radius: 6px; box-shadow: 0 4px 15px rgba(0,0,0,0.6); font-size: 14px; animation: slideIn 0.4s ease-out forwards; pointer-events: auto; }
.toast.info { border-left-color: #3182ce; }
.toast.error { border-left-color: #c53030; font-weight: bold; }
@keyframes slideIn { from { transform: translateX(120%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

.file-row { display: flex; justify-content: space-between; align-items: center; background: #1a1a24; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #333; }
.file-name { font-size: 15px; font-weight: bold; color: #ff7777; margin-bottom: 4px; }
.file-meta { font-size: 12px; color: #aaa; }
.reply-block { margin-top: 15px; padding: 12px; background: #0a0a0f; border-left: 3px solid #ff2a2a; }

/* Дизайн Мессенджера тикетов */
.support-layout { display: flex; height: 70vh; min-height: 500px; background: #0a0a0f; border: 1px solid #2a0000; border-radius: 10px; overflow: hidden; margin-top: 15px; }
.sup-sidebar { width: 300px; border-right: 1px solid #2a0000; overflow-y: auto; background: #050509; display: flex; flex-direction: column; }
#ticketSidebarList { flex: 1; overflow-y: auto; }
.sup-ticket { padding: 15px; border-bottom: 1px solid #222; text-decoration: none; color: #ccc; display: block; transition: 0.2s; }
.sup-ticket:hover { background: #101018; }
.sup-ticket.active { background: #1a0a0a; border-left: 4px solid #ff2a2a; color: #fff; }
.sup-chat { flex: 1; display: flex; flex-direction: column; background: #101018; position: relative; }
.sup-header { padding: 15px; border-bottom: 1px solid #2a0000; background: #0a0a0f; display: flex; justify-content: space-between; align-items: center; }
.sup-history { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
.sup-controls { padding: 15px; border-top: 1px solid #2a0000; background: #0a0a0f; display: flex; gap: 10px; align-items: center; }

#repliesContainer { display: flex; flex-direction: column; gap: 15px; }
.bubble { max-width: 75%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.4; }
.bubble.admin { background: #2a0a0a; border: 1px solid #ff2a2a; align-self: flex-end; border-bottom-right-radius: 2px; }
.bubble.client { background: #1a1a24; border: 1px solid #333; align-self: flex-start; border-bottom-left-radius: 2px; }
.b-meta { font-size: 11px; font-weight: bold; margin-bottom: 5px; color: #ff7777; }
.file-upload-btn { background: #2d3748; padding: 10px; border-radius: 8px; cursor: pointer; font-size: 16px; border: 1px solid #333; display: flex; align-items: center; justify-content: center; }
.file-upload-btn:hover { background: #3a475e; }
</style>
<script>
function updateFormType(prefix = '') {
    var type = document.getElementById(prefix + 'project_type').value;
    var admLink = document.getElementById(prefix + 'adm_link');
    var admFile = document.getElementById(prefix + 'adm_file');
    var fileLabel = document.getElementById(prefix + 'file_label');
    var fileInput = document.getElementById(prefix + 'file_input');

    if (type === 'link') {
        admLink.style.display = 'block'; admFile.style.display = 'none';
        if(fileInput) fileInput.removeAttribute('required');
    } else {
        admLink.style.display = 'none'; admFile.style.display = 'block';
        if (prefix === '' && fileInput) fileInput.setAttribute('required', 'true');
        if (type === 'site' && fileLabel) { fileLabel.innerText = 'Выберите ZIP-архив с сайтом (авто-распаковка на сервере)'; if(fileInput) fileInput.setAttribute('accept', '.zip'); } 
        else if (type === 'zip_view' && fileLabel) { fileLabel.innerText = 'Выберите ZIP-архив для просмотра содержимого онлайн'; if(fileInput) fileInput.setAttribute('accept', '.zip'); } 
        else if(fileLabel) { fileLabel.innerText = 'Выберите любой файл (Если это .EXE, пользователь сможет его скачать)'; if(fileInput) fileInput.removeAttribute('accept'); }
    }
}
window.addEventListener('DOMContentLoaded', function() {
    if(document.getElementById('project_type')) updateFormType(''); 
    if(document.getElementById('edit_project_type')) updateFormType('edit_'); 
});
</script>
</head>
<body>

<div id="toast-container"></div>

<div class="wrap">
    <h1>Админ‑панель Rteam</h1>
    <p>Вы вошли как <b><?=htmlspecialchars($user)?></b> (<?=htmlspecialchars($role)?>) — <a href="index.php">← На сайт</a></p>

    <div class="stat-grid">
        <div class="stat">Заявок<br><b><?=$stats["apps_total"]?></b></div>
        <div class="stat">Чат<br><b><?=$stats["chat_total"]?></b></div>
        <div class="stat">Проекты<br><b><?=$stats["projects_total"]?></b></div>
        <div class="stat">Файлы<br><b><?=$stats["files_total"]?></b></div>
        <div class="stat">Цели<br><b><?=$stats["goals_total"]?></b></div>
        <div class="stat">Штрафы<br><b><?=$stats["fines_total"]?></b></div>
        <div class="stat">Тикетов<br><b><?=count($tickets)?></b></div>
        <div class="stat">Баны<br><b><?=$stats["bans_total"]?></b></div>
        <div class="stat">Пользователи<br><b><?=$stats["users_total"]?></b></div>
        <div class="stat">Логи<br><b><?=$stats["logs_total"]?></b></div>
    </div>

    <div class="tabs">
        <a class="tab <?=$tab==='chat'?'active':''?>" href="?tab=chat">Чат</a>
        <a class="tab <?=$tab==='projects'?'active':''?>" href="?tab=projects">Проекты</a>
        <a class="tab <?=$tab==='files'?'active':''?>" href="?tab=files">Файлы</a>
        <a class="tab <?=$tab==='goals'?'active':''?>" href="?tab=goals">Цели</a>
        <a class="tab <?=$tab==='fines'?'active':''?>" href="?tab=fines">Штрафы</a>
        <a class="tab <?=$tab==='apps'?'active':''?>" href="?tab=apps">Заявки</a>
        <a class="tab <?=$tab==='directors'?'active':''?>" href="?tab=directors">Директора<?php $pendingDirCount = count(array_filter($director_requests, fn($r) => ($r["status"] ?? "pending") === "pending")); if ($pendingDirCount > 0): ?> <span class="badge badge-new" style="padding:2px 6px; font-size:10px;"><?=$pendingDirCount?></span><?php endif; ?></a>
        <a class="tab <?=$tab==='messages'?'active':''?>" href="?tab=messages">Сообщения</a>
        <a class="tab <?=$tab==='support'?'active':''?>" href="?tab=support">Тикеты</a>
        <a class="tab <?=$tab==='bans'?'active':''?>" href="?tab=bans">Баны</a>
        <a class="tab <?=$tab==='blacklist'?'active':''?>" href="?tab=blacklist">⚫ Чёрный список</a>
        <a class="tab <?=$tab==='team'?'active':''?>" href="?tab=team">Команда</a>
        <a class="tab <?=$tab==='leaks'?'active':''?>" href="?tab=leaks">Сливы</a>
        <a class="tab <?=$tab==='blog'?'active':''?>" href="?tab=blog">Блог</a>
        <a class="tab <?=$tab==='users'?'active':''?>" href="?tab=users">Пользователи</a>
        <a class="tab <?=$tab==='recruit'?'active':''?>" href="?tab=recruit">Набор</a>
        <a class="tab <?=$tab==='themes'?'active':''?>" href="?tab=themes">🎭 Темы сайта</a>
        <a class="tab <?=$tab==='settings'?'active':''?>" href="?tab=settings">Настройки</a>
        <a class="tab <?=$tab==='logs'?'active':''?>" href="?tab=logs">Логи</a>
        <a class="tab <?=$tab==='bot'?'active':''?>" href="?tab=bot">Бот</a>
        <a class="tab <?=$tab==='gold'?'active':''?>" href="?tab=gold" style="color:#ffd76a;">🎫 Золотой билет</a>
    </div>

    <!-- === ВКЛАДКА: ПРОЕКТЫ === -->
    <?php if ($tab === "projects"): ?>
        <?php 
        $edit_project = null;
        if (isset($_GET['edit_id'])) { foreach ($projects_data as $p) { if ((string)$p['id'] === (string)$_GET['edit_id']) { $edit_project = $p; break; } } }
        ?>
        <?php if ($edit_project): ?>
            <h3 style="color: #e67e22;">Редактировать проект: <?= htmlspecialchars($edit_project['title']) ?></h3>
            <form action="?tab=projects" method="POST" enctype="multipart/form-data" class="card" style="max-width: 600px; margin-bottom:40px; border-color: #e67e22;">
                <input type="hidden" name="action" value="edit_project">
                <input type="hidden" name="id" value="<?= $edit_project['id'] ?>">
                <label>Название проекта</label>
                <input type="text" name="title" required value="<?= htmlspecialchars($edit_project['title']) ?>">
                <label style="display:block; margin-top:10px;">Описание</label>
                <textarea name="description" required><?= htmlspecialchars($edit_project['description']) ?></textarea>
                <label style="display:block; margin-top:10px;">Иконка проекта (Оставьте пустым, чтобы не менять)</label>
                <?php if(!empty($edit_project['icon']) && file_exists($edit_project['icon'])): ?>
                    <div style="margin: 5px 0;"><img src="<?=$edit_project['icon']?>" style="width:32px; height:32px; object-fit:cover; border-radius:4px;"></div>
                <?php endif; ?>
                <input type="file" name="icon" accept="image/png, image/jpeg, image/webp">
                <label style="display:block; margin-top:10px;">Тип загрузки</label>
                <select name="type" id="edit_project_type" onchange="updateFormType('edit_')">
                    <option value="link" <?= $edit_project['type'] === 'link' ? 'selected' : '' ?>>Внешняя ссылка (Кнопка «Перейти»)</option>
                    <option value="file" <?= $edit_project['type'] === 'file' ? 'selected' : '' ?>>Файл / Программа (Любой формат / .EXE)</option>
                    <option value="zip_view" <?= $edit_project['type'] === 'zip_view' ? 'selected' : '' ?>>ZIP-архив (С возможностью смотреть файлы онлайн)</option>
                    <option value="site" <?= $edit_project['type'] === 'site' ? 'selected' : '' ?>>Полноценный сайт (Из ZIP-архива, Кнопка «Открыть сайт»)</option>
                </select>
                <div id="edit_adm_link">
                    <label style="display:block; margin-top:10px;">Ссылка на целевой проект (URL)</label>
                    <input type="text" name="link" value="<?= $edit_project['type'] === 'link' ? htmlspecialchars($edit_project['path']) : 'https://' ?>">
                </div>
                <div id="edit_adm_file" style="display:none;">
                    <label id="edit_file_label" style="display:block; margin-top:10px; color:#ff7777;">Выберите файл (Оставьте пустым, чтобы не перезаписывать текущий файл)</label>
                    <div style="font-size:11px; color:#aaa; margin-bottom:5px;">Текущий путь: <?= htmlspecialchars($edit_project['path']) ?></div>
                    <input type="file" name="file" id="edit_file_input">
                </div>
                <div style="margin-top:15px; display:flex; gap:10px;">
                    <button class="btn orange" type="submit" style="padding:10px 20px;">Сохранить изменения</button>
                    <a href="?tab=projects" class="btn gray" style="padding:10px 20px;">Отмена</a>
                </div>
            </form>
        <?php else: ?>
            <h3>Добавить новый проект</h3>
            <form action="?tab=projects" method="POST" enctype="multipart/form-data" class="card" style="max-width: 600px; margin-bottom:40px;">
                <input type="hidden" name="action" value="add_project">
                <label>Название проекта</label>
                <input type="text" name="title" required placeholder="Введите название проекта">
                <label style="display:block; margin-top:10px;">Описание</label>
                <textarea name="description" required placeholder="Введите краткое описание"></textarea>
                <label style="display:block; margin-top:10px;">Иконка проекта (авто-сжатие в WebP)</label>
                <input type="file" name="icon" accept="image/png, image/jpeg, image/webp">
                <label style="display:block; margin-top:10px;">Тип загрузки</label>
                <select name="type" id="project_type" onchange="updateFormType('')">
                    <option value="link">Внешняя ссылка (Кнопка «Перейти»)</option>
                    <option value="file">Файл / Программа (Любой формат / .EXE)</option>
                    <option value="zip_view">ZIP-архив (С возможностью смотреть файлы онлайн)</option>
                    <option value="site">Полноценный сайт (Из ZIP-архива, Кнопка «Открыть сайт»)</option>
                </select>
                <div id="adm_link">
                    <label style="display:block; margin-top:10px;">Ссылка на целевой проект (URL)</label>
                    <input type="text" name="link" placeholder="https://domain.com">
                </div>
                <div id="adm_file" style="display:none;">
                    <label id="file_label" style="display:block; margin-top:10px; color:#ff7777;">Выберите файл</label>
                    <input type="file" name="file" id="file_input">
                </div>
                <button class="btn ok" type="submit" style="margin-top:15px; padding:10px 20px;">Опубликовать проект</button>
            </form>
        <?php endif; ?>

        <h3>Управление загрузками</h3>
        <?php if (empty($projects_data)): ?>
            <p style="color:#666;">Список пуст.</p>
        <?php else: ?>
            <?php foreach (array_reverse($projects_data, true) as $key => $p): ?>
                <div class="card" style="<?= !empty($p['hidden']) ? 'opacity:0.4; border-color:#444;' : '' ?>">
                    <div style="float: right; display: flex; gap: 5px;">
                        <a href="?tab=projects&edit_id=<?=$p['id']?>" class="btn blue">Редактировать</a>
                        <form action="?tab=projects" method="POST" style="display:inline;"><input type="hidden" name="action" value="toggle_project"><input type="hidden" name="id" value="<?=$p['id']?>"><button class="btn gray" type="submit"><?= !empty($p['hidden']) ? 'Показать' : 'Скрыть' ?></button></form>
                        <form action="?tab=projects" method="POST" style="display:inline;" onsubmit="return confirm('Удалить проект и все его файлы безвозвратно?');"><input type="hidden" name="action" value="del_project"><input type="hidden" name="id" value="<?=$p['id']?>"><button class="btn no" type="submit">Удалить</button></form>
                    </div>
                    <div style="display:flex; gap:12px; align-items:center;">
                        <?php if(!empty($p['icon']) && file_exists($p['icon'])): ?><img src="<?=$p['icon']?>" style="width:44px; height:44px; object-fit:cover; border-radius:8px; border:1px solid #2a0000;"><?php endif; ?>
                        <h3 style="margin:0; font-size:18px;"><?=htmlspecialchars($p['title'])?></h3>
                    </div>
                    <p style="color:#ccc; font-size:14px; margin:10px 0; max-width:70%;"><?=nl2br(htmlspecialchars($p['description']))?></p>
                    <div class="meta">Тип: <b><?php if($p['type']==='link') echo 'Ссылка (Перейти)'; elseif($p['type']==='site') echo 'Распакованный сайт (Открыть)'; elseif($p['type']==='zip_view') echo 'ZIP-архив (Просмотр содержимого)'; else echo 'Файл / Программа'; ?></b> | Путь: <code style="color:#ff7777; word-break: break-all;"><?=htmlspecialchars($p['path'])?></code></div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === ФАЙЛЫ === -->
    <?php elseif ($tab === "files"): ?>
        <div class="card">
            <h3>Поделиться файлом с отделом</h3>
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="action" value="upload_file">
                <input type="file" name="team_file" required style="background: #1a1a24; padding: 10px; margin-bottom: 8px;">
                <input type="text" name="description" placeholder="Краткое описание (например: Исходник нового лаунчера Rmain)">
                <label style="font-size: 13px; color: #aaa; margin-top: 8px; display: block;">Кому доступен файл:</label>
                <select name="department" required><option value="all">Всей команде (Всем отделам)</option><option value="leader">Отделу Руководителей (самый важный)</option><option value="tester">Отделу Тестирования (Тестеры)</option><option value="admin">Административному отделу (Админы)</option><option value="dev">Разработчикам и Кодерам</option></select>
                <button class="btn ok" type="submit">Загрузить файл</button>
            </form>
        </div>
        <h3 style="margin-top: 20px;">Доступные вам файлы</h3>
        <?php
        $my_dept = [];
        if ($role === "Руководитель") $my_dept[] = "leader";
        if (in_array($role, ["Тестер", "Главный Тестер"])) $my_dept[] = "tester";
        if (in_array($role, ["Администратор", "Главный Администратор"])) $my_dept[] = "admin";
        if (in_array($role, ["Кодер", "Главный Кодер", "Главный разработчик", "Разработчик"])) $my_dept[] = "dev";
        $visible_files = array_filter($files_data, function($f) use ($my_dept, $user, $is_leader) {
            if ($is_leader || $f["uploader"] === $user || $f["department"] === "all") return true;
            if (in_array($f["department"], $my_dept)) return true; return false;
        });
        if (empty($visible_files)): ?>
            <p>Нет доступных файлов для вашего отдела.</p>
        <?php else: ?>
            <?php foreach (array_reverse($visible_files) as $f): ?>
                <?php $dept_label = "Всей команде"; if ($f["department"] === "leader") $dept_label = "Руководителям"; if ($f["department"] === "tester") $dept_label = "Тестерам"; if ($f["department"] === "admin") $dept_label = "Администраторам"; if ($f["department"] === "dev") $dept_label = "Разработчикам/Кодерам"; ?>
                <div class="file-row">
                    <div class="file-info">
                        <div class="file-name"><?=htmlspecialchars($f["name"])?> <span class="badge badge-new" style="background:#444;"><?=formatBytes($f["size"])?></span></div>
                        <div class="file-meta">Загрузил: <b><?=htmlspecialchars($f["uploader"])?></b> | Дата: <?=htmlspecialchars($f["time"])?> | Доступ: <b style="color:#ff2a2a;"><?=$dept_label?></b></div>
                        <?php if(!empty($f["desc"])): ?><div class="file-desc"><?=htmlspecialchars($f["desc"])?></div><?php endif; ?>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <a href="<?=htmlspecialchars($f["path"])?>" download class="btn blue" style="text-decoration:none;">Скачать</a>
                        <?php if ($is_leader || $f["uploader"] === $user): ?><form method="POST" style="margin:0;"><input type="hidden" name="action" value="del_file"><input type="hidden" name="id" value="<?=htmlspecialchars($f["id"])?>"><button class="btn no" type="submit">Удалить</button></form><?php endif; ?>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === ЧАТ === -->
    <?php elseif ($tab === "chat"): ?>
        <h3 style="color:#ff2a2a; margin:bottom:15px;">Командный чат</h3>
        <div class="chat-container" id="chatbox">
            <?php
            if (!empty($chat_data["pinned_id"])) {
                foreach ($chat_data["messages"] as $m) {
                    if ((string)$m["id"] === (string)$chat_data["pinned_id"]) {
                        $snippet = mb_strimwidth($m["text"], 0, 55, "...");
                        if (empty($snippet) && !empty($m["photo"])) $snippet = "[Фотография]";
                        if (empty($snippet) && !empty($m["poll"])) $snippet = "[Опрос]";
                        echo '<a href="#msg-' . $m["id"] . '" class="pinned-mini-bar"><div class="pinned-icon">📌</div><div class="pinned-content"><div class="pinned-author">' . htmlspecialchars($m["user"]) . '</div><div class="pinned-text-snippet">' . htmlspecialchars($snippet) . '</div></div><form method="POST" style="margin:0; margin-left:10px; z-index:11; position:relative;"><input type="hidden" name="action" value="unpin_msg"><button class="btn gray" type="submit" style="padding:4px 8px; margin-top:0;">Открепить</button></form></a>';
                        break;
                    }
                }
            }
            if (empty($chat_data["messages"])) echo "<p>В чате пока нет сообщений.</p>";
            else foreach ($chat_data["messages"] as $m) echo render_chat_message($m, ((string)$m["id"] === (string)$chat_data["pinned_id"]), $user, $is_leader);
            ?>
        </div>
        <script>const chatbox = document.getElementById('chatbox'); if(chatbox && !window.location.hash) chatbox.scrollTop = chatbox.scrollHeight;</script>

        <div class="card">
            <h3>Написать сообщение</h3>
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="action" value="send_chat_msg">
                <textarea name="text" placeholder="Введите сообщение..."></textarea>
                <div style="display:flex; gap:10px; margin-top:8px;">
                    <div style="flex:1;"><label style="font-size:12px; color:#aaa;">Прикрепить фото:</label><input type="file" name="photo" accept="image/*" style="margin-top:5px;"></div>
                </div>
                <div style="margin-top:10px; padding:10px; background:#050509; border-radius:8px; border:1px solid #333;">
                    <h4 style="margin:0 0 6px 0; font-size:13px; color:#aaa;">Прикрепить опрос (необязательно)</h4>
                    <input type="text" name="poll_q" placeholder="Вопрос опроса">
                    <input type="text" name="poll_opt" placeholder="Варианты ответа через запятую">
                </div>
                <button class="btn ok" type="submit" style="margin-top:12px; width:100%; padding:10px; font-size:14px;">Отправить</button>
            </form>
        </div>

    <!-- === ЦЕЛИ === -->
    <?php elseif ($tab === "goals"): ?>
        <?php if ($is_leader): ?>
            <div class="card">
                <h3>Поставить новую цель</h3>
                <form method="POST">
                    <input type="hidden" name="action" value="add_goal">
                    <input type="text" name="title" placeholder="Название работы / Цель" required>
                    <textarea name="description" placeholder="Описание"></textarea>
                    <div style="display: flex; gap: 10px; margin-top: 6px;">
                        <div style="flex: 1;"><label style="font-size: 13px; color: #aaa;">Дата дедлайна:</label><input type="date" name="deadline_date" required></div>
                        <div style="flex: 1;"><label style="font-size: 13px; color: #aaa;">Время:</label><input type="time" name="deadline_time" required></div>
                    </div>
                    <label style="font-size: 13px; color: #aaa; margin-top: 8px; display: block;">Кому назначить задачу:</label>
                    <select name="assigned_to" required>
                        <option value="all">Всей команде</option>
                        <optgroup label="Отделам (Классам)"><option value="class:admin">Администрации</option><option value="class:coder">Кодерам</option><option value="class:tester">Тестерам</option></optgroup>
                        <optgroup label="Конкретным сотрудникам">
                            <?php foreach ($users as $login => $u): ?><?php if (($u["role"] ?? "Пользователь") !== "Пользователь"): ?><option value="user:<?=htmlspecialchars($login)?>"><?=htmlspecialchars($login)?> (<?=htmlspecialchars($u["role"])?>)</option><?php endif; ?><?php endforeach; ?>
                        </optgroup>
                    </select>
                    <button class="btn ok" type="submit">Поставить цель</button>
                </form>
            </div>
        <?php endif; ?>
        <h3 style="margin-top: 20px;">Текущие цели команды</h3>
        <?php if (!$goals): ?><p>Активных целей пока нет.</p><?php else: ?>
            <?php foreach (array_reverse($goals) as $g): ?>
                <?php
                $now = new DateTime(); $target = new DateTime($g["deadline"]); $is_expired = $now > $target;
                if ($is_expired) { $time_left_str = "Время вышло!"; $badge_class = "badge-dec"; } 
                else { $diff = $now->diff($target); $time_left_str = "Осталось: " . $diff->format('%a дней, %h часов, %i минут'); $badge_class = "badge-new"; }
                $assigned = $g["assigned_to"] ?? "all"; $assigned_text = "Всей команде";
                if ($assigned === "class:admin") $assigned_text = "Отделу Администрации"; elseif ($assigned === "class:coder") $assigned_text = "Разработчикам и Кодерам"; elseif ($assigned === "class:tester") $assigned_text = "Отделу Тестирования"; elseif (strpos($assigned, "user:") === 0) $assigned_text = "Сотруднику: " . htmlspecialchars(substr($assigned, 5));
                ?>
                <div class="card">
                    <h3><?=htmlspecialchars($g["title"])?> <span class="badge <?=$badge_class?>"><?=$time_left_str?></span></h3>
                    <div class="meta" style="border-left: 2px solid #ff2a2a; padding-left: 8px; margin-bottom: 8px;">Назначено: <b style="color:#fff;"><?=$assigned_text?></b></div>
                    <div class="meta">Поставил: <?=htmlspecialchars($g["created_by"])?> | Точный дедлайн: <?=htmlspecialchars($g["deadline"])?></div>
                    <?php if (!empty($g["description"])): ?><div style="margin-top: 8px; font-size: 14px; background: #050509; padding: 10px; border-radius: 6px; border: 1px solid #333;"><?=nl2br(htmlspecialchars($g["description"]))?></div><?php endif; ?>
                    <?php if ($is_leader): ?><form method="POST" style="margin-top:10px;"><input type="hidden" name="action" value="del_goal"><input type="hidden" name="id" value="<?=htmlspecialchars($g["id"])?>"><button class="btn no" type="submit">Удалить цель</button></form><?php endif; ?>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === ШТРАФЫ === -->
    <?php elseif ($tab === "fines"): ?>
        <?php if ($is_leader): ?>
            <div class="card">
                <h3>Выписать штраф сотруднику</h3>
                <form method="POST">
                    <input type="hidden" name="action" value="add_fine">
                    <label style="font-size: 13px; color: #aaa;">Выберите сотрудника:</label>
                    <select name="user" required><option value="">-- Выбрать из команды --</option><?php foreach ($users as $login => $u) if (($u["role"] ?? "Пользователь") !== "Пользователь") echo '<option value="'.htmlspecialchars($login).'">'.htmlspecialchars($login).' ('.htmlspecialchars($u["role"]).')</option>'; ?></select>
                    <label style="font-size: 13px; color: #aaa; margin-top: 8px; display: block;">Сумма штрафа (от 10 руб.):</label>
                    <input type="number" name="amount" min="10" placeholder="Например: 500" required>
                    <label style="font-size: 13px; color: #aaa; margin-top: 8px; display: block;">Причина штрафа:</label>
                    <textarea name="reason" placeholder="Почему был выписан штраф..." required></textarea>
                    <p style="font-size: 12px; color: #aaa;">* Если штраф не оплачен за 30 дней, система заберет все права.</p>
                    <button class="btn no" type="submit">Выписать штраф</button>
                </form>
            </div>
        <?php endif; ?>
        <h3 style="margin-top: 20px;">Список штрафов</h3>
        <?php if (!$fines): ?><p>Штрафов пока нет.</p><?php else: ?>
            <?php foreach (array_reverse($fines) as $f): ?>
                <?php
                $is_paid = !empty($f["paid"]);
                if ($is_paid) { $status_text = "Оплачен (" . htmlspecialchars($f["paid_date"]) . ")"; $badge = "badge-acc"; } 
                else { $days_left = 30 - floor((time() - strtotime($f["issue_date"])) / 86400); if ($days_left <= 0) { $status_text = "Просрочен! Права забраны."; $badge = "badge-dec"; } else { $status_text = "Ожидает оплаты (осталось $days_left дн.)"; $badge = "badge-warn"; } }
                ?>
                <div class="card">
                    <h3>Сотрудник: <?=htmlspecialchars($f["user"])?> — <?=htmlspecialchars($f["amount"])?> ₽ <span class="badge <?=$badge?>"><?=$status_text?></span></h3>
                    <div class="meta">Выписан: <?=htmlspecialchars($f["issue_date"])?> | Выписал: <?=htmlspecialchars($f["issued_by"])?></div>
                    <div style="margin-top: 8px; font-size: 14px; border-left: 2px solid #c53030; padding-left: 10px;"><b>Причина:</b> <?=nl2br(htmlspecialchars($f["reason"]))?></div>
                    <div style="margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap;">
                        <?php if (!$is_paid): ?>
                            <?php if ($f["user"] === $user): ?><form method="POST"><input type="hidden" name="action" value="pay_fine_online"><input type="hidden" name="id" value="<?=htmlspecialchars($f["id"])?>"><button class="btn blue" type="submit">Оплатить онлайн (Platega)</button></form><?php endif; ?>
                            <?php if ($is_leader): ?><form method="POST"><input type="hidden" name="action" value="pay_fine_manual"><input type="hidden" name="id" value="<?=htmlspecialchars($f["id"])?>"><button class="btn ok" type="submit">Подтвердить получение (вручную)</button></form><?php endif; ?>
                        <?php endif; ?>
                        <?php if ($is_leader): ?><form method="POST"><input type="hidden" name="action" value="del_fine"><input type="hidden" name="id" value="<?=htmlspecialchars($f["id"])?>"><button class="btn gray" type="submit">Удалить запись</button></form><?php endif; ?>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === ЗАЯВКИ === -->
    <?php elseif ($tab === "apps"): ?>
        <form class="search-bar" method="GET">
            <input type="hidden" name="tab" value="apps">
            <div><label>Поиск по нику / email</label><br><input type="text" name="search" value="<?=htmlspecialchars($search)?>" placeholder="Ник или email"></div>
            <div><label>Сортировка</label><br><select name="sort"><option value="newest" <?=$sort==="newest"?"selected":""?>>Сначала новые</option><option value="oldest" <?=$sort==="oldest"?"selected":""?>>Сначала старые</option><option value="status" <?=$sort==="status"?"selected":""?>>По статусу</option></select></div>
            <div style="align-self:flex-end;"><button class="btn gray" type="submit" style="margin-top:0;">Применить</button></div>
        </form>
        <?php if (!$applications): ?><p>Заявок пока нет.</p><?php else: ?>
            <?php foreach ($applications as $app): ?>
                <?php
                $status = $app["status"] ?? "new"; $badgeText = "Новая"; $badgeClass = "badge-new";
                if ($status === "viewed") { $badgeText = "Просмотрена"; $badgeClass = "badge-viewed"; } 
                elseif ($status === "resolved_accept") { $badgeText = "Решена (принята)"; $badgeClass = "badge-acc"; } 
                elseif ($status === "resolved_decline") { $badgeText = "Решена (отказ)"; $badgeClass = "badge-dec"; }
                $email = ""; $nick  = "";
                foreach ($app["answers"] as $row) { if (mb_stripos($row["q"], "email") !== false) $email = $row["a"]; if (mb_stripos($row["q"], "Ник") !== false) $nick  = $row["a"]; }
                ?>
                <div class="card">
                    <div class="meta">ID: <?=htmlspecialchars($app["id"])?> | <?=htmlspecialchars($app["type"])?> | <?=htmlspecialchars($app["time"])?> <span class="badge <?=$badgeClass?>"><?=$badgeText?></span></div>
                    <div class="meta">Ник: <?=htmlspecialchars($nick)?> | Email: <?=htmlspecialchars($email)?></div>
                    <?php foreach ($app["answers"] as $row): ?><div class="meta"><b><?=htmlspecialchars($row["q"])?></b><br><?=nl2br(htmlspecialchars($row["a"]))?></div><?php endforeach; ?>
                    <form action="decision.php" method="POST" style="margin-top:8px;"><input type="hidden" name="id" value="<?=htmlspecialchars($app["id"])?>"><textarea name="comment" placeholder="Комментарий кандидату (необязательно)"></textarea><div style="margin-top:6px;"><button class="btn ok" name="decision" value="accept">Принять</button><button class="btn no" name="decision" value="decline">Отказать</button></div></form>
                    <?php if ($status === "new"): ?><form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="mark_viewed"><input type="hidden" name="id" value="<?=htmlspecialchars($app["id"])?>"><button class="btn gray" type="submit">Отметить как просмотренную</button></form><?php endif; ?>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === СООБЩЕНИЯ САЙТА === -->
    <?php elseif ($tab === "directors"): ?>
        <h3>Заявки на регистрацию школы</h3>
        <?php
        $pendingReqs = array_filter($director_requests, fn($r) => ($r["status"] ?? "pending") === "pending");
        $resolvedReqs = array_filter($director_requests, fn($r) => ($r["status"] ?? "pending") !== "pending");
        ?>
        <?php if (!$pendingReqs): ?><p style="color:#666;">Новых заявок нет.</p><?php else: ?>
            <?php foreach ($pendingReqs as $req): ?>
                <div class="card" style="border-left: 4px solid #2b6cb0;">
                    <div style="float:right;"><span class="badge badge-new">Новая</span></div>
                    <h3><?=htmlspecialchars($req["schoolName"])?></h3>
                    <div class="meta">Директор: <b><?=htmlspecialchars($req["fullName"] ?? "—")?></b> | Email: <b><?=htmlspecialchars($req["email"] ?? "—")?></b><?php if (!empty($req["phone"])): ?> | Телефон: <b><?=htmlspecialchars($req["phone"])?></b><?php endif; ?></div>
                    <div class="meta">Желаемый логин: <b><?=htmlspecialchars($req["login"])?></b> | Пароль: <b><?=htmlspecialchars($req["password"])?></b></div>
                    <div class="meta">Дата заявки: <?=htmlspecialchars($req["date"] ?? "")?></div>
                    <div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;">
                        <form method="POST"><input type="hidden" name="action" value="approve_request"><input type="hidden" name="id" value="<?=htmlspecialchars($req["id"])?>"><button class="btn ok" type="submit">Одобрить</button></form>
                        <form method="POST" onsubmit="return confirm('Отклонить заявку?');"><input type="hidden" name="action" value="decline_request"><input type="hidden" name="id" value="<?=htmlspecialchars($req["id"])?>"><button class="btn no" type="submit">Отклонить</button></form>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

        <?php if ($resolvedReqs): ?>
            <h3 style="margin-top:20px;">Обработанные заявки</h3>
            <?php foreach ($resolvedReqs as $req): $st = $req["status"]; ?>
                <div class="card" style="opacity:0.7;">
                    <div style="float:right;"><span class="badge <?= $st === 'approved' ? 'badge-acc' : 'badge-dec' ?>"><?= $st === 'approved' ? 'Одобрена' : 'Отклонена' ?></span></div>
                    <h3><?=htmlspecialchars($req["schoolName"])?></h3>
                    <div class="meta">Директор: <?=htmlspecialchars($req["fullName"] ?? "—")?> | Email: <?=htmlspecialchars($req["email"] ?? "—")?> | Логин: <?=htmlspecialchars($req["login"])?></div>
                    <form method="POST" style="margin-top:6px;" onsubmit="return confirm('Удалить запись о заявке?');"><input type="hidden" name="action" value="delete_request"><input type="hidden" name="id" value="<?=htmlspecialchars($req["id"])?>"><button class="btn gray" type="submit">Удалить запись</button></form>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

        <h3 style="margin-top:26px;">Добавить директора вручную</h3>
        <div class="card">
            <form method="POST">
                <input type="hidden" name="action" value="add_director">
                <input type="text" name="schoolName" placeholder="Название школы" required>
                <input type="text" name="fullName" placeholder="ФИО директора">
                <input type="email" name="email" placeholder="Email директора" required>
                <input type="text" name="login" placeholder="Логин" required>
                <input type="text" name="password" placeholder="Пароль" required>
                <button class="btn ok" type="submit">Создать аккаунт директора</button>
            </form>
        </div>

        <?php
            // Постраничный список: даже при огромном числе школ страница
            // администратора не пытается отрисовать их все разом — только
            // текущую страницу (по умолчанию 30 штук), плюс поиск по
            // названию школы или логину через лёгкий индекс.
            $dirSearch = trim($_GET["dsearch"] ?? "");
            $dirPageSize = 30;
            $dirPage = max(1, (int)($_GET["dpage"] ?? 1));
            $dirOffset = ($dirPage - 1) * $dirPageSize;
            $dirPageData = dl_list_index_page($dirSearch, $dirOffset, $dirPageSize);
            $dirTotal = $dirPageData["total"];
            $dirTotalPages = max(1, (int)ceil($dirTotal / $dirPageSize));
        ?>

        <h3 style="margin-top:26px;">Директора школ (<?=$dirTotal?>)</h3>

        <?php if (!empty($__migrationResult['skipped'])): ?>
            <div class="card" style="border-color:#c53030;">
                <b>При переносе старых данных в MySQL пропущено школ: <?=count($__migrationResult['skipped'])?></b> (обычно из-за задвоенного логина директора — в MySQL логин теперь обязан быть уникален). Эти школы <b>не потеряны</b> — их старые файлы (<code>database_&lt;slug&gt;.json</code>) остались на диске, их можно добавить вручную ниже под другим логином, если это разные школы.
                <ul style="margin:8px 0 0 20px; font-size:12px; color:#555;">
                    <?php foreach ($__migrationResult['skipped'] as $s): ?><li><?=htmlspecialchars($s)?></li><?php endforeach; ?>
                </ul>
            </div>
        <?php endif; ?>

        <?php if (isset($_GET["regen_offset"])): ?>
            <div class="card" style="border-color:#3182ce;">
                Обновление файлов школ: обработано <?=(int)$_GET["regen_offset"]?> из <?=(int)($_GET["regen_total"] ?? 0)?>.
                <form method="POST" style="display:inline;"><input type="hidden" name="action" value="regenerate_all"><input type="hidden" name="offset" value="<?=(int)$_GET["regen_offset"]?>"><button class="btn blue" type="submit">Обработать дальше</button></form>
            </div>
        <?php elseif (isset($_GET["regen_done"])): ?>
            <div class="card" style="border-color:#38a169;">Готово — файлы всех школ обновлены.</div>
        <?php endif; ?>

        <?php if ($dirTotal): ?>
            <form method="POST" onsubmit="return confirm('Пересоздать dairy.html и сайт-визитку для ВСЕХ школ? Для большого числа школ это может потребовать несколько нажатий «Обработать дальше».');" style="margin-bottom:14px;">
                <input type="hidden" name="action" value="regenerate_all">
                <input type="hidden" name="offset" value="0">
                <button class="btn blue" type="submit">Обновить файлы всех школ</button>
                <span style="font-size:12px; color:#999; margin-left:8px;">У каждой школы своя копия dairy.html — после правок в оригинальном dairy.html нажмите сюда, чтобы разослать обновление всем школам разом.</span>
            </form>
        <?php endif; ?>

        <form method="GET" style="margin-bottom:14px;">
            <input type="hidden" name="tab" value="directors">
            <input type="text" name="dsearch" value="<?=htmlspecialchars($dirSearch)?>" placeholder="Поиск по названию школы или логину директора">
            <button class="btn blue" type="submit">Искать</button>
            <?php if ($dirSearch !== ""): ?><a href="admin.php?tab=directors" style="margin-left:8px; color:#999; font-size:13px;">Сбросить</a><?php endif; ?>
        </form>

        <?php if (!$dirPageData["rows"]): ?><p style="color:#666;">Школ не найдено.</p><?php else: ?>
            <?php foreach ($dirPageData["rows"] as $row): $d = dl_load_full($row["slug"]); if (!$d) continue; ?>
                <div class="card">
                    <h3><?=htmlspecialchars($d["schoolName"])?></h3>
                    <div class="meta">Директор: <?=htmlspecialchars($d["fullName"] ?? "—")?> | Email: <?=htmlspecialchars($d["email"] ?? "—")?></div>
                    <div class="meta">Логин: <b><?=htmlspecialchars($d["login"])?></b> | Пароль: <b><?=htmlspecialchars($d["password"])?></b> | Данные: <code>database_<?=htmlspecialchars($d["slug"])?>.json</code></div>
                    <div class="meta">Страница журнала школы:
                        <?php if (!empty($d["schoolFile"]) && file_exists($d["schoolFile"])): ?>
                            <a href="<?=htmlspecialchars($d["schoolFile"])?>" target="_blank"><?=htmlspecialchars($d["schoolFile"])?></a>
                        <?php else: ?>
                            <span style="color:#c53030;">не создана</span>
                            <form method="POST" style="display:inline;"><input type="hidden" name="action" value="regenerate_file"><input type="hidden" name="slug" value="<?=htmlspecialchars($d["slug"])?>"><button class="btn blue" type="submit" style="padding:3px 8px; font-size:11px; margin:0;">Создать файл</button></form>
                            <span style="font-size:11px; color:#999;">(нужен dairy.html рядом с admin.php)</span>
                        <?php endif; ?>
                    </div>
                    <div class="meta">Сайт-визитка школы (редактируется программистом в scheduler.html):
                        <?php $siteFile = "schools/" . $d["slug"] . "/index.html"; ?>
                        <?php if (file_exists($siteFile)): ?>
                            <a href="<?=htmlspecialchars($siteFile)?>" target="_blank"><?=htmlspecialchars($siteFile)?></a>
                        <?php else: ?>
                            <span style="color:#c53030;">не создана</span>
                            <span style="font-size:11px; color:#999;">(нужен school_site_template.html рядом с admin.php — нажмите «Создать файл» выше, чтобы пересоздать)</span>
                        <?php endif; ?>
                    </div>
                    <div style="margin-top:8px; display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
                        <form method="POST" style="display:flex; gap:6px; align-items:center;"><input type="hidden" name="action" value="reset_director_password"><input type="hidden" name="id" value="<?=htmlspecialchars($d["id"])?>"><input type="hidden" name="slug" value="<?=htmlspecialchars($d["slug"])?>"><input type="text" name="password" placeholder="Новый пароль" style="margin:0;" required><button class="btn blue" type="submit" style="margin:0;">Сменить пароль</button></form>
                        <form method="POST" onsubmit="return confirm('Удалить аккаунт директора? Данные школы (журнал) при этом не удаляются.');"><input type="hidden" name="action" value="delete_director"><input type="hidden" name="slug" value="<?=htmlspecialchars($d["slug"])?>"><button class="btn no" type="submit">Удалить директора</button></form>
                    </div>
                </div>
            <?php endforeach; ?>
            <?php if ($dirTotalPages > 1): ?>
                <div style="display:flex; gap:8px; align-items:center; margin-top:14px;">
                    <?php if ($dirPage > 1): ?><a class="btn blue" href="admin.php?tab=directors&dpage=<?=$dirPage - 1?>&dsearch=<?=urlencode($dirSearch)?>">← Назад</a><?php endif; ?>
                    <span style="color:#999; font-size:13px;">Страница <?=$dirPage?> из <?=$dirTotalPages?></span>
                    <?php if ($dirPage < $dirTotalPages): ?><a class="btn blue" href="admin.php?tab=directors&dpage=<?=$dirPage + 1?>&dsearch=<?=urlencode($dirSearch)?>">Вперёд →</a><?php endif; ?>
                </div>
            <?php endif; ?>
        <?php endif; ?>

    <?php elseif ($tab === "messages"): ?>
        <h3 style="color:#ff2a2a; margin-bottom:15px;">Сообщения от пользователей</h3>
        <?php if (!$messages): ?><p>Сообщений пока нет.</p><?php else: ?>
            <?php foreach (array_reverse($messages) as $m): ?>
                <div class="card">
                    <h3>От: <?=htmlspecialchars($m["name"])?> (<?=$m["email"]?>)</h3>
                    <div class="meta"><?=htmlspecialchars($m["time"] ?? "")?></div>
                    <?php if(!empty($m["ip"])): ?><div class="meta" style="color:#e67e22;">IP: <b><?=htmlspecialchars($m["ip"])?></b></div><?php endif; ?>
                    <div style="margin-top:10px; background:#050509; padding:10px; border-radius:6px; border:1px solid #333;"><?=nl2br(htmlspecialchars($m["text"]))?></div>
                    <?php if (!empty($m["reply"])): ?>
                        <div class="reply-block"><b>Ваш ответ:</b><br><?=nl2br(htmlspecialchars($m["reply"]["text"]))?><div class="reply-sig">Сотрудник: <?=htmlspecialchars($m["reply"]["author"])?> (<?=htmlspecialchars($m["reply"]["role"])?>)<br>С уважением, Rteam</div></div>
                    <?php else: ?>
                        <form method="POST" style="margin-top:10px;"><input type="hidden" name="action" value="reply_msg"><input type="hidden" name="id" value="<?=htmlspecialchars($m["id"])?>"><textarea name="reply_text" placeholder="Введите ответ пользователю..." required></textarea><button class="btn ok" type="submit">Отправить ответ (и Email)</button></form>
                    <?php endif; ?>
                    <form method="POST" style="margin-top:10px;"><input type="hidden" name="action" value="del_msg"><input type="hidden" name="id" value="<?=htmlspecialchars($m["id"])?>"><button class="btn no" type="submit">Удалить из системы</button></form>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === ТИКЕТЫ ПОДДЕРЖКИ САЙТА === -->
    <?php elseif ($tab === "support"): ?>
        <h3 style="color:#ff2a2a; margin:0;">Центр поддержки (Тикеты)</h3>
        <div class="support-layout">
            <div class="sup-sidebar"><div id="ticketSidebarList">
                <?php $active_id = $_GET['ticket_id'] ?? null; if (!$tickets): ?><div style="padding: 20px; color: #777; text-align: center; font-size: 13px;">Тикетов пока нет.</div><?php else: ?>
                    <?php foreach (array_reverse($tickets) as $t): $statusColor = $t['status'] === 'Открыт' ? '#1f9d55' : ($t['status'] === 'Закрыт' ? '#777' : '#d97706'); ?>
                        <a href="?tab=support&ticket_id=<?=$t['id']?>" class="sup-ticket <?= ($active_id == $t['id']) ? 'active' : '' ?>"><div style="font-weight: bold; margin-bottom: 5px; color: #ff7777;"><?=$t['topic']?></div><div style="font-size: 11px; color: #777; display: flex; justify-content: space-between;"><span>#<?=$t['id']?> | <?=$t['client']?></span><span id="sidebar_status_<?=$t['id']?>" style="background: <?=$statusColor?>; padding: 2px 6px; border-radius: 4px; color: #fff;"><?=$t['status']?></span></div></a>
                    <?php endforeach; ?>
                <?php endif; ?>
            </div></div>
            <div class="sup-chat">
                <?php if ($active_id): ?>
                    <?php $curr_ticket = null; foreach ($tickets as $t) if ((string)$t["id"] === (string)$active_id) $curr_ticket = $t; if ($curr_ticket): ?>
                        <div class="sup-header">
                            <div><h3 style="margin:0; color:#fff;"><?=$curr_ticket['topic']?></h3><div style="font-size: 12px; color: #aaa;">Клиент: <b><?=$curr_ticket['client']?></b> | Статус: <span id="header_status"><?=$curr_ticket['status']?></span></div></div>
                            <?php if ($curr_ticket['status'] !== 'Закрыт'): ?><form method="POST" style="margin:0;" id="closeForm"><input type="hidden" name="action" value="close_ticket"><input type="hidden" name="id" value="<?=$curr_ticket['id']?>"><button class="btn no" type="submit" style="margin:0; padding:6px 12px;">Закрыть тикет</button></form><?php endif; ?>
                        </div>
                        <div class="sup-history" id="adminChatHistory">
                            <div class="bubble client">
                                <div class="b-meta">Клиент: <?=$curr_ticket['client']?> <span style="color:#777; font-weight:normal; font-size:10px;">(<?=$curr_ticket['date']?>)</span></div><?=nl2br(htmlspecialchars($curr_ticket['description']))?>
                                <?php if (!empty($curr_ticket["photo"])): ?><div style="margin-top: 10px; border-top: 1px dashed #333; padding-top: 10px;"><img src="<?=$curr_ticket["photo"]?>" style="max-height: 200px; border-radius: 4px; display:block; margin-bottom:10px;"><form method="POST" style="margin:0;"><input type="hidden" name="action" value="pin_photo"><input type="hidden" name="id" value="<?=$curr_ticket["id"]?>"><button class="btn <?=empty($curr_ticket['pinned_photo']) ? 'blue' : 'gray'?>" type="submit" style="padding:4px 8px; font-size:12px; margin:0;"><?=empty($curr_ticket['pinned_photo']) ? '📌 Закрепить фото' : 'Открепить фото'?></button></form></div><?php endif; ?>
                            </div>
                            <div id="repliesContainer">
                                <?php foreach ($curr_ticket["replies"] as $reply): $is_admin = $reply["is_admin"] ?? true; ?>
                                    <div class="bubble <?= $is_admin ? 'admin' : 'client' ?>"><div class="b-meta"><?= $is_admin ? htmlspecialchars($reply["employee"]) . ' (Rteam)' : 'Клиент: ' . htmlspecialchars($curr_ticket['client']) ?> <span style="color:#777; font-weight:normal; font-size:10px;">(<?=$reply["date"]?>)</span></div><?=nl2br(htmlspecialchars($reply["text"]))?><?php if (!empty($reply["photo"])): ?><div style="margin-top: 8px;"><img src="<?=htmlspecialchars($reply["photo"])?>" style="max-height: 150px; border-radius: 6px; border: 1px solid #333;"></div><?php endif; ?></div>
                                <?php endforeach; ?>
                            </div>
                        </div>
                        <form class="sup-controls" id="replyForm" method="POST" enctype="multipart/form-data" style="<?= $curr_ticket['status'] === 'Закрыт' ? 'display:none;' : '' ?>"><input type="hidden" name="action" value="reply_ticket"><input type="hidden" name="id" value="<?=$curr_ticket['id']?>"><input type="hidden" name="is_ajax" value="1"><label class="file-upload-btn" title="Прикрепить фото">📷 <input type="file" name="reply_photo" accept="image/*" style="display: none;"></label><input type="text" name="reply_text" placeholder="Ответить клиенту..." required style="margin:0; flex:1;"><button class="btn ok" type="submit" style="margin:0; width: auto;">Отправить</button></form>
                        <script>
                            const adminHist = document.getElementById("adminChatHistory"); const replyForm = document.getElementById("replyForm"); let lastHtml = document.getElementById("repliesContainer").innerHTML; const ticketId = "<?=$curr_ticket['id']?>";
                            if(adminHist) adminHist.scrollTop = adminHist.scrollHeight;
                            if (replyForm) { replyForm.addEventListener('submit', function(e) { e.preventDefault(); fetch('', { method: 'POST', body: new FormData(this) }).then(() => { this.reset(); loadMessages(); }); }); }
                            function loadMessages() { fetch('?ajax_html_ticket=' + ticketId).then(r => r.json()).then(data => { if (data.html !== lastHtml) { document.getElementById('repliesContainer').innerHTML = data.html; lastHtml = data.html; adminHist.scrollTop = adminHist.scrollHeight; } if (data.status === 'Закрыт') { if (replyForm) replyForm.style.display = 'none'; if (document.getElementById('closeForm')) document.getElementById('closeForm').style.display = 'none'; document.getElementById('header_status').innerText = 'Закрыт'; } }); }
                            setInterval(loadMessages, 2500);
                        </script>
                    <?php endif; ?>
                <?php else: ?><div style="display:flex; flex:1; align-items:center; justify-content:center; color:#777;">Выберите тикет в меню слева.</div><?php endif; ?>
            </div>
        </div>
        <script> function loadTicketList() { const activeId = "<?= $_GET['ticket_id'] ?? '' ?>"; fetch('?ajax_ticket_list=1&active_id=' + activeId).then(r => r.json()).then(data => { let sidebarList = document.getElementById('ticketSidebarList'); if (sidebarList && data.html !== sidebarList.innerHTML) { sidebarList.innerHTML = data.html; } }); } setInterval(loadTicketList, 3000); </script>

    <!-- === БАНЫ === -->
    <?php elseif ($tab === "bans"): ?>
        <h3 style="color:#ff2a2a; margin-bottom:15px;">Управление блокировками</h3>

        <div class="card" id="geoBlockCard">
            <h3>🌍 Гео-блокировка по странам</h3>
            <p class="meta" style="margin-bottom:10px;">Пользователи из указанных стран не смогут открыть сайт (index.php). Коды стран — по стандарту ISO 3166-1 alpha-2, через запятую или пробел.</p>
            <form method="POST">
                <input type="hidden" name="action" value="save_geoblock">
                <label style="display:flex; align-items:center; gap:8px; margin-bottom:10px; font-size:14px;">
                    <input type="checkbox" name="enabled" <?= !empty($geoblock_settings["enabled"]) ? "checked" : "" ?> style="width:auto;">
                    Гео-блокировка включена
                </label>
                <textarea name="countries" rows="2" placeholder="UA, PL, LT, LV, EE" style="width:100%; resize:vertical;"><?=htmlspecialchars(implode(", ", $geoblock_settings["countries"] ?? []))?></textarea>
                <div class="meta" style="margin:6px 0 10px;">По умолчанию: UA — Украина, PL — Польша, LT — Литва, LV — Латвия, EE — Эстония.</div>
                <button class="btn no" type="submit">Сохранить</button>
            </form>
        </div>

        <?php if (!empty($blocked_attempts)): ?>
        <div class="card" style="margin-top:15px;">
            <h3>🌍 Последние заблокированные попытки входа (<?=count($blocked_attempts)?>)</h3>
            <div style="max-height: 320px; overflow-y: auto; padding-right: 10px; margin-top:10px;">
                <?php foreach (array_reverse(array_slice($blocked_attempts, -50)) as $ba): ?>
                    <div class="card" style="border-color:#333; margin-top:5px;">
                        <div class="meta">Страна: <b style="color:#ff7777;"><?=htmlspecialchars($ba["country"] ?? "?")?></b> | IP: <b><?=htmlspecialchars($ba["ip"] ?? "?")?></b> | <?=htmlspecialchars($ba["time"] ?? "")?></div>
                        <?php $safe_ip2 = htmlspecialchars($ba["ip"] ?? ""); ?>
                        <button class="btn gray" style="margin-top:6px; font-size:11px; padding:4px 8px;" onclick="quickBanSetup('<?=$safe_ip2?>', 'Гео-блокировка: <?=htmlspecialchars($ba["country"] ?? "")?>')">🎯 Забанить этот IP</button>
                    </div>
                <?php endforeach; ?>
            </div>
            <form method="POST" style="margin-top:10px;" onsubmit="return confirm('Очистить журнал заблокированных попыток?');">
                <input type="hidden" name="action" value="clear_blocked_attempts">
                <button class="btn gray" type="submit">Очистить журнал</button>
            </form>
        </div>
        <?php endif; ?>

        <h3 style="margin-top:20px;">Выдать бан по IP вручную</h3>
        <div class="card" id="banFormCard"><form method="POST"><input type="hidden" name="action" value="add_ban"><input type="text" name="ip" placeholder="IP-адрес нарушителя (например: 192.168.1.1)" required><input type="text" name="reason" placeholder="Причина (например: Спам сообщениями)" required><label style="font-size: 13px; color: #aaa; margin-top: 8px; display: block;">Срок блокировки:</label><select name="duration"><option value="0">Навсегда</option><option value="1">На 1 час</option><option value="24">На 24 часа (1 день)</option><option value="168">На 7 дней</option><option value="720">На 30 дней</option></select><button class="btn no" type="submit">Заблокировать</button></form></div>
        <?php if (!empty($_GET["quickban_ip"])): ?>
        <script>
            (function() {
                const ipInput = document.querySelector('#banFormCard input[name="ip"]');
                const reasonInput = document.querySelector('#banFormCard input[name="reason"]');
                if (ipInput) ipInput.value = <?=json_encode($_GET["quickban_ip"])?>;
                if (reasonInput) reasonInput.value = <?=json_encode($_GET["quickban_reason"] ?? "")?>;
                document.getElementById('banFormCard')?.scrollIntoView({ behavior: 'smooth' });
            })();
        </script>
        <?php endif; ?>
        <h3 style="margin-top: 20px;">Активные блокировки</h3>
        <?php if (!$bans): ?><p>Заблокированных пользователей нет.</p><?php else: ?>
            <?php foreach (array_reverse($bans) as $b): $is_expired = ($b["expires"] > 0 && time() > $b["expires"]); $time_text = ($b["expires"] === 0) ? "Навсегда" : "До: " . date("Y-m-d H:i:s", $b["expires"]); $badge = $is_expired ? "badge-viewed" : "badge-dec"; $status = $is_expired ? "Истек" : "Активен"; ?>
                <div class="card" <?= $is_expired ? 'style="opacity: 0.6;"' : '' ?>><h3>IP: <?=htmlspecialchars($b["ip"])?> <span class="badge <?=$badge?>"><?=$status?></span></h3><div class="meta">Выдал: <?=htmlspecialchars($b["issued_by"] ?? "Неизвестно")?> | Дата бана: <?=htmlspecialchars($b["date"])?></div><div class="meta" style="color: #ff7777;">Срок: <?=$time_text?></div><div style="margin-top:8px; border-left: 2px solid #c53030; padding-left:10px; font-size:14px;"><b>Причина:</b> <?=htmlspecialchars($b["reason"])?></div><form method="POST" style="margin-top:10px;"><input type="hidden" name="action" value="unban"><input type="hidden" name="id" value="<?=htmlspecialchars($b["id"])?>"><button class="btn gray" type="submit">Снять бан</button></form></div>
            <?php endforeach; ?>
        <?php endif; ?>
        <h3 style="margin-top: 20px;">Последние сообщения (для быстрой блокировки)</h3>
        <?php if (!$messages): ?><p>Сообщений пока нет.</p><?php else: ?>
            <script> function quickBanSetup(ip, reason) { const ipInput = document.querySelector('input[name="ip"]'); const reasonInput = document.querySelector('input[name="reason"]'); if(ipInput && reasonInput) { ipInput.value = ip; reasonInput.value = reason; ipInput.focus(); window.scrollTo({ top: 0, behavior: 'smooth' }); } } </script>
            <div style="max-height: 400px; overflow-y: auto; padding-right: 10px;">
            <?php foreach (array_reverse(array_slice($messages, -20)) as $m): ?>
                <div class="card" style="border-color: #333; margin-top: 5px;"><div class="meta" style="margin-bottom: 2px;">От: <b><?=htmlspecialchars($m["name"])?></b> (<?=$m["email"]?>) | Дата: <?=htmlspecialchars($m["time"] ?? "")?></div><?php if(!empty($m["ip"])): ?><div class="meta" style="color:#e67e22;">IP: <b><?=htmlspecialchars($m["ip"])?></b></div><?php endif; ?><div style="font-size: 13px; margin-top: 4px; color: #ccc;"><?=mb_strimwidth(htmlspecialchars($m["text"]), 0, 100, "...")?></div><?php if(!empty($m["ip"])): ?><?php $safe_ip = htmlspecialchars($m["ip"]); $safe_reason = htmlspecialchars(addslashes("Спам: " . str_replace(["\r","\n"], " ", mb_strimwidth($m["text"], 0, 40, "...")))); ?><button class="btn gray" style="margin-top:8px; font-size:11px; padding:4px 8px;" onclick="quickBanSetup('<?=$safe_ip?>', '<?=$safe_reason?>')">🎯 Выбрать для бана</button><?php else: ?><div style="margin-top: 8px; font-size: 11px; color: #777;">IP-адрес неизвестен</div><?php endif; ?></div>
            <?php endforeach; ?>
            </div>
        <?php endif; ?>

    <!-- === ЧЁРНЫЙ СПИСОК === -->
    <?php elseif ($tab === "blacklist"): ?>
        <h3 style="color:#ff2a2a; margin-bottom:15px;">⚫ Чёрный список</h3>

        <div class="card" id="blacklistFormCard">
            <h3>Внести в чёрный список</h3>
            <form method="POST">
                <input type="hidden" name="action" value="add_blacklist">
                <input type="text" name="identifier" placeholder="ФИО или ник">
                <input type="text" name="ip" placeholder="IP-адрес (если указан — будет реально забанен сразу)" style="margin-top:8px;">
                <input type="text" name="reason" placeholder="Причина" style="margin-top:8px;">
                <label style="font-size:13px; color:#aaa; margin-top:8px; display:block;">Дата внесения:</label>
                <input type="date" name="date_added" value="<?=date("Y-m-d")?>">
                <p style="font-size:12px; color:#7fbf7f; margin-top:6px;">Если указать IP-адрес — он будет забанен реально и сразу, без дополнительного подписания.</p>
                <button class="btn no" type="submit" style="margin-top:10px;">Внести в чёрный список</button>
            </form>
        </div>

        <h3 style="margin-top:20px;">Записи (<?=count($blacklist)?>)</h3>
        <?php if (!$blacklist): ?><p>Чёрный список пуст.</p><?php else: ?>
            <?php foreach (array_reverse($blacklist) as $bl):
                $bl_ip = trim($bl["ip"] ?? "");
                $is_ip = $bl_ip !== "" && filter_var($bl_ip, FILTER_VALIDATE_IP) !== false;
                if (!empty($bl["released"])) { $status_text = "Выпущен"; $status_badge = "badge-viewed"; }
                elseif ($is_ip && !empty($bl["ip_ban_id"])) { $status_text = "IP реально забанен"; $status_badge = "badge-dec"; }
                elseif (!empty($bl["signed"])) { $status_text = "Подписан"; $status_badge = "badge-dec"; }
                else { $status_text = "Не подписан"; $status_badge = "badge-new"; }
            ?>
                <div class="card" <?=!empty($bl["released"]) ? 'style="opacity:0.6;"' : ''?>>
                    <h3><?=htmlspecialchars($bl["identifier"])?> <span class="badge <?=$status_badge?>"><?=$status_text?></span> <?php if ($is_ip): ?><span class="badge" style="background:#333;">IP</span><?php endif; ?></h3>
                    <div class="meta">Дата внесения: <?=htmlspecialchars($bl["date_added"])?> | Внёс: <b><?=htmlspecialchars($bl["added_by"] ?? "Неизвестно")?></b></div>
                    <?php if ($is_ip): ?>
                        <div class="meta" style="color:#e67e22;">IP: <b><?=htmlspecialchars($bl_ip)?></b></div>
                    <?php endif; ?>
                    <?php if (!empty($bl["reason"])): ?>
                        <div style="margin-top:6px; border-left:2px solid #c53030; padding-left:10px; font-size:14px;"><b>Причина:</b> <?=htmlspecialchars($bl["reason"])?></div>
                    <?php endif; ?>
                    <?php if (!empty($bl["signed"])): ?>
                        <div class="meta">Подписал: <b><?=htmlspecialchars($bl["signed_by"] ?? "")?></b> · <?=htmlspecialchars($bl["signed_at"] ?? "")?></div>
                    <?php endif; ?>
                    <?php if (!empty($bl["released"])): ?>
                        <div class="meta" style="color:#7fbf7f;">Выпустил: <b><?=htmlspecialchars($bl["released_by"] ?? "")?></b> · <?=htmlspecialchars($bl["released_at"] ?? "")?></div>
                        <div style="margin-top:6px; border-left:2px solid #4a9; padding-left:10px; font-size:14px;"><b>Причина выпуска:</b> <?=htmlspecialchars($bl["release_reason"] ?? "")?></div>
                    <?php endif; ?>

                    <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px;">
                        <?php if (empty($bl["signed"])): ?>
                            <form method="POST" onsubmit="return confirm('Подписать запись? <?=$is_ip ? 'IP будет забанен.' : ''?>');">
                                <input type="hidden" name="action" value="sign_blacklist">
                                <input type="hidden" name="id" value="<?=htmlspecialchars($bl["id"])?>">
                                <button class="btn ok" type="submit">✍️ Подписать</button>
                            </form>
                        <?php endif; ?>
                        <?php if (!empty($bl["signed"]) && empty($bl["released"])): ?>
                            <button type="button" class="btn gray" onclick="document.getElementById('releaseForm_<?=htmlspecialchars($bl["id"])?>').style.display='flex';">🔓 Выпустить</button>
                        <?php endif; ?>
                        <button type="button" class="btn gray" onclick="document.getElementById('editForm_<?=htmlspecialchars($bl["id"])?>').style.display='flex';">✏️ Редактировать</button>
                        <form method="POST" onsubmit="return confirm('Удалить запись из чёрного списка?');">
                            <input type="hidden" name="action" value="delete_blacklist">
                            <input type="hidden" name="id" value="<?=htmlspecialchars($bl["id"])?>">
                            <button class="btn no" type="submit">🗑 Удалить</button>
                        </form>
                    </div>

                    <?php if (!empty($bl["signed"]) && empty($bl["released"])): ?>
                    <form method="POST" id="releaseForm_<?=htmlspecialchars($bl["id"])?>" style="display:none; gap:8px; margin-top:10px; flex-wrap:wrap;">
                        <input type="hidden" name="action" value="release_blacklist">
                        <input type="hidden" name="id" value="<?=htmlspecialchars($bl["id"])?>">
                        <input type="text" name="release_reason" placeholder="Причина выпуска" required style="flex:1; min-width:200px;">
                        <button class="btn ok" type="submit">Подтвердить выпуск</button>
                    </form>
                    <?php endif; ?>

                    <form method="POST" id="editForm_<?=htmlspecialchars($bl["id"])?>" style="display:none; gap:8px; margin-top:10px; flex-wrap:wrap;">
                        <input type="hidden" name="action" value="edit_blacklist">
                        <input type="hidden" name="id" value="<?=htmlspecialchars($bl["id"])?>">
                        <input type="text" name="identifier" value="<?=htmlspecialchars($bl["identifier"])?>" placeholder="ФИО или ник" style="flex:1; min-width:160px;">
                        <input type="text" name="ip" value="<?=htmlspecialchars($bl_ip)?>" placeholder="IP-адрес" style="flex:1; min-width:160px;">
                        <input type="text" name="reason" value="<?=htmlspecialchars($bl["reason"] ?? "")?>" placeholder="Причина" style="flex:1; min-width:160px;">
                        <input type="date" name="date_added" value="<?=htmlspecialchars($bl["date_added"])?>">
                        <button class="btn ok" type="submit">Сохранить</button>
                    </form>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <!-- === БОТ TELEGRAM (БЕЗ ПЕРЕЗАГРУЗКИ / AJAX И РОЗЫГРЫШИ) === -->
    <?php elseif ($tab === "bot"): ?>
        <?php $bot_token = $settings["bot_token"] ?? ""; ?>
        
        <!-- НАСТРОЙКИ БОТА И РАССЫЛКА -->
        <h3 style="color:#ff2a2a; margin-bottom:15px;">Telegram Бот (Управление)</h3>
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
            <div class="card" style="flex: 1; min-width: 300px; margin-top: 0;">
                <h3>Настройки бота</h3>
                <form class="ajax-bot-form" method="POST" onsubmit="event.preventDefault(); const fd = new FormData(this); fd.append('is_ajax', '1'); fetch('admin.php?tab=bot', {method: 'POST', body: fd}).then(() => { showToast('Токен сохранен!', 'info'); });">
                    <input type="hidden" name="action" value="save_bot_token">
                    <label>Токен бота (от @BotFather)</label>
                    <input type="text" name="bot_token" value="<?=htmlspecialchars($bot_token)?>" placeholder="123456789:ABCdefGHI...">
                    <button class="btn ok" type="submit" style="margin-top:10px;">Сохранить токен</button>
                </form>
            </div>
            <div class="card" style="flex: 1; min-width: 300px; margin-top: 0; border-color: #805ad5;">
                <h3 style="color: #805ad5;">Массовая рассылка</h3>
                <form class="ajax-bot-form" method="POST" onsubmit="event.preventDefault(); const t = this.broadcast_text.value; if(!t) return; const fd = new FormData(this); fd.append('is_ajax', '1'); fetch('admin.php?tab=bot', {method: 'POST', body: fd}).then(r => r.text()).then(res => { if(res.trim()=='error') showToast('Ошибка токена!', 'error'); else { this.reset(); showToast('Рассылка выполнена!', 'info'); } });">
                    <input type="hidden" name="action" value="broadcast_tg">
                    <textarea name="broadcast_text" required placeholder="Текст сообщения для всех пользователей бота..." style="height: 45px; margin-bottom: 5px;"></textarea>
                    <button class="btn" type="submit" style="background:#805ad5; color:#fff; width: 100%;">Отправить всем пользователям</button>
                </form>
            </div>
        </div>

        <!-- УПРАВЛЕНИЕ РОЗЫГРЫШАМИ (НОВОЕ) -->
        <h3 style="color:#e67e22; margin-top:30px;">Управление Розыгрышами</h3>
        <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 20px;">
            <div class="card" style="flex: 1; min-width: 300px; margin-top: 0; border-color: #e67e22;">
                <h3>Создать розыгрыш</h3>
                <form method="POST" onsubmit="event.preventDefault(); const fd = new FormData(this); fd.append('is_ajax', '1'); fetch('admin.php?tab=bot', {method: 'POST', body: fd}).then(() => { this.reset(); showToast('Розыгрыш создан!', 'info'); loadBotData(); });">
                    <input type="hidden" name="action" value="add_bot_gw">
                    <input type="text" name="title" required placeholder="Название (Например: 1000 RUB на Platega)">
                    <textarea name="description" required placeholder="Описание и условия розыгрыша..." style="height: 60px; margin-top: 8px;"></textarea>
                    <label style="font-size: 13px; color: #aaa; margin-top: 8px; display: block;">Количество победителей:</label>
                    <input type="number" name="winners_count" required min="1" value="1">
                    <button class="btn orange" type="submit" style="margin-top:10px; width:100%;">Запустить розыгрыш</button>
                </form>
            </div>
            
            <div style="flex: 2; min-width: 300px;" id="botGiveawaysFeed" data-lasthtml="">
                <?= render_bot_giveaways_list(load_json("bot_giveaways.json", [])) ?>
            </div>
        </div>

        <!-- ВХОДЯЩИЕ ЗАЯВКИ ИЗ ТЕЛЕГРАМА -->
        <h3 style="margin-top:30px;">Входящие заявки из Telegram</h3>
        <div id="botTicketsFeed" data-lasthtml="">
            <?php
            $tg_tickets = load_json("bot_tickets.json", []);
            $banned_users = load_json("bot_banned.json", []);
            if (!is_array($banned_users)) $banned_users = [];
            echo render_bot_tickets($tg_tickets, $banned_users);
            ?>
        </div>

    <!-- === ПРОЧИЕ ВКЛАДКИ === -->
    <?php elseif ($tab === "leaks"): ?>
        <div class="card">
            <h3>Добавить слив</h3>
            <form method="POST"><input type="hidden" name="action" value="add_leak"><input type="text" name="title" placeholder="Заголовок" required><textarea name="content" placeholder="Текст / описание" required></textarea><button class="btn gray" type="submit">Сохранить</button></form>
        </div>
        <?php if ($leaks): ?>
            <?php foreach (array_reverse($leaks) as $l): ?>
                <div class="card">
                    <h3><?=htmlspecialchars($l["title"])?></h3>
                    <div class="meta">ID: <?=htmlspecialchars($l["id"])?> | <?=htmlspecialchars($l["time"] ?? "")?> | <?=!empty($l["hidden"]) ? "Скрыт" : "Показан"?></div>
                    <form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="edit_leak"><input type="hidden" name="id" value="<?=htmlspecialchars($l["id"])?>"><input type="text" name="title" value="<?=htmlspecialchars($l["title"])?>"><textarea name="content"><?=htmlspecialchars($l["content"])?></textarea><button class="btn gray" type="submit">Сохранить изменения</button></form>
                    <form method="POST" style="margin-top:6px;display:inline-block;"><input type="hidden" name="action" value="toggle_leak"><input type="hidden" name="id" value="<?=htmlspecialchars($l["id"])?>"><button class="btn ok" type="submit"><?=!empty($l["hidden"]) ? "Показать" : "Скрыть"?></button></form>
                    <form method="POST" style="margin-top:6px;display:inline-block;"><input type="hidden" name="action" value="del_leak"><input type="hidden" name="id" value="<?=htmlspecialchars($l["id"])?>"><button class="btn no" type="submit">Удалить</button></form>
                </div>
            <?php endforeach; ?>
        <?php else: ?><p>Сливов пока нет.</p><?php endif; ?>

    <?php elseif ($tab === "blog"): ?>
        <div class="card">
            <h3>Добавить пост</h3>
            <form method="POST"><input type="hidden" name="action" value="add_post"><input type="text" name="title" placeholder="Заголовок" required><textarea name="content" placeholder="Текст поста" required></textarea><button class="btn gray" type="submit">Сохранить</button></form>
        </div>
        <?php if ($blog): ?>
            <?php foreach (array_reverse($blog) as $p): ?>
                <div class="card">
                    <h3><?=htmlspecialchars($p["title"])?></h3>
                    <div class="meta">ID: <?=htmlspecialchars($p["id"])?> | <?=htmlspecialchars($p["date"] ?? "")?> | <?=!empty($p["hidden"]) ? "Скрыт" : "Показан"?></div>
                    <form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="edit_post"><input type="hidden" name="id" value="<?=htmlspecialchars($p["id"])?>"><input type="text" name="title" value="<?=htmlspecialchars($p["title"])?>"><textarea name="content"><?=htmlspecialchars($p["content"])?></textarea><button class="btn gray" type="submit">Сохранить изменения</button></form>
                    <form method="POST" style="margin-top:6px;display:inline-block;"><input type="hidden" name="action" value="toggle_post"><input type="hidden" name="id" value="<?=htmlspecialchars($p["id"])?>"><button class="btn ok" type="submit"><?=!empty($p["hidden"]) ? "Показать" : "Скрыть"?></button></form>
                    <form method="POST" style="margin-top:6px;display:inline-block;"><input type="hidden" name="action" value="del_post"><input type="hidden" name="id" value="<?=htmlspecialchars($p["id"])?>"><button class="btn no" type="submit">Удалить</button></form>
                </div>
            <?php endforeach; ?>
        <?php else: ?><p>Постов пока нет.</p><?php endif; ?>

    <?php elseif ($tab === "users"): ?>
        <div class="card">
            <h3>Добавить пользователя</h3>
            <form method="POST"><input type="hidden" name="action" value="add_user"><input type="text" name="login" placeholder="Логин" required><input type="password" name="password" placeholder="Пароль" required><select name="role"><option value="Пользователь">Пользователь</option><option value="Администратор">Администратор</option><option value="Главный разработчик">Главный разработчик</option></select><button class="btn gray" type="submit">Создать</button></form>
        </div>
        <?php if (!$users): ?><p>Пользователей пока нет.</p><?php else: ?>
            <?php foreach ($users as $login => $u): ?>
                <div class="card">
                    <h3><?=htmlspecialchars($login)?></h3>
                    <div class="meta">Роль: <?=htmlspecialchars($u["role"] ?? "Пользователь")?></div>
                    <?php if (!empty($u["ip"])): ?>
                        <div class="meta" style="color:#e67e22;">IP: <b><?=htmlspecialchars($u["ip"])?></b><?php if (!empty($u["last_seen"])): ?> · последний вход: <?=htmlspecialchars($u["last_seen"])?><?php endif; ?></div>
                        <a class="btn gray" style="margin-top:4px; font-size:11px; padding:4px 8px; display:inline-block; text-decoration:none; text-align:center;" href="?tab=bans&quickban_ip=<?=urlencode($u["ip"])?>&quickban_reason=<?=urlencode("Блокировка по IP пользователя " . $login)?>">🎯 Забанить IP этого пользователя</a>
                    <?php else: ?>
                        <div class="meta" style="color:#777;">IP: неизвестен</div>
                    <?php endif; ?>
                    <form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="set_role"><input type="hidden" name="login" value="<?=htmlspecialchars($login)?>"><select name="role"><option value="Пользователь" <?=($u["role"]??"")==="Пользователь"?"selected":""?>>Пользователь</option><option value="Администратор" <?=($u["role"]??"")==="Администратор"?"selected":""?>>Администратор</option><option value="Главный разработчик" <?=($u["role"]??"")==="Главный разработчик"?"selected":""?>>Главный разработчик</option></select><button class="btn gray" type="submit">Сохранить роль</button></form>
                    <form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="set_pass"><input type="hidden" name="login" value="<?=htmlspecialchars($login)?>"><input type="password" name="password" placeholder="Новый пароль"><button class="btn gray" type="submit">Сменить пароль</button></form>
                    <?php if ($login !== "Roma_07b" && $login !== "Petryha"): ?><form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="del_user"><input type="hidden" name="login" value="<?=htmlspecialchars($login)?>"><button class="btn no" type="submit">Удалить пользователя</button></form><?php endif; ?>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <?php elseif ($tab === "team"): ?>
        <div class="card">
            <h3>Добавить пользователя в команду</h3>
            <form method="POST">
                <input type="hidden" name="action" value="add_to_team">
                <select name="login" required><option value="">Выберите пользователя</option><?php foreach ($users as $login => $u): ?><?php if (($u["role"] ?? "Пользователь") === "Пользователь"): ?><option value="<?=$login?>"><?=$login?></option><?php endif; ?><?php endforeach; ?></select>
                <select name="role" required><option value="Администратор">Администратор</option><option value="Главный разработчик">Главный разработчик</option></select>
                <button class="btn gray" type="submit">Добавить в команду</button>
            </form>
        </div>
        <h3 style="margin-top:20px;">Состав команды</h3>
        <?php
        $team = []; foreach ($users as $login => $u) if (($u["role"] ?? "Пользователь") !== "Пользователь") $team[] = [$login, $u["role"]];
        if (!$team): ?><p>Команда пока пуста.</p><?php else: ?>
            <?php foreach ($team as $member): ?>
                <div class="card">
                    <h3><?=$member[0]?></h3>
                    <div class="meta">Роль: <?=$member[1]?></div>
                    <form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="change_team_role"><input type="hidden" name="login" value="<?=$member[0]?>"><select name="role"><option value="Администратор" <?=$member[1]==="Администратор"?"selected":""?>>Администратор</option><option value="Главный разработчик" <?=$member[1]==="Главный разработчик"?"selected":""?>>Главный разработчик</option></select><button class="btn gray" type="submit">Сохранить</button></form>
                    <?php if ($member[0] !== "Roma_07b" && $member[0] !== "Petryha"): ?><form method="POST" style="margin-top:6px;"><input type="hidden" name="action" value="remove_from_team"><input type="hidden" name="login" value="<?=$member[0]?>"><button class="btn no" type="submit">Удалить из команды</button></form><?php endif; ?>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

    <?php elseif ($tab === "gold"): ?>
        <div class="card gold-card">
            <h3>💳 Платные услуги для держателей золотого билета</h3>
            <p style="color:#aaa; font-size:13px;">Список услуг (можно добавить сколько угодно — хоть 1000 штук), которые видят у себя в профиле <b>все</b> обладатели золотого билета. Каждую можно отредактировать или удалить.</p>
            <form method="POST">
                <input type="hidden" name="action" value="add_gold_service">
                <label>Название услуги</label>
                <input type="text" name="service_name" placeholder="Например: Приоритетная поддержка RTeam" required>
                <label>Ссылка для получения</label>
                <input type="text" name="service_link" placeholder="https://...">
                <button class="btn gray" type="submit" style="margin-top:10px;">➕ Добавить услугу</button>
            </form>
        </div>

        <?php if (!$gold_services): ?>
            <p style="margin-top:14px;">Пока не добавлено ни одной платной услуги.</p>
        <?php else: ?>
            <h3 style="margin-top:24px;">Список услуг (<?=count($gold_services)?>)</h3>
            <?php foreach ($gold_services as $svc): ?>
                <div class="card gold-card">
                    <form method="POST" style="display:flex; flex-wrap:wrap; gap:8px; align-items:flex-end;">
                        <input type="hidden" name="action" value="edit_gold_service">
                        <input type="hidden" name="service_id" value="<?=htmlspecialchars($svc["id"])?>">
                        <div style="flex:1 1 220px;">
                            <label>Название</label>
                            <input type="text" name="service_name" value="<?=htmlspecialchars($svc["name"])?>" required>
                        </div>
                        <div style="flex:1 1 220px;">
                            <label>Ссылка</label>
                            <input type="text" name="service_link" value="<?=htmlspecialchars($svc["link"])?>" placeholder="https://...">
                        </div>
                        <button class="btn gray" type="submit">Сохранить</button>
                    </form>
                    <form method="POST" style="margin-top:6px;">
                        <input type="hidden" name="action" value="delete_gold_service">
                        <input type="hidden" name="service_id" value="<?=htmlspecialchars($svc["id"])?>">
                        <button class="btn no" type="submit" onclick="return confirm('Удалить услугу «<?=htmlspecialchars(addslashes($svc["name"]))?>»?')">🗑 Удалить</button>
                    </form>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

        <div class="card gold-card">
            <h3>🎫 Выдать / обновить Золотой билет RTeam</h3>
            <p style="color:#aaa; font-size:13px;">Билет дарит владельцу отдельную премиальную страницу профиля со своим названием, ссылкой и личным чатом с закреплённым сотрудником. Всю переписку по золотым билетам видит вся администрация.</p>
            <form method="POST">
                <input type="hidden" name="action" value="grant_golden">
                <label>Кому выдать</label>
                <select name="login" required>
                    <option value="">-- Выберите пользователя --</option>
                    <?php foreach ($users as $login => $u): ?>
                        <option value="<?=htmlspecialchars($login)?>"<?=$login===$user?' data-self="1"':''?>><?=htmlspecialchars($login)?> (<?=htmlspecialchars($u["role"] ?? "Пользователь")?>)<?=!empty($u["golden"])?" — уже есть билет":""?></option>
                    <?php endforeach; ?>
                </select>
                <button type="button" class="btn gray" style="padding:6px 10px; font-size:12px;" onclick="const s=this.previousElementSibling; for (const o of s.options) if (o.value === '<?=htmlspecialchars($user)?>') { s.value = o.value; break; }">Выдать себе</button>
                <label style="margin-top:10px;">Название билета (отображается в профиле)</label>
                <input type="text" name="golden_title" placeholder="Например: Золотой билет RTeam — Победитель" value="Золотой билет RTeam">
                <label>Ссылка в профиле</label>
                <input type="text" name="golden_link" placeholder="https://...">
                <label>Закреплённый сотрудник (кому владелец билета сможет писать)</label>
                <select name="golden_staff">
                    <option value="">-- Без закрепления --</option>
                    <?php foreach ($users as $login => $u): if (($u["role"] ?? "Пользователь") !== "Пользователь"): ?>
                        <option value="<?=htmlspecialchars($login)?>"><?=htmlspecialchars($login)?> (<?=htmlspecialchars($u["role"])?>)</option>
                    <?php endif; endforeach; ?>
                </select>
                <button class="btn gray" type="submit" style="margin-top:10px;">Сохранить билет</button>
            </form>
        </div>

        <h3 style="margin-top:24px;">Владельцы золотого билета</h3>
        <?php
        $golden_users = [];
        foreach ($users as $login => $u) if (!empty($u["golden"])) $golden_users[$login] = $u;
        ?>
        <?php if (!$golden_users): ?><p>Пока никто не получил золотой билет.</p><?php else: ?>
            <?php foreach ($golden_users as $login => $u): ?>
                <div class="card gold-card">
                    <h3><?=htmlspecialchars($login)?> <span class="badge badge-gold">🎫 <?=htmlspecialchars($u["golden_title"] ?? "Золотой билет RTeam")?></span></h3>
                    <div class="meta">Ссылка: <?php if (!empty($u["golden_link"])): ?><a href="<?=htmlspecialchars($u["golden_link"])?>" target="_blank" style="color:#ffd76a;"><?=htmlspecialchars($u["golden_link"])?></a><?php else: ?>—<?php endif; ?></div>
                    <div class="meta">Закреплённый сотрудник: <b><?=htmlspecialchars($u["golden_staff"] ?: "не назначен")?></b></div>
                    <div class="meta">Сообщений в чате: <?=count($gold_chats[$login]["messages"] ?? [])?></div>
                    <a href="?tab=gold&thread=<?=urlencode($login)?>" class="btn blue" style="text-decoration:none;">Открыть чат</a>
                    <form method="POST" style="margin-top:6px; display:inline-block;"><input type="hidden" name="action" value="revoke_golden"><input type="hidden" name="login" value="<?=htmlspecialchars($login)?>"><button class="btn no" type="submit" onclick="return confirm('Забрать золотой билет?')">Отозвать билет</button></form>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>

        <?php
        $thread = $_GET["thread"] ?? "";
        if ($thread !== "" && isset($users[$thread]) && !empty($users[$thread]["golden"])):
            $chat = $gold_chats[$thread] ?? ["staff" => "", "messages" => []];
        ?>
            <h3 style="margin-top:24px;">Чат с <?=htmlspecialchars($thread)?> <span class="badge badge-gold">🎫</span></h3>
            <div class="card gold-card">
                <div class="meta" style="margin-bottom:10px;">Закреплённый сотрудник: <b><?=htmlspecialchars($chat["staff"] ?: "не назначен")?></b> — но отвечать может любой сотрудник администрации.</div>
                <div style="max-height:360px; overflow-y:auto; display:flex; flex-direction:column; gap:8px; margin-bottom:12px;">
                    <?php if (!$chat["messages"]): ?><p style="color:#666;">Сообщений пока нет.</p><?php endif; ?>
                    <?php foreach ($chat["messages"] as $m): $isStaff = ($m["from"] === "staff"); ?>
                        <div style="align-self:<?=$isStaff?'flex-end':'flex-start'?>; max-width:75%; background:<?=$isStaff?'#3a2d00':'#101018'?>; border:1px solid <?=$isStaff?'#7a5c00':'#333'?>; border-radius:8px; padding:8px 10px;">
                            <div style="font-size:11px; color:#ffd76a; margin-bottom:4px;"><?=$isStaff?htmlspecialchars($m["author"])." (Rteam)":htmlspecialchars($thread)?> — <?=htmlspecialchars($m["time"])?></div>
                            <div><?=nl2br(htmlspecialchars($m["text"]))?></div>
                        </div>
                    <?php endforeach; ?>
                </div>
                <form method="POST">
                    <input type="hidden" name="action" value="gold_reply">
                    <input type="hidden" name="login" value="<?=htmlspecialchars($thread)?>">
                    <textarea name="reply_text" placeholder="Написать владельцу золотого билета..." required style="height:60px;"></textarea>
                    <button class="btn gray" type="submit" style="margin-top:8px;">Отправить</button>
                </form>
            </div>
        <?php endif; ?>

    <?php elseif ($tab === "recruit"): ?>
        <div class="card">
            <h3>Набор</h3>
            <form method="POST">
                <input type="hidden" name="action" value="save_recruit">
                <label><input type="checkbox" name="recruit_open" <?=!empty($settings["recruit_open"])?"checked":""?>> Набор открыт</label>
                <h4 style="margin-top:12px;">Вопросы для заявки «Команда» (по одному на строку)</h4><textarea name="team_questions"><?=htmlspecialchars(implode("\n", $questions["team"] ?? []))?></textarea>
                <h4 style="margin-top:12px;">Вопросы для заявки «Администратор» (по одному на строку)</h4><textarea name="admin_questions"><?=htmlspecialchars(implode("\n", $questions["admin"] ?? []))?></textarea>
                <button class="btn gray" type="submit" style="margin-top:10px;">Сохранить</button>
            </form>
        </div>

    <?php elseif ($tab === "themes"): ?>
        <div class="card">
            <h3>🎭 Темы сайта</h3>
            <p style="color:#999; font-size:13px; margin-top:-6px;">Выберите тематику — на сайте появится баннер и плавающие иконки по выбранной теме (турнир, праздник, событие RTeam). Активна одновременно только одна тема.</p>
            <form method="POST">
                <input type="hidden" name="action" value="save_theme">
                <label><input type="checkbox" name="theme_enabled" <?=!empty($theme_settings["enabled"])?"checked":""?>> Тема включена на сайте</label>

                <h4 style="margin-top:14px;">Тематика</h4>
                <select name="theme_active" id="themeSelect" onchange="rteamUpdateThemeField()">
                    <?php
                    $themeGroups = [];
                    foreach ($THEME_CATALOG as $tkey => $tinfo) { $themeGroups[$tinfo["group"]][$tkey] = $tinfo; }
                    foreach ($themeGroups as $groupName => $items):
                    ?>
                        <optgroup label="<?=htmlspecialchars($groupName)?>">
                        <?php foreach ($items as $tkey => $tinfo): ?>
                            <option value="<?=htmlspecialchars($tkey)?>" <?=($theme_settings["active"]===$tkey)?"selected":""?>><?=$tinfo["icon"]?> <?=htmlspecialchars($tinfo["name"])?></option>
                        <?php endforeach; ?>
                        </optgroup>
                    <?php endforeach; ?>
                </select>

                <h4 style="margin-top:14px;" id="themeFieldLabel">Текст для баннера</h4>
                <input type="text" name="theme_text" id="themeTextInput" value="<?=htmlspecialchars($theme_settings["text"] ?? "")?>" placeholder="">

                <button class="btn gray" type="submit" style="margin-top:14px;">Сохранить</button>
            </form>
        </div>

        <?php if (!empty($theme_settings["enabled"])): $curTheme = $THEME_CATALOG[$theme_settings["active"]]; ?>
        <div class="card">
            <h3>Предпросмотр баннера</h3>
            <div style="background:#101018; border:1px solid #333; border-radius:8px; padding:14px; text-align:center; font-size:15px;">
                <?=$curTheme["icon"]?> <b><?=htmlspecialchars($curTheme["name"])?></b><?php if (trim($theme_settings["text"] ?? "") !== ""): ?> — <?=htmlspecialchars($theme_settings["text"])?><?php endif; ?>
            </div>
        </div>
        <?php endif; ?>

        <div class="card">
            <h3>🦑 Игра в кальмара — управление</h3>
            <p style="color:#999; font-size:13px; margin-top:-6px;">На сайте показываются 3 последовательных сезона (Красный свет/зелёный свет → Дальгона → Стеклянный мост). Прошедшие все три сезона попадают в список претендентов на «Золотой билет RTeam» ниже.</p>

            <form method="POST">
                <input type="hidden" name="action" value="squid_set_paused">
                <label><input type="checkbox" name="squid_paused" <?=!empty($squid_game["paused"])?"checked":""?>> Остановить игру (игроки увидят «Игры приостановлены»)</label>
                <button class="btn gray" type="submit" style="margin-top:10px;">Сохранить</button>
            </form>

            <h4 style="margin-top:18px;">Прогресс игроков</h4>
            <?php if (empty($squid_game["progress"])): ?>
                <p style="color:#888; font-size:13px;">Пока никто не начинал игру.</p>
            <?php else: ?>
                <table style="width:100%; border-collapse:collapse; font-size:13px; margin-top:8px;">
                    <tr style="text-align:left; color:#999; border-bottom:1px solid #333;">
                        <th style="padding:6px 4px;">Игрок</th>
                        <th style="padding:6px 4px;">Сезон</th>
                        <th style="padding:6px 4px;">Статус</th>
                        <th style="padding:6px 4px;">Завершил</th>
                        <th style="padding:6px 4px;"></th>
                    </tr>
                    <?php foreach ($squid_game["progress"] as $sq_login => $sq_p): ?>
                    <tr style="border-bottom:1px solid #222;">
                        <td style="padding:6px 4px;"><b><?=htmlspecialchars($sq_login)?></b></td>
                        <td style="padding:6px 4px;"><?=(int)($sq_p["season"] ?? 0)?> / 3</td>
                        <td style="padding:6px 4px;">
                            <?php if (!empty($sq_p["completed"])): ?>
                                <span style="color:#39ff6a;">✅ прошёл всё</span>
                            <?php else: ?>
                                <span style="color:#ffb84d;">в процессе</span>
                            <?php endif; ?>
                        </td>
                        <td style="padding:6px 4px; color:#999;"><?=htmlspecialchars($sq_p["completed_at"] ?? "—")?></td>
                        <td style="padding:6px 4px;">
                            <form method="POST" style="display:inline;" onsubmit="return confirm('Сбросить прогресс игрока?');">
                                <input type="hidden" name="action" value="squid_reset_user">
                                <input type="hidden" name="login" value="<?=htmlspecialchars($sq_login)?>">
                                <button class="btn no" type="submit" style="padding:4px 10px; font-size:12px;">Сбросить</button>
                            </form>
                            <?php if (!empty($sq_p["completed"]) && empty($users[$sq_login]["golden"])): ?>
                            <form method="POST" style="display:inline;" onsubmit="return confirm('Выдать «Золотой билет RTeam» этому игроку?');">
                                <input type="hidden" name="action" value="grant_golden">
                                <input type="hidden" name="login" value="<?=htmlspecialchars($sq_login)?>">
                                <input type="hidden" name="golden_title" value="Золотой билет RTeam — Игра в кальмара">
                                <input type="hidden" name="golden_link" value="">
                                <input type="hidden" name="golden_staff" value="<?=htmlspecialchars($user)?>">
                                <button class="btn" type="submit" style="padding:4px 10px; font-size:12px; background:linear-gradient(135deg,#ffe066,#d4a017); color:#3a2a00;">🎫 Выдать билет</button>
                            </form>
                            <?php elseif (!empty($users[$sq_login]["golden"])): ?>
                                <span class="badge badge-gold" style="font-size:10px;">🎫 уже есть билет</span>
                            <?php endif; ?>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                </table>
            <?php endif; ?>
        </div>

        <script>
        const RTEAM_THEME_META = <?=json_encode($THEME_CATALOG, JSON_UNESCAPED_UNICODE)?>;
        function rteamUpdateThemeField() {
            const sel = document.getElementById('themeSelect');
            const meta = RTEAM_THEME_META[sel.value];
            if (meta) {
                document.getElementById('themeFieldLabel').textContent = meta.field;
                document.getElementById('themeTextInput').placeholder = meta.placeholder || '';
            }
        }
        rteamUpdateThemeField();
        </script>

    <?php elseif ($tab === "settings"): ?>
        <div class="card">
            <h3>Настройки сайта</h3>
            <form method="POST">
                <input type="hidden" name="action" value="save_settings">
                <label>Название сайта</label><input type="text" name="site_name" value="<?=htmlspecialchars($settings["site_name"])?>">
                <label>Цвет акцента (hex)</label><input type="text" name="accent" value="<?=htmlspecialchars($settings["accent"])?>">
                <label><input type="checkbox" name="neon" <?=!empty($settings["neon"])?"checked":""?>> Неон‑эффекты</label>
                <label><input type="checkbox" name="animations" <?=!empty($settings["animations"])?"checked":""?>> Анимации</label>
                <button class="btn gray" type="submit">Сохранить</button>
            </form>
        </div>

    <?php elseif ($tab === "logs"): ?>
        <?php if (!$logs): ?><p>Логов пока нет.</p><?php else: ?>
            <?php foreach (array_reverse($logs) as $log): ?><div class="card"><div class="meta"><?=htmlspecialchars($log["time"] ?? "")?> — <?=htmlspecialchars($log["type"] ?? "")?></div><div><?=nl2br(htmlspecialchars($log["msg"] ?? ""))?></div></div><?php endforeach; ?>
        <?php endif; ?>
    <?php endif; ?>
</div>

<script>
    // --- ГЛОБАЛЬНЫЕ УВЕДОМЛЕНИЯ ---
    let lastCheckTime = <?=time()?>;
    function showToast(text, type='info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div'); toast.className = 'toast ' + type; toast.innerText = text;
        container.appendChild(toast); setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 500); }, 5000);
    }
    setInterval(() => {
        fetch('?ajax_check=1&last_time=' + lastCheckTime).then(r => r.json()).then(data => {
            if (data.status === 'ok') {
                data.msgs.forEach(msg => { showToast(msg, 'info'); });
                data.fines.forEach(fine => { showToast(fine, 'error'); });
                lastCheckTime = data.time;
            }
        });
    }, 5000);

    // --- ПРЯМАЯ ИЗОЛИРОВАННАЯ ФУНКЦИЯ ДЛЯ КНОПОК БОТА (БЕЗ ПЕРЕЗАГРУЗКИ) ---
    function sendBotAction(action, userId, ticketId, text = '') {
        const fd = new FormData();
        fd.append('action', action);
        if (userId) fd.append('user_id', userId);
        if (ticketId) fd.append('ticket_id', ticketId);
        fd.append('is_ajax', '1');
        if (text) fd.append('reply_text', text);

        fetch('admin.php?tab=bot', { method: 'POST', body: fd })
        .then(r => r.text())
        .then(res => {
            if(res.trim() === 'error') showToast('Ошибка! Проверьте токен бота в настройках.', 'error');
            else { showToast('Действие выполнено!', 'info'); if (typeof loadBotData === 'function') loadBotData(); }
        }).catch(() => showToast('Ошибка сети', 'error'));
    }

    // --- ОБНОВЛЕНИЕ БЛОКА ТИКЕТОВ И РОЗЫГРЫШЕЙ (AJAX + JSON) ---
    function loadBotData() {
        fetch('admin.php?ajax_bot_data=1')
        .then(r => r.json())
        .then(data => {
            // Обновляем Заявки
            const tickContainer = document.getElementById('botTicketsFeed');
            if (tickContainer) {
                const activeEl = document.activeElement;
                let activeId = null, activeVal = '', cursorStart = 0;
                
                // Сохраняем фокус, если ты пишешь ответ во время авто-обновления
                if (activeEl && activeEl.tagName === 'TEXTAREA' && tickContainer.contains(activeEl)) {
                    activeId = activeEl.id; activeVal = activeEl.value; cursorStart = activeEl.selectionStart;
                }
                
                if (tickContainer.dataset.lasthtml !== data.tickets) {
                    tickContainer.innerHTML = data.tickets;
                    tickContainer.dataset.lasthtml = data.tickets;
                    if (activeId) {
                        const newEl = document.getElementById(activeId);
                        if (newEl) { newEl.focus(); newEl.value = activeVal; newEl.setSelectionRange(cursorStart, cursorStart); }
                    }
                }
            }
            
            // Обновляем Розыгрыши (Live счетчик)
            const gwContainer = document.getElementById('botGiveawaysFeed');
            if (gwContainer && gwContainer.dataset.lasthtml !== data.giveaways) {
                gwContainer.innerHTML = data.giveaways;
                gwContainer.dataset.lasthtml = data.giveaways;
            }
        }).catch(err => console.log('AJAX Sync Error', err));
    }

    // Запускаем синхронизацию
    if (window.location.search.includes('tab=bot')) {
        setInterval(loadBotData, 3000);
    }
</script>

</body>
</html>