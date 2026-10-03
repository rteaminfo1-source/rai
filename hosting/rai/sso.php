<?php
/*
 * Единый вход: AI Studio присылает сюда пользователя (sso.php?client=aistudio&state=…),
 * мы проверяем, что он вошёл в аккаунт Rai, и возвращаем его обратно с подписанным пропуском.
 * Возврат — только на заранее известный адрес из SSO_CLIENTS (никаких чужих ссылок).
 */
require __DIR__ . '/config.php';

$client = (string)($_GET['client'] ?? '');
$state = (string)($_GET['state'] ?? '');
if (!isset(SSO_CLIENTS[$client]) || !preg_match('/^[a-f0-9]{32}$/', $state)) {
    http_response_code(400);
    page_head('Ошибка входа — Rai');
    echo '<main class="auth"><section class="panel"><h1>Ссылка входа неверная</h1><p class="muted">Откройте сервис и нажмите «Войти» ещё раз.</p>'
       . '<a class="btn" href="' . CHAT_URL . '">В Rai</a></section></main>';
    page_foot();
    exit;
}
if (!sso_ready()) {
    http_response_code(503);
    page_head('Единый вход не настроен — Rai');
    echo '<main class="auth"><section class="panel"><h1>Единый вход ещё не настроен</h1>'
       . '<p class="muted">Администратору: впишите одинаковый SSO_SECRET (от 32 символов) в config.php сайтов rai.rteam.info и AI Studio.</p></section></main>';
    page_foot();
    exit;
}

$user = current_user();
if (!$user) {
    redirect('login.php?next=' . rawurlencode('sso.php?client=' . $client . '&state=' . $state));
}
redirect(SSO_CLIENTS[$client]['callback'] . '?token=' . rawurlencode(sso_token($user, $client, $state)));
