<?php
/*
 * chat.php — переход с сайта Rteam в чат Rai, который работает на GitHub Pages.
 * Положите этот файл на виртуальный хостинг ВМЕСТО старого chat.php.
 * Адрес чата можно поменять в config.php: define('RAI_CHAT_URL', 'https://...');
 */
require __DIR__ . '/config.php';

// Чат только для вошедших на сайт (уберите эти 4 строки, если чат должен быть открыт всем)
if (empty($_SESSION['user'])) {
    header('Location: login.php');
    exit;
}

$rai = defined('RAI_CHAT_URL') ? RAI_CHAT_URL : 'https://rai.rteam.info/';

// Адрес сайта для кнопки «← На сайт Rteam» в чате
$https = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
      || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
$host  = preg_replace('/[^A-Za-z0-9.\-:]/', '', $_SERVER['HTTP_HOST'] ?? '');
$back  = ($https ? 'https' : 'http') . '://' . $host . '/';

header('Location: ' . $rai . (strpos($rai, '?') === false ? '?' : '&') . 'back=' . rawurlencode($back));
exit;
