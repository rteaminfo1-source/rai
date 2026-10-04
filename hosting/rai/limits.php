<?php
/*
 * Лимиты нейросети для страницы Rai.
 *   GET  limits.php            — тариф, сколько сообщений осталось сегодня, какие модели доступны
 *   POST limits.php action=use — засчитать одно сообщение нейросети (заголовок X-CSRF-Token из me.php)
 * Без входа — GUEST_NEURO_DAY сообщений в день на IP, после входа — по тарифу.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';
require __DIR__ . '/moderation.php';

// Нейросеть в AI Studio (aistudio.rteam.info) — тот же аккаунт и тариф Rai: студия спрашивает лимиты отсюда.
// Это один сайт rteam.info, поэтому браузер присылает cookie входа в Rai; другим адресам ответы не открываются.
$origin = rtrim((string)($_SERVER['HTTP_ORIGIN'] ?? ''), '/');
if ($origin !== '' && $origin === rtrim(STUDIO_URL, '/')) {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Allow-Headers: X-CSRF-Token, Content-Type');
    header('Access-Control-Allow-Methods: GET, POST');
    header('Access-Control-Max-Age: 600');
    header('Vary: Origin');
    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
}

$user = current_user();
if (rai_current_ban($user)) json_out(['ok' => false, 'error' => 'Доступ к Rai заблокирован за нарушение правил.', 'banned' => true], 403);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!csrf_ok()) json_out(['ok' => false, 'error' => 'Страница устарела — обновите её.'], 403);
    $state = limits_state($user);
    list($allowed, $used) = usage_take(usage_key($user), $state['limit']);
    $state['used'] = $used;
    $state['left'] = $state['limit'] > 0 ? max(0, $state['limit'] - $used) : null;
    if (!$allowed) {
        $state['ok'] = false;
        $state['error'] = $user
            ? 'Сообщения нейросети на сегодня закончились (' . $state['limit'] . ' в день на тарифе «' . $state['plan_name'] . '»).'
            : 'Без входа нейросеть отвечает ' . guest_limit() . ' раз в день. Войдите — бесплатно будет ' . plans()['free']['neuro_day'] . '.';
        json_out($state, 429);
    }
    $state['ok'] = true;
    json_out($state);
}

json_out(limits_state($user) + ['csrf' => csrf_token()]);
