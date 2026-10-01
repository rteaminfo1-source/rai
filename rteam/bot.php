<?php
require_once __DIR__ . '/_roles.php'; // роли и права (общий файл с admin.php)

// Читаем токен из настроек сайта
$settings = file_exists('settings.json') ? json_decode(file_get_contents('settings.json'), true) : [];
$token = $settings['bot_token'] ?? "";

if (empty($token)) {
    die("Бот не настроен. Укажите токен во вкладке 'Бот' в админ-панели.");
}

$update = json_decode(file_get_contents('php://input'), TRUE);

// Функция для сохранения ID пользователей бота (для рассылки)
function saveUser($user_id) {
    $file = 'bot_users.json';
    $users = file_exists($file) ? json_decode(file_get_contents($file), true) : [];
    if (!in_array($user_id, $users)) {
        $users[] = $user_id;
        file_put_contents($file, json_encode($users, JSON_PRETTY_PRINT));
    }
}

// Загружаем списки (Муты, Заметки, Настройки уведомлений и База юзеров)
$banned_file = 'bot_banned.json';
$banned_users = file_exists($banned_file) ? json_decode(file_get_contents($banned_file), true) : [];
if (!is_array($banned_users)) $banned_users = [];

$users_file = 'users.json';
$all_users = file_exists($users_file) ? json_decode(file_get_contents($users_file), true) : [];

$notes_file = 'bot_notes.json';
$all_notes = file_exists($notes_file) ? json_decode(file_get_contents($notes_file), true) : [];

$notifs_file = 'bot_notifs.json';
$notif_settings = file_exists($notifs_file) ? json_decode(file_get_contents($notifs_file), true) : [];

// Аккаунт сайта, к которому привязан этот Telegram: [логин, данные] или [null, null]
function botAccount($all_users, $tg_id) {
    foreach ($all_users as $l => $u) {
        if (is_array($u) && isset($u['tg_id']) && (string)$u['tg_id'] === (string)$tg_id) return [(string)$l, $u];
    }
    return [null, null];
}

// Привязывает Telegram к аккаунту (и отвязывает его от других аккаунтов, если был)
function botLinkAccount(&$all_users, $users_file, $login, $tg_id, $tg_username) {
    foreach ($all_users as $l => &$u) {
        if (is_array($u) && isset($u['tg_id']) && (string)$u['tg_id'] === (string)$tg_id && (string)$l !== (string)$login) unset($u['tg_id'], $u['tg_username']);
    }
    unset($u);
    $all_users[$login]['tg_id'] = $tg_id;
    $all_users[$login]['tg_username'] = $tg_username;
    file_put_contents($users_file, json_encode($all_users, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

// Какое право нужно для кнопок админ-панели бота (как на сайте)
function botActionPerm($data) {
    if ($data === "adm_tickets" || strpos($data, "adm_reply_") === 0 || strpos($data, "adm_close_") === 0) return "bot.tickets";
    if (strpos($data, "adm_ban_") === 0) return "bans.manage";
    return "bot.manage"; // розыгрыши и рассылка
}

// Вспомогательная функция транслитерации
function transliterate($text) {
    $cyr = ['а','б','в','г','д','е','ё','ж','з','и','й','к','л','м','н','о','п','р','с','т','у','ф','х','ц','ч','ш','щ','ъ','ы','ь','э','ю','я','А','Б','В','Г','Д','Е','Ё','Ж','З','И','Й','К','Л','М','Н','О','П','Р','С','Т','У','Ф','Х','Ц','Ч','Ш','Щ','Ъ','Ы','Ь','Э','Ю','Я'];
    $lat = ['a','b','v','g','d','e','io','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','shch','','y','','e','yu','ya','A','B','V','G','D','E','Io','Zh','Z','I','Y','K','L','M','N','O','P','R','S','T','U','F','H','Ts','Ch','Sh','Shch','','Y','','E','Yu','Ya'];
    return str_replace($cyr, $lat, $text);
}

// 1. ОБРАБОТКА ИНЛАЙН-КНОПОК (НАЖАТИЯ)
if (isset($update['callback_query'])) {
    $cq = $update['callback_query'];
    $chat_id = $cq['message']['chat']['id'];
    $user_id = $cq['from']['id'];
    $data = $cq['data'];

    saveUser($user_id);

    // --- КТО НАЖАЛ: привязанный аккаунт сайта и его роль ---
    [$cb_login, $cb_user] = botAccount($all_users, $user_id);
    $cb_role = $cb_user['role'] ?? "Пользователь";

    // --- ЛОГИКА АДМИН-ПАНЕЛИ БОТА ---
    if (mb_strpos($data, "adm_") === 0) {
        if (!$cb_login || !rt_is_staff($cb_role, $cb_login)) {
            file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id'] . "&text=" . urlencode("❌ У вас нет прав администратора!") . "&show_alert=true");
            exit;
        }
        if (!rt_can($cb_login, $cb_role, botActionPerm($data))) {
            file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id'] . "&text=" . urlencode("❌ Для этого действия у роли «" . rt_role_label($cb_role, $cb_user['direction'] ?? "") . "» нет прав.") . "&show_alert=true");
            exit;
        }

        if ($data == "adm_tickets") {
            $tickets = file_exists('bot_tickets.json') ? json_decode(file_get_contents('bot_tickets.json'), true) : [];
            $new_tickets = array_filter($tickets, function($t) { return $t['status'] == 'new'; });
            
            if (empty($new_tickets)) {
                sendMessage($chat_id, "✅ Неотвеченных заявок сейчас нет.", $token);
            } else {
                foreach (array_slice($new_tickets, 0, 5) as $t) {
                    $msg = "🎟 <b>Заявка от " . htmlspecialchars($t['username']) . "</b> (ID: " . $t['user_id'] . ")\n\n" . htmlspecialchars($t['text']);
                    $ik = [
                        "inline_keyboard" => [
                            [
                                ["text" => "✍️ Ответить", "callback_data" => "adm_reply_" . $t['id']],
                                ["text" => "❌ Закрыть", "callback_data" => "adm_close_" . $t['id']]
                            ]
                        ]
                    ];
                    // мут — это бан, кнопку видят только те, кто может банить
                    if (rt_can($cb_login, $cb_role, "bans.manage")) $ik["inline_keyboard"][] = [["text" => "🔇 Выдать Мут", "callback_data" => "adm_ban_" . $t['user_id']]];
                    sendMessage($chat_id, $msg, $token, null, $ik);
                }
            }
        } 
        elseif (mb_strpos($data, "adm_reply_") === 0) {
            $t_id = str_replace("adm_reply_", "", $data);
            $msg = "✍️ <b>Чтобы ответить на заявку, отправьте команду:</b>\n\n`/reply $t_id Ваш текст ответа`";
            sendMessage($chat_id, $msg, $token);
        }
        elseif (mb_strpos($data, "adm_close_") === 0) {
            $t_id = str_replace("adm_close_", "", $data);
            $tickets = file_exists('bot_tickets.json') ? json_decode(file_get_contents('bot_tickets.json'), true) : [];
            foreach ($tickets as &$t) { if ($t['id'] == $t_id) { $t['status'] = 'closed'; break; } }
            file_put_contents('bot_tickets.json', json_encode($tickets, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
            sendMessage($chat_id, "✅ Заявка $t_id закрыта.", $token);
        }
        elseif (mb_strpos($data, "adm_ban_") === 0) {
            $u_id = str_replace("adm_ban_", "", $data);
            if (!in_array($u_id, $banned_users)) {
                $banned_users[] = $u_id;
                file_put_contents($banned_file, json_encode($banned_users, JSON_PRETTY_PRINT));
            }
            sendMessage($chat_id, "🔇 Пользователь $u_id больше не сможет отправлять заявки.", $token);
        }
        elseif ($data == "adm_gws") {
            $gws = file_exists('bot_giveaways.json') ? json_decode(file_get_contents('bot_giveaways.json'), true) : [];
            $active_gws = array_filter($gws, function($g) { return $g['status'] == 'active'; });
            if (empty($active_gws)) {
                sendMessage($chat_id, "🎁 Активных розыгрышей нет. Создайте их в Админ-панели на сайте.", $token);
            } else {
                foreach ($active_gws as $gw) {
                    $msg = "🎁 <b>" . htmlspecialchars($gw['title']) . "</b>\nУчастников: " . count($gw['participants']) . "\nКоличество победителей: " . $gw['winners_count'];
                    $ik = [ "inline_keyboard" => [ [["text" => "🎲 Завершить и выбрать победителей", "callback_data" => "adm_roll_" . $gw['id']]] ] ];
                    sendMessage($chat_id, $msg, $token, null, $ik);
                }
            }
        }
        elseif (mb_strpos($data, "adm_roll_") === 0) {
            $gw_id = str_replace("adm_roll_", "", $data);
            $bot_gws = file_exists('bot_giveaways.json') ? json_decode(file_get_contents('bot_giveaways.json'), true) : [];
            
            foreach ($bot_gws as &$gw) {
                if ($gw['id'] === $gw_id && $gw['status'] === 'active') {
                    $gw['status'] = 'closed';
                    $participants = $gw['participants'];
                    $count = (int)$gw['winners_count'];
                    if ($count < 1) $count = 1;
                    
                    $winners = [];
                    if (!empty($participants)) {
                        shuffle($participants);
                        $winners = array_slice($participants, 0, $count);
                    }
                    $gw['winners'] = $winners;
                    
                    $win_text = empty($winners) ? "Участников не было 😔" : "🏆 <b>Победители:</b>\n" . implode("\n", array_map(function($w) { return "👤 <a href='tg://user?id={$w}'>Пользователь $w</a>"; }, $winners));
                    $msg = "🎉 <b>РОЗЫГРЫШ ЗАВЕРШЁН!</b> 🎉\n\n<b>" . htmlspecialchars($gw['title']) . "</b>\n\n" . $win_text . "\n\nПоздравляем победителей! Спасибо всем за участие!";
                    
                    $bot_users = file_exists('bot_users.json') ? json_decode(file_get_contents('bot_users.json'), true) : [];
                    foreach ($bot_users as $uid) { sendMessage($uid, $msg, $token); }
                    sendMessage($chat_id, "✅ Розыгрыш завершен! Результаты автоматически отправлены всем пользователям бота.", $token);
                    break;
                }
            }
            file_put_contents('bot_giveaways.json', json_encode($bot_gws, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        }
        elseif ($data == "adm_broadcast") {
            sendMessage($chat_id, "📢 <b>Сделать рассылку:</b>\n\nОтправьте команду:\n`/bc Ваш текст для рассылки всем пользователям бота`", $token);
        }

        file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id']);
        exit;
    }

    // --- ОБЫЧНЫЕ КНОПКИ (Пользовательские) ---
    if (mb_strpos($data, "gw_part_") === 0) {
        $gw_id = str_replace("gw_part_", "", $data);
        $gws_file = 'bot_giveaways.json';
        $gws = file_exists($gws_file) ? json_decode(file_get_contents($gws_file), true) : [];
        $found = false;

        foreach ($gws as &$gw) {
            if ($gw['id'] == $gw_id && $gw['status'] == 'active') {
                $found = true;
                if (!in_array($user_id, $gw['participants'])) {
                    $gw['participants'][] = $user_id;
                    file_put_contents($gws_file, json_encode($gws, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
                    file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id'] . "&text=" . urlencode("🎉 Вы успешно зарегистрированы как участник розыгрыша!") . "&show_alert=true");
                } else {
                    file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id'] . "&text=" . urlencode("⚠️ Вы уже участвуете в этом розыгрыше!") . "&show_alert=true");
                }
                break;
            }
        }
        if (!$found) file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id'] . "&text=" . urlencode("❌ Розыгрыш не найден или уже завершен.") . "&show_alert=true");
        exit;
    }

    file_get_contents("https://api.telegram.org/bot" . $token . "/answerCallbackQuery?callback_query_id=" . $cq['id']);
    exit;
}

// 2. ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ
if (isset($update['message'])) {
    $chat_id = $update['message']['chat']['id'];
    $user_id = $update['message']['from']['id'];
    $text = trim($update['message']['text'] ?? '');

    saveUser($user_id);

    // --- 1. ПРИВЯЗКА АККАУНТА (ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ) ---
    // /link КОД            — код из личного кабинета на сайте (рекомендуется)
    // /link Логин Пароль   — старый способ, по паролю
    if (mb_strpos($text, '/link ') === 0) {
        $parts = preg_split('/\s+/', trim($text));
        $tg_username = $update['message']['from']['username'] ?? '';
        $linked_login = null;

        if (count($parts) == 2) {
            $code = strtoupper($parts[1]);
            $tg_codes = file_exists('tg_link_codes.json') ? json_decode(file_get_contents('tg_link_codes.json'), true) : [];
            if (!is_array($tg_codes)) $tg_codes = [];
            if (isset($tg_codes[$code]) && ($tg_codes[$code]['expires'] ?? 0) >= time() && isset($all_users[$tg_codes[$code]['login'] ?? ''])) {
                $linked_login = $tg_codes[$code]['login'];
                unset($tg_codes[$code]);
                file_put_contents('tg_link_codes.json', json_encode($tg_codes, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
            } else {
                sendMessage($chat_id, "❌ Код не найден или устарел (код действует 15 минут).\n\nПолучите новый в личном кабинете на сайте: rteam.info/cabinet.php → «Telegram-бот».", $token);
                exit;
            }
        } elseif (count($parts) >= 3) {
            $l = $parts[1];
            $p = $parts[2];
            if (isset($all_users[$l]) && isset($all_users[$l]['password']) && $all_users[$l]['password'] === $p) {
                $linked_login = $l;
            } else {
                sendMessage($chat_id, "❌ Неверный логин или пароль от сайта.", $token);
                exit;
            }
        } else {
            sendMessage($chat_id, "⚠️ Использование: <code>/link КОД</code> — код возьмите в личном кабинете на сайте (rteam.info/cabinet.php).", $token);
            exit;
        }

        botLinkAccount($all_users, $users_file, $linked_login, $user_id, $tg_username);
        $l_role = $all_users[$linked_login]['role'] ?? "Пользователь";
        if (rt_is_staff($l_role, $linked_login)) {
            sendMessage($chat_id, "✅ Аккаунт <b>" . htmlspecialchars($linked_login) . "</b> успешно привязан!\n\nРоль: <b>" . htmlspecialchars(rt_role_label($l_role, $all_users[$linked_login]['direction'] ?? "")) . "</b>. Теперь при входе в админ-панель на сайте бот будет присылать код подтверждения (2FA), а здесь доступна админ-панель бота.\n\n👉 Нажмите /start для обновления меню.", $token);
        } else {
            sendMessage($chat_id, "✅ Аккаунт <b>" . htmlspecialchars($linked_login) . "</b> успешно привязан!\n\nТеперь ваш Telegram профиль синхронизирован с сайтом rteam.info.", $token);
        }
        exit;
    }

    // --- 2. ОПРЕДЕЛЯЕМ, СОТРУДНИК ЛИ ЭТОТ ПОЛЬЗОВАТЕЛЬ (роли — из _roles.php) ---
    $admin_login = null;
    $admin_role = null;
    [$acc_login, $acc_user] = botAccount($all_users, $user_id);
    if ($acc_login && rt_is_staff($acc_user['role'] ?? "Пользователь", $acc_login)) {
        $admin_login = $acc_login;
        $admin_role = $acc_user['role'] ?? "Пользователь";
    }

    // --- 3. АДМИНСКИЕ ТЕКСТОВЫЕ КОМАНДЫ ---
    if ($admin_login) {
        
        // Получение 2FA Кода
        if ($text == '/code' || $text == '🔑 Получить код 2FA') {
            $codes = file_exists('2fa_codes.json') ? json_decode(file_get_contents('2fa_codes.json'), true) : [];
            if (isset($codes[$admin_login])) {
                sendMessage($chat_id, "🔐 Ваш защитный код для входа на сайт:\n\n👉 <b>" . $codes[$admin_login] . "</b> 👈", $token);
            } else {
                sendMessage($chat_id, "ℹ️ Система входа не запрашивала код для вашего аккаунта.\nСначала введите логин и пароль на сайте rteam.info", $token);
            }
            exit;
        }

        // Открытие админ панели внутри бота: кнопки — по правам роли
        if ($text == '⚙️ Админ-панель' || $text == '/admin') {
            $role_text = rt_role_label($admin_role, $acc_user['direction'] ?? "");
            $rows = [];
            $row1 = [];
            if (rt_can($admin_login, $admin_role, "bot.tickets")) $row1[] = ["text" => "🎟 Новые заявки", "callback_data" => "adm_tickets"];
            if (rt_can($admin_login, $admin_role, "bot.manage"))  $row1[] = ["text" => "🎁 Розыгрыши", "callback_data" => "adm_gws"];
            if ($row1) $rows[] = $row1;
            if (rt_can($admin_login, $admin_role, "bot.manage"))  $rows[] = [["text" => "📢 Сделать рассылку", "callback_data" => "adm_broadcast"]];
            if (!$rows) {
                sendMessage($chat_id, "👨‍💻 Привет, <b>" . htmlspecialchars($admin_login) . "</b>!\nВаша роль: <b>" . htmlspecialchars($role_text) . "</b>.\n\nУправление ботом для вашей роли пока недоступно. Здесь вы можете получать код входа: /code", $token);
                exit;
            }
            $reply = "👨‍💻 <b>Секретная Панель Rteam</b>\n\nПриветствую, <b>" . htmlspecialchars($admin_login) . "</b> (" . htmlspecialchars($role_text) . ")!\nОтсюда ты можешь управлять ботом.";
            sendMessage($chat_id, $reply, $token, null, ["inline_keyboard" => $rows]);
            exit;
        }

        // Ответ на заявку (/reply ID текст)
        if (mb_strpos($text, '/reply ') === 0) {
            if (!rt_can($admin_login, $admin_role, "bot.tickets")) { sendMessage($chat_id, "❌ Отвечать на заявки вашей роли нельзя.", $token); exit; }
            $parts = explode(' ', $text, 3);
            if (count($parts) == 3) {
                $t_id = $parts[1];
                $reply_text = $parts[2];
                $tickets = file_exists('bot_tickets.json') ? json_decode(file_get_contents('bot_tickets.json'), true) : [];
                $found = false;
                foreach ($tickets as &$t) {
                    if ($t['id'] == $t_id) {
                        $t['status'] = 'answered';
                        sendMessage($t['user_id'], "👨‍💻 <b>Ответ от поддержки RTeam:</b>\n\n" . htmlspecialchars($reply_text), $token);
                        sendMessage($chat_id, "✅ Ответ успешно отправлен пользователю!", $token);
                        $found = true;
                        break;
                    }
                }
                if ($found) file_put_contents('bot_tickets.json', json_encode($tickets, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
                else sendMessage($chat_id, "❌ Заявка с ID $t_id не найдена.", $token);
            }
            exit;
        }

        // Массовая рассылка (/bc текст)
        if (mb_strpos($text, '/bc ') === 0) {
            if (!rt_can($admin_login, $admin_role, "bot.manage")) { sendMessage($chat_id, "❌ Делать рассылку вашей роли нельзя.", $token); exit; }
            $bc_text = mb_substr($text, 4);
            $bot_users = file_exists('bot_users.json') ? json_decode(file_get_contents('bot_users.json'), true) : [];
            $count = 0;
            foreach ($bot_users as $uid) {
                // Проверяем, не отключил ли юзер уведомления
                if (!isset($notif_settings[$uid]) || $notif_settings[$uid] === true) {
                    sendMessage($uid, "📢 <b>Уведомление от RTeam:</b>\n\n" . htmlspecialchars($bc_text), $token);
                    $count++;
                }
            }
            sendMessage($chat_id, "✅ Рассылка завершена. Сообщение получили $count человек.", $token);
            exit;
        }
    }

    if (!$admin_login && in_array($text, ['/admin', '/code'], true)) {
        sendMessage($chat_id, "Это доступно только сотрудникам команды с привязанным аккаунтом.\n\nЧтобы привязать аккаунт, откройте личный кабинет на сайте (rteam.info/cabinet.php), нажмите «Привязать Telegram» и отправьте сюда команду <code>/link КОД</code>.", $token);
        exit;
    }


    // --- 4. НОВЫЕ И ПОЛЬЗОВАТЕЛЬСКИЕ ФУНКЦИИ ---

    // Профиль пользователя
    if ($text == "👤 Профиль" || $text == "/profile") {
        $linked_acc = "Не привязан";
        $user_role = "Пользователь";
        if ($acc_login) {
            $linked_acc = htmlspecialchars($acc_login);
            $user_role = htmlspecialchars(rt_role_label($acc_user['role'] ?? "Пользователь", $acc_user['direction'] ?? ""));
        }
        $notif_status = (!isset($notif_settings[$user_id]) || $notif_settings[$user_id] === true) ? "🔔 Включены" : "🔕 Выключены";
        $reply = "👤 <b>Ваш Профиль:</b>\n\n";
        $reply .= "🆔 <b>TG ID:</b> <code>$user_id</code>\n";
        $reply .= "🔗 <b>Аккаунт на сайте:</b> <b>$linked_acc</b>\n";
        $reply .= "🎭 <b>Ваша роль:</b> $user_role\n";
        $reply .= "📩 <b>Уведомления:</b> $notif_status\n\n";
        $reply .= $acc_login ? "<i>Отвязать аккаунт можно в личном кабинете на сайте.</i>" : "<i>Для привязки аккаунта возьмите код в личном кабинете на сайте и отправьте /link КОД</i>";
        sendMessage($chat_id, $reply, $token);
        exit;
    }

    // Быстрый просмотр ID
    elseif ($text == "/id") {
        sendMessage($chat_id, "🆔 Ваш Telegram ID: <code>$user_id</code>\n💬 Chat ID: <code>$chat_id</code>", $token);
        exit;
    }

    // Генератор паролей
    elseif (mb_strpos($text, '/genpass') === 0) {
        $parts = explode(' ', $text);
        $len = isset($parts[1]) ? (int)$parts[1] : 12;
        if ($len < 6) $len = 6;
        if ($len > 32) $len = 32;
        
        $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()';
        $pass = '';
        for ($i = 0; $i < $len; $i++) {
            $pass .= $chars[rand(0, strlen($chars) - 1)];
        }
        sendMessage($chat_id, "🔑 <b>Сгенерированный пароль:</b>\n\n<code>" . htmlspecialchars($pass) . "</code>", $token);
        exit;
    }

    // Генератор случайных чисел
    elseif (mb_strpos($text, '/rand') === 0) {
        $parts = explode(' ', $text);
        $min = isset($parts[1]) ? (int)$parts[1] : 1;
        $max = isset($parts[2]) ? (int)$parts[2] : 100;
        if ($min >= $max) { $min = 1; $max = 100; }
        $rand_val = rand($min, $max);
        sendMessage($chat_id, "🎲 Случайное число от $min до $max: <b>$rand_val</b>", $token);
        exit;
    }

    // Орел и решка
    elseif ($text == "/coin" || $text == "🪙 Орел и решка") {
        $res = rand(0, 1) == 1 ? "🪙 Выпал: <b>Орел</b>!" : "🪙 Выпала: <b>Решка</b>!";
        sendMessage($chat_id, $res, $token);
        exit;
    }

    // Случайная айтишная цитата
    elseif ($text == "/quote") {
        $quotes = [
            "«Работает? Не трогай!» — Главная заповедь программиста.",
            "«Код — как юмор. Если его нужно объяснять, значит он плохой.» — Cory House",
            "«Существует 10 типов людей: те, кто понимают двоичную систему, и те, кто нет.»",
            "«Перед тем как писать код, подумай. Перед тем как подумать, прочитай ТЗ.»",
            "«Ошибки в коде — это просто незапланированные фичи.»"
        ];
        $q = $quotes[array_rand($quotes)];
        sendMessage($chat_id, "💡 <b>Цитата дня:</b>\n\n<i>$q</i>", $token);
        exit;
    }

    // Простой калькулятор
    elseif (mb_strpos($text, '/calc ') === 0) {
        $expr = trim(mb_substr($text, 6));
        if (preg_match('/^[0-9\+\-\*\/\(\)\.\s]+$/', $expr)) {
            try {
                @eval("\$res = $expr;");
                if (isset($res)) {
                    sendMessage($chat_id, "🧮 Результат: <b>$expr = $res</b>", $token);
                } else {
                    sendMessage($chat_id, "❌ Ошибка вычисления.", $token);
                }
            } catch (Throwable $e) {
                sendMessage($chat_id, "❌ Некорректное математическое выражение.", $token);
            }
        } else {
            sendMessage($chat_id, "⚠️ Допустимы только числа и знаки +, -, *, /", $token);
        }
        exit;
    }

    // Статистика бота
    elseif ($text == "📊 Статистика" || $text == "/stats") {
        $bot_users = file_exists('bot_users.json') ? json_decode(file_get_contents('bot_users.json'), true) : [];
        $tickets = file_exists('bot_tickets.json') ? json_decode(file_get_contents('bot_tickets.json'), true) : [];
        $gws = file_exists('bot_giveaways.json') ? json_decode(file_get_contents('bot_giveaways.json'), true) : [];
        
        $u_count = count($bot_users);
        $t_count = count($tickets);
        $g_count = count($gws);
        $site_u_count = count($all_users);

        $reply = "📊 <b>Статистика системы RTeam:</b>\n\n";
        $reply .= "👥 Пользователей в боте: <b>$u_count</b>\n";
        $reply .= "🌐 Аккаунтов на сайте: <b>$site_u_count</b>\n";
        $reply .= "🎟 Всего обращений: <b>$t_count</b>\n";
        $reply .= "🎁 Создано розыгрышей: <b>$g_count</b>\n";
        sendMessage($chat_id, $reply, $token);
        exit;
    }

    // Проверка статуса сервера
    elseif ($text == "/ping") {
        $start = microtime(true);
        $time_taken = round((microtime(true) - $start) * 1000, 2);
        sendMessage($chat_id, "🏓 <b>ПОНГ!</b>\n\n🟢 Сервер работает штатно.\n⏱ Время отклика: <b>{$time_taken} ms</b>", $token);
        exit;
    }

    // Серверное время
    elseif ($text == "/time") {
        $server_time = date('d.m.Y H:i:s');
        sendMessage($chat_id, "🕒 Текущее время сервера: <b>$server_time</b>", $token);
        exit;
    }

    // Правила проекта
    elseif ($text == "📜 Правила" || $text == "/rules") {
        $reply = "📜 <b>Правила использования бота RTeam:</b>\n\n";
        $reply .= "1. Запрещен спам и отправка ложных заявок.\n";
        $reply .= "2. Оскорбление администрации ведет к бессрочному муту.\n";
        $reply .= "3. Запрещено передавать свои 2FA коды третьим лицам.\n";
        $reply .= "4. Все обращения обрабатываются в порядке очереди.";
        sendMessage($chat_id, $reply, $token);
        exit;
    }

    // Добавление заметки
    elseif (mb_strpos($text, '/note_add ') === 0) {
        $note_text = trim(mb_substr($text, 10));
        if (!empty($note_text)) {
            if (!isset($all_notes[$user_id])) $all_notes[$user_id] = [];
            $all_notes[$user_id][] = [
                'date' => date('d.m.Y H:i'),
                'text' => $note_text
            ];
            file_put_contents($notes_file, json_encode($all_notes, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
            sendMessage($chat_id, "📌 Заметка успешно сохранена!", $token);
        } else {
            sendMessage($chat_id, "⚠️ Использование: `/note_add Текст заметки`", $token);
        }
        exit;
    }

    // Просмотр заметок
    elseif ($text == "📝 Заметки" || $text == "/notes") {
        if (empty($all_notes[$user_id])) {
            sendMessage($chat_id, "📝 У вас пока нет сохраненных заметок.\n\nЧтобы добавить, используйте:\n`/note_add Текст вашей заметки`", $token);
        } else {
            $reply = "📝 <b>Ваши личные заметки:</b>\n\n";
            foreach ($all_notes[$user_id] as $idx => $note) {
                $num = $idx + 1;
                $reply .= "<b>$num.</b> [" . $note['date'] . "] " . htmlspecialchars($note['text']) . "\n";
            }
            $reply .= "\n<i>Очистить все заметки: /note_clear</i>";
            sendMessage($chat_id, $reply, $token);
        }
        exit;
    }

    // Очистить заметки
    elseif ($text == "/note_clear") {
        unset($all_notes[$user_id]);
        file_put_contents($notes_file, json_encode($all_notes, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
        sendMessage($chat_id, "🧹 Все ваши заметки успешно удалены!", $token);
        exit;
    }

    // Поиск обращения по ID
    elseif (mb_strpos($text, '/ticket ') === 0) {
        $search_id = trim(mb_substr($text, 8));
        $tickets = file_exists('bot_tickets.json') ? json_decode(file_get_contents('bot_tickets.json'), true) : [];
        $found_t = null;
        foreach ($tickets as $t) {
            if ($t['id'] === $search_id) {
                $found_t = $t;
                break;
            }
        }
        if ($found_t) {
            $st = $found_t['status'] == 'new' ? "🟡 На рассмотрении" : ($found_t['status'] == 'answered' ? "🟢 Дан ответ" : "🔴 Закрыта");
            $reply = "🎟 <b>Заявка ID: {$found_t['id']}</b>\n";
            $reply .= "📅 Дата: {$found_t['date']}\n";
            $reply .= "📊 Статус: <b>$st</b>\n\n";
            $reply .= "💬 Текст: " . htmlspecialchars($found_t['text']);
            sendMessage($chat_id, $reply, $token);
        } else {
            sendMessage($chat_id, "❌ Заявка с ID <code>$search_id</code> не найдена.", $token);
        }
        exit;
    }

    // Переворот текста
    elseif (mb_strpos($text, '/flip ') === 0) {
        $inp = mb_substr($text, 6);
        $flipped = implode('', array_reverse(mb_str_split($inp)));
        sendMessage($chat_id, "🔄 <b>Перевернутый текст:</b>\n\n" . htmlspecialchars($flipped), $token);
        exit;
    }

    // Транслитерация текста
    elseif (mb_strpos($text, '/translit ') === 0) {
        $inp = mb_substr($text, 10);
        $res = transliterate($inp);
        sendMessage($chat_id, "🔤 <b>Транслит:</b>\n\n<code>" . htmlspecialchars($res) . "</code>", $token);
        exit;
    }

    // Проверка блокировки
    elseif ($text == "/checkban") {
        if (in_array((string)$user_id, $banned_users) || in_array((int)$user_id, $banned_users)) {
            sendMessage($chat_id, "🚫 <b>Статус: Вы заблокированы.</b>\nВы не можете отправлять новые заявки.", $token);
        } else {
            sendMessage($chat_id, "🟢 <b>Статус: Чист.</b>\nУ вас нет активных ограничений или блокировок.", $token);
        }
        exit;
    }

    // Переключение рассылок и уведомлений
    elseif ($text == "/notif") {
        $current = !isset($notif_settings[$user_id]) || $notif_settings[$user_id] === true;
        $notif_settings[$user_id] = !$current;
        file_put_contents($notifs_file, json_encode($notif_settings, JSON_PRETTY_PRINT));
        
        $status_msg = !$current ? "🔔 Уведомления и рассылки <b>включены</b>." : "🔕 Уведомления и рассылки <b>выключены</b>.";
        sendMessage($chat_id, $status_msg, $token);
        exit;
    }


    // --- 5. ДРУГИЕ ПОЛЬЗОВАТЕЛЬСКИЕ КОМАНДЫ ---

    // Инструкция по привязке аккаунта
    if ($text == "🔗 Привязать аккаунт") {
        $reply = "🔗 <b>Синхронизация профиля</b>\n\nПривязка аккаунта с сайта <b>rteam.info</b> к боту позволит вам:\n• Быть в курсе новостей и статусов заявок\n• <i>Для команды:</i> получать код подтверждения при входе в админ-панель и управлять ботом.\n\nПривязка необязательна: без неё вход на сайт работает по паролю.\n\n👉 <b>Как привязать:</b>\n1. Откройте личный кабинет: rteam.info/cabinet.php\n2. Нажмите «Привязать Telegram» — появится код\n3. Отправьте сюда: <code>/link КОД</code>";
        sendMessage($chat_id, $reply, $token);
    }

    // Новая заявка (проверка на мут)
    elseif (mb_strpos(mb_strtolower($text), 'заявка:') === 0) {
        if (in_array((string)$user_id, $banned_users) || in_array((int)$user_id, $banned_users)) {
            $reply = "🚫 <b>Доступ ограничен.</b>\n\nВы были заблокированы администратором за нарушение правил и больше не можете писать в техническую поддержку бота.";
            sendMessage($chat_id, $reply, $token);
            exit;
        }

        $ticket_text = trim(mb_substr($text, 7));
        $username = isset($update['message']['from']['username']) ? '@' . $update['message']['from']['username'] : 'Скрытый пользователь';

        $new_ticket = [
            'id' => uniqid(),
            'date' => date('Y-m-d H:i:s'),
            'username' => $username,
            'user_id' => $user_id,
            'text' => $ticket_text,
            'status' => 'new'
        ];

        $file_path = 'bot_tickets.json';
        $current_data = file_exists($file_path) ? json_decode(file_get_contents($file_path), true) : [];
        array_unshift($current_data, $new_ticket);
        file_put_contents($file_path, json_encode($current_data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));

        $reply = "✅ <b>Ваша заявка успешно отправлена!</b>\n\nВы можете отслеживать её статус, нажав кнопку «📋 Мои заявки» в меню или командой `/ticket " . $new_ticket['id'] . "`.";
        sendMessage($chat_id, $reply, $token);
    } 
    
    // Старт и Клавиатура
    elseif ($text == "/start") {
        $keyboard = [
            "keyboard" => [
                [["text" => "👤 Профиль"], ["text" => "📋 Мои заявки"]],
                [["text" => "🎁 Розыгрыши"], ["text" => "🆘 Поддержка"]],
                [["text" => "📝 Заметки"], ["text" => "📊 Статистика"]],
                [["text" => "🔗 Привязать аккаунт"], ["text" => "📜 Правила"]],
                [["text" => "🌐 О команде"]]
            ],
            "resize_keyboard" => true
        ];
        
        if ($admin_login) {
            $keyboard["keyboard"][] = [["text" => "🔑 Получить код 2FA"], ["text" => "⚙️ Админ-панель"]];
        }

        $reply = "Привет! Я обновленный официальный бот команды <b>RTeam</b> 🚀\n\nВыберите нужный раздел в меню или отправьте команду:";
        sendMessage($chat_id, $reply, $token, $keyboard);
    } 
    
    // Розыгрыши
    elseif ($text == "🎁 Розыгрыши") {
        $gws_file = 'bot_giveaways.json';
        $gws = file_exists($gws_file) ? json_decode(file_get_contents($gws_file), true) : [];
        $active_gws = array_filter($gws, function($g) { return $g['status'] == 'active'; });

        if (empty($active_gws)) {
            $reply = "😔 В данный момент активных розыгрышей нет. \n\nСледите за обновлениями, скоро мы запустим что-то интересное!";
            sendMessage($chat_id, $reply, $token);
        } else {
            foreach ($active_gws as $gw) {
                $msg = "🎁 <b>РОЗЫГРЫШ: " . htmlspecialchars($gw['title']) . "</b>\n\n";
                $msg .= htmlspecialchars($gw['description']) . "\n\n";
                $msg .= "👥 <i>Количество участников: " . count($gw['participants']) . "</i>";
                
                $inline_keyboard = [ "inline_keyboard" => [ [["text" => "🎉 Участвовать", "callback_data" => "gw_part_" . $gw['id']]] ] ];
                sendMessage($chat_id, $msg, $token, null, $inline_keyboard);
            }
        }
    }

    // Мои заявки
    elseif ($text == "📋 Мои заявки") {
        $file_path = 'bot_tickets.json';
        $tickets = file_exists($file_path) ? json_decode(file_get_contents($file_path), true) : [];
        $my_tickets = [];
        foreach ($tickets as $t) { if ($t['user_id'] == $user_id) $my_tickets[] = $t; }

        if (empty($my_tickets)) {
            $reply = "У вас пока нет открытых или прошлых заявок.";
        } else {
            $reply = "<b>Ваши последние обращения:</b>\n\n";
            $count = 0;
            foreach ($my_tickets as $t) {
                if ($count >= 5) break;
                if ($t['status'] == 'new') $status = "🟡 На рассмотрении";
                elseif ($t['status'] == 'answered') $status = "🟢 Дан ответ";
                else $status = "🔴 Закрыта";

                $preview = mb_strimwidth($t['text'], 0, 40, "...");
                $reply .= "🔹 <code>" . $t['id'] . "</code>: <i>" . htmlspecialchars($preview) . "</i>\n└ Статус: <b>" . $status . "</b>\n\n";
                $count++;
            }
        }
        sendMessage($chat_id, $reply, $token);
    }
    
    elseif ($text == "🌐 О команде") {
        $reply = "<b>RTeam</b> — это профессиональная команда IT-разработки.\n\nВся информация о нас доступна на нашем официальном сайте:\n👉 https://rteam.info";
        sendMessage($chat_id, $reply, $token);
    } 
    
    elseif ($text == "🆘 Поддержка" || $text == "/support") {
        if (in_array((string)$user_id, $banned_users) || in_array((int)$user_id, $banned_users)) {
             $reply = "🚫 <b>Ваш аккаунт ограничен в боте.</b>\nВы не можете отправлять заявки сюда. Если это ошибка, попробуйте обратиться через сайт 👇";
        } else {
             $reply = "Вы можете создать обращение прямо здесь!\n\nПросто напишите сообщение, начав его со слова <b>Заявка:</b>\n\n<i>Пример: Заявка: Здравствуйте, мне нужна консультация.</i>\n\nЛибо перейдите в наш Центр Поддержки 👇";
        }
        $inline_keyboard = [ "inline_keyboard" => [ [["text" => "🎧 Перейти в Центр Поддержки", "url" => "https://rteam.info/support.php"]] ] ];
        sendMessage($chat_id, $reply, $token, null, $inline_keyboard);
    } 
    
    else {
        if (mb_strpos($text, '/') !== 0) {
            $reply = "Пожалуйста, используйте кнопки меню для навигации 👇";
            sendMessage($chat_id, $reply, $token);
        }
    }
}

// ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЙ В TELEGRAM
function sendMessage($chat_id, $text, $token, $keyboard = null, $inline_keyboard = null) {
    $url = "https://api.telegram.org/bot" . $token . "/sendMessage";
    $data = [
        'chat_id' => $chat_id,
        'text' => $text,
        'parse_mode' => 'HTML',
        'disable_web_page_preview' => true
    ];
    if ($keyboard != null) {
        $data['reply_markup'] = json_encode($keyboard);
    } elseif ($inline_keyboard != null) {
        $data['reply_markup'] = json_encode($inline_keyboard);
    }
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_exec($ch);
    curl_close($ch);
}
?>