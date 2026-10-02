<?php
require __DIR__ . '/config.php';
require_once __DIR__ . '/_roles.php'; // роли, права и настройки Discord

/* ВХОД, РЕГИСТРАЦИЯ И ПРИВЯЗКА ЧЕРЕЗ DISCORD (OAuth2)
   discord_auth.php?mode=login | register | link → Discord спрашивает разрешение → возвращает сюда с ?code=…
   - login / register: аккаунт с этим Discord есть — входим (сотрудникам с Telegram — ещё код из Telegram),
     нет — создаём новый аккаунт и входим;
   - link: привязываем Discord к аккаунту, в который уже вошли (cabinet.php → «Привязки»).
   В Discord Developer Portal → OAuth2 → Redirects должен быть адрес этой страницы, например
   https://rteam.info/discord_auth.php (и https://www.rteam.info/discord_auth.php, если сайт открывается и с www).
   Запрос привязан к браузеру (state в файле + cookie): чужую ссылку возврата подсунуть нельзя. */

header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");

const DS_STATE_FILE = "discord_states.json";
const DS_STATE_TTL = 600;

$settings = load_json("settings.json", []);
$conf = rt_discord_conf($settings);
$redirect_uri = rt_discord_redirect_uri($conf);
$https = (!empty($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off") || ($_SERVER["HTTP_X_FORWARDED_PROTO"] ?? "") === "https";

function ds_go($url) { header("Location: " . $url); exit; }
function ds_fail($mode, $err) {
    ds_go($mode === "link" ? "cabinet.php?discord_error=" . urlencode($err) . "#links" : "login.php?discord_error=" . urlencode($err));
}
function ds_cookie($value, $https) {
    setcookie("rt_ds_state", $value, ["expires" => $value === "" ? time() - 3600 : time() + DS_STATE_TTL, "path" => "/",
                                       "secure" => $https, "httponly" => true, "samesite" => "Lax"]);
}

$mode = in_array($_GET["mode"] ?? "", ["login", "register", "link"], true) ? $_GET["mode"] : "login";
if (!rt_discord_login_ready($settings)) ds_fail($mode, "off");

/* ---------- 1. Начало: отправляем на Discord ---------- */
if (!isset($_GET["code"]) && !isset($_GET["error"])) {
    // Discord вернёт человека на адрес из настроек: если он открыл сайт по другому адресу (www),
    // сначала переходим туда же, иначе cookie и вход останутся на другом адресе
    $want = parse_url($redirect_uri, PHP_URL_HOST);
    if ($want && strcasecmp($want, (string)($_SERVER["HTTP_HOST"] ?? "")) !== 0 && !isset($_GET["moved"])) {
        ds_go(preg_replace('~/discord_auth\.php.*$~', "", $redirect_uri) . "/discord_auth.php?mode=" . urlencode($mode) . "&moved=1");
    }
    $me = (string)($_SESSION["user"] ?? "");
    if ($mode === "link" && $me === "") ds_go("login.php?discord_hint=1");
    if ($mode !== "link" && $me !== "") ds_go("index.php");

    $state = bin2hex(random_bytes(16));
    $states = load_json(DS_STATE_FILE, []);
    foreach ($states as $k => $s) if (time() - (int)($s["time"] ?? 0) > DS_STATE_TTL) unset($states[$k]);
    $states[$state] = ["mode" => $mode, "login" => $mode === "link" ? $me : "", "time" => time()];
    save_json(DS_STATE_FILE, $states);
    ds_cookie($state, $https);
    $_SESSION["discord_state"] = $state;

    ds_go($conf["oauth"] . "?" . http_build_query([
        "client_id" => $conf["client_id"], "redirect_uri" => $redirect_uri, "response_type" => "code",
        "scope" => "identify", "state" => $state, "prompt" => "none",
    ]));
}

/* ---------- 2. Возврат с Discord ---------- */
$state = (string)($_GET["state"] ?? "");
$states = load_json(DS_STATE_FILE, []);
$st = ($state !== "" && isset($states[$state])) ? $states[$state] : null;
if ($st) { unset($states[$state]); save_json(DS_STATE_FILE, $states); } // ссылка одноразовая
$mode = $st["mode"] ?? "login";
$bound = $state !== "" && (hash_equals($state, (string)($_COOKIE["rt_ds_state"] ?? "")) || hash_equals($state, (string)($_SESSION["discord_state"] ?? "")));
ds_cookie("", $https);
unset($_SESSION["discord_state"]);

if (!$st || !$bound || time() - (int)($st["time"] ?? 0) > DS_STATE_TTL) ds_fail($mode, "state");
if (isset($_GET["error"])) ds_fail($mode, "denied");

[$code, $token] = rt_discord_http("POST", $conf["api"] . "/oauth2/token", [
    "client_id" => $conf["client_id"], "client_secret" => $conf["client_secret"], "grant_type" => "authorization_code",
    "code" => (string)$_GET["code"], "redirect_uri" => $redirect_uri,
], ["Content-Type: application/x-www-form-urlencoded"]);
if (empty($token["access_token"])) {
    rteam_log("login", "Discord: не удалось получить токен (HTTP $code: " . mb_substr((string)($token["error_description"] ?? $token["error"] ?? $token["message"] ?? ""), 0, 120) . ")");
    ds_fail($mode, "failed");
}
[$code, $ds] = rt_discord_http("GET", $conf["api"] . "/users/@me", null, ["Authorization: Bearer " . $token["access_token"]]);
if (empty($ds["id"]) || !preg_match('/^\d{15,22}$/', (string)$ds["id"])) ds_fail($mode, "failed");

$did = (string)$ds["id"];
/* Данные Discord, которые храним: ID, ник, имя, аватар. Токен Discord не сохраняем. */
$apply = function (array $u) use ($ds, $did) {
    $u["discord_id"] = $did;
    $u["discord_username"] = mb_substr((string)($ds["username"] ?? ""), 0, 40);
    $u["discord_name"] = mb_substr((string)($ds["global_name"] ?? $ds["username"] ?? ""), 0, 60);
    $u["discord_avatar"] = preg_match('/^(a_)?[0-9a-f]{32}$/', (string)($ds["avatar"] ?? "")) ? $ds["avatar"] : "";
    if (trim((string)($u["discord"] ?? "")) === "") $u["discord"] = $u["discord_username"];
    return $u;
};

$users = load_json("users.json", []);
$owner = null;
foreach ($users as $l => $u) {
    if (is_array($u) && (string)($u["discord_id"] ?? "") === $did) { $owner = (string)$l; break; }
}

/* Привязка к аккаунту, в который вошли */
if ($mode === "link") {
    $login = (string)($st["login"] ?? "");
    $now = (string)($_SESSION["user"] ?? "");
    if ($login === "" || !isset($users[$login]) || ($now !== "" && $now !== $login)) ds_fail("link", "failed");
    if ($owner !== null && $owner !== $login) ds_fail("link", "already_linked");
    $users[$login] = $apply($users[$login]);
    save_json("users.json", $users);
    rteam_log("profile", "Привязан Discord: $login");
    rt_discord_dm($did, "Discord привязан к аккаунту **" . $login . "** на rteam.info. Сюда будут приходить коды входа и уведомления сайта.\n\nЕсли это были не вы — отвяжите Discord в кабинете и смените пароль.", "✅ Аккаунт привязан", ["label" => "Открыть кабинет", "url" => rt_site_url() . "/cabinet.php#links"], $settings);
    ds_go("cabinet.php?discord_linked=1#links");
}

/* Вход: аккаунт с этим Discord уже есть */
if ($owner !== null) {
    $login = $owner;
    $users[$login] = $apply($users[$login]);
    save_json("users.json", $users);
    $role = $users[$login]["role"] ?? "Пользователь";
    // Вход через Discord сам подтверждает Discord, поэтому сотрудникам с привязанным Telegram — ещё код из Telegram
    $is_panel_role = rt_is_staff($role, $login) || in_array($role, rteam_admin_roles());
    if ($is_panel_role && in_array("tg", rt_2fa_channels($users[$login], $settings), true)) {
        rt_2fa_begin($login, $role, $users[$login], $settings, "tg");
        ds_go("login.php?step=2fa&u=" . urlencode($login));
    }
    rteam_login_user($login, $role);
    rt_track_login_ip($login);
    rteam_log("login", "Вход через Discord: $login");
    ds_go(rteam_post_login_redirect());
}

/* Регистрация: новый аккаунт. Логин — из ника Discord (латиница, цифры, «_» и «.»), если занят — с цифрами */
$base = strtolower(preg_replace('/[^a-z0-9_.]/i', '', (string)($ds["username"] ?? "")));
if (strlen($base) < 3) $base = "ds_" . substr($did, -6);
$base = substr($base, 0, 28);
$login = $base;
for ($n = 2; isset($users[$login]); $n++) $login = $base . $n;
$users[$login] = $apply(["role" => "Пользователь", "created" => date("Y-m-d H:i:s"), "created_via" => "discord"]);
save_json("users.json", $users);
rteam_log("register", "Регистрация через Discord: $login");
rteam_login_user($login, "Пользователь");
rt_track_login_ip($login);
ds_go("cabinet.php?discord_new=1");
