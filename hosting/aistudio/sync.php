<?php
/* Сообщения от rai.rteam.info: профиль изменился (update) или аккаунт удалён (delete). Подпись — HMAC SSO_SECRET. */
require __DIR__ . '/config.php';
require __DIR__ . '/sitegen.php';
header('Content-Type: application/json; charset=utf-8');

$body = file_get_contents('php://input');
$m = sync_verify($body, $_SERVER['HTTP_X_RTEAM_SIGNATURE'] ?? '');
if (!$m) { http_response_code(403); echo '{"error":"bad signature"}'; exit; }
$u = $m['user'];
$user = find_user('rai_id', $u['login']);
if (!$user) { echo '{"ok":true,"known":false}'; exit; }  // в студию ещё не входил
$name = $user['username'];

if (($m['event'] ?? '') === 'delete') {
    sg_unpublish($name);
    $spec = json_path('specs/' . $name . '.json');
    if (is_file($spec)) unlink($spec);
    update_json('users.json', function (&$users) use ($name) { unset($users[$name]); });
    echo json_encode(['ok' => true, 'deleted' => $name]);
    exit;
}
update_json('users.json', function (&$users) use ($name, $u) {
    $users[$name]['name'] = mb_substr((string)($u['name'] ?? $name), 0, 60);
    $users[$name]['email'] = $u['email'] ?? null;
    $users[$name]['avatar'] = $u['avatar'] ?? null;
});
echo json_encode(['ok' => true]);
