<?php
/* Сообщения от rteam.info: профиль изменился (update) или аккаунт удалён (delete). Подпись — HMAC SSO_SECRET. */
require __DIR__ . '/config.php';
$body = file_get_contents('php://input');
$m = sync_verify($body, $_SERVER['HTTP_X_RTEAM_SIGNATURE'] ?? '');
if (!$m) json_out(['error' => 'bad signature'], 403);
$u = $m['user'];
$login = $u['login'];
if (($m['event'] ?? '') === 'delete') {
    update_json('users.json', function (&$users) use ($login) { unset($users[$login]); });
    $chats = data_path('chats/' . $login . '.json');
    if (is_file($chats)) unlink($chats);
    json_out(['ok' => true, 'deleted' => $login]);
}
update_json('users.json', function (&$users) use ($login, $u) {
    if (!isset($users[$login])) return;  // ещё ни разу не входил в Rai — хранить нечего
    foreach (['name', 'email', 'avatar'] as $k) $users[$login][$k] = $u[$k] ?? null;
});
json_out(['ok' => true]);
