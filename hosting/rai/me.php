<?php
/* Кто вошёл (для страницы Rai) и куда вести на вход, регистрацию и в кабинет. Ответ — JSON. */
require __DIR__ . '/config.php';
$user = current_user();
json_out([
    'user' => $user ? ['login' => $user['login'], 'name' => $user['name'], 'email' => $user['email'], 'avatar' => $user['avatar']] : null,
    'csrf' => csrf_token(),
    'login' => 'login.php?next=' . rawurlencode('./'),
    'register' => 'login.php?tab=register&next=' . rawurlencode('./'),
    'google' => google_ready() ? 'google_start.php' : null,
    'account' => 'account.php',
    'studio' => STUDIO_URL . '/sso_start.php',
]);
