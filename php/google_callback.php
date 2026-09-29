<?php
/*
 * Возврат после входа через Google (Authorized redirect URI в Google Cloud Console).
 * Нужны из config.php: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI,
 * load_json/save_json, rteam_find_user_by_google_id, rteam_login_user,
 * rteam_unique_login_from_name, rteam_post_login_redirect, rteam_log.
 */
require __DIR__ . '/config.php';

function rteam_google_request($url, $post = null, $headers = []) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_HTTPHEADER     => $headers,
    ]);
    if ($post !== null) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($post));
    }
    $res  = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($res === false || $code < 200 || $code >= 300) {
        return null;
    }
    $data = json_decode($res, true);
    return is_array($data) ? $data : null;
}

function rteam_google_fail($reason) {
    rteam_log('login', 'Вход через Google не удался: ' . $reason);
    header('Location: login.php?oauth_error=1');
    exit;
}

// 0) Пользователь нажал «Отмена» на странице Google
if (!empty($_GET['error'])) {
    rteam_google_fail('отменён пользователем');
}

// 1) Проверка state (защита от CSRF) — одноразовый, сверяем безопасным сравнением
$state = $_SESSION['google_oauth_state'] ?? '';
unset($_SESSION['google_oauth_state']);
if ($state === '' || empty($_GET['state']) || !hash_equals($state, (string)$_GET['state'])) {
    rteam_google_fail('неверный state');
}
if (empty($_GET['code'])) {
    rteam_google_fail('нет кода');
}

// 2) Меняем код на токен
$token = rteam_google_request('https://oauth2.googleapis.com/token', [
    'code'          => $_GET['code'],
    'client_id'     => GOOGLE_CLIENT_ID,
    'client_secret' => GOOGLE_CLIENT_SECRET,
    'redirect_uri'  => GOOGLE_REDIRECT_URI,
    'grant_type'    => 'authorization_code',
], ['Content-Type: application/x-www-form-urlencoded']);
if (empty($token['access_token'])) {
    rteam_google_fail('Google не выдал токен (проверьте секрет и redirect URI)');
}

// 3) Профиль пользователя
$profile = rteam_google_request('https://www.googleapis.com/oauth2/v3/userinfo', null, [
    'Authorization: Bearer ' . $token['access_token'],
]);
if (empty($profile['sub'])) {
    rteam_google_fail('нет профиля');
}

$google_id      = (string)$profile['sub'];
$email_verified = !empty($profile['email_verified']);
$google_email   = $email_verified ? strtolower($profile['email'] ?? '') : '';
$google_name    = $profile['name'] ?? ($google_email !== '' ? explode('@', $google_email)[0] : 'user');
$google_avatar  = $profile['picture'] ?? '';

$users = load_json('users.json', []);

$mode      = $_SESSION['google_oauth_mode'] ?? 'login';
$link_user = $_SESSION['google_oauth_link_user'] ?? null;
unset($_SESSION['google_oauth_mode'], $_SESSION['google_oauth_link_user']);

$existing_login = rteam_find_user_by_google_id($google_id);

/* ---------- Привязка Google к уже открытому аккаунту (кнопка в личном кабинете) ---------- */
if ($mode === 'link') {
    if (empty($link_user) || !isset($users[$link_user])) {
        header('Location: login.php');
        exit;
    }
    if ($existing_login && $existing_login !== $link_user) {
        header('Location: cabinet.php?google_error=already_linked');
        exit;
    }
    $users[$link_user]['google_id']     = $google_id;
    $users[$link_user]['google_email']  = $google_email;
    $users[$link_user]['google_name']   = $google_name;
    $users[$link_user]['google_avatar'] = $google_avatar;
    save_json('users.json', $users);
    rteam_log('profile', "Привязан Google к аккаунту: $link_user ($google_email)");
    header('Location: cabinet.php?google_linked=1');
    exit;
}

/* ---------- Вход ---------- */
if ($existing_login && isset($users[$existing_login])) {
    session_regenerate_id(true);
    rteam_login_user($existing_login, $users[$existing_login]['role'] ?? 'Пользователь');
    rteam_log('login', "Вход через Google: $existing_login");
    header('Location: ' . rteam_post_login_redirect());
    exit;
}

// Аккаунт с той же (подтверждённой Google) почтой — привязываем и входим
$login = null;
if ($google_email !== '') {
    foreach ($users as $u_login => $u_data) {
        $emails = [strtolower($u_data['google_email'] ?? ''), strtolower($u_data['email'] ?? '')];
        if (in_array($google_email, $emails, true)) {
            $login = $u_login;
            break;
        }
    }
}
if ($login) {
    $users[$login]['google_id']     = $google_id;
    $users[$login]['google_email']  = $google_email;
    $users[$login]['google_name']   = $google_name;
    $users[$login]['google_avatar'] = $google_avatar;
    save_json('users.json', $users);
    session_regenerate_id(true);
    rteam_login_user($login, $users[$login]['role'] ?? 'Пользователь');
    rteam_log('login', "Вход через Google (связан по почте): $login");
    header('Location: ' . rteam_post_login_redirect());
    exit;
}

/* ---------- Регистрация нового пользователя через Google ---------- */
$new_login = rteam_unique_login_from_name(strtok($google_email !== '' ? $google_email : $google_name, '@'));
$users[$new_login] = [
    // Входа по паролю у такого аккаунта нет; храним только хеш случайной строки.
    'password'      => password_hash(bin2hex(random_bytes(16)), PASSWORD_DEFAULT),
    'role'          => 'Пользователь',
    'google_id'     => $google_id,
    'google_email'  => $google_email,
    'google_name'   => $google_name,
    'google_avatar' => $google_avatar,
    'display_name'  => $google_name,
];
save_json('users.json', $users);
rteam_log('register', "Регистрация через Google: $new_login ($google_email)");

session_regenerate_id(true);
rteam_login_user($new_login, 'Пользователь');
$redirect = rteam_post_login_redirect();
$redirect .= (strpos($redirect, '?') !== false ? '&' : '?') . 'google_new=1';
header('Location: ' . $redirect);
exit;
