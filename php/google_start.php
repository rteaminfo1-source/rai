<?php
require __DIR__ . '/config.php';

// Режим: обычный вход (login) или привязка Google к уже открытому аккаунту (link)
$mode = (($_GET['mode'] ?? '') === 'link') ? 'link' : 'login';

// Привязать Google можно только будучи уже авторизованным в RTeam
if ($mode === 'link' && empty($_SESSION['user'])) {
    header('Location: login.php');
    exit;
}

// CSRF-защита: одноразовый state, сверяется в google_callback.php
$state = bin2hex(random_bytes(16));
$_SESSION['google_oauth_state'] = $state;
$_SESSION['google_oauth_mode']  = $mode;

if ($mode === 'link') {
    // Запоминаем, к какому именно аккаунту привязываем — callback не должен
    // ни искать, ни тем более регистрировать нового пользователя в этом режиме
    $_SESSION['google_oauth_link_user'] = $_SESSION['user'];
} else {
    unset($_SESSION['google_oauth_link_user']);
}

$params = [
    'client_id'     => GOOGLE_CLIENT_ID,
    'redirect_uri'  => GOOGLE_REDIRECT_URI,
    'response_type' => 'code',
    'scope'         => 'openid email profile',
    'state'         => $state,
    'prompt'        => 'select_account',
];

header('Location: https://accounts.google.com/o/oauth2/v2/auth?' . http_build_query($params));
exit;
