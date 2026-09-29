<?php
/* Вход в AI Studio через Google: отправляем на страницу выбора аккаунта. */
require __DIR__ . '/config.php';

if (GOOGLE_CLIENT_SECRET === '' || strpos(GOOGLE_CLIENT_SECRET, 'ВСТАВЬТЕ') === 0) redirect('index.php?error=google_off');
$state = bin2hex(random_bytes(16));
$_SESSION['google_state'] = $state;
redirect('https://accounts.google.com/o/oauth2/v2/auth?' . http_build_query([
    'client_id' => GOOGLE_CLIENT_ID, 'redirect_uri' => GOOGLE_REDIRECT_URI, 'response_type' => 'code',
    'scope' => 'openid email profile', 'state' => $state, 'prompt' => 'select_account',
]));
