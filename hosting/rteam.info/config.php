<?php
/*
 * Rteam — основной сайт: регистрация, вход (в том числе через Google), личный кабинет
 * и единый вход (SSO) в AI Studio.  https://rteam.info
 *
 * ВАЖНО: секреты (GOOGLE_CLIENT_SECRET и SSO_SECRET) вписывайте только в этот файл НА ХОСТИНГЕ
 * или задавайте переменными окружения. В GitHub их не выкладывайте.
 */

// ====================================================================== настройки
define('SITE_URL', getenv('RTEAM_URL') ?: 'https://rteam.info');
define('RAI_URL', 'https://rai.rteam.info/');                         // основной ИИ
define('RAI_CODE_URL', 'https://rai.rteam.info/#code');               // Rai, вкладка Code
define('STUDIO_URL', getenv('STUDIO_URL') ?: 'https://aistudio.rteam.info');
define('GITHUB_URL', 'https://github.com/rteaminfo1-source/rai');

define('GOOGLE_CLIENT_ID', '40211315152-jq7a91jcqrpu8hkmlqmg1poh6bthgs5j.apps.googleusercontent.com');
define('GOOGLE_CLIENT_SECRET', getenv('GOOGLE_CLIENT_SECRET') ?: 'ВСТАВЬТЕ_СЮДА_СЕКРЕТ_GOCSPX');
// Этот адрес должен быть в Google Cloud Console → Credentials → Authorized redirect URIs
define('GOOGLE_REDIRECT_URI', SITE_URL . '/google_callback.php');

// Общий секрет единого входа: ОДИНАКОВАЯ длинная случайная строка здесь и в config.php AI Studio.
define('SSO_SECRET', getenv('RTEAM_SSO_SECRET') ?: 'ВСТАВЬТЕ_ОДИНАКОВУЮ_СЛУЧАЙНУЮ_СТРОКУ');
// Сайты, которые могут входить через аккаунт Rteam, и куда им возвращать пользователя
const SSO_CLIENTS = [
    'aistudio' => ['name' => 'AI Studio', 'callback' => STUDIO_URL . '/sso_callback.php'],
];

// Папка с данными (пользователи). Если хостинг позволяет — вынесите её выше корня сайта.
define('DATA_DIR', __DIR__ . '/data');

// ====================================================================== сессия
if (session_status() !== PHP_SESSION_ACTIVE) {
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
          || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
    session_name('rteam');
    session_set_cookie_params([
        'lifetime' => 60 * 60 * 24 * 30, 'path' => '/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Lax',
    ]);
    session_start();
}
header('X-Frame-Options: SAMEORIGIN');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: strict-origin-when-cross-origin');

if (!function_exists('mb_strlen')) {  // на случай хостинга без mbstring
    function mb_strlen($s) { return strlen(utf8_decode($s)); }
    function mb_substr($s, $start, $len = null) {
        preg_match_all('/./us', $s, $m);
        return implode('', array_slice($m[0], $start, $len));
    }
    function mb_strtoupper($s) { return strtoupper($s); }
}

// ====================================================================== помощники
function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

function redirect($url) {
    header('Location: ' . $url);
    exit;
}

function json_path($name) {
    if (!is_dir(DATA_DIR)) mkdir(DATA_DIR, 0750, true);
    return DATA_DIR . '/' . $name;
}

function load_json($name, $default = []) {
    $path = json_path($name);
    if (!is_file($path)) return $default;
    $data = json_decode((string)file_get_contents($path), true);
    return is_array($data) ? $data : $default;
}

function save_json($name, $data) {
    $path = json_path($name);
    $tmp = $path . '.' . bin2hex(random_bytes(4)) . '.tmp';
    file_put_contents($tmp, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
    rename($tmp, $path);
}

/** Изменить JSON-файл под блокировкой: $fn получает данные по ссылке. */
function update_json($name, callable $fn, $default = []) {
    $lock = fopen(json_path($name . '.lock'), 'c');
    flock($lock, LOCK_EX);
    $data = load_json($name, $default);
    $result = $fn($data);
    save_json($name, $data);
    flock($lock, LOCK_UN);
    fclose($lock);
    return $result;
}

function csrf_token() {
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(16));
    return $_SESSION['csrf'];
}

function csrf_ok() {
    $given = $_POST['csrf'] ?? '';
    return !empty($_SESSION['csrf']) && is_string($given) && hash_equals($_SESSION['csrf'], $given);
}

function client_ip() { return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0'; }

/** Не больше $limit событий за $window секунд для ключа $key. */
function rate_limited($key, $limit, $window) {
    return update_json('ratelimit.json', function (&$all) use ($key, $limit, $window) {
        $now = time();
        foreach ($all as $k => $hits) {
            $all[$k] = array_values(array_filter($hits, function ($t) use ($now) { return $now - $t < 86400; }));
            if (!$all[$k]) unset($all[$k]);
        }
        $hits = array_values(array_filter($all[$key] ?? [], function ($t) use ($now, $window) { return $now - $t < $window; }));
        $hits[] = $now;
        $all[$key] = $hits;
        return count($hits) > $limit;
    });
}

// ====================================================================== пользователи
const RESERVED_NAMES = ['admin', 'api', 'data', 'sites', 'www', 'assets', 'studio', 'rai', 'root', 'test', 'mail', 'support', 'rteam'];

/** Логин: 3–20 символов, латиница в нижнем регистре, цифры, дефис. В AI Studio он же — адрес сайта. */
function valid_login($name) {
    return is_string($name) && preg_match('/^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$/', $name)
        && !in_array($name, RESERVED_NAMES, true) && strpos($name, '--') === false;
}

function users() { return load_json('users.json'); }

function find_user($field, $value) {
    if ($value === '' || $value === null) return null;
    foreach (users() as $u) {
        if (isset($u[$field]) && strcasecmp((string)$u[$field], (string)$value) === 0) return $u;
    }
    return null;
}

function current_user() {
    $login = $_SESSION['user'] ?? null;
    if (!$login) return null;
    return users()[$login] ?? null;
}

function require_user() {
    $user = current_user();
    if (!$user) redirect('login.php?next=' . rawurlencode(basename($_SERVER['SCRIPT_NAME']) . (empty($_SERVER['QUERY_STRING']) ? '' : '?' . $_SERVER['QUERY_STRING'])));
    return $user;
}

function login_user($login) {
    session_regenerate_id(true);
    $_SESSION['user'] = $login;
    update_json('users.json', function (&$users) use ($login) {
        if (isset($users[$login])) $users[$login]['last_login'] = time();
    });
}

function unique_login($base) {
    $base = preg_replace('/[^a-z0-9-]/', '', strtolower((string)$base));
    $base = trim(substr($base, 0, 16), '-');
    if (strlen($base) < 3) $base = 'user' . $base;
    $users = users();
    $name = $base;
    $n = 1;
    while (isset($users[$name]) || !valid_login($name)) {
        $n++;
        $name = $base . $n;
    }
    return $name;
}

function create_user($login, $fields) {
    return update_json('users.json', function (&$users) use ($login, $fields) {
        $users[$login] = array_merge([
            'login' => $login, 'name' => $login, 'email' => null, 'password' => null,
            'google_id' => null, 'avatar' => null, 'created' => time(), 'last_login' => null,
        ], $fields);
        return $users[$login];
    });
}

/** Куда вернуться после входа: только страницы этого сайта (без открытых редиректов). */
function safe_next($next) {
    $next = (string)$next;
    return preg_match('#^[a-z_]+\.php(\?[A-Za-z0-9_=&%.\-]*)?$#', $next) ? $next : 'account.php';
}

// ====================================================================== единый вход (SSO)
function b64url($s) { return rtrim(strtr(base64_encode($s), '+/', '-_'), '='); }

function sso_ready() { return SSO_SECRET !== '' && strpos(SSO_SECRET, 'ВСТАВЬТЕ') !== 0 && strlen(SSO_SECRET) >= 32; }

/** Подписанный пропуск для сайта-клиента: действует 2 минуты и привязан к его одноразовому state. */
function sso_token($user, $client, $state) {
    $body = b64url(json_encode([
        'sub' => $user['login'], 'name' => $user['name'], 'email' => $user['email'], 'avatar' => $user['avatar'],
        'aud' => $client, 'nonce' => $state, 'iat' => time(), 'exp' => time() + 120,
    ], JSON_UNESCAPED_UNICODE));
    return $body . '.' . b64url(hash_hmac('sha256', $body, SSO_SECRET, true));
}

function google_ready() { return GOOGLE_CLIENT_SECRET !== '' && strpos(GOOGLE_CLIENT_SECRET, 'ВСТАВЬТЕ') !== 0; }

function avatar_html($user, $class = 'ava') {
    $initial = mb_strtoupper(mb_substr($user['name'] ?: $user['login'], 0, 1));
    return '<span class="' . h($class) . '">' . (!empty($user['avatar'])
        ? '<img alt="" src="' . h($user['avatar']) . '" referrerpolicy="no-referrer">' : h($initial)) . '</span>';
}

/** Шапка и подвал страниц (общие). */
function page_head($title, $user = null) {
    ?><!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= h($title) ?></title>
<meta name="description" content="Rteam: свой ИИ Rai, Rai Code для программирования и AI Studio для сайтов. Один аккаунт для всех сервисов.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23e10600'/%3E%3Ctext x='16' y='23' font-size='19' font-family='Arial' font-weight='900' text-anchor='middle' fill='white'%3ER%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@700;800&family=Onest:wght@400;500;600;700&family=JetBrains+Mono&display=swap">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<header class="topbar">
  <a class="brand" href="index.php">R<span>team</span></a>
  <nav aria-label="Сервисы">
    <a href="<?= h(RAI_URL) ?>">Rai</a>
    <a href="<?= h(RAI_CODE_URL) ?>">Code</a>
    <a href="<?= h(STUDIO_URL . ($user ? '/sso_start.php' : '/')) ?>">AI Studio</a>
    <a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>
    <?php if ($user): ?>
      <a class="me" href="account.php"><?= avatar_html($user) ?><span><?= h($user['name'] ?: $user['login']) ?></span></a>
    <?php else: ?>
      <a class="btn small" href="login.php">Войти</a>
    <?php endif; ?>
  </nav>
</header>
<?php
}

function page_foot() {
    ?>
<footer class="foot"><span>© <?= date('Y') ?> Rteam</span><a href="<?= h(RAI_URL) ?>">rai.rteam.info</a>
  <a href="<?= h(STUDIO_URL) ?>/">aistudio.rteam.info</a><a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a></footer>
</body>
</html>
<?php
}
