<?php
/*
 * Скачать приложение Rai: download.php?os=win | mac | mac-x64 | linux | deb
 * Считает скачивания (видно в админке, вкладка «Rai») и отправляет на файл — с хостинга или с GitHub.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/app.php';

$os = (string)($_GET['os'] ?? '');
if (!isset(APP_FILES[$os])) redirect('./');

if (!rate_limited('dl:' . client_ip(), 30, 3600)) {
    update_json('downloads.json', function (&$d) use ($os) {
        $day = date('Y-m-d');
        $d['total'][$os] = ($d['total'][$os] ?? 0) + 1;
        $d['days'][$day] = ($d['days'][$day] ?? 0) + 1;
        if (count($d['days']) > 90) $d['days'] = array_slice($d['days'], -90, null, true);
    });
}
header('Cache-Control: no-store');
redirect(app_file_url($os));
