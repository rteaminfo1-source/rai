<?php
/* Вход, регистрация и выход в AI Studio (обычные формы). */
require __DIR__ . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_ok()) redirect('index.php?error=csrf');
$action = $_POST['action'] ?? '';

if ($action === 'logout') {
    $_SESSION = [];
    session_destroy();
    redirect('index.php');
}

if (rate_limited('auth:' . client_ip(), 10, 300)) redirect('index.php?error=too_many');

if ($action === 'register') {
    $username = strtolower(trim((string)($_POST['username'] ?? '')));
    $password = (string)($_POST['password'] ?? '');
    $email = strtolower(trim((string)($_POST['email'] ?? '')));
    $name = trim(mb_substr((string)($_POST['name'] ?? ''), 0, 60));
    if (!valid_username($username)) redirect('index.php?tab=register&error=username');
    if (strlen($password) < 8) redirect('index.php?tab=register&error=password');
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) redirect('index.php?tab=register&error=email');
    if (isset(users()[$username])) redirect('index.php?tab=register&error=taken');
    if ($email !== '' && find_user('email', $email)) redirect('index.php?tab=register&error=email_taken');
    create_user($username, [
        'name' => $name !== '' ? $name : $username, 'email' => $email !== '' ? $email : null,
        'password' => password_hash($password, PASSWORD_DEFAULT),
    ]);
    login_user($username);
    redirect('studio.php?welcome=1');
}

if ($action === 'login') {
    $who = strtolower(trim((string)($_POST['login'] ?? '')));
    $password = (string)($_POST['password'] ?? '');
    $user = strpos($who, '@') !== false ? find_user('email', $who) : (users()[$who] ?? null);
    if (!$user || empty($user['password']) || !password_verify($password, $user['password'])) {
        redirect('index.php?error=' . ($user && empty($user['password']) ? 'google_only' : 'login'));
    }
    login_user($user['username']);
    redirect('studio.php');
}

redirect('index.php');
