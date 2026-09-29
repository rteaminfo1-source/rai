<?php
/*
 * Rai на rai.rteam.info — вход через аккаунт Rteam (единый вход) и сохранение чатов в аккаунте.
 * Сам ИИ работает в браузере (Python через Pyodide), PHP нужен только для аккаунта и чатов.
 *
 * ВАЖНО: SSO_SECRET — та же строка, что в config.php сайтов rteam.info и aistudio.rteam.info.
 * Вписывайте её только НА ХОСТИНГЕ (или в переменную окружения RTEAM_SSO_SECRET), не в GitHub.
 */

define('RAI_URL', getenv('RAI_URL') ?: 'https://rai.rteam.info');
define('RTEAM_URL', getenv('RTEAM_URL') ?: 'https://rteam.info');
define('SSO_SECRET', getenv('RTEAM_SSO_SECRET') ?: 'ВСТАВЬТЕ_ОДИНАКОВУЮ_СЛУЧАЙНУЮ_СТРОКУ');
define('DATA_DIR', __DIR__ . '/data');
define('CHATS_MAX_BYTES', 4 * 1024 * 1024);  // чаты одного человека (со скриншотами)

if (session_status() !== PHP_SESSION_ACTIVE) {
    $https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
    session_name('rai');
    session_set_cookie_params(['lifetime' => 60 * 60 * 24 * 30, 'path' => '/', 'secure' => $https, 'httponly' => true, 'samesite' => 'Lax']);
    session_start();
}
header('X-Content-Type-Options: nosniff');

function redirect($url) { header('Location: ' . $url); exit; }

function json_out($data, $code = 200) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
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

function data_path($name) {
    $path = DATA_DIR . '/' . $name . '.php';
    if (!is_dir(dirname($path))) mkdir(dirname($path), 0750, true);
    return $path;
}

function load_json($name, $default = []) {
    $path = data_path($name);
    if (!is_file($path)) return $default;
    $data = json_decode(read_data_file($path), true);
    return is_array($data) ? $data : $default;
}

function save_json($name, $data) {
    $path = data_path($name);
    $tmp = substr($path, 0, -4) . '.' . bin2hex(random_bytes(4)) . '.tmp.php';
    file_put_contents($tmp, DATA_GUARD . json_encode($data, JSON_UNESCAPED_UNICODE), LOCK_EX);
    rename($tmp, $path);
}

function update_json($name, callable $fn, $default = []) {
    $lock = fopen(data_path($name . '.lock'), 'c');
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
    $given = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? ($_POST['csrf'] ?? '');
    return !empty($_SESSION['csrf']) && is_string($given) && hash_equals($_SESSION['csrf'], $given);
}

/** Логины Rteam: латиница, цифры, дефис — годятся как имя файла. */
function valid_login($login) { return is_string($login) && preg_match('/^[a-z0-9][a-z0-9-]{1,18}[a-z0-9]$/', $login); }

function current_user() {
    $login = $_SESSION['user'] ?? null;
    if (!$login) return null;
    return load_json('users.json')[$login] ?? null;
}

// ====================================================================== единый вход и синхронизация
function b64url_decode($s) { return base64_decode(strtr($s, '-_', '+/') . str_repeat('=', (4 - strlen($s) % 4) % 4)); }
function sso_ready() { return SSO_SECRET !== '' && strpos(SSO_SECRET, 'ВСТАВЬТЕ') !== 0 && strlen(SSO_SECRET) >= 32; }

function sso_verify($token, $state) {
    if (!sso_ready() || !is_string($token) || substr_count($token, '.') !== 1 || $state === '') return null;
    list($body, $sig) = explode('.', $token);
    $expected = rtrim(strtr(base64_encode(hash_hmac('sha256', $body, SSO_SECRET, true)), '+/', '-_'), '=');
    if (!hash_equals($expected, $sig)) return null;
    $p = json_decode((string)b64url_decode($body), true);
    if (!is_array($p) || ($p['aud'] ?? '') !== 'rai' || !hash_equals($state, (string)($p['nonce'] ?? ''))) return null;
    if ((int)($p['exp'] ?? 0) < time() || (int)($p['iat'] ?? 0) > time() + 60 || !valid_login($p['sub'] ?? '')) return null;
    return $p;
}

/** Проверить подписанное сообщение от rteam.info (изменение профиля, удаление аккаунта). */
function sync_verify($body, $sig) {
    if (!sso_ready() || !is_string($sig) || !hash_equals(hash_hmac('sha256', $body, SSO_SECRET), $sig)) return null;
    $m = json_decode($body, true);
    if (!is_array($m) || abs(time() - (int)($m['time'] ?? 0)) > 300 || empty($m['nonce']) || !valid_login($m['user']['login'] ?? '')) return null;
    $fresh = update_json('nonces.json', function (&$seen) use ($m) {  // одно сообщение — один раз
        $now = time();
        foreach ($seen as $n => $t) if ($now - $t > 900) unset($seen[$n]);
        if (isset($seen[$m['nonce']])) return false;
        $seen[$m['nonce']] = $now;
        return true;
    });
    return $fresh ? $m : null;
}
