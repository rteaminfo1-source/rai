<?php
/*
 * Свой сервер нейросети Rai. Всё, что нужно нейросети в браузере, хранится на ЭТОМ сайте:
 *
 *   ai.php/npm/...   библиотеки: WebLLM (видеокарта), wllama (процессор), Python (Pyodide), распознавание текста
 *   ai.php/hf/...    веса моделей (файлы нейросети)
 *   ai.php/gh/...    программы моделей для видеокарты (WebGPU)
 *   ai.php/ping      проверка; ai.php?status=1 — сколько места занято
 *
 * Первый раз файл скачивается с исходного сервера (jsdelivr, Hugging Face, GitHub) и одновременно отдаётся
 * посетителю, а копия сохраняется в data/ai/. Дальше — только отсюда, с вашего сайта.
 * Если адреса вида ai.php/... на хостинге не работают (редкие настройки nginx), страница сама возьмёт файлы
 * с исходных серверов — Rai всё равно будет работать.
 */

// Что разрешено хранить: только нужные Rai библиотеки и модели (никакого произвольного кода)
const AI_SOURCES = [
    'npm' => ['https://cdn.jsdelivr.net/npm/', [
        '#^@mlc-ai/web-llm@[0-9][\w.-]*/#', '#^@wllama/wllama@[0-9][\w.-]*/#', '#^pyodide@[0-9][\w.-]*/#',
        '#^tesseract\.js(-core)?@[0-9][\w.-]*/#', '#^@tesseract\.js-data/(rus|eng)/#', '#^pptxgenjs@[0-9][\w.-]*/#',
        '#^@huggingface/transformers@[0-9][\w.-]*/#',  // зрение Rai (vision.js) и расшифровка речи (files.js)
        '#^pdfjs-dist@[0-9][\w.-]*/build/#',              // чтение PDF (files.js)
    ]],
    'hf' => ['https://huggingface.co/', ['#^mlc-ai/[\w.-]+/resolve/[\w.-]+/#', '#^Qwen/[\w.-]+/resolve/[\w.-]+/#', '#^unsloth/Qwen[\w.-]+/resolve/[\w.-]+/#', '#^Xenova/clip[\w.-]+/resolve/[\w.-]+/#', '#^Xenova/whisper[\w.-]+/resolve/[\w.-]+/#']],
    'gh' => ['https://raw.githubusercontent.com/', ['#^mlc-ai/binary-mlc-llm-libs/#']],
];
define('AI_DIR', __DIR__ . '/data/ai');
// Сколько места на хостинге можно занять под нейросеть (ГБ). Больше — файлы просто проходят насквозь, без копии.
define('AI_MAX_GB', (float)(getenv('AI_MAX_GB') ?: 8));
// Файлы больше этого за один запрос через PHP не качаем (ограничение времени на хостинге) — отдаём с исходного сервера
define('AI_BIG_FILE', 400 * 1024 * 1024);
const AI_TYPES = [
    'js' => 'text/javascript; charset=utf-8', 'mjs' => 'text/javascript; charset=utf-8', 'wasm' => 'application/wasm',
    'json' => 'application/json; charset=utf-8', 'txt' => 'text/plain; charset=utf-8', 'zip' => 'application/zip',
    'whl' => 'application/zip', 'tar' => 'application/x-tar', 'gz' => 'application/gzip',
];

header('Access-Control-Allow-Origin: *');
header('Cross-Origin-Resource-Policy: cross-origin');
header('X-Content-Type-Options: nosniff');

function ai_fail($code, $message) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode(['error' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

function ai_json($data) {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/** Путь запроса → [адрес на исходном сервере, путь] или ошибка. */
function ai_upstream($path) {
    if ($path === '' || strlen($path) > 600 || strpos($path, '..') !== false || strpos($path, '//') !== false
        || !preg_match('#^[A-Za-z0-9@._+\-/]+$#', $path)) {
        ai_fail(400, 'Неверный путь');
    }
    $slash = strpos($path, '/');
    $source = $slash === false ? $path : substr($path, 0, $slash);
    $rest = $slash === false ? '' : substr($path, $slash + 1);
    if (!isset(AI_SOURCES[$source])) ai_fail(404, 'Неизвестный источник');
    [$base, $allowed] = AI_SOURCES[$source];
    $ok = false;
    foreach ($allowed as $re) {
        if (preg_match($re, $rest)) { $ok = true; break; }
    }
    if (!$ok) ai_fail(403, 'Этот файл сервер нейросети не хранит');
    $override = getenv('AI_UPSTREAM_' . strtoupper($source));  // для проверок на своём компьютере
    return [($override ?: $base) . $rest, $path];
}

function ai_type($path) {
    $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
    if (substr($path, -4) === '+esm') return AI_TYPES['js'];
    return AI_TYPES[$ext] ?? 'application/octet-stream';
}

function ai_used_bytes() {
    $f = AI_DIR . '/_size.json';
    $d = is_file($f) ? json_decode((string)@file_get_contents($f), true) : null;
    return (int)($d['bytes'] ?? 0);
}

function ai_add_bytes($n) {
    $f = AI_DIR . '/_size.json';
    $fp = @fopen($f, 'c+');
    if (!$fp) return;
    flock($fp, LOCK_EX);
    $d = json_decode((string)stream_get_contents($fp), true) ?: [];
    $d['bytes'] = (int)($d['bytes'] ?? 0) + $n;
    $d['files'] = (int)($d['files'] ?? 0) + 1;
    ftruncate($fp, 0);
    rewind($fp);
    fwrite($fp, json_encode($d));
    flock($fp, LOCK_UN);
    fclose($fp);
}

function ai_cache_headers($path) {
    // Версия зашита в адрес (пакет@версия, файлы модели) — можно хранить в кэше браузера год
    header('Cache-Control: public, max-age=31536000, immutable');
}

/** Отдать сохранённый файл (с поддержкой Range — докачки). */
function ai_send_file($file, $path) {
    $size = filesize($file);
    header('Content-Type: ' . ai_type($path));
    header('Accept-Ranges: bytes');
    header('X-Rai-AI: stored');
    ai_cache_headers($path);
    $start = 0; $end = $size - 1;
    if (preg_match('/^bytes=(\d*)-(\d*)$/', trim($_SERVER['HTTP_RANGE'] ?? ''), $m) && ($m[1] !== '' || $m[2] !== '')) {
        if ($m[1] === '') { $start = max(0, $size - (int)$m[2]); }
        else { $start = (int)$m[1]; if ($m[2] !== '') $end = min($end, (int)$m[2]); }
        if ($start > $end || $start >= $size) {
            http_response_code(416);
            header("Content-Range: bytes */$size");
            exit;
        }
        http_response_code(206);
        header("Content-Range: bytes $start-$end/$size");
    }
    header('Content-Length: ' . ($end - $start + 1));
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'HEAD') exit;
    while (ob_get_level()) ob_end_clean();
    $fh = fopen($file, 'rb');
    fseek($fh, $start);
    $left = $end - $start + 1;
    while ($left > 0 && !feof($fh)) {
        $chunk = fread($fh, min(1 << 20, $left));
        if ($chunk === false || $chunk === '') break;
        echo $chunk;
        $left -= strlen($chunk);
        flush();
        if (connection_aborted()) break;
    }
    fclose($fh);
    exit;
}

/** Скачать с исходного сервера: сразу отдаём посетителю и одновременно сохраняем копию на сайте. */
function ai_fetch($url, $path, $file) {
    @set_time_limit(0);
    ignore_user_abort(true);
    while (ob_get_level()) ob_end_clean();
    $canStore = ai_used_bytes() < AI_MAX_GB * 1073741824 && is_dir(AI_DIR) && is_writable(AI_DIR);
    $tmp = $file . '.part' . getmypid();
    $fh = $canStore ? @fopen($tmp, 'wb') : null;
    $status = 0; $length = -1; $sent = false; $gone = false; $tooBig = false; $error = ''; $got = 0;
    $head = ($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'HEAD';
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_FOLLOWLOCATION => true, CURLOPT_MAXREDIRS => 5,
        // только https; http — лишь для проверки на своём компьютере (AI_TEST_HTTP)
        CURLOPT_PROTOCOLS => getenv('AI_TEST_HTTP') ? CURLPROTO_HTTP | CURLPROTO_HTTPS : CURLPROTO_HTTPS,
        CURLOPT_REDIR_PROTOCOLS => getenv('AI_TEST_HTTP') ? CURLPROTO_HTTP | CURLPROTO_HTTPS : CURLPROTO_HTTPS,
        CURLOPT_CONNECTTIMEOUT => 20, CURLOPT_LOW_SPEED_LIMIT => 2048, CURLOPT_LOW_SPEED_TIME => 60,
        CURLOPT_USERAGENT => 'RaiAI/1.0 (+https://rai.rteam.info)',
        CURLOPT_HEADERFUNCTION => function ($c, $line) use (&$status, &$length) {
            if (preg_match('#^HTTP/\S+\s+(\d+)#', $line, $m)) { $status = (int)$m[1]; $length = -1; }
            elseif (stripos($line, 'content-length:') === 0) $length = (int)trim(substr($line, 15));
            return strlen($line);
        },
        CURLOPT_WRITEFUNCTION => function ($c, $chunk) use (&$status, &$length, &$sent, &$gone, &$tooBig, &$error, &$got, $fh, $path, $head) {
            if ($status !== 200) { $error .= substr($chunk, 0, 300); return strlen($chunk); }
            if (!$sent) {
                if ($length > AI_BIG_FILE) { $tooBig = true; return 0; }
                http_response_code(200);
                header('Content-Type: ' . ai_type($path));
                if ($length >= 0) header('Content-Length: ' . $length);
                header('X-Rai-AI: fetched');
                header('X-Accel-Buffering: no');
                ai_cache_headers($path);
                $sent = true;
                if ($head) { $gone = true; if (!$fh) return 0; }
            }
            if ($fh) fwrite($fh, $chunk);
            $got += strlen($chunk);
            if (!$gone) {
                echo $chunk;
                flush();
                if (connection_aborted()) { $gone = true; if (!$fh) return 0; }
            }
            return strlen($chunk);
        },
    ]);
    $ok = curl_exec($ch);
    $curlError = curl_error($ch);
    curl_close($ch);
    if ($fh) fclose($fh);
    $complete = $ok && $status === 200 && ($length < 0 || $got === $length);
    if ($fh && $complete && $got > 0) {
        if (@rename($tmp, $file)) ai_add_bytes($got);
        else @unlink($tmp);
    } elseif ($fh) {
        @unlink($tmp);
    }
    if ($tooBig) {  // очень большой файл — пусть браузер возьмёт его прямо с исходного сервера
        header('Location: ' . $url, true, 302);
        header('Cache-Control: no-store');
        exit;
    }
    if (!$sent) {
        ai_fail($status === 404 ? 404 : 502, $status ? "Исходный сервер ответил $status" : 'Исходный сервер не отвечает: ' . $curlError);
    }
    exit;
}

// ====================================================================== запрос
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    header('Access-Control-Allow-Headers: Range');
    http_response_code(204);
    exit;
}
$path = ltrim((string)($_SERVER['PATH_INFO'] ?? ''), '/');
$viaPath = $path !== '';
if (!$viaPath) $path = ltrim((string)($_GET['p'] ?? ''), '/');
if ($path === 'ping' || isset($_GET['ping'])) {
    ai_json(['ok' => true, 'service' => 'rai-ai', 'path_info' => $path === 'ping', 'curl' => function_exists('curl_init'),
             'writable' => (is_dir(AI_DIR) || @mkdir(AI_DIR, 0775, true)) && is_writable(AI_DIR)]);
}
if (isset($_GET['status'])) {
    ai_json(['used_gb' => round(ai_used_bytes() / 1073741824, 2), 'max_gb' => AI_MAX_GB]);
}
if (!function_exists('curl_init')) ai_fail(501, 'На хостинге нет расширения PHP curl');
[$url, $path] = ai_upstream($path);
if (!is_dir(AI_DIR)) @mkdir(AI_DIR, 0775, true);
// Имя копии — по пути (без расширения .php: содержимое никогда не выполняется как код)
$file = AI_DIR . '/' . sha1($path) . '.bin';
if (is_file($file) && filesize($file) > 0) ai_send_file($file, $path);
ai_fetch($url, $path, $file);
