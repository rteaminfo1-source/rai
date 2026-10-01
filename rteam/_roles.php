<?php
/* ==========================================================
   РОЛИ И ПРАВА RTEAM
   Общий файл для admin.php и index.php — должен лежать рядом с ними.

   Как это устроено:
   • У каждой роли есть уровень (level). Чем он выше, тем старше роль.
   • Что умеет роль, задаёт список прав (rt_default_role_perms ниже).
     Руководитель может поменять права любой роли прямо в админ-панели
     (вкладка «Права ролей») — изменения сохраняются в roles_perms.json,
     а этот файл править не нужно.
   • Роли и направления сотрудников назначаются в админ-панели
     (вкладки «Команда» и «Пользователи») — в users.json лезть не нужно.
   • Одобрение заявки в админ-панели автоматически выдаёт роль «Стажёр»
     и направление, на которое человек подавал заявку.
   ========================================================== */

/* Владельцы сайта: у них всегда все права, их роль и аккаунт может менять
   только другой владелец. Это страховка, чтобы никто случайно не закрыл
   доступ к панели всем. Если владельцы другие — поменяйте логины здесь. */
function rt_owners() {
    return ["Roma_07b", "Petryha"];
}

/* Файл, где хранятся права ролей, изменённые в панели */
const RT_PERMS_FILE = "roles_perms.json";

/* Роль, которую получает человек после одобрения заявки */
const RT_TRAINEE_ROLE = "Стажёр";

/* Роль руководителя: у неё всегда все права, отключить их нельзя */
const RT_TOP_ROLE = "Руководитель";

/* ---------- Каталог ролей ----------
   Ключ — точное название роли, как оно хранится в users.json.
   level  — старшинство: менять роль можно только тем, кто младше тебя.
   dept   — отдел (для файлов и целей): dev, tester, admin, leader.
   head   — «главный» своего отдела. */
function rt_roles() {
    return [
        "Пользователь" => [
            "level" => 0, "dept" => null, "head" => false, "icon" => "👤", "color" => "#718096",
            "desc" => "Обычный аккаунт сайта. В админ-панель не пускает.",
        ],
        "Стажёр" => [
            "level" => 10, "dept" => null, "head" => false, "icon" => "🌱", "color" => "#2fb9a8",
            "desc" => "Выдаётся автоматически после одобрения заявки. Чат с командой, файлы и цели своего направления. Не может банить, управлять контентом и людьми.",
        ],
        "Тестер" => [
            "level" => 20, "dept" => "tester", "head" => false, "icon" => "🧪", "color" => "#d69e2e",
            "desc" => "Проверяет проекты, ведёт тикеты поддержки, загружает файлы отдела.",
        ],
        "Кодер" => [
            "level" => 20, "dept" => "dev", "head" => false, "icon" => "⌨️", "color" => "#4c8dff",
            "desc" => "Пишет код, публикует проекты, загружает файлы отдела.",
        ],
        "Разработчик" => [
            "level" => 20, "dept" => "dev", "head" => false, "icon" => "🛠️", "color" => "#5a67d8",
            "desc" => "Разрабатывает проекты, публикует их на сайте, помогает в тикетах поддержки.",
        ],
        "Администратор" => [
            "level" => 20, "dept" => "admin", "head" => false, "icon" => "🛡️", "color" => "#e0503a",
            "desc" => "Модерация: смотрит заявки, отвечает в тикетах и Telegram-боте, ведёт блог.",
        ],
        "Главный Тестер" => [
            "level" => 30, "dept" => "tester", "head" => true, "icon" => "🔬", "color" => "#ecc94b",
            "desc" => "Глава тестеров. Доступно всё, кроме банов, ролей и штрафов: почта, заявки, директора, контент, настройки, логи.",
        ],
        "Главный Кодер" => [
            "level" => 30, "dept" => "dev", "head" => true, "icon" => "💻", "color" => "#63a4ff",
            "desc" => "Глава кодеров. Доступно всё, кроме банов, ролей и штрафов: почта, заявки, директора, контент, настройки, логи.",
        ],
        "Главный разработчик" => [
            "level" => 30, "dept" => "dev", "head" => true, "icon" => "🚀", "color" => "#7f8cff",
            "desc" => "Глава разработки. Доступно всё, кроме банов, ролей и штрафов: почта, заявки, директора, контент, настройки, логи.",
        ],
        "Главный Администратор" => [
            "level" => 40, "dept" => "admin", "head" => true, "icon" => "⚔️", "color" => "#ff3b3b",
            "desc" => "Банит (IP, чёрный список, гео-блок, мут в боте), назначает и меняет роли, управляет пользователями и штрафами.",
        ],
        "Руководитель" => [
            "level" => 50, "dept" => "leader", "head" => true, "icon" => "👑", "color" => "#f6c445",
            "desc" => "Полный доступ ко всему. Назначает любые роли и настраивает права ролей.",
        ],
    ];
}

/* Направления, на которые подают заявку и которые получает стажёр.
   Ключ — роль, которой стажёр станет после повышения. */
function rt_directions() {
    return [
        "Кодер"         => "Кодер",
        "Разработчик"   => "Разработчик",
        "Тестер"        => "Тестер",
        "Администратор" => "Администратор",
    ];
}

function rt_departments() {
    return ["dev" => "Разработка", "tester" => "Тестирование", "admin" => "Администрация", "leader" => "Руководство"];
}

/* ---------- Каталог прав ---------- */
function rt_permissions() {
    return [
        "Команда" => [
            "chat.view"      => "Командный чат: читать, писать, голосовать",
            "chat.pin"       => "Чат: закреплять сообщения",
            "chat.moderate"  => "Чат: удалять чужие сообщения",
            "team.view"      => "Команда: видеть состав и роли",
            "files.view"     => "Файлы своего отдела: смотреть и скачивать",
            "files.upload"   => "Файлы: загружать",
            "files.manage"   => "Файлы: видеть все отделы, удалять чужие",
            "goals.view"     => "Цели: смотреть",
            "goals.manage"   => "Цели: ставить и удалять",
            "fines.view_all" => "Штрафы: видеть штрафы всей команды",
            "fines.manage"   => "Штрафы: выписывать, подтверждать, удалять",
        ],
        "Работа" => [
            "projects.manage"  => "Проекты: публиковать и редактировать",
            "apps.view"        => "Заявки: смотреть",
            "apps.decide"      => "Заявки: принимать (выдаёт «Стажёр») и отклонять",
            "directors.manage" => "Директора школ",
            "support.view"     => "Тикеты поддержки сайта",
            "mail.view"        => "Почта: сообщения с сайта и ответы на email",
            "bot.tickets"      => "Telegram-бот: отвечать на заявки",
            "bot.manage"       => "Telegram-бот: рассылка и розыгрыши",
        ],
        "Контент" => [
            "blog.manage"    => "Блог",
            "leaks.manage"   => "Сливы",
            "themes.manage"  => "Темы сайта и «Игра в кальмара»",
            "recruit.manage" => "Набор: открыть/закрыть, вопросы заявки",
            "gold.chat"      => "Золотой билет: переписка с владельцами",
            "gold.manage"    => "Золотой билет: выдавать, отзывать, услуги",
        ],
        "Управление" => [
            "users.view"      => "Пользователи: список, IP, последний вход",
            "users.manage"    => "Пользователи: создать, сменить пароль, удалить",
            "roles.manage"    => "Назначать и менять роли и направления",
            "bans.manage"     => "Баны: IP, чёрный список, гео-блок, мут в боте",
            "settings.manage" => "Настройки сайта и токен бота",
            "logs.view"       => "Логи",
            "perms.manage"    => "Настраивать права ролей",
        ],
    ];
}

function rt_all_perm_keys() {
    $keys = [];
    foreach (rt_permissions() as $group) foreach ($group as $k => $_) $keys[] = $k;
    return $keys;
}

/* ---------- Права по умолчанию ---------- */
function rt_default_role_perms() {
    $all = rt_all_perm_keys();
    $trainee = ["chat.view", "team.view", "files.view", "goals.view"];
    $staff   = array_merge($trainee, ["chat.pin", "files.upload"]);
    // «Главные»: всё, кроме банов, ролей, пользователей, штрафов и настройки прав
    $head    = array_values(array_diff($all, ["bans.manage", "roles.manage", "users.manage", "fines.manage", "perms.manage"]));
    // Главный администратор: всё, кроме настройки прав ролей
    $chief   = array_values(array_diff($all, ["perms.manage"]));
    return [
        "Пользователь"          => [],
        "Стажёр"                => $trainee,
        "Тестер"                => array_merge($staff, ["support.view"]),
        "Кодер"                 => array_merge($staff, ["projects.manage"]),
        "Разработчик"           => array_merge($staff, ["projects.manage", "support.view"]),
        "Администратор"         => array_merge($staff, ["apps.view", "support.view", "bot.tickets", "blog.manage", "gold.chat"]),
        "Главный Тестер"        => $head,
        "Главный Кодер"         => $head,
        "Главный разработчик"   => $head,
        "Главный Администратор" => $chief,
        "Руководитель"          => $all,
    ];
}

/* ---------- Чтение/запись файлов ---------- */
function rt_json_load($file, $default) {
    if (function_exists('load_json')) return load_json($file, $default);
    if (!file_exists($file)) return $default;
    $data = json_decode((string)@file_get_contents($file), true);
    return is_array($data) ? $data : $default;
}
function rt_json_save($file, $data) {
    if (function_exists('save_json')) return save_json($file, $data);
    return @file_put_contents($file, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
}

/* Итоговые права всех ролей: по умолчанию + изменения из панели */
function rt_role_perms_matrix($reload = false) {
    static $cache = null;
    if ($cache !== null && !$reload) return $cache;
    $matrix = rt_default_role_perms();
    $saved = rt_json_load(RT_PERMS_FILE, []);
    $known = rt_all_perm_keys();
    if (is_array($saved)) {
        foreach ($saved as $role => $perms) {
            if (!isset($matrix[$role]) || !is_array($perms)) continue;
            $matrix[$role] = array_values(array_intersect($known, $perms));
        }
    }
    $matrix[RT_TOP_ROLE] = $known;   // руководителю — всегда всё
    $matrix["Пользователь"] = [];    // обычным пользователям панель не положена
    return $cache = $matrix;
}

/* Сохраняет права ролей из панели (руководитель всегда остаётся со всеми правами) */
function rt_save_role_perms($matrix) {
    $known = rt_all_perm_keys();
    $clean = [];
    foreach (rt_roles() as $role => $_) {
        if ($role === RT_TOP_ROLE || $role === "Пользователь") continue;
        $perms = isset($matrix[$role]) && is_array($matrix[$role]) ? $matrix[$role] : [];
        $clean[$role] = array_values(array_intersect($known, $perms));
    }
    rt_json_save(RT_PERMS_FILE, $clean);
    rt_role_perms_matrix(true);
}

function rt_reset_role_perms() {
    rt_json_save(RT_PERMS_FILE, []);
    rt_role_perms_matrix(true);
}

/* ---------- Проверки ---------- */
function rt_role_info($role) {
    $roles = rt_roles();
    return $roles[$role] ?? null;
}

function rt_is_owner($login) {
    return $login !== null && $login !== "" && in_array((string)$login, rt_owners(), true);
}

/* Уровень роли. Неизвестные роли считаются обычным пользователем. */
function rt_level($role) {
    $info = rt_role_info($role);
    return $info ? (int)$info["level"] : 0;
}

/* Уровень конкретного человека: владельцы старше всех */
function rt_user_level($login, $role) {
    return rt_is_owner($login) ? 1000 : rt_level($role);
}

/* Пускать ли в админ-панель */
function rt_is_staff($role, $login = null) {
    return rt_is_owner($login) || rt_level($role) >= rt_level(RT_TRAINEE_ROLE);
}

function rt_role_perms($role) {
    $m = rt_role_perms_matrix();
    return $m[$role] ?? [];
}

function rt_can($login, $role, $perm) {
    if (rt_is_owner($login) || $role === RT_TOP_ROLE) return true;
    return in_array($perm, rt_role_perms($role), true);
}

/* Можно ли мне выдать эту роль кому-то */
function rt_can_assign_role($meLogin, $meRole, $newRole) {
    if (!rt_role_info($newRole)) return false;
    if (rt_is_owner($meLogin)) return true;
    if (!rt_can($meLogin, $meRole, "roles.manage")) return false;
    if ($meRole === RT_TOP_ROLE) return true;
    return rt_level($newRole) < rt_level($meRole);
}

/* Можно ли мне менять роль/аккаунт этого человека */
function rt_can_edit_user($meLogin, $meRole, $targetLogin, $targetRole) {
    if ((string)$meLogin === (string)$targetLogin) return false;          // себе роль не меняем
    if (rt_is_owner($targetLogin)) return rt_is_owner($meLogin);           // владельцев трогают только владельцы
    if (rt_is_owner($meLogin)) return true;
    return rt_level($targetRole) < rt_level($meRole);                      // только тех, кто младше
}

function rt_assignable_roles($meLogin, $meRole) {
    $out = [];
    foreach (rt_roles() as $role => $_) if (rt_can_assign_role($meLogin, $meRole, $role)) $out[] = $role;
    return $out;
}

/* Отдел человека: у стажёра — отдел его направления */
function rt_user_dept($role, $direction = "") {
    if ($role === RT_TRAINEE_ROLE && $direction !== "" && $direction !== null) {
        $info = rt_role_info($direction);
        return $info["dept"] ?? null;
    }
    $info = rt_role_info($role);
    return $info["dept"] ?? null;
}

/* «Стажёр · Кодер», «Главный Кодер» и т.п. */
function rt_role_label($role, $direction = "") {
    $role = (string)($role ?: "Пользователь");
    if ($role === RT_TRAINEE_ROLE && (string)$direction !== "") return $role . " · " . $direction;
    return $role;
}

/* Цветной бейдж роли для админ-панели */
function rt_role_badge($role, $direction = "", $login = null) {
    $role = (string)($role ?: "Пользователь");
    $info = rt_role_info($role) ?? ["icon" => "❔", "color" => "#718096"];
    $html = '<span class="role-badge" style="--rc:' . htmlspecialchars($info["color"]) . '">' . $info["icon"] . ' ' . htmlspecialchars(rt_role_label($role, $direction)) . '</span>';
    if ($login !== null && rt_is_owner($login)) $html .= ' <span class="role-badge owner-badge" title="Владелец сайта: все права">★ Владелец</span>';
    return $html;
}

/* ---------- Заявки ---------- */

/* Ответ на вопрос заявки, в тексте которого есть $needle */
function rt_app_answer($app, $needle) {
    foreach (($app["answers"] ?? []) as $row) {
        if (mb_stripos((string)($row["q"] ?? ""), $needle) !== false) return trim((string)($row["a"] ?? ""));
    }
    return "";
}

/* Направление по свободному тексту ответа */
function rt_direction_from_text($text) {
    $t = mb_strtolower(trim((string)$text));
    if ($t === "") return null;
    foreach (rt_directions() as $key => $_) if ($t === mb_strtolower($key)) return $key;
    if (mb_strpos($t, "тест") !== false || mb_strpos($t, "qa") !== false) return "Тестер";
    if (mb_strpos($t, "разраб") !== false || mb_strpos($t, "dev") !== false) return "Разработчик";
    if (mb_strpos($t, "админ") !== false || mb_strpos($t, "модер") !== false) return "Администратор";
    if (mb_strpos($t, "код") !== false || mb_strpos($t, "програм") !== false || mb_strpos($t, "code") !== false) return "Кодер";
    return null;
}

/* На какое направление подавал человек: из типа заявки и ответа «Направление» */
function rt_app_direction($app) {
    $type = (string)($app["type"] ?? "");
    if (mb_stripos($type, "админ") !== false) return "Администратор";
    $fromType = rt_direction_from_text($type);
    if ($fromType) return $fromType;
    $fromAnswer = rt_direction_from_text(rt_app_answer($app, "направлен"));
    if ($fromAnswer) return $fromAnswer;
    return "Кодер";
}

/* Ищет аккаунт заявителя: по логину в заявке, по нику, по email */
function rt_app_account($app, $users) {
    foreach (["user", "login"] as $k) {
        if (!empty($app[$k]) && isset($users[$app[$k]])) return (string)$app[$k];
    }
    $nick = rt_app_answer($app, "Ник");
    if ($nick !== "") {
        if (isset($users[$nick])) return $nick;
        foreach ($users as $login => $_) if (mb_strtolower((string)$login) === mb_strtolower($nick)) return (string)$login;
    }
    $email = mb_strtolower(rt_app_answer($app, "email"));
    if ($email !== "") {
        foreach ($users as $login => $u) {
            if (is_array($u) && mb_strtolower(trim((string)($u["email"] ?? ""))) === $email) return (string)$login;
        }
    }
    return null;
}

/* ---------- IP (для банов) ---------- */

/* IP посетителя: Cloudflare / прокси заголовки, затем REMOTE_ADDR */
function rt_client_ip() {
    foreach (["HTTP_CF_CONNECTING_IP", "HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP", "REMOTE_ADDR"] as $key) {
        if (!empty($_SERVER[$key])) {
            $candidate = trim(explode(",", $_SERVER[$key])[0]);
            if (filter_var($candidate, FILTER_VALIDATE_IP)) return $candidate;
        }
    }
    return $_SERVER["REMOTE_ADDR"] ?? "0.0.0.0";
}

/* Запоминает IP аккаунта: последний адрес и историю до 10 разных адресов
   (когда впервые и когда последний раз заходил с каждого) — видно в админ-панели */
function rt_track_ip(array &$u, $ip) {
    if (!filter_var($ip, FILTER_VALIDATE_IP)) return;
    $now = date("Y-m-d H:i:s");
    $u["ip"] = $ip;
    $u["last_seen"] = $now;
    $hist = (isset($u["ip_history"]) && is_array($u["ip_history"])) ? $u["ip_history"] : [];
    $found = false;
    foreach ($hist as &$h) {
        if (($h["ip"] ?? "") === $ip) { $h["last"] = $now; $h["visits"] = (int)($h["visits"] ?? 0) + 1; $found = true; break; }
    }
    unset($h);
    if (!$found) $hist[] = ["ip" => $ip, "first" => $now, "last" => $now, "visits" => 1];
    usort($hist, fn($a, $b) => strcmp($b["last"] ?? "", $a["last"] ?? ""));
    $u["ip_history"] = array_slice($hist, 0, 10);
}

/* То же, но сразу с записью в users.json (для входа: перечитываем свежий файл) */
function rt_track_login_ip($login) {
    $users = rt_json_load("users.json", []);
    if (!isset($users[$login]) || !is_array($users[$login])) return;
    rt_track_ip($users[$login], rt_client_ip());
    rt_json_save("users.json", $users);
}

/* Действующий бан для IP из bans.json (вкладка «Баны» в админ-панели) или null */
function rt_active_ban($ip) {
    foreach ((array)rt_json_load("bans.json", []) as $b) {
        if (($b["ip"] ?? "") === $ip && ((int)($b["expires"] ?? 0) === 0 || (int)$b["expires"] > time())) return $b;
    }
    return null;
}
