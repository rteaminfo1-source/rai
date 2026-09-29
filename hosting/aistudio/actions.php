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

/** ZIP-архив без сжатия: [имя => содержимое]. */
function zip_store($files) {
    $data = ''; $central = ''; $n = 0;
    $time = (date('H') << 11) | (date('i') << 5) | (date('s') >> 1);
    $date = ((date('Y') - 1980) << 9) | (date('n') << 5) | date('j');
    foreach ($files as $fname => $body) {
        $crc = crc32($body); $len = strlen($body); $offset = strlen($data);
        $data .= pack('VvvvvvVVVvv', 0x04034b50, 20, 0x0800, 0, $time, $date, $crc, $len, $len, strlen($fname), 0) . $fname . $body;
        $central .= pack('VvvvvvvVVVvvvvvVV', 0x02014b50, 20, 20, 0x0800, 0, $time, $date, $crc, $len, $len, strlen($fname), 0, 0, 0, 0, 0, $offset) . $fname;
        $n++;
    }
    return $data . $central . pack('VvvvvVVv', 0x06054b50, 0, 0, $n, $n, strlen($central), strlen($data), 0);
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

if ($a === 'zip') {
    // Скачать сайт одним архивом (ZIP без сжатия — работает на любом хостинге, без расширения zip)
    $spec = sg_load($name);
    if (!$spec) out(['error' => 'Сначала создайте сайт.'], 400);
    $zip = zip_store(['index.html' => sg_render($spec)]);
    header('Content-Type: application/zip');
    header('Content-Disposition: attachment; filename="' . $name . '-site.zip"');
    header('Content-Length: ' . strlen($zip));
    echo $zip;
    exit;
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
