<?php
/* Возврат от Google. В Google Cloud Console → Authorized redirect URIs: https://rteam.info/google_callback.php */
require __DIR__ . '/config.php';

function g_request($url, $post = null, $headers = []) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_TIMEOUT => 15,
                                CURLOPT_HTTPHEADER => $headers, CURLOPT_SSL_VERIFYPEER => true]);
        if ($post !== null) {
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($post));
        }
        $res = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
    } else {  // хостинг без curl
        $opts = ['http' => ['method' => $post !== null ? 'POST' : 'GET', 'timeout' => 15, 'ignore_errors' => true,
                            'header' => implode("\r\n", array_merge($headers, $post !== null ? ['Content-Type: application/x-www-form-urlencoded'] : []))]];
        if ($post !== null) $opts['http']['content'] = http_build_query($post);
        $res = @file_get_contents($url, false, stream_context_create($opts));
        $code = isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m) ? (int)$m[1] : 0;
    }
    if ($res === false || $code < 200 || $code >= 300) return null;
    $data = json_decode($res, true);
    return is_array($data) ? $data : null;
}

$state = $_SESSION['google_state'] ?? '';
$link = !empty($_SESSION['google_link']);
unset($_SESSION['google_state'], $_SESSION['google_link']);
$back = $link ? 'account.php' : 'login.php';
if (!empty($_GET['error'])) redirect($back . '?error=google_cancel');
if ($state === '' || !hash_equals($state, (string)($_GET['state'] ?? '')) || empty($_GET['code'])) redirect($back . '?error=google');

$token = g_request('https://oauth2.googleapis.com/token', [
    'code' => $_GET['code'], 'client_id' => GOOGLE_CLIENT_ID, 'client_secret' => GOOGLE_CLIENT_SECRET,
    'redirect_uri' => GOOGLE_REDIRECT_URI, 'grant_type' => 'authorization_code',
]);
if (empty($token['access_token'])) redirect($back . '?error=google');
$p = g_request('https://www.googleapis.com/oauth2/v3/userinfo', null, ['Authorization: Bearer ' . $token['access_token']]);
if (empty($p['sub'])) redirect($back . '?error=google');

$gid = (string)$p['sub'];
$email = !empty($p['email_verified']) ? strtolower($p['email'] ?? '') : '';
$owner = find_user('google_id', $gid);

// Привязка Google к уже открытому аккаунту
$me = current_user();
if ($link && $me) {
    if ($owner && $owner['login'] !== $me['login']) redirect('account.php?error=google_taken');
    update_json('users.json', function (&$users) use ($me, $gid, $p) {
        $users[$me['login']]['google_id'] = $gid;
        $users[$me['login']]['avatar'] = $p['picture'] ?? null;
    });
    sync_push('update', users()[$me['login']]);
    redirect('account.php?ok=google');
}

$next = safe_next($_SESSION['next'] ?? 'account.php');
unset($_SESSION['next']);
$user = $owner ?: ($email !== '' ? find_user('email', $email) : null);
if ($user) {
    update_json('users.json', function (&$users) use ($user, $gid, $p) {
        $users[$user['login']]['google_id'] = $gid;
        $users[$user['login']]['avatar'] = $p['picture'] ?? null;
    });
    login_user($user['login']);
    redirect($next);
}
$login = unique_login($email !== '' ? strtok($email, '@') : ($p['given_name'] ?? 'user'));
create_user($login, ['name' => $p['name'] ?? $login, 'email' => $email ?: null, 'google_id' => $gid, 'avatar' => $p['picture'] ?? null]);
$_SESSION['flash'] = 'Аккаунт создан через Google. Ваш логин: ' . $login . '.';
login_user($login);
redirect($next);
