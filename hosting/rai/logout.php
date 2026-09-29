<?php
/* Выход из Rai (чаты остаются в аккаунте). */
require __DIR__ . '/config.php';
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !csrf_ok()) json_out(['error' => 'Страница устарела'], 403);
$_SESSION = [];
session_destroy();
json_out(['ok' => true]);
