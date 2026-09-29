<?php
/* Кто вошёл (для страницы Rai). Ответ — JSON. */
require __DIR__ . '/config.php';
$user = current_user();
json_out([
    'user' => $user ? ['login' => $user['login'], 'name' => $user['name'], 'email' => $user['email'], 'avatar' => $user['avatar']] : null,
    'csrf' => csrf_token(), 'login' => sso_ready() ? 'sso_start.php' : null,
    'register' => RTEAM_URL . '/login.php?tab=register', 'account' => RTEAM_URL . '/account.php',
]);
