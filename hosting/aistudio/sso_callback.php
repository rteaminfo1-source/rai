<?php
/* Возврат с rai.rteam.info: проверяем подписанный пропуск и входим (аккаунт студии создаётся сам). */
require __DIR__ . '/config.php';

$state = $_SESSION['sso_state'] ?? '';
unset($_SESSION['sso_state']);  // пропуск одноразовый
$p = sso_verify($_GET['token'] ?? '', $state);
if (!$p) redirect('index.php?error=sso');

$rid = (string)$p['sub'];
$email = !empty($p['email']) ? strtolower((string)$p['email']) : null;
$fields = ['name' => mb_substr((string)($p['name'] ?? $rid), 0, 60), 'email' => $email, 'avatar' => $p['avatar'] ?? null, 'rai_id' => $rid];

$user = find_user('rai_id', $rid);
if (!$user) {
    // Логин Rai = адрес сайта в студии (если свободен)
    $users = users();
    $username = valid_username($rid) && !isset($users[$rid]) ? $rid : unique_username($rid);
    $user = create_user($username, $fields);
    $welcome = true;
} else {
    update_json('users.json', function (&$users) use ($user, $fields) {
        $users[$user['username']] = array_merge($users[$user['username']], $fields);
    });
}
login_user($user['username']);
redirect('studio.php' . (!empty($welcome) ? '?welcome=1' : ''));
