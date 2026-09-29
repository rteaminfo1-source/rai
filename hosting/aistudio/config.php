<?php
/*
 * AI Studio Rteam — настройки и общие функции.
 * Сайт: https://aistudio.rteam.info   Основной ИИ: https://rai.rteam.info
 *
 * Вход — через аккаунт Rteam (https://rteam.info): регистрация, пароль и Google живут там,
 * а сюда приходит подписанный пропуск (единый вход, SSO).
 * ВАЖНО: SSO_SECRET вписывайте только в этот файл НА ХОСТИНГЕ (или в переменную окружения
 * RTEAM_SSO_SECRET) — та же строка, что в config.php сайта rteam.info. В GitHub его не выкладывайте.
 */

// ====================================================================== настройки
define('STUDIO_URL', getenv('STUDIO_URL') ?: 'https://aistudio.rteam.info');
define('RAI_URL', 'https://rai.rteam.info/');                              // основной ИИ
define('RAI_EMBED_URL', 'https://rteaminfo1-source.github.io/rai/');       // чат Rai на GitHub Pages
define('GITHUB_URL', 'https://github.com/rteaminfo1-source/rai');

define('RTEAM_URL', getenv('RTEAM_URL') ?: 'https://rteam.info');                                 // аккаунты Rteam
define('SSO_SECRET', getenv('RTEAM_SSO_SECRET') ?: 'ВСТАВЬТЕ_ОДИНАКОВУЮ_СЛУЧАЙНУЮ_СТРОКУ');

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

// Данные хранятся в .php-файлах: первая строка останавливает PHP, поэтому из браузера их не прочитать
// даже на хостинге, где не работает .htaccess. Внутри — обычный JSON.
const DATA_GUARD = "<?php http_response_code(404); exit; ?>\n";

function read_data_file($path) {
    $raw = (string)file_get_contents($path);
    if (strpos($raw, '<?php') === 0) $raw = (string)substr($raw, strpos($raw, "\n") + 1);
    return $raw;
}

function json_path($name) {
    $path = DATA_DIR . '/' . $name . '.php';
    if (!is_dir(dirname($path))) mkdir(dirname($path), 0750, true);
    return $path;
}

function load_json($name, $default = []) {
    $path = json_path($name);
    if (!is_file($path)) {
        $old = DATA_DIR . '/' . $name;  // файл старого формата (до .php) — читаем его
        if (!is_file($old)) return $default;
        $path = $old;
    }
    $data = json_decode(read_data_file($path), true);
    return is_array($data) ? $data : $default;
}

function save_json($name, $data) {
    $path = json_path($name);
    $tmp = substr($path, 0, -4) . '.' . bin2hex(random_bytes(4)) . '.tmp.php';
    file_put_contents($tmp, DATA_GUARD . json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
    rename($tmp, $path);
    $old = DATA_DIR . '/' . $name;
    if (is_file($old)) @unlink($old);  // старый .json больше не нужен
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

// ====================================================================== единый вход (SSO)
function b64url_decode($s) { return base64_decode(strtr($s, '-_', '+/') . str_repeat('=', (4 - strlen($s) % 4) % 4)); }

function sso_ready() { return SSO_SECRET !== '' && strpos(SSO_SECRET, 'ВСТАВЬТЕ') !== 0 && strlen(SSO_SECRET) >= 32; }

/** Проверить пропуск от rteam.info: подпись, срок, адресата и одноразовый state. Возвращает данные или null. */
function sso_verify($token, $state) {
    if (!sso_ready() || !is_string($token) || substr_count($token, '.') !== 1 || $state === '') return null;
    list($body, $sig) = explode('.', $token);
    $expected = rtrim(strtr(base64_encode(hash_hmac('sha256', $body, SSO_SECRET, true)), '+/', '-_'), '=');
    if (!hash_equals($expected, $sig)) return null;
    $p = json_decode((string)b64url_decode($body), true);
    if (!is_array($p) || ($p['aud'] ?? '') !== 'aistudio' || !hash_equals($state, (string)($p['nonce'] ?? ''))) return null;
    if ((int)($p['exp'] ?? 0) < time() || (int)($p['iat'] ?? 0) > time() + 60 || empty($p['sub'])) return null;
    return $p;
}

/** Сообщение от rteam.info об изменении профиля или удалении аккаунта. */
function sync_verify($body, $sig) {
    if (!sso_ready() || !is_string($sig) || !hash_equals(hash_hmac('sha256', $body, SSO_SECRET), $sig)) return null;
    $m = json_decode($body, true);
    if (!is_array($m) || abs(time() - (int)($m['time'] ?? 0)) > 300 || empty($m['nonce']) || empty($m['user']['login'])) return null;
    $fresh = update_json('nonces.json', function (&$seen) use ($m) {
        $now = time();
        foreach ($seen as $n => $t) if ($now - $t > 900) unset($seen[$n]);
        if (isset($seen[$m['nonce']])) return false;
        $seen[$m['nonce']] = $now;
        return true;
    });
    return $fresh ? $m : null;
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
