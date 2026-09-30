<?php
/*
 * Посредник Rai для интернета: страница Rai (index.html) спрашивает погоду, курсы, перевод, Википедию и картинки
 * через этот файл на хостинге — браузеру не мешают блокировки чужих сайтов (CORS, фильтры, расширения).
 *
 *   net.php?url=https://api.open-meteo.com/v1/forecast?...   — ответ сервиса как есть
 *   net.php?search=кто изобрёл радио&n=6                     — поиск в интернете: {"results": [{title, url, snippet}]}
 *   net.php?ping=1                                           — проверка, что посредник работает
 *
 * Поиск: Google (если заданы GOOGLE_CSE_KEY и GOOGLE_CSE_CX — ключ Programmable Search Engine), иначе DuckDuckGo,
 * а если и он не ответил — Википедия.
 *
 * Ходит только к списку сервисов ниже и только по https. Ответы кэшируются в data/cache/.
 */

const NET_HOSTS = [
    '/^geocoding-api\.open-meteo\.com$/', '/^api\.open-meteo\.com$/',                // погода
    '/^open\.er-api\.com$/', '/^www\.cbr-xml-daily\.ru$/',                           // курсы валют
    '/^api\.mymemory\.translated\.net$/',                                            // перевод
    '/^[a-z]{2,3}\.wikipedia\.org$/', '/^[a-z]{2,3}\.wikiquote\.org$/',              // тексты для ответов и презентаций
    '/^commons\.wikimedia\.org$/', '/^upload\.wikimedia\.org$/',                     // картинки для презентаций
];
// Необязательно: поиск Google (programmablesearchengine.google.com + ключ Custom Search API).
// Задайте переменными окружения или впишите здесь НА ХОСТИНГЕ (в GitHub ключи не выкладывайте).
define('GOOGLE_CSE_KEY', getenv('GOOGLE_CSE_KEY') ?: '');
define('GOOGLE_CSE_CX', getenv('GOOGLE_CSE_CX') ?: '');
const NET_MAX_BYTES = 8 * 1024 * 1024;
const NET_PER_MINUTE = 150;               // запросов в минуту с одного адреса
const NET_GUARD = "<?php http_response_code(404); exit; ?>\n";
define('NET_CACHE', __DIR__ . '/data/cache');

header('Access-Control-Allow-Origin: *');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');

function net_fail($code, $message) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode(['error' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

function net_allowed($address) {
    $p = parse_url($address);
    if (!$p || ($p['scheme'] ?? '') !== 'https' || empty($p['host']) || isset($p['user']) || isset($p['pass'])
        || (isset($p['port']) && (int)$p['port'] !== 443)) {
        return false;
    }
    $host = strtolower($p['host']);
    foreach (NET_HOSTS as $re) {
        if (preg_match($re, $host)) return true;
    }
    return false;
}

/** Сколько хранить ответ: погода — 10 минут, курсы — час, статьи и картинки — сутки. */
function net_ttl($address) {
    $host = strtolower(parse_url($address, PHP_URL_HOST));
    if (strpos($host, 'open-meteo') !== false) return strpos($host, 'geocoding') === 0 ? 86400 : 600;
    if ($host === 'open.er-api.com' || $host === 'www.cbr-xml-daily.ru') return 3600;
    return 86400;
}

/** Один GET без перехода по редиректам: [код, тип, тело, адрес редиректа]. */
function net_get($address, $ua = null) {
    $ua = $ua ?: 'RaiBot/1.0 (+https://rai.rteam.info; https://github.com/rteaminfo1-source/rai)';
    if (function_exists('curl_init')) {
        $ch = curl_init($address);
        $body = '';
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => false, CURLOPT_FOLLOWLOCATION => false, CURLOPT_TIMEOUT => 15, CURLOPT_CONNECTTIMEOUT => 6,
            CURLOPT_USERAGENT => $ua, CURLOPT_HTTPHEADER => ['Accept: application/json, image/*, */*;q=0.5'],
            CURLOPT_PROTOCOLS => CURLPROTO_HTTPS, CURLOPT_ENCODING => '',
            CURLOPT_WRITEFUNCTION => function ($c, $chunk) use (&$body) {
                $body .= $chunk;
                return strlen($body) > NET_MAX_BYTES ? 0 : strlen($chunk);  // слишком большой ответ — обрываем
            },
        ]);
        curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $type = (string)curl_getinfo($ch, CURLINFO_CONTENT_TYPE);
        $location = (string)curl_getinfo($ch, CURLINFO_REDIRECT_URL);
        $error = curl_error($ch);
        curl_close($ch);
        if (strlen($body) > NET_MAX_BYTES) throw new RuntimeException('Ответ слишком большой', 413);
        if ($code === 0) throw new RuntimeException('Сервис не отвечает: ' . $error, 502);
        return [$code, $type, $body, $location];
    }
    $ctx = stream_context_create(['http' => [
        'method' => 'GET', 'timeout' => 15, 'follow_location' => 0, 'ignore_errors' => true,
        'header' => "User-Agent: $ua\r\nAccept: application/json, image/*, */*;q=0.5\r\n",
    ]]);
    $body = @file_get_contents($address, false, $ctx, 0, NET_MAX_BYTES + 1);
    if ($body === false) throw new RuntimeException('Сервис не отвечает', 502);
    if (strlen($body) > NET_MAX_BYTES) throw new RuntimeException('Ответ слишком большой', 413);
    $code = 0; $type = ''; $location = '';
    foreach ($http_response_header ?? [] as $line) {
        if (preg_match('#^HTTP/\S+\s+(\d+)#', $line, $m)) $code = (int)$m[1];
        elseif (stripos($line, 'Content-Type:') === 0) $type = trim(substr($line, 13));
        elseif (stripos($line, 'Location:') === 0) $location = trim(substr($line, 9));
    }
    return [$code, $type, $body, $location];
}

// ====================================================================== поиск
function net_clean($html) {
    $text = html_entity_decode(strip_tags((string)$html), ENT_QUOTES | ENT_HTML5, 'UTF-8');
    return trim(preg_replace('/\s+/u', ' ', $text));
}

function search_google($q, $n) {
    if (GOOGLE_CSE_KEY === '' || GOOGLE_CSE_CX === '') return [];
    [$code, , $body] = net_get('https://www.googleapis.com/customsearch/v1?' . http_build_query(
        ['key' => GOOGLE_CSE_KEY, 'cx' => GOOGLE_CSE_CX, 'q' => $q, 'num' => min(10, $n), 'hl' => 'ru']));
    $data = $code === 200 ? json_decode($body, true) : null;
    $out = [];
    foreach (($data['items'] ?? []) as $it) {
        $out[] = ['title' => net_clean($it['title'] ?? ''), 'url' => (string)($it['link'] ?? ''), 'snippet' => net_clean($it['snippet'] ?? '')];
    }
    return $out;
}

/** Разбор страницы результатов DuckDuckGo (html.duckduckgo.com/html). */
function parse_duckduckgo($html) {
    $out = [];
    if (!preg_match_all('#<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="[^"]*result__a|$)#s', $html, $m, PREG_SET_ORDER)) {
        return $out;
    }
    foreach ($m as $row) {
        $href = html_entity_decode($row[1], ENT_QUOTES | ENT_HTML5, 'UTF-8');
        if (preg_match('#[?&]uddg=([^&]+)#', $href, $u)) $href = urldecode($u[1]);
        if (strpos($href, '//') === 0) $href = 'https:' . $href;
        if (!preg_match('#^https?://#', $href) || preg_match('#duckduckgo\.com/(y\.js|l/)#', $href)) continue;  // реклама
        $snippet = preg_match('#class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|div|td)>#s', $row[3], $sm) ? net_clean($sm[1]) : '';
        $out[] = ['title' => net_clean($row[2]), 'url' => $href, 'snippet' => $snippet];
    }
    return $out;
}

function search_duckduckgo($q, $n) {
    [$code, , $body] = net_get('https://html.duckduckgo.com/html/?' . http_build_query(['q' => $q, 'kl' => 'ru-ru']),
                               'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36');
    return $code === 200 ? array_slice(parse_duckduckgo($body), 0, $n) : [];
}

function search_wikipedia($q, $n) {
    $out = [];
    foreach (['ru', 'en'] as $lang) {
        [$code, , $body] = net_get("https://$lang.wikipedia.org/w/api.php?" . http_build_query(
            ['action' => 'query', 'list' => 'search', 'srsearch' => $q, 'srlimit' => $n, 'format' => 'json', 'utf8' => 1]));
        $data = $code === 200 ? json_decode($body, true) : null;
        foreach (($data['query']['search'] ?? []) as $it) {
            $out[] = ['title' => $it['title'], 'url' => "https://$lang.wikipedia.org/wiki/" . rawurlencode(str_replace(' ', '_', $it['title'])),
                      'snippet' => net_clean($it['snippet'] ?? '')];
        }
        if ($out) break;
    }
    return $out;
}

function net_rate_limit() {
    $ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
    $file = NET_CACHE . '/rl-' . substr(hash('sha256', $ip . date('YmdHi')), 0, 24) . '.php';
    $n = is_file($file) ? (int)substr((string)@file_get_contents($file), strlen(NET_GUARD)) : 0;
    if ($n >= NET_PER_MINUTE) net_fail(429, 'Слишком много запросов, подождите минуту');
    @file_put_contents($file, NET_GUARD . ($n + 1), LOCK_EX);
}

function net_cleanup() {  // изредка удаляем старые файлы кэша
    if (mt_rand(1, 200) !== 1) return;
    foreach (glob(NET_CACHE . '/*.php') ?: [] as $f) {
        if (filemtime($f) < time() - 2 * 86400) @unlink($f);
    }
}

// ====================================================================== запрос
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') { http_response_code(204); exit; }
if (isset($_GET['ping'])) {
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode(['ok' => true, 'service' => 'rai-net']);
    exit;
}
if (isset($_GET['search'])) {
    $q = trim(preg_replace('/\s+/u', ' ', (string)$_GET['search']));
    $n = max(1, min(10, (int)($_GET['n'] ?? 6)));
    if ($q === '' || strlen($q) > 1200) net_fail(400, 'Пустой или слишком длинный запрос');
    if (!is_dir(NET_CACHE)) @mkdir(NET_CACHE, 0775, true);
    $key = NET_CACHE . '/s-' . sha1(strtolower($q) . '|' . $n) . '.php';
    header('Content-Type: application/json; charset=utf-8');
    if (is_file($key) && filemtime($key) > time() - 3600) {
        header('X-Rai-Cache: hit');
        echo substr((string)@file_get_contents($key), strlen(NET_GUARD));
        exit;
    }
    net_rate_limit();
    $results = []; $engine = '';
    foreach (['google' => 'search_google', 'duckduckgo' => 'search_duckduckgo', 'wikipedia' => 'search_wikipedia'] as $name => $fn) {
        try { $results = $fn($q, $n); } catch (Throwable $e) { $results = []; }
        if ($results) { $engine = $name; break; }
    }
    $json = json_encode(['query' => $q, 'engine' => $engine, 'results' => $results], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($results) @file_put_contents($key, NET_GUARD . $json, LOCK_EX);
    header('Cache-Control: ' . ($results ? 'public, max-age=3600' : 'no-store'));
    echo $json;
    exit;
}
$address = (string)($_GET['url'] ?? '');
if ($address === '' || strlen($address) > 4000) net_fail(400, 'Нужен параметр url');
if (!net_allowed($address)) net_fail(403, 'Этот адрес посредник не открывает');

if (!is_dir(NET_CACHE)) @mkdir(NET_CACHE, 0775, true);
$key = NET_CACHE . '/' . sha1($address) . '.php';
$ttl = net_ttl($address);
if (is_file($key) && filemtime($key) > time() - $ttl) {
    $raw = (string)@file_get_contents($key);
    $raw = substr($raw, strlen(NET_GUARD));
    $nl = strpos($raw, "\n");
    $meta = json_decode(substr($raw, 0, $nl), true) ?: [];
    header('Content-Type: ' . ($meta['type'] ?? 'application/octet-stream'));
    header('Cache-Control: public, max-age=' . min($ttl, 3600));
    header('X-Rai-Cache: hit');
    echo substr($raw, $nl + 1);
    exit;
}
net_rate_limit();

// Редиректы — только на разрешённые адреса
for ($hop = 0; ; $hop++) {
    try {
        [$code, $type, $body, $location] = net_get($address);
    } catch (RuntimeException $e) {
        net_fail($e->getCode() ?: 502, $e->getMessage());
    }
    if ($code >= 300 && $code < 400 && $location !== '') {
        if ($hop >= 3) net_fail(502, 'Слишком много перенаправлений');
        if (strpos($location, '//') === 0) $location = 'https:' . $location;
        elseif ($location[0] === '/') $location = 'https://' . parse_url($address, PHP_URL_HOST) . $location;
        if (!net_allowed($location)) net_fail(403, 'Перенаправление на неразрешённый адрес');
        $address = $location;
        continue;
    }
    break;
}

// Отдаём только данные и картинки — никакого HTML/скриптов с чужих сайтов от имени rai.rteam.info
$base = strtolower(trim(explode(';', $type)[0]));
if (preg_match('#^image/(png|jpe?g|gif|webp)$#', $base)) {
    $safe = $base;
} elseif (preg_match('#^(application/(json|[a-z.+-]*\+json|javascript)|text/(plain|javascript|json))$#', $base)) {
    $safe = 'application/json; charset=utf-8';
} else {
    $safe = 'text/plain; charset=utf-8';
}
http_response_code($code ?: 502);
header('Content-Type: ' . $safe);
if ($code === 200) {
    @file_put_contents($key, NET_GUARD . json_encode(['type' => $safe]) . "\n" . $body, LOCK_EX);
    header('Cache-Control: public, max-age=' . min($ttl, 3600));
    net_cleanup();
} else {
    header('Cache-Control: no-store');
}
echo $body;
