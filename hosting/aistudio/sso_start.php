<?php
/* «Войти через аккаунт Rai»: отправляем на rai.rteam.info с одноразовым state. */
require __DIR__ . '/config.php';

if (current_user()) redirect('studio.php');
if (!sso_ready()) redirect('index.php?error=sso_off');
$state = bin2hex(random_bytes(16));
$_SESSION['sso_state'] = $state;
redirect(ACCOUNT_URL . '/sso.php?' . http_build_query(['client' => 'aistudio', 'state' => $state]));
