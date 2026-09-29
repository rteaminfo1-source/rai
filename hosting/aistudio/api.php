<?php
/*
 * API AI Studio. Ключ: заголовок «Authorization: Bearer rai_…» (или X-API-Key).
 *   GET  api.php?a=site                    — ваш сайт: адрес, опубликован ли, название
 *   POST api.php?a=generate  {"prompt": "…", "publish": true}   — ИИ создаёт сайт
 *   POST api.php?a=edit      {"instruction": "…", "publish": true} — ИИ правит сайт
 *   POST api.php?a=publish | a=unpublish
 * Файлы сайта создаёт только ИИ студии — загрузить свои файлы через API нельзя.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/sitegen.php';
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Authorization, X-API-Key, Content-Type');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') exit;

function api_out($data, $code = 200) {
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$auth = $_SERVER['HTTP_AUTHORIZATION'] ?? ($_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '');
$key = preg_match('/^Bearer\s+(\S+)$/i', $auth, $m) ? $m[1] : ($_SERVER['HTTP_X_API_KEY'] ?? '');
if ($key === '') api_out(['error' => 'Нужен API-ключ: заголовок Authorization: Bearer rai_…'], 401);
$user = api_user_by_key($key);
if (!$user) {
    // считаем только неудачные попытки — защита от перебора ключей
    $code = rate_limited('apikey-fail:' . client_ip(), 30, 600) ? 429 : 401;
    api_out(['error' => $code === 429 ? 'Слишком много неудачных попыток.' : 'Неверный или отозванный API-ключ.'], $code);
}
$name = $user['username'];
if (rate_limited('api:' . $name, API_LIMIT_PER_HOUR, 3600)) api_out(['error' => 'Лимит: ' . API_LIMIT_PER_HOUR . ' запросов в час.'], 429);

$body = json_decode((string)file_get_contents('php://input'), true);
if (!is_array($body)) $body = $_POST;
$a = $_GET['a'] ?? ($body['a'] ?? 'site');
$publish = !isset($body['publish']) || filter_var($body['publish'], FILTER_VALIDATE_BOOLEAN);

if ($a === 'site') {
    $spec = sg_load($name);
    api_out(['username' => $name, 'url' => site_url($name), 'published' => is_file(site_file($name)),
             'title' => $spec['title'] ?? null, 'sections' => $spec ? array_column($spec['sections'], 'title') : []]);
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') api_out(['error' => 'Используйте POST.'], 405);

switch ($a) {
    case 'generate': $r = studio_generate($name, $body['prompt'] ?? '', $publish); break;
    case 'edit':     $r = studio_edit($name, $body['instruction'] ?? '', $publish); break;
    case 'publish':
        $spec = sg_load($name);
        if (!$spec) api_out(['error' => 'Сначала создайте сайт (a=generate).'], 400);
        api_out(['url' => sg_publish($name, $spec), 'published' => true]);
    case 'unpublish':
        sg_unpublish($name);
        api_out(['published' => false]);
    default:
        api_out(['error' => 'Неизвестное действие. Есть: site, generate, edit, publish, unpublish.'], 400);
}
if (isset($r['error'])) api_out(['error' => $r['error']], 400);
api_out(['message' => $r['message'], 'title' => $r['spec']['title'], 'url' => $r['url'] ?? site_url($name),
         'published' => $publish, 'sections' => array_column($r['spec']['sections'], 'title')]);
