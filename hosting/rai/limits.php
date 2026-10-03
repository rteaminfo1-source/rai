<?php
/*
 * Лимиты нейросети для страницы Rai.
 *   GET  limits.php            — тариф, сколько сообщений осталось сегодня, какие модели доступны
 *   POST limits.php action=use — засчитать одно сообщение нейросети (заголовок X-CSRF-Token из me.php)
 * Без входа — GUEST_NEURO_DAY сообщений в день на IP, после входа — по тарифу.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';

$user = current_user();

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
            : 'Без входа нейросеть отвечает ' . GUEST_NEURO_DAY . ' раз в день. Войдите — бесплатно будет ' . plans()['free']['neuro_day'] . '.';
        json_out($state, 429);
    }
    $state['ok'] = true;
    json_out($state);
}

json_out(limits_state($user) + ['csrf' => csrf_token()]);
