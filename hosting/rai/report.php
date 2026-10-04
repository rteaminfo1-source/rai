<?php
/*
 * Страница Rai сообщает о нарушении правил (rules.php): POST JSON {"category", "text", "chat", "version"}.
 * Запись появляется в админ-панели (вкладка «Rai: правила») — там пользователя можно заблокировать.
 * Ответ: {"ok": true, "banned": null | {"reason", "until"}}.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/moderation.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') json_out(['ok' => false, 'error' => 'POST only'], 405);
$in = json_decode((string)file_get_contents('php://input'), true);
$category = is_array($in) ? (string)($in['category'] ?? '') : '';
if (!isset(RULE_LABELS[$category])) json_out(['ok' => false, 'error' => 'unknown category'], 400);

$user = current_user();
$ban = rai_current_ban($user);
// не больше 20 записей в час с одного адреса — чтобы журнал нельзя было засыпать
if (!rate_limited('report:' . client_ip(), 20, 3600)) {
    rai_violation_add([
        'login' => $user['login'] ?? null,
        'name' => $user ? ($user['name'] ?? $user['login']) : null,
        'ip' => client_ip(),
        'category' => $category,
        'text' => mb_substr(trim((string)($in['text'] ?? '')), 0, 500),
        'chat' => preg_replace('/[^\w\-]/', '', mb_substr((string)($in['chat'] ?? ''), 0, 40)),
        'version' => preg_replace('/[^\w\-]/', '', mb_substr((string)($in['version'] ?? ''), 0, 20)),
        'ua' => mb_substr((string)($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 160),
    ]);
}
json_out(['ok' => true, 'banned' => rai_ban_public($ban)]);
