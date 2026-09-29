<?php
/* Чаты вошедшего пользователя: GET — получить, PUT — сохранить (слияние по id: остаётся более свежий). */
require __DIR__ . '/config.php';
$user = current_user();
if (!$user) json_out(['error' => 'Нужно войти'], 401);
$file = 'chats/' . $user['login'] . '.json';

if ($_SERVER['REQUEST_METHOD'] === 'GET') json_out(['chats' => load_json($file)]);
if ($_SERVER['REQUEST_METHOD'] !== 'PUT' && $_SERVER['REQUEST_METHOD'] !== 'POST') json_out(['error' => 'Метод не поддерживается'], 405);
if (!csrf_ok()) json_out(['error' => 'Страница устарела — обновите её'], 403);

$raw = file_get_contents('php://input');
if (strlen($raw) > CHATS_MAX_BYTES) json_out(['error' => 'Слишком много чатов для хранения — удалите старые или скриншоты'], 413);
$in = json_decode($raw, true);
if (!is_array($in) || !isset($in['chats']) || !is_array($in['chats'])) json_out(['error' => 'Неверный формат'], 400);
$deleted = array_flip(array_filter((array)($in['deleted'] ?? []), 'is_string'));

$merged = update_json($file, function (&$chats) use ($in, $deleted) {
    $byId = [];
    foreach ($chats as $c) if (is_array($c) && isset($c['id']) && !isset($deleted[$c['id']])) $byId[$c['id']] = $c;
    foreach ($in['chats'] as $c) {
        if (!is_array($c) || !isset($c['id'], $c['messages']) || !is_string($c['id']) || strlen($c['id']) > 64 || !is_array($c['messages'])) continue;
        $old = $byId[$c['id']] ?? null;
        if (!$old || (int)($c['updated'] ?? 0) >= (int)($old['updated'] ?? 0)) $byId[$c['id']] = $c;
    }
    uasort($byId, function ($a, $b) { return (int)($b['updated'] ?? 0) <=> (int)($a['updated'] ?? 0); });
    $chats = array_slice(array_values($byId), 0, 300);
    return $chats;
});
json_out(['ok' => true, 'chats' => $merged]);
