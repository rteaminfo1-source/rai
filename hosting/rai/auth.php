<?php
/* Обработчик форм: регистрация, вход, выход, изменение профиля и пароля, удаление аккаунта. */
require __DIR__ . '/config.php';
require __DIR__ . '/moderation.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_ok()) redirect('login.php?error=csrf');
$action = $_POST['action'] ?? '';

function finish_login($login) {
    login_user($login);
    $next = safe_next($_SESSION['next'] ?? './');
    unset($_SESSION['next']);
    redirect($next);
}

if ($action === 'logout') {
    $_SESSION = [];
    session_destroy();
    redirect('./');
}

if ($action === 'register' || $action === 'login') {
    if (rate_limited('auth:' . client_ip(), 10, 300)) redirect('login.php?tab=' . $action . '&error=too_many');
}

if ($action === 'register') {
    $login = strtolower(trim((string)($_POST['login'] ?? '')));
    $password = (string)($_POST['password'] ?? '');
    $email = strtolower(trim((string)($_POST['email'] ?? '')));
    $name = trim(mb_substr((string)($_POST['name'] ?? ''), 0, 60));
    if (!valid_login($login)) redirect('login.php?tab=register&error=username');
    if (strlen($password) < 8) redirect('login.php?tab=register&error=password');
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) redirect('login.php?tab=register&error=email');
    if (isset(users()[$login])) redirect('login.php?tab=register&error=taken');
    if ($email !== '' && find_user('email', $email)) redirect('login.php?tab=register&error=email_taken');
    create_user($login, [
        'name' => $name !== '' ? $name : $login, 'email' => $email !== '' ? $email : null,
        'password' => password_hash($password, PASSWORD_DEFAULT),
    ]);
    $_SESSION['flash'] = 'Аккаунт создан. Добро пожаловать!';
    finish_login($login);
}

if ($action === 'login') {
    $who = strtolower(trim((string)($_POST['login'] ?? '')));
    $password = (string)($_POST['password'] ?? '');
    $user = strpos($who, '@') !== false ? find_user('email', $who) : (users()[$who] ?? null);
    if (!$user || empty($user['password']) || !password_verify($password, $user['password'])) {
        redirect('login.php?error=' . ($user && empty($user['password']) ? 'google_only' : 'login'));
    }
    if (rai_ban_of($user['login'], null)) redirect('login.php?error=banned');  // заблокирован за нарушение правил
    if (password_needs_rehash($user['password'], PASSWORD_DEFAULT)) {
        update_json('users.json', function (&$users) use ($user, $password) {
            $users[$user['login']]['password'] = password_hash($password, PASSWORD_DEFAULT);
        });
    }
    finish_login($user['login']);
}

// ---- дальше — только для вошедших
$user = current_user();
if (!$user) redirect('login.php');
$login = $user['login'];

if ($action === 'profile') {
    $name = trim(mb_substr((string)($_POST['name'] ?? ''), 0, 60));
    $email = strtolower(trim((string)($_POST['email'] ?? '')));
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) redirect('account.php?error=email');
    $other = $email !== '' ? find_user('email', $email) : null;
    if ($other && $other['login'] !== $login) redirect('account.php?error=email_taken');
    update_json('users.json', function (&$users) use ($login, $name, $email) {
        $users[$login]['name'] = $name !== '' ? $name : $login;
        $users[$login]['email'] = $email !== '' ? $email : null;
    });
    sync_push('update', users()[$login]);  // AI Studio и Rai узнают новое имя и почту
    redirect('account.php?ok=profile');
}

if ($action === 'password') {
    if (rate_limited('pass:' . $login, 10, 600)) redirect('account.php?error=too_many');
    $current = (string)($_POST['current'] ?? '');
    $new = (string)($_POST['new'] ?? '');
    if (!empty($user['password']) && !password_verify($current, $user['password'])) redirect('account.php?error=current');
    if (strlen($new) < 8) redirect('account.php?error=password');
    update_json('users.json', function (&$users) use ($login, $new) {
        $users[$login]['password'] = password_hash($new, PASSWORD_DEFAULT);
    });
    session_regenerate_id(true);
    redirect('account.php?ok=password');
}

if ($action === 'unlink_google') {
    if (empty($user['password'])) redirect('account.php?error=need_password');
    update_json('users.json', function (&$users) use ($login) {
        $users[$login]['google_id'] = null;
        $users[$login]['avatar'] = null;
    });
    sync_push('update', users()[$login]);
    redirect('account.php?ok=unlinked');
}

if ($action === 'delete') {
    if (strtolower(trim((string)($_POST['confirm'] ?? ''))) !== $login) redirect('account.php?error=confirm');
    update_json('users.json', function (&$users) use ($login) { unset($users[$login]); });
    $chats = json_path('chats/' . $login . '.json');  // чаты в Rai
    if (is_file($chats)) unlink($chats);
    sync_push('delete', $user);  // и сайт с API-ключами в AI Studio
    $_SESSION = [];
    session_destroy();
    redirect('login.php?error=deleted');
}

redirect('account.php');
