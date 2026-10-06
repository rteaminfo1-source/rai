<?php
/* Кто вошёл (для страницы Rai) и куда вести на вход, регистрацию и в кабинет. Ответ — JSON. */
require __DIR__ . '/config.php';
require __DIR__ . '/moderation.php';
require __DIR__ . '/plans.php';
$user = current_user();
json_out([
    'user' => $user ? ['login' => $user['login'], 'name' => $user['name'], 'email' => $user['email'], 'avatar' => $user['avatar'],
                     'role' => user_role_public($user)] : null,
    'csrf' => csrf_token(),
    'login' => 'login.php?next=' . rawurlencode(CHAT_URL),
    'register' => 'login.php?tab=register&next=' . rawurlencode(CHAT_URL),
    'google' => google_ready() ? 'google_start.php' : null,
    'account' => 'account.php',
    'studio' => STUDIO_URL . '/sso_start.php',
    'banned' => rai_ban_public(rai_current_ban($user)),  // заблокирован за нарушение правил — Rai не отвечает
]);
