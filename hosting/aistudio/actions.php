<?php
/* Действия студии (для кнопок на studio.php): только для вошедших, с CSRF-токеном. Ответ — JSON. */
require __DIR__ . '/config.php';
require __DIR__ . '/sitegen.php';
header('Content-Type: application/json; charset=utf-8');

function out($data, $code = 200) {
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

$user = current_user();
if (!$user) out(['error' => 'Нужно войти.'], 401);
$name = $user['username'];
$a = $_GET['a'] ?? ($_POST['a'] ?? '');

if ($a === 'state') {
    $spec = sg_load($name);
    $keys = array_map(function ($k) {
        return ['id' => $k['id'], 'prefix' => $k['prefix'], 'label' => $k['label'],
                'created' => date('d.m.Y H:i', $k['created']), 'last_used' => $k['last_used'] ? date('d.m.Y H:i', $k['last_used']) : null];
    }, $user['api_keys'] ?? []);
    out([
        'user' => ['username' => $name, 'name' => $user['name']],
        'url' => site_url($name), 'published' => is_file(site_file($name)),
        'html' => $spec ? sg_render($spec) : null, 'title' => $spec['title'] ?? null, 'keys' => $keys,
    ]);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_ok()) out(['error' => 'Страница устарела — обновите её.'], 403);

if (in_array($a, ['generate', 'edit'], true) && rate_limited('ai:' . $name, 120, 3600)) {
    out(['error' => 'Слишком много запросов к ИИ за час. Попробуйте позже.'], 429);
}

switch ($a) {
    case 'generate':
        $r = studio_generate($name, $_POST['prompt'] ?? '');
        break;
    case 'edit':
        $r = studio_edit($name, $_POST['instruction'] ?? '');
        break;
    case 'publish':
        $spec = sg_load($name);
        if (!$spec) out(['error' => 'Сначала создайте сайт.'], 400);
        out(['message' => 'Опубликовано!', 'url' => sg_publish($name, $spec), 'published' => true]);
    case 'unpublish':
        sg_unpublish($name);
        out(['message' => 'Сайт снят с публикации.', 'published' => false]);
    case 'key_create':
        out(['key' => api_key_create($name, $_POST['label'] ?? '')]);
    case 'key_revoke':
        api_key_revoke($name, (string)($_POST['id'] ?? ''));
        out(['ok' => true]);
    default:
        out(['error' => 'Неизвестное действие.'], 400);
}
if (isset($r['error'])) out($r, 400);
out(['message' => $r['message'], 'html' => sg_render($r['spec']), 'title' => $r['spec']['title']]);
