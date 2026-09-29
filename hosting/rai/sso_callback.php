<?php
/* Возврат с rteam.info: проверяем пропуск и входим. Профиль берём из пропуска. */
require __DIR__ . '/config.php';
$state = $_SESSION['sso_state'] ?? '';
unset($_SESSION['sso_state']);
$p = sso_verify($_GET['token'] ?? '', $state);
if (!$p) redirect('./?login_error=sso');
$login = $p['sub'];
update_json('users.json', function (&$users) use ($login, $p) {
    $users[$login] = array_merge($users[$login] ?? ['created' => time()], [
        'login' => $login, 'name' => mb_substr((string)($p['name'] ?? $login), 0, 60),
        'email' => $p['email'] ?? null, 'avatar' => $p['avatar'] ?? null, 'last_login' => time(),
    ]);
});
session_regenerate_id(true);
$_SESSION['user'] = $login;
redirect('./?login=ok');
