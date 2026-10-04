<?php
// Папка с файлами приложения (список файлов не показываем) — отправляем на главную сайта.
// Если этот файл случайно положили в корень сайта вместо главной, перенаправления нет — иначе браузер
// бесконечно ходил бы по кругу (ERR_TOO_MANY_REDIRECTS). Тогда покажем подсказку.
if (basename(__DIR__) === 'app' && is_file(dirname(__DIR__) . '/index.php')) {
    header('Location: ../');
    exit;
}
header('Content-Type: text/html; charset=utf-8');
?><!DOCTYPE html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Rai</title>
<body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#07070b;color:#f3f1f1;font:16px/1.5 system-ui,sans-serif">
<p style="max-width:34em;padding:24px">Здесь должен быть главный файл сайта <b>index.php</b> (из папки rai.rteam.info), а это файл из папки <b>app/</b>. Загрузите правильный index.php в корень сайта.</p>
</body></html>
