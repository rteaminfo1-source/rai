<?php
/*
 * Настройки входа через Google для сайта Rteam.
 * Добавьте эти строки в ваш config.php НА ХОСТИНГЕ.
 * Секрет не храните в GitHub: вставьте его только в config.php на сервере
 * (или задайте переменную окружения GOOGLE_CLIENT_SECRET в панели хостинга).
 */
define('GOOGLE_CLIENT_ID', '40211315152-jq7a91jcqrpu8hkmlqmg1poh6bthgs5j.apps.googleusercontent.com');
define('GOOGLE_CLIENT_SECRET', getenv('GOOGLE_CLIENT_SECRET') ?: 'ВСТАВЬТЕ_СЮДА_СЕКРЕТ_GOCSPX');
// Этот адрес должен В ТОЧНОСТИ совпадать с «Authorized redirect URI» в Google Cloud Console.
define('GOOGLE_REDIRECT_URI', 'https://ВАШ-САЙТ/google_callback.php');
