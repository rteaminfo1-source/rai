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

/* ---------- ИИ поддержки (Rai) ----------
   Нейросеть лежит на GitHub (папка support/ репозитория rai: rai-support.js и model.json)
   и работает в браузере посетителя. Сайт её только загружает и сохраняет ответы в тикет.
   Включение, адрес папки на GitHub и поиск в интернете — в админ-панели («Тикеты» → «ИИ поддержки»).
   Нейросеть получает только текст тикета: паролей, users.json и токенов она не видит. */

const RT_AI_NAME = "Rai · ИИ";
const RT_AI_SRC_DEFAULT = "https://raw.githubusercontent.com/rteaminfo1-source/rai/claude/awesome-mendel-tzoqsf/support/";

/* Папка с нейросетью: https://…/support/ (со слешем в конце) */
function rt_support_ai_src($settings) {
    $src = trim((string)($settings["support_ai_src"] ?? ""));
    if ($src === "" || !preg_match('~^(https://|http://(127\.0\.0\.1|localhost)[:/])[^\s"\'<>]+$~i', $src)) $src = RT_AI_SRC_DEFAULT;
    return rtrim($src, "/") . "/";
}

/* net.php для поиска в интернете (необязательно) */
function rt_support_ai_search($settings) {
    $u = trim((string)($settings["support_ai_search"] ?? ""));
    return preg_match('~^https://[^\s"\'<>]+$~i', $u) ? $u : "";
}

function rt_support_ai_ready($settings) {
    return !empty($settings["support_ai_enabled"]);
}

/* Отвечает ли ИИ в этом тикете: ИИ включён, тикет не закрыт и его не забрал администратор (ai = false) */
function rt_ticket_ai_on($ticket, $settings) {
    return rt_support_ai_ready($settings) && ($ticket["ai"] ?? true) !== false && ($ticket["status"] ?? "") !== "Закрыт";
}

/* История тикета для нейросети: [{"from": "client"|"admin"|"ai", "text"}] */
function rt_ticket_ai_history($ticket) {
    $hist = [["from" => "client", "text" => (string)($ticket["description"] ?? "")]];
    foreach ((array)($ticket["replies"] ?? []) as $r) {
        if (!empty($r["is_system"])) continue;
        $from = !empty($r["is_ai"]) ? "ai" : (($r["is_admin"] ?? true) ? "admin" : "client");
        $hist[] = ["from" => $from, "text" => (string)($r["text"] ?? "")];
    }
    return $hist;
}

/* На что отвечать: сообщения клиента после последнего ответа сотрудника или ИИ (или последнее сообщение клиента) */
function rt_ticket_unanswered($ticket) {
    $msgs = []; $last = "";
    foreach (rt_ticket_ai_history($ticket) as $h) {
        if ($h["from"] === "client") { $msgs[] = $h["text"]; $last = $h["text"]; }
        else $msgs = [];
    }
    return trim(implode("\n", $msgs)) ?: $last;
}

/* Данные тикета для нейросети в браузере */
function rt_ticket_ai_payload($ticket) {
    return ["ai_history" => array_slice(rt_ticket_ai_history($ticket), -20), "ai_message" => rt_ticket_unanswered($ticket),
            "topic" => (string)($ticket["topic"] ?? ""), "n" => count($ticket["replies"] ?? [])];
}

/* Загрузчик нейросети для страницы: RaiLoader(src) → RaiSupport.
   GitHub отдаёт .js как текст, поэтому файл скачивается и подключается через Blob. */
function rt_support_ai_loader_js() {
    return <<<'JS'
window.RaiLoader = function (src) {
    if (window.RaiSupport && window.RaiSupport.model && window.RaiSupport.base === src) return Promise.resolve(window.RaiSupport);
    if (window.__raiLoading && window.__raiLoadingSrc === src) return window.__raiLoading;
    const bases = [src];
    const gh = src.match(/^https:\/\/raw\.githubusercontent\.com\/([^/]+)\/([^/]+)\/([^/]+)\/(.*)$/);
    if (gh) bases.push(`https://cdn.jsdelivr.net/gh/${gh[1]}/${gh[2]}@${gh[3]}/${gh[4]}`); // запасной адрес, если GitHub недоступен
    window.__raiLoadingSrc = src;
    window.__raiLoading = (async () => {
        let last = null;
        for (const base of bases) {
            try {
                const r = await fetch(base + "rai-support.js", { cache: "no-cache" });
                if (!r.ok) throw new Error("rai-support.js: HTTP " + r.status);
                const code = await r.text();
                await new Promise((ok, fail) => {
                    const s = document.createElement("script");
                    s.src = URL.createObjectURL(new Blob([code], { type: "text/javascript" }));
                    s.onload = ok; s.onerror = () => fail(new Error("не удалось запустить rai-support.js"));
                    document.head.appendChild(s);
                });
                await window.RaiSupport.load(base, { cache: "no-cache" });
                window.RaiSupport.base = src;
                return window.RaiSupport;
            } catch (e) { last = e; }
        }
        window.__raiLoading = null;
        throw last || new Error("нейросеть недоступна");
    })();
    return window.__raiLoading;
};
JS;
}

/* Помощник Rai на страницах сайта (кнопка ✨): rai-guide.js с GitHub. Вставляется перед </body>.
   Включён, пока в админ-панели не снята галочка «Помощник Rai на страницах сайта». */
function rt_rai_widget($settings, $user = null) {
    if (!($settings["rai_widget"] ?? true)) return "";
    $cfg = json_encode(["base" => rt_support_ai_src($settings), "user" => $user ? (string)$user : null,
                        "searchUrl" => rt_support_ai_search($settings), "support" => "support.php"], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    return '<script>(function(c){if(window.RaiGuide)return RaiGuide.init(c);fetch(c.base+"rai-guide.js",{cache:"no-cache"})'
         . '.then(function(r){if(!r.ok)throw 0;return r.text()}).then(function(t){var s=document.createElement("script");'
         . 's.src=URL.createObjectURL(new Blob([t],{type:"text/javascript"}));s.onload=function(){RaiGuide.init(c)};'
         . 'document.head.appendChild(s)}).catch(function(){})})(' . $cfg . ');</script>';
}

/* ---------- Тикеты поддержки ---------- */

/* Изменение tickets.json под блокировкой (support.php и admin.php): ответ клиента, ответ ИИ и ответ
   сотрудника приходят разными запросами почти одновременно и не должны затирать друг друга.
   Файл записывается целиком через временный (rename), чтобы никто не прочитал его наполовину. */
function rt_tickets_update(callable $fn) {
    $lock = @fopen("tickets.json.lock", "c");
    if ($lock) flock($lock, LOCK_EX);
    $raw = file_exists("tickets.json") ? (string)file_get_contents("tickets.json") : "";
    $tickets = json_decode($raw, true);
    if (!is_array($tickets)) {
        if (trim($raw) !== "") { if ($lock) { flock($lock, LOCK_UN); fclose($lock); } return null; } // файл повреждён — не трогаем
        $tickets = [];
    }
    $result = $fn($tickets);
    $tmp = "tickets.json.tmp" . getmypid();
    if (@file_put_contents($tmp, json_encode($tickets, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)) === false || !@rename($tmp, "tickets.json")) {
        @unlink($tmp);
        rt_json_save("tickets.json", $tickets); // хостинг не дал создать временный файл — пишем напрямую
    }
    if ($lock) { flock($lock, LOCK_UN); fclose($lock); }
    return $result;
}

/* Только картинки: проверяем расширение и содержимое, имя файла придумываем сами */
function rt_save_image_upload($file, $prefix) {
    if (empty($file["name"]) || ($file["error"] ?? 1) !== 0 || ($file["size"] ?? 0) > 8 * 1024 * 1024) return null;
    $ext = strtolower(pathinfo($file["name"], PATHINFO_EXTENSION));
    if (!in_array($ext, ["jpg", "jpeg", "png", "gif", "webp"], true) || !@getimagesize($file["tmp_name"])) return null;
    $dir = "support_uploads/";
    if (!is_dir($dir)) mkdir($dir, 0755, true);
    $name = $dir . time() . "_" . $prefix . bin2hex(random_bytes(4)) . "." . $ext;
    return move_uploaded_file($file["tmp_name"], $name) ? $name : null;
}

/* ---------- Discord: вход, регистрация, привязка и сообщения от бота ----------
   Вход и привязка — discord_auth.php (Discord OAuth2: client_id и client_secret из Developer Portal).
   Бот (папка discord/ в репозитории, index.js) присылает в ЛС коды входа и уведомления: сайт отправляет
   запрос на адрес бота с ключом api_key — тем же, что в secret.json бота.
   Секреты лежат в discord_config.php рядом с сайтом (в GitHub его нет) или задаются в админ-панели
   (вкладка «Discord»): значения из админ-панели важнее. */

function rt_discord_conf($settings = null) {
    static $file = null;
    if ($file === null) {
        $file = [];
        $f = __DIR__ . "/discord_config.php";
        if (is_file($f)) { $c = include $f; if (is_array($c)) $file = $c; }
    }
    if (!is_array($settings)) $settings = rt_json_load("settings.json", []);
    $pick = function ($key) use ($file, $settings) {
        $v = trim((string)($settings["discord_" . $key] ?? ""));
        return $v !== "" ? $v : trim((string)($file[$key] ?? ""));
    };
    $api = $pick("api_base"); // только для проверки на своём компьютере
    return [
        "client_id"     => preg_match('/^\d{15,22}$/', $pick("client_id")) ? $pick("client_id") : "",
        "client_secret" => $pick("client_secret"),
        "bot_url"       => preg_match('~^https?://[^\s"\'<>]+$~i', $pick("bot_url")) ? rtrim($pick("bot_url"), "/") : "",
        "api_key"       => $pick("api_key"),
        "invite"        => preg_match('~^https://[^\s"\'<>]+$~i', $pick("invite")) ? $pick("invite") : "",
        "redirect"      => preg_match('~^https?://[^\s"\'<>]+$~i', $pick("redirect")) ? $pick("redirect") : "",
        "api"           => preg_match('~^http://(127\.0\.0\.1|localhost)(:\d+)?$~', rtrim($api, "/")) ? rtrim($api, "/") : "https://discord.com/api",
        "oauth"         => preg_match('~^http://(127\.0\.0\.1|localhost)(:\d+)?$~', rtrim($api, "/")) ? rtrim($api, "/") . "/oauth2/authorize" : "https://discord.com/oauth2/authorize",
    ];
}
function rt_discord_login_ready($settings = null) {
    $c = rt_discord_conf($settings);
    return $c["client_id"] !== "" && $c["client_secret"] !== "";
}
function rt_discord_bot_ready($settings = null) {
    $c = rt_discord_conf($settings);
    return $c["bot_url"] !== "" && $c["api_key"] !== "";
}

/* Адрес сайта (https://rteam.info) — для ссылок в сообщениях бота */
function rt_site_url() {
    $host = preg_replace('/[^a-z0-9.\-:\[\]]/i', '', (string)($_SERVER["HTTP_HOST"] ?? "rteam.info"));
    $local = preg_match('/^(127\.0\.0\.1|localhost)(:\d+)?$/', $host);
    $dir = rtrim(str_replace("\\", "/", dirname((string)($_SERVER["SCRIPT_NAME"] ?? "/"))), "/");
    return ($local ? "http://" : "https://") . $host . $dir;
}
/* Куда Discord возвращает после входа. Этот адрес должен быть в Developer Portal → OAuth2 → Redirects */
function rt_discord_redirect_uri($conf) {
    return $conf["redirect"] !== "" ? $conf["redirect"] : rt_site_url() . "/discord_auth.php";
}

function rt_discord_avatar($u) {
    $id = (string)($u["discord_id"] ?? "");
    if ($id === "") return "";
    if (!empty($u["discord_avatar"])) return "https://cdn.discordapp.com/avatars/" . rawurlencode($id) . "/" . rawurlencode($u["discord_avatar"]) . ".png?size=64";
    return "https://cdn.discordapp.com/embed/avatars/" . (((int)$id >> 22) % 6) . ".png";
}

/* Запрос к Discord или к боту: [http-код, ответ JSON или null] */
function rt_discord_http($method, $url, $form = null, $headers = [], $timeout = 15, $insecure = false) {
    $ch = curl_init($url);
    $opts = [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => $timeout, CURLOPT_CONNECTTIMEOUT => 8,
             CURLOPT_HTTPHEADER => array_merge(["Accept: application/json", "User-Agent: RTeamSite (https://rteam.info, 1.0)"], $headers)];
    if ($form !== null) $opts[CURLOPT_POSTFIELDS] = is_array($form) ? http_build_query($form) : $form;
    if ($insecure) { $opts[CURLOPT_SSL_VERIFYPEER] = false; $opts[CURLOPT_SSL_VERIFYHOST] = 0; }
    curl_setopt_array($ch, $opts);
    $res = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $errno = curl_errno($ch);
    $err = curl_error($ch);
    curl_close($ch);
    if ($res === false) return [0, ["error" => "no_connection", "message" => $err, "errno" => $errno], ""];
    $json = json_decode((string)$res, true);
    return [$code, is_array($json) ? $json : null, (string)$res];
}

/* Ошибки curl, при которых виноват сертификат (у поддомена бота нет своего SSL) */
const RT_CURL_SSL_ERRORS = [35, 51, 53, 54, 58, 59, 60, 64, 66, 77, 80, 82, 83, 90, 91];

/* Запрос к боту. Если у поддомена бота ещё нет SSL-сертификата, повторяем без проверки сертификата:
   бот на своём же адресе, а «Проверить всё» в админ-панели подскажет выпустить сертификат. */
function rt_discord_bot_call($method, $path, $body = null, $timeout = 15, $settings = null) {
    $c = rt_discord_conf($settings);
    if ($c["bot_url"] === "" || $c["api_key"] === "") return [0, ["error" => "not_configured"], ""];
    $h = ["X-Api-Key: " . $c["api_key"]];
    if ($body !== null) $h[] = "Content-Type: application/json";
    $r = rt_discord_http($method, $c["bot_url"] . $path, $body, $h, $timeout);
    if ($r[0] === 0 && in_array((int)($r[1]["errno"] ?? 0), RT_CURL_SSL_ERRORS, true)) {
        $r = rt_discord_http($method, $c["bot_url"] . $path, $body, $h, $timeout, true);
    }
    return $r;
}
/* Ответ бота → массив с ok; ошибка связи — с понятной причиной */
function rt_discord_bot_result($r) {
    [$code, $res] = $r;
    if (is_array($res) && isset($res["ok"])) return $res;
    if (is_array($res) && isset($res["error"])) return ["ok" => false] + $res;
    return ["ok" => false, "error" => $code ? "http_$code" : "no_connection"];
}
/* Понятное объяснение ошибки связи с ботом */
function rt_discord_error_text($r) {
    $e = (string)($r["error"] ?? "");
    $map = [
        "not_configured" => "не указан адрес бота или ключ (админ-панель → «Discord» или discord_config.php)",
        "forbidden"      => "ключ не совпадает: api_key в discord_config.php и в secret.json бота должен быть одинаковым",
        "dm_closed"      => "у человека закрыты ЛС или его нет на сервере",
        "api_key_not_set"=> "в secret.json бота не указан api_key",
    ];
    if (isset($map[$e])) return $map[$e];
    if ($e === "no_connection") return "сайт не может подключиться к адресу бота" . (!empty($r["message"]) ? " (" . $r["message"] . ")" : "") . " — нажмите «Проверить всё», там будет причина";
    if (preg_match('/^http_(\d+)$/', $e, $m)) return "по адресу бота отвечает не бот (HTTP " . $m[1] . ") — нажмите «Проверить всё», там будет причина";
    return $e !== "" ? $e : "ошибка";
}

/* Сообщение в ЛС Discord от бота. $button = ["label" => …, "url" => "https://…"] */
function rt_discord_dm($discord_id, $text, $title = "", $button = null, $settings = null) {
    $c = rt_discord_conf($settings);
    if (!preg_match('/^\d{15,22}$/', (string)$discord_id)) return ["ok" => false, "error" => "bad_user"];
    if ($c["bot_url"] === "" || $c["api_key"] === "") return ["ok" => false, "error" => "not_configured"];
    $body = ["user_id" => (string)$discord_id, "text" => (string)$text];
    if ($title !== "") $body["title"] = $title;
    if (is_array($button) && preg_match('~^https://~', (string)($button["url"] ?? ""))) $body["button"] = $button;
    return rt_discord_bot_result(rt_discord_bot_call("POST", "/dm", json_encode($body, JSON_UNESCAPED_UNICODE), 15, $settings));
}
/* Состояние бота для админ-панели */
function rt_discord_bot_status($settings = null) {
    $c = rt_discord_conf($settings);
    if ($c["bot_url"] === "" || $c["api_key"] === "") return ["ok" => false, "error" => "not_configured"];
    $r = rt_discord_bot_call("GET", "/status", null, 20, $settings);
    return rt_discord_bot_result($r) + ["http" => $r[0]];
}

/* Подробная проверка связи сайта с ботом — строки для «Проверить всё» с причиной и тем, что сделать */
function rt_discord_probe($settings = null) {
    $c = rt_discord_conf($settings);
    $out = [];
    if ($c["bot_url"] === "") return ["❌ Не указан адрес бота (админ-панель → «Discord» → «Адрес бота», например https://discord.rteam.info)"];
    $host = (string)parse_url($c["bot_url"], PHP_URL_HOST);
    $ip = gethostbyname($host);
    if ($ip === $host && !filter_var($host, FILTER_VALIDATE_IP)) {
        return ["❌ Адрес $host не найден в DNS. В Plesk: «Сайты и домены» → «Добавить поддомен» → discord (DNS-запись Plesk создаст сам; если DNS у регистратора — добавьте A-запись discord с IP сайта)."];
    }
    $out[] = "✅ DNS: $host → $ip";
    $r = rt_discord_http("GET", $c["bot_url"] . "/health");
    if ($r[0] === 0 && in_array((int)($r[1]["errno"] ?? 0), RT_CURL_SSL_ERRORS, true)) {
        $out[] = "⚠️ У $host нет своего SSL-сертификата (" . ($r[1]["message"] ?? "") . "). Plesk → $host → «SSL/TLS-сертификаты» → Let's Encrypt. Пока сайт связывается с ботом без проверки сертификата.";
        $r = rt_discord_http("GET", $c["bot_url"] . "/health", null, [], 15, true);
    }
    [$code, $json, $raw] = $r;
    if ($code === 0) {
        $errno = (int)($r[1]["errno"] ?? 0);
        $msg = (string)($r[1]["message"] ?? "");
        if ($errno === 28) $out[] = "❌ $host не ответил за 15 секунд ($msg). Бот, скорее всего, не запускается: Plesk → $host → Node.js → «NPM install», затем «Restart App».";
        elseif ($errno === 7) $out[] = "❌ Сервер не принимает подключения к $host ($msg). Проверьте, что поддомен создан в Plesk и сайт на нём включён.";
        else $out[] = "❌ Сайт не может подключиться к $host: $msg";
        return $out;
    }
    $is_bot = is_array($json) && ($json["service"] ?? "") === "rteam-discord-bot";
    if (!$is_bot) {
        if ($code >= 500 || stripos($raw, "passenger") !== false) {
            $out[] = "❌ Бот падает при запуске (HTTP $code). Plesk → $host → Node.js: нажмите «NPM install», потом «Restart App». Не помогло — переключите Application mode на development, откройте $host в браузере и пришлите текст ошибки.";
        } elseif ($code === 404 || $code === 403 || $code === 200 || $code === 301 || $code === 302) {
            $out[] = "❌ По адресу $host открывается не бот, а обычная страница (HTTP $code): для поддомена не включён Node.js. Plesk → $host → «Node.js»: Application root — папка с index.js, Document root — её папка public, Application startup file — index.js → «Enable Node.js» → «NPM install» → «Restart App».";
        } else {
            $out[] = "❌ По адресу $host отвечает не бот (HTTP $code).";
        }
        return $out;
    }
    $out[] = "✅ Бот запущен на $host (Node.js работает)";
    if (empty($json["online"])) $out[] = "❌ Но бот не подключён к Discord" . (!empty($json["reason"]) ? ": " . $json["reason"] : "") . ". Откройте " . $c["bot_url"] . " в браузере — там написана причина.";
    return $out;
}

/* «Перезапустить бота»: бот перечитывает config.json и заново пишет начальные сообщения
   (кнопка заявок, подсказка в канале идей, правила). Ответ: ["ok" => …, "report" => [["ok", "text"], …]] */
function rt_discord_bot_restart($settings = null) {
    $c = rt_discord_conf($settings);
    if ($c["bot_url"] === "" || $c["api_key"] === "") return ["ok" => false, "error" => "not_configured"];
    return rt_discord_bot_result(rt_discord_bot_call("POST", "/restart", "{}", 60, $settings));
}

/* ---------- Код входа в админ-панель (2FA): Telegram или Discord ---------- */

/* Куда можно прислать код этому пользователю: "tg", "ds" */
function rt_2fa_channels($u, $settings) {
    $out = [];
    if (!empty($u["tg_id"]) && !empty($settings["bot_token"])) $out[] = "tg";
    if (!empty($u["discord_id"]) && rt_discord_bot_ready($settings)) $out[] = "ds";
    return $out;
}
function rt_2fa_label($via) { return $via === "ds" ? "Discord" : "Telegram"; }

/* Отправить код в выбранное место. true — отправлено */
function rt_2fa_deliver($u, $settings, $via, $code) {
    if ($via === "tg") {
        $ch = curl_init("https://api.telegram.org/bot" . $settings["bot_token"] . "/sendMessage");
        curl_setopt_array($ch, [CURLOPT_POST => 1, CURLOPT_RETURNTRANSFER => true, CURLOPT_SSL_VERIFYPEER => false, CURLOPT_TIMEOUT => 10,
            CURLOPT_POSTFIELDS => ['chat_id' => $u["tg_id"], 'parse_mode' => 'HTML',
                'text' => "🔐 Ваш одноразовый код для входа в панель Rteam:\n\n<b>$code</b>\n\nКод действует 10 минут."]]);
        $res = json_decode((string)curl_exec($ch), true);
        curl_close($ch);
        return !empty($res["ok"]);
    }
    if ($via === "ds") {
        $r = rt_discord_dm($u["discord_id"] ?? "", "Ваш одноразовый код для входа в панель RTeam:\n\n**`$code`**\n\nКод действует 10 минут. Никому его не сообщайте — администрация его не спрашивает.", "🔐 Код входа", null, $settings);
        return !empty($r["ok"]);
    }
    return false;
}

/* Начать вход с кодом: создать код и прислать его. $via — куда (пусто — куда выбрал пользователь).
   Если туда не дошло, пробуем другое место. Возвращает, куда отправлено ("" — никуда не дошло). */
function rt_2fa_begin($login, $role, $u, $settings, $via = "") {
    $channels = rt_2fa_channels($u, $settings);
    if (!$channels) return "";
    if (!in_array($via, $channels, true)) $via = in_array($u["2fa_via"] ?? "", $channels, true) ? $u["2fa_via"] : $channels[0];
    $code = (string)random_int(100000, 999999);
    $codes = rt_json_load("2fa_codes.json", []);
    $codes[$login] = $code;
    rt_json_save("2fa_codes.json", $codes);
    $sent = "";
    foreach (array_unique(array_merge([$via], $channels)) as $try) {
        if (rt_2fa_deliver($u, $settings, $try, $code)) { $sent = $try; break; }
    }
    $pending = rt_json_load("2fa_pending.json", []);
    $pending[$login] = ["time" => time(), "tries" => 0, "via" => $sent !== "" ? $sent : $via, "sent" => time(), "resends" => 0, "failed" => $sent === ""];
    rt_json_save("2fa_pending.json", $pending);
    $_SESSION["pending_2fa_user"] = $login;
    $_SESSION["pending_2fa_role"] = $role;
    return $sent;
}
