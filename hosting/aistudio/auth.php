<?php
/* Выход из AI Studio. Вход и регистрация — через аккаунт Rai (sso_start.php). */
require __DIR__ . '/config.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_ok()) redirect('index.php?error=csrf');
if (($_POST['action'] ?? '') === 'logout') {
    $_SESSION = [];
    session_destroy();
}
redirect('index.php');
