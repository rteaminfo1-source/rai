<?php
/* Вход через Google: отправляем на страницу выбора аккаунта Google. ?link=1 — привязать к текущему аккаунту. */
require __DIR__ . '/config.php';

if (!google_ready()) redirect('login.php?error=google_off');
$state = bin2hex(random_bytes(16));
$_SESSION['google_state'] = $state;
$_SESSION['google_link'] = !empty($_GET['link']) && current_user() ? 1 : 0;
redirect('https://accounts.google.com/o/oauth2/v2/auth?' . http_build_query([
    'client_id' => GOOGLE_CLIENT_ID, 'redirect_uri' => GOOGLE_REDIRECT_URI, 'response_type' => 'code',
    'scope' => 'openid email profile', 'state' => $state, 'prompt' => 'select_account',
    // ответ — после # в адресе: его не видит сервер, и защита хостинга не блокирует ссылки, которые Google туда дописывает
    'response_mode' => 'fragment',
]));
