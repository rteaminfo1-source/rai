<?php
/*
 * Анализ по ссылке: TikTok (видео и аккаунты), YouTube (видео, Shorts, каналы), Telegram (каналы и посты),
 * Instagram, VK, X (Twitter) и любые сайты. Подключается из net.php (net.php?social=ссылка) и возвращает
 * единый JSON: площадка, что это (видео / аккаунт / канал / пост / страница), автор, цифры, текст, хэштеги,
 * последние посты. Сам разбор цифр и советы делает Rai.
 */
if (!defined('NET_CACHE')) { http_response_code(404); exit; }

const SOCIAL_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36';

/** «1.2M», «12,3 тыс.», «1 234», «45K» → число. */
function social_num($s) {
    if ($s === null || $s === '') return null;
    if (is_int($s) || is_float($s)) return (int)$s;
    $s = trim(str_replace(["\u{00a0}", "\u{202f}", ' '], '', mb_strtolower((string)$s)));
    $mult = 1;
    if (preg_match('/(млрд|b)\.?$/u', $s)) $mult = 1e9;
    elseif (preg_match('/(млн|m)\.?$/u', $s)) $mult = 1e6;
    elseif (preg_match('/(тыс|k|к)\.?$/u', $s)) $mult = 1e3;
    if ($mult > 1) {
        $n = (float)str_replace(',', '.', preg_replace('/[^\d.,]/', '', $s));
        return (int)round($n * $mult);
    }
    $digits = preg_replace('/\D/', '', $s);
    return $digits === '' ? null : (int)$digits;
}

function social_text($html) {
    $html = preg_replace('#<br\s*/?>#i', "\n", (string)$html);
    return trim(html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5, 'UTF-8'));
}

function social_meta($html) {
    $out = [];
    if (preg_match_all('#<meta\s+[^>]*>#i', $html, $m)) {
        foreach ($m[0] as $tag) {
            if (preg_match('#(?:property|name|itemprop)\s*=\s*["\']([^"\']+)["\']#i', $tag, $k)
                && preg_match('#content\s*=\s*"([^"]*)"|content\s*=\s*\'([^\']*)\'#i', $tag, $v)) {
                $key = strtolower($k[1]);
                if (!isset($out[$key])) $out[$key] = html_entity_decode($v[1] !== '' ? $v[1] : ($v[2] ?? ''), ENT_QUOTES | ENT_HTML5, 'UTF-8');
            }
        }
    }
    if (preg_match('#<title[^>]*>(.*?)</title>#is', $html, $t)) $out['_title'] = social_text($t[1]);
    return $out;
}

/** JSON из <script id="..."> */
function social_script_json($html, $id) {
    if (preg_match('#<script[^>]+id="' . preg_quote($id, '#') . '"[^>]*>(.*?)</script>#s', $html, $m)) {
        $d = json_decode($m[1], true);
        if (is_array($d)) return $d;
    }
    return null;
}

/** JSON-объект сразу после метки (var ytInitialData = {...};) — с учётом строк и вложенных скобок. */
function social_json_after($html, $marker) {
    $pos = strpos($html, $marker);
    if ($pos === false) return null;
    $start = strpos($html, '{', $pos);
    if ($start === false) return null;
    $depth = 0; $inStr = false; $esc = false; $len = strlen($html);
    for ($i = $start; $i < $len; $i++) {
        $c = $html[$i];
        if ($inStr) {
            if ($esc) $esc = false;
            elseif ($c === '\\') $esc = true;
            elseif ($c === '"') $inStr = false;
            continue;
        }
        if ($c === '"') $inStr = true;
        elseif ($c === '{') $depth++;
        elseif ($c === '}' && --$depth === 0) {
            $d = json_decode(substr($html, $start, $i - $start + 1), true);
            return is_array($d) ? $d : null;
        }
    }
    return null;
}

function social_hashtags($text) {
    preg_match_all('/#([\p{L}\p{N}_]{2,40})/u', (string)$text, $m);
    return array_values(array_unique($m[1]));
}

function social_base($platform, $kind, $url) {
    return ['platform' => $platform, 'kind' => $kind, 'url' => $url, 'title' => '', 'text' => '',
            'author' => [], 'stats' => [], 'hashtags' => [], 'posts' => [], 'warnings' => [], 'source' => 'page'];
}

function social_fetch($url, $opts = []) {
    [$final, $type, $body] = net_read_page($url, $opts + ['ua' => SOCIAL_UA]);
    return [$final, $body];
}

// ====================================================================== TikTok
function social_tiktok($url) {
    [$final, $html] = social_fetch($url);  // короткие ссылки vm.tiktok.com раскрываются сами
    $isVideo = (bool)preg_match('#/(video|photo)/(\d+)#', $final);
    $r = social_base('tiktok', $isVideo ? 'video' : 'profile', $final);
    $scope = (social_script_json($html, '__UNIVERSAL_DATA_FOR_REHYDRATION__') ?: [])['__DEFAULT_SCOPE__'] ?? [];
    $sigi = social_script_json($html, 'SIGI_STATE') ?: [];
    $item = $scope['webapp.video-detail']['itemInfo']['itemStruct'] ?? null;
    if (!$item && !empty($sigi['ItemModule'])) $item = reset($sigi['ItemModule']);
    $user = $scope['webapp.user-detail']['userInfo'] ?? null;
    if (!$user && !empty($sigi['UserModule']['users'])) {
        $u = reset($sigi['UserModule']['users']);
        $user = ['user' => $u, 'stats' => $sigi['UserModule']['stats'][$u['uniqueId'] ?? ''] ?? []];
    }
    $stat = function ($a, $k) { return isset($a[$k]) ? social_num($a[$k]) : null; };
    if ($isVideo && $item) {
        $st = array_merge($item['stats'] ?? [], $item['statsV2'] ?? []);
        $au = $item['author'] ?? [];
        $as = $item['authorStats'] ?? [];
        $r['title'] = $r['text'] = (string)($item['desc'] ?? '');
        $r['stats'] = ['views' => $stat($st, 'playCount'), 'likes' => $stat($st, 'diggCount'), 'comments' => $stat($st, 'commentCount'),
                       'shares' => $stat($st, 'shareCount'), 'saves' => $stat($st, 'collectCount')];
        $r['author'] = ['name' => $au['nickname'] ?? '', 'handle' => $au['uniqueId'] ?? '', 'verified' => !empty($au['verified']),
                        'bio' => $au['signature'] ?? '', 'url' => 'https://www.tiktok.com/@' . ($au['uniqueId'] ?? ''),
                        'followers' => $stat($as, 'followerCount'), 'following' => $stat($as, 'followingCount'),
                        'likes' => $stat($as, 'heartCount') ?? $stat($as, 'heart'), 'videos' => $stat($as, 'videoCount')];
        $tags = [];
        foreach (($item['textExtra'] ?? []) as $t) if (!empty($t['hashtagName'])) $tags[] = $t['hashtagName'];
        foreach (($item['challenges'] ?? []) as $t) if (!empty($t['title'])) $tags[] = $t['title'];
        $r['hashtags'] = array_values(array_unique($tags ?: social_hashtags($r['text'])));
        $r['music'] = trim(($item['music']['title'] ?? '') . (isset($item['music']['authorName']) ? ' — ' . $item['music']['authorName'] : ''));
        $r['duration'] = social_num($item['video']['duration'] ?? null);
        $r['published'] = isset($item['createTime']) ? gmdate('c', (int)$item['createTime']) : null;
        $r['thumbnail'] = $item['video']['cover'] ?? ($item['video']['originCover'] ?? null);
        return $r;
    }
    if (!$isVideo && $user) {
        $u = $user['user'] ?? [];
        $st = array_merge($user['stats'] ?? [], $user['statsV2'] ?? []);
        $r['title'] = $u['nickname'] ?? '';
        $r['text'] = $u['signature'] ?? '';
        $r['author'] = ['name' => $u['nickname'] ?? '', 'handle' => $u['uniqueId'] ?? '', 'verified' => !empty($u['verified']),
                        'bio' => $u['signature'] ?? '', 'url' => $final, 'avatar' => $u['avatarLarger'] ?? ($u['avatarMedium'] ?? null),
                        'followers' => $stat($st, 'followerCount'), 'following' => $stat($st, 'followingCount'),
                        'likes' => $stat($st, 'heartCount') ?? $stat($st, 'heart'), 'videos' => $stat($st, 'videoCount')];
        $r['hashtags'] = social_hashtags($r['text']);
        $r['thumbnail'] = $r['author']['avatar'];
        return $r;
    }
    // TikTok не отдал данные страницы — берём то, что есть в его открытом oEmbed
    if ($isVideo) {
        try {
            [, $raw] = social_fetch('https://www.tiktok.com/oembed?url=' . rawurlencode($final), ['json' => true]);
            $o = json_decode($raw, true) ?: [];
            $r['source'] = 'oembed';
            $r['title'] = $r['text'] = $o['title'] ?? '';
            $r['author'] = ['name' => $o['author_name'] ?? '', 'handle' => $o['author_unique_id'] ?? '', 'url' => $o['author_url'] ?? ''];
            $r['thumbnail'] = $o['thumbnail_url'] ?? null;
            $r['hashtags'] = social_hashtags($r['text']);
        } catch (RuntimeException $e) { /* без oEmbed */ }
    }
    $r['warnings'][] = 'TikTok не отдал статистику (просмотры, лайки) — показываю то, что открыто';
    return $r;
}

// ====================================================================== YouTube
function social_youtube($url) {
    $p = parse_url($url);
    $host = strtolower($p['host'] ?? '');
    $path = $p['path'] ?? '/';
    parse_str($p['query'] ?? '', $q);
    $id = null;
    if (preg_match('#youtu\.be$#', $host)) $id = trim($path, '/');
    elseif (!empty($q['v'])) $id = $q['v'];
    elseif (preg_match('#^/(shorts|live|embed)/([\w-]{6,})#', $path, $m)) $id = $m[2];
    $opts = ['lang' => 'ru,en;q=0.8', 'headers' => ['Cookie: CONSENT=YES+1; SOCS=CAI']];
    if ($id && preg_match('/^[\w-]{6,20}$/', $id)) {
        $watch = 'https://www.youtube.com/watch?v=' . $id;
        [$final, $html] = social_fetch($watch, $opts);
        $r = social_base('youtube', strpos($path, '/shorts/') === 0 ? 'short' : 'video', $watch);
        $pr = social_json_after($html, 'ytInitialPlayerResponse = ') ?: [];
        $vd = $pr['videoDetails'] ?? [];
        $mf = $pr['microformat']['playerMicroformatRenderer'] ?? [];
        $meta = social_meta($html);
        $r['title'] = $vd['title'] ?? ($meta['og:title'] ?? '');
        $r['text'] = $vd['shortDescription'] ?? ($meta['og:description'] ?? '');
        $likes = null;
        if (preg_match('#"likeCount(?:IfIndifferentNumber)?":"(\d+)"#', $html, $m)) $likes = (int)$m[1];
        elseif (preg_match('#"accessibilityText":"[^"]*?([\d\s ,.]+\s*(?:тыс\.?|млн|K|M)?)\s*(?:отмет|likes?|лайк)#u', $html, $m)) $likes = social_num($m[1]);
        $comments = null;
        if (preg_match('#"commentCount":\{"simpleText":"([^"]+)"#', $html, $m)) $comments = social_num($m[1]);
        $r['stats'] = ['views' => social_num($vd['viewCount'] ?? ($mf['viewCount'] ?? null)), 'likes' => $likes, 'comments' => $comments];
        $r['author'] = ['name' => $vd['author'] ?? ($mf['ownerChannelName'] ?? ''), 'url' => $mf['ownerProfileUrl'] ?? '',
                        'handle' => $vd['channelId'] ?? ''];
        $r['duration'] = social_num($vd['lengthSeconds'] ?? null);
        $r['published'] = $mf['publishDate'] ?? ($mf['uploadDate'] ?? null);
        $r['category'] = $mf['category'] ?? '';
        $r['keywords'] = array_slice($vd['keywords'] ?? [], 0, 30);
        $r['hashtags'] = social_hashtags($r['text']);
        $thumbs = $vd['thumbnail']['thumbnails'] ?? [];
        $r['thumbnail'] = $thumbs ? end($thumbs)['url'] : ($meta['og:image'] ?? null);
        if (!$vd) {
            $r['warnings'][] = 'YouTube не отдал данные видео — показываю открытые сведения';
            try {
                [, $raw] = social_fetch('https://www.youtube.com/oembed?format=json&url=' . rawurlencode($watch), ['json' => true]);
                $o = json_decode($raw, true) ?: [];
                $r['title'] = $o['title'] ?? $r['title'];
                $r['author']['name'] = $o['author_name'] ?? '';
                $r['author']['url'] = $o['author_url'] ?? '';
                $r['thumbnail'] = $o['thumbnail_url'] ?? $r['thumbnail'];
                $r['source'] = 'oembed';
            } catch (RuntimeException $e) { /* без oEmbed */ }
        }
        return $r;
    }
    // канал: /@имя, /channel/ID, /c/имя, /user/имя
    [$final, $html] = social_fetch($url, $opts);
    $r = social_base('youtube', 'channel', $final);
    $meta = social_meta($html);
    $data = social_json_after($html, 'ytInitialData = ') ?: [];
    $cm = $data['metadata']['channelMetadataRenderer'] ?? [];
    $r['title'] = $cm['title'] ?? ($meta['og:title'] ?? '');
    $r['text'] = $cm['description'] ?? ($meta['og:description'] ?? '');
    $subs = null; $videos = null;
    if (preg_match('#"subscriberCountText":\{"simpleText":"([^"]+)"#', $html, $m)) $subs = social_num(preg_replace('/\s*(subscribers?|подписчик\w*)/iu', '', $m[1]));
    elseif (preg_match('#"content":"([\d\s ,.]+\s*(?:тыс\.?|млн|K|M|B)?)\s*(?:subscribers|подписчик)#u', $html, $m)) $subs = social_num($m[1]);
    if (preg_match('#"content":"([\d\s ,.]+\s*(?:тыс\.?|K)?)\s*(?:videos|видео)#u', $html, $m)) $videos = social_num($m[1]);
    elseif (preg_match('#"videosCountText":\{"runs":\[\{"text":"([^"]+)"#', $html, $m)) $videos = social_num($m[1]);
    $r['author'] = ['name' => $r['title'], 'url' => $cm['vanityChannelUrl'] ?? $final, 'handle' => $cm['externalId'] ?? '',
                    'followers' => $subs, 'videos' => $videos, 'bio' => $r['text']];
    $r['keywords'] = array_slice(preg_split('/\s+/', (string)($cm['keywords'] ?? ''), -1, PREG_SPLIT_NO_EMPTY), 0, 30);
    $r['thumbnail'] = $cm['avatar']['thumbnails'][0]['url'] ?? ($meta['og:image'] ?? null);
    $r['hashtags'] = social_hashtags($r['text']);
    if ($subs === null) $r['warnings'][] = 'YouTube не показал число подписчиков';
    return $r;
}

// ====================================================================== Telegram
function social_telegram($url) {
    $p = parse_url($url);
    $parts = array_values(array_filter(explode('/', $p['path'] ?? '')));
    if ($parts && $parts[0] === 's') array_shift($parts);
    $name = $parts[0] ?? '';
    if (!preg_match('/^[A-Za-z0-9_]{3,64}$/', $name)) throw new RuntimeException('Не понял, какой это канал Telegram', 400);
    $postId = isset($parts[1]) && ctype_digit($parts[1]) ? (int)$parts[1] : null;
    [$final, $html] = social_fetch('https://t.me/s/' . $name);
    $r = social_base('telegram', $postId ? 'post' : 'channel', 'https://t.me/' . $name . ($postId ? '/' . $postId : ''));
    $meta = social_meta($html);
    if (preg_match('#class="tgme_channel_info_header_title[^"]*"[^>]*>(.*?)</div>#s', $html, $m)) $r['title'] = social_text($m[1]);
    else $r['title'] = $meta['og:title'] ?? $name;
    if (preg_match('#class="tgme_channel_info_description[^"]*"[^>]*>(.*?)</div>#s', $html, $m)) $r['text'] = social_text($m[1]);
    else $r['text'] = $meta['og:description'] ?? '';
    $counters = [];
    if (preg_match_all('#<span class="counter_value">([^<]+)</span>\s*<span class="counter_type">([^<]+)</span>#', $html, $m, PREG_SET_ORDER)) {
        foreach ($m as $c) $counters[mb_strtolower(trim($c[2]))] = social_num($c[1]);
    }
    $subs = null;
    foreach ($counters as $k => $v) if (preg_match('/subscriber|подписчик|member|участник/u', $k)) $subs = $v;
    if ($subs === null && preg_match('#class="tgme_page_extra"[^>]*>([^<]+)<#', $html, $m)) $subs = social_num(preg_replace('/[^\d\s.,KMkmтысмлн]/u', '', $m[1]));
    $r['author'] = ['name' => $r['title'], 'handle' => $name, 'url' => 'https://t.me/' . $name, 'followers' => $subs, 'bio' => $r['text'],
                    'photos' => $counters['photos'] ?? ($counters['фото'] ?? null), 'videos' => $counters['videos'] ?? ($counters['видео'] ?? null)];
    $posts = [];
    foreach (array_slice(explode('class="tgme_widget_message_wrap', $html), 1) as $chunk) {
        $post = ['url' => '', 'text' => '', 'views' => null, 'date' => null, 'media' => ''];
        if (preg_match('#data-post="([^"]+)"#', $chunk, $m)) $post['url'] = 'https://t.me/' . $m[1];
        if (preg_match('#class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>#s', $chunk, $m)) $post['text'] = mb_substr(social_text($m[1]), 0, 600);
        if (preg_match('#class="tgme_widget_message_views">([^<]+)<#', $chunk, $m)) $post['views'] = social_num($m[1]);
        if (preg_match('#<time[^>]+datetime="([^"]+)"#', $chunk, $m)) $post['date'] = $m[1];
        if (strpos($chunk, 'tgme_widget_message_video') !== false) $post['media'] = 'видео';
        elseif (strpos($chunk, 'tgme_widget_message_photo') !== false) $post['media'] = 'фото';
        $reactions = 0;
        if (preg_match_all('#class="tgme_reaction[^"]*"[^>]*>.*?</i>\s*([\d.,KMk]+)#s', $chunk, $rm)) foreach ($rm[1] as $x) $reactions += (int)social_num($x);
        if ($reactions) $post['reactions'] = $reactions;
        if ($post['url']) $posts[] = $post;
    }
    $r['posts'] = array_slice(array_reverse($posts), 0, 20);  // сначала новые
    if ($postId) {
        foreach ($posts as $post) {
            if (preg_match('#/' . $postId . '$#', $post['url'])) {
                $r['stats'] = ['views' => $post['views'], 'reactions' => $post['reactions'] ?? null];
                $r['text'] = $post['text'];
                $r['published'] = $post['date'];
            }
        }
    }
    $r['hashtags'] = social_hashtags(implode(' ', array_column($r['posts'], 'text')));
    $r['thumbnail'] = $meta['og:image'] ?? null;
    if (!$posts) $r['warnings'][] = 'Посты не видны: это не публичный канал (группа, бот или человек) или канал закрыт';
    return $r;
}

// ====================================================================== Instagram, VK, X — открытые сведения
function social_instagram($url) {
    // Instagram показывает краткую статистику в превью для ботов соцсетей
    [$final, $html] = social_fetch($url, ['ua' => 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)', 'lang' => 'en']);
    $isPost = (bool)preg_match('#/(p|reel|reels|tv)/[\w-]+#', $final);
    $r = social_base('instagram', $isPost ? 'post' : 'profile', $final);
    $r['source'] = 'og';
    $meta = social_meta($html);
    $desc = $meta['og:description'] ?? ($meta['description'] ?? '');
    $r['title'] = $meta['og:title'] ?? '';
    $num = '([\d.,]+\s*[KMBkmb]?)';
    if (!$isPost && preg_match("/$num\\s*Followers?,\\s*$num\\s*Following,\\s*$num\\s*Posts?/i", $desc, $m)) {
        $handle = preg_match('/\(@([\w.]+)\)/', $desc, $h) ? $h[1] : trim(parse_url($final, PHP_URL_PATH), '/');
        $r['author'] = ['name' => preg_replace('/\s*\(@.*$/', '', $r['title']), 'handle' => $handle, 'url' => $final,
                        'followers' => social_num($m[1]), 'following' => social_num($m[2]), 'videos' => social_num($m[3])];
        $r['text'] = trim(preg_replace("/^.*?Posts?\\s*-\\s*/i", '', $desc));
    } elseif ($isPost && preg_match("/$num\\s*likes?,\\s*$num\\s*comments?\\s*-\\s*([\\w.]+)\\s+(?:on\\s+)?([^:]*):\\s*(.*)$/is", $desc, $m)) {
        $r['stats'] = ['likes' => social_num($m[1]), 'comments' => social_num($m[2])];
        $r['author'] = ['handle' => $m[3], 'url' => 'https://www.instagram.com/' . $m[3] . '/'];
        $r['published'] = trim($m[4]);
        $r['text'] = trim($m[5], " \"“”");
    } else {
        $r['text'] = $desc;
        $r['warnings'][] = 'Instagram закрыл статистику для просмотра без входа — показываю открытое описание';
    }
    $r['hashtags'] = social_hashtags($r['text']);
    $r['thumbnail'] = $meta['og:image'] ?? null;
    return $r;
}

function social_vk($url) {
    [$final, $html] = social_fetch($url);
    $r = social_base('vk', preg_match('#/(wall|video|clip)-?\d#', $final) ? 'post' : 'profile', $final);
    $r['source'] = 'og';
    $meta = social_meta($html);
    $r['title'] = $meta['og:title'] ?? ($meta['_title'] ?? '');
    $r['text'] = $meta['og:description'] ?? ($meta['description'] ?? '');
    $followers = null;
    if (preg_match('/([\d\s  ,.]+(?:K|тыс\.?|млн)?)\s*(?:подписчик|участник|followers|members)/u', social_text($html), $m)) $followers = social_num($m[1]);
    $r['author'] = ['name' => $r['title'], 'url' => $final, 'followers' => $followers];
    $r['hashtags'] = social_hashtags($r['text']);
    $r['thumbnail'] = $meta['og:image'] ?? null;
    if ($followers === null) $r['warnings'][] = 'VK показывает подробную статистику только после входа';
    return $r;
}

function social_x($url) {
    $r = social_base('x', preg_match('#/status/\d+#', $url) ? 'post' : 'profile', $url);
    $r['source'] = 'oembed';
    if ($r['kind'] === 'post') {
        $tw = preg_replace('#^https?://(www\.)?(x|twitter)\.com#', 'https://twitter.com', $url);
        [, $raw] = social_fetch('https://publish.twitter.com/oembed?omit_script=1&url=' . rawurlencode($tw), ['json' => true]);
        $o = json_decode($raw, true) ?: [];
        $r['text'] = preg_match('#<p[^>]*>(.*?)</p>#s', $o['html'] ?? '', $m) ? social_text($m[1]) : '';
        $r['author'] = ['name' => $o['author_name'] ?? '', 'url' => $o['author_url'] ?? ''];
        $r['hashtags'] = social_hashtags($r['text']);
    }
    $r['warnings'][] = 'X (Twitter) не показывает просмотры и лайки без входа — разбираю текст';
    return $r;
}

// ====================================================================== любой сайт: SEO и содержание
function social_web($url) {
    [$final, $html] = social_fetch($url);
    $r = social_base('web', 'page', $final);
    $meta = social_meta($html);
    $r['title'] = $meta['_title'] ?? '';
    $r['text'] = $meta['description'] ?? ($meta['og:description'] ?? '');
    preg_match_all('#<h1[^>]*>(.*?)</h1>#is', $html, $h1);
    preg_match_all('#<h2[^>]*>(.*?)</h2>#is', $html, $h2);
    preg_match_all('#<img\b[^>]*>#i', $html, $imgs);
    $noAlt = 0;
    foreach ($imgs[0] as $img) if (!preg_match('#\balt\s*=\s*["\'][^"\']+#i', $img)) $noAlt++;
    preg_match_all('#<a\b[^>]*href=["\']([^"\'\#]+)#i', $html, $links);
    $host = parse_url($final, PHP_URL_HOST);
    $external = 0;
    foreach ($links[1] as $l) if (preg_match('#^https?://#i', $l) && parse_url($l, PHP_URL_HOST) !== $host) $external++;
    [, $text] = net_page_text($html, '');
    $words = preg_match_all('/[\p{L}\p{N}]+/u', $text);
    $r['seo'] = [
        'https' => strpos($final, 'https://') === 0,
        'title_len' => mb_strlen($r['title']), 'description_len' => mb_strlen($r['text']),
        'h1' => array_slice(array_map('social_text', $h1[1]), 0, 5), 'h2' => count($h2[1]),
        'images' => count($imgs[0]), 'images_no_alt' => $noAlt, 'links' => count($links[1]), 'external_links' => $external,
        'words' => $words, 'lang' => preg_match('#<html[^>]+lang=["\']([\w-]+)#i', $html, $m) ? $m[1] : '',
        'viewport' => isset($meta['viewport']), 'canonical' => (bool)preg_match('#rel=["\']canonical#i', $html),
        'og' => isset($meta['og:title']) || isset($meta['og:image']), 'favicon' => (bool)preg_match('#rel=["\'][^"\']*icon#i', $html),
    ];
    $r['summary'] = mb_substr($text, 0, 1500);
    $r['thumbnail'] = $meta['og:image'] ?? null;
    return $r;
}

/** Ссылка → данные для анализа. */
function social_analyze($url) {
    $host = strtolower((string)parse_url($url, PHP_URL_HOST));
    $host = preg_replace('/^(www|m|mobile)\./', '', $host);
    if (preg_match('/(^|\.)tiktok\.com$/', $host)) return social_tiktok($url);
    if (preg_match('/(^|\.)(youtube\.com|youtu\.be)$/', $host)) return social_youtube($url);
    if (preg_match('/^(t\.me|telegram\.me)$/', $host)) return social_telegram($url);
    if (preg_match('/(^|\.)instagram\.com$/', $host)) return social_instagram($url);
    if (preg_match('/(^|\.)(vk\.com|vk\.ru|vkvideo\.ru)$/', $host)) return social_vk($url);
    if (preg_match('/^(x\.com|twitter\.com)$/', $host)) return social_x($url);
    return social_web($url);
}
