<?php
/*
 * AI Studio Rteam — настройки и общие функции.
 * Сайт: https://aistudio.rteam.info   Основной ИИ: https://rai.rteam.info
 *
 * ВАЖНО: секрет Google вставляйте только в этот файл НА ХОСТИНГЕ
 * (или в переменную окружения GOOGLE_CLIENT_SECRET). В GitHub его не выкладывайте.
 */

// ====================================================================== настройки
define('STUDIO_URL', 'https://aistudio.rteam.info');
define('RAI_URL', 'https://rai.rteam.info/');                              // основной ИИ
define('RAI_EMBED_URL', 'https://rteaminfo1-source.github.io/rai/');       // чат Rai на GitHub Pages
define('GITHUB_URL', 'https://github.com/rteaminfo1-source/rai');

define('GOOGLE_CLIENT_ID', '40211315152-jq7a91jcqrpu8hkmlqmg1poh6bthgs5j.apps.googleusercontent.com');
define('GOOGLE_CLIENT_SECRET', getenv('GOOGLE_CLIENT_SECRET') ?: 'ВСТАВЬТЕ_СЮДА_СЕКРЕТ_GOCSPX');
define('GOOGLE_REDIRECT_URI', STUDIO_URL . '/google_callback.php');

// Папка с данными (пользователи, черновики). Если хостинг позволяет — вынесите её выше корня сайта.
define('DATA_DIR', __DIR__ . '/data');
// Папка с сайтами пользователей: https://aistudio.rteam.info/sites/<имя>/
define('SITES_DIR', __DIR__ . '/sites');
define('SITES_URL', STUDIO_URL . '/sites/');

define('API_LIMIT_PER_HOUR', 60);

// ====================================================================== сессия
if (session_status() !== PHP_SESSION_ACTIVE) {
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
          || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
    session_name('aistudio');
    session_set_cookie_params([
        'lifetime' => 60 * 60 * 24 * 30, 'path' => '/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Lax',
    ]);
    session_start();
}

if (!function_exists('mb_strlen')) {  // на случай хостинга без mbstring
    function mb_strlen($s) { return strlen(utf8_decode($s)); }
    function mb_substr($s, $start, $len = null) {
        preg_match_all('/./us', $s, $m);
        return implode('', array_slice($m[0], $start, $len));
    }
    function mb_strtolower($s) { return strtolower($s); }
    function mb_strtoupper($s) { return strtoupper($s); }
}

// ====================================================================== помощники
function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

function redirect($url) {
    header('Location: ' . $url);
    exit;
}

function json_path($name) {
    if (!is_dir(DATA_DIR)) {
        mkdir(DATA_DIR, 0750, true);
    }
    return DATA_DIR . '/' . $name;
}

function load_json($name, $default = []) {
    $path = json_path($name);
    if (!is_file($path)) {
        return $default;
    }
    $data = json_decode((string)file_get_contents($path), true);
    return is_array($data) ? $data : $default;
}

function save_json($name, $data) {
    $path = json_path($name);
    $dir = dirname($path);
    if (!is_dir($dir)) {
        mkdir($dir, 0750, true);
    }
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
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
    }
    return $_SESSION['csrf'];
}

function csrf_ok() {
    $given = $_POST['csrf'] ?? ($_SERVER['HTTP_X_CSRF_TOKEN'] ?? '');
    return !empty($_SESSION['csrf']) && is_string($given) && hash_equals($_SESSION['csrf'], $given);
}

function client_ip() {
    return $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
}

/** Не больше $limit событий за $window секунд для ключа $key. */
function rate_limited($key, $limit, $window) {
    return update_json('ratelimit.json', function (&$all) use ($key, $limit, $window) {
        $now = time();
        foreach ($all as $k => $hits) {  // чистим старое
            $all[$k] = array_values(array_filter($hits, function ($t) use ($now, $window) { return $now - $t < 3600 * 24; }));
            if (!$all[$k]) unset($all[$k]);
        }
        $hits = array_values(array_filter($all[$key] ?? [], function ($t) use ($now, $window) { return $now - $t < $window; }));
        $hits[] = $now;
        $all[$key] = $hits;
        return count($hits) > $limit;
    });
}

// ====================================================================== пользователи
const RESERVED_NAMES = ['admin', 'api', 'data', 'sites', 'www', 'assets', 'studio', 'rai', 'root', 'test', 'mail', 'support'];

/** Имя пользователя = имя папки его сайта: 3–20 символов, латиница, цифры, дефис. */
function valid_username($name) {
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
    $name = $_SESSION['user'] ?? null;
    if (!$name) return null;
    $users = users();
    return $users[$name] ?? null;
}

function require_user() {
    $user = current_user();
    if (!$user) redirect('index.php');
    return $user;
}

function login_user($username) {
    session_regenerate_id(true);
    $_SESSION['user'] = $username;
}

function unique_username($base) {
    $base = preg_replace('/[^a-z0-9-]/', '', strtolower((string)$base));
    $base = trim(substr($base, 0, 16), '-');
    if (strlen($base) < 3) $base = 'user' . $base;
    $users = users();
    $name = $base;
    $n = 1;
    while (isset($users[$name]) || !valid_username($name)) {
        $n++;
        $name = $base . $n;
    }
    return $name;
}

function create_user($username, $fields) {
    return update_json('users.json', function (&$users) use ($username, $fields) {
        $users[$username] = array_merge([
            'username' => $username, 'name' => $username, 'email' => null, 'password' => null,
            'google_id' => null, 'avatar' => null, 'created' => time(), 'api_keys' => [],
        ], $fields);
        return $users[$username];
    });
}

function site_url($username) { return SITES_URL . rawurlencode($username) . '/'; }
function site_file($username) { return SITES_DIR . '/' . $username . '/index.html'; }

// ====================================================================== API-ключи
// Ключ показывается пользователю один раз, а хранится только его хеш — как пароль.
function api_key_create($username, $label = '') {
    $key = 'rai_' . bin2hex(random_bytes(20));
    update_json('users.json', function (&$users) use ($username, $key, $label) {
        $users[$username]['api_keys'][] = [
            'id' => bin2hex(random_bytes(6)), 'hash' => hash('sha256', $key), 'prefix' => substr($key, 0, 10),
            'label' => mb_substr((string)$label, 0, 40), 'created' => time(), 'last_used' => null,
        ];
        $users[$username]['api_keys'] = array_slice($users[$username]['api_keys'], -5);  // не больше 5 ключей
    });
    return $key;
}

function api_key_revoke($username, $id) {
    update_json('users.json', function (&$users) use ($username, $id) {
        $users[$username]['api_keys'] = array_values(array_filter($users[$username]['api_keys'] ?? [],
            function ($k) use ($id) { return $k['id'] !== $id; }));
    });
}

/** Найти пользователя по ключу (и отметить время использования). */
function api_user_by_key($key) {
    if (!is_string($key) || strpos($key, 'rai_') !== 0) return null;
    $hash = hash('sha256', $key);
    return update_json('users.json', function (&$users) use ($hash) {
        foreach ($users as $name => $u) {
            foreach ($u['api_keys'] ?? [] as $i => $k) {
                if (hash_equals($k['hash'], $hash)) {
                    $users[$name]['api_keys'][$i]['last_used'] = time();
                    return $users[$name];
                }
            }
        }
        return null;
    });
}
