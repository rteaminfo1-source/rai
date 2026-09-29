<?php
/* «Войти через аккаунт Rteam»: на rteam.info за подписанным пропуском. */
require __DIR__ . '/config.php';
if (!sso_ready()) redirect('./?login_error=sso_off');
$state = bin2hex(random_bytes(16));
$_SESSION['sso_state'] = $state;
redirect(RTEAM_URL . '/sso.php?' . http_build_query(['client' => 'rai', 'state' => $state]));
