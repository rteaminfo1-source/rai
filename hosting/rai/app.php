<?php
/*
 * Приложение Rai для компьютера (Windows, macOS, Linux): какие файлы есть и откуда их скачивать.
 * Файлы кладёт в папку app/ GitHub Actions (.github/workflows/desktop.yml) или вы сами по FTP.
 * Если в app/ файла нет — ссылка ведёт на последний релиз на GitHub.
 */
const APP_FILES = [
    'win'     => ['name' => 'Windows',    'note' => 'Windows 10 и 11 · установщик',       'files' => ['Rai-Setup.exe']],
    'mac'     => ['name' => 'macOS',      'note' => 'Apple M1–M4',                         'files' => ['Rai-mac-arm64.dmg', 'Rai-mac-arm64.zip']],
    'mac-x64' => ['name' => 'macOS Intel', 'note' => 'Mac с процессором Intel',            'files' => ['Rai-mac-x64.dmg', 'Rai-mac-x64.zip']],
    'linux'   => ['name' => 'Linux',      'note' => 'AppImage — любой дистрибутив',        'files' => ['Rai-linux.AppImage']],
    'deb'     => ['name' => 'Linux .deb', 'note' => 'Ubuntu, Debian, Mint',                'files' => ['Rai-linux.deb']],
];

function app_dir() { return __DIR__ . '/app'; }

/** Файл для этой системы, если он лежит на хостинге (app/), иначе null. */
function app_local_file($os) {
    foreach (APP_FILES[$os]['files'] ?? [] as $f) {
        if (is_file(app_dir() . '/' . $f)) return $f;
    }
    return null;
}

/** Прямая ссылка на файл: с хостинга, а если его там нет — из последнего релиза на GitHub. */
function app_file_url($os) {
    $f = app_local_file($os);
    return $f ? 'app/' . rawurlencode($f) : GITHUB_URL . '/releases/latest/download/' . rawurlencode(APP_FILES[$os]['files'][0]);
}

/** Версия приложения на хостинге (из latest*.yml, их же читает автообновление) или null. */
function app_version() {
    foreach (['latest.yml', 'latest-mac.yml', 'latest-linux.yml'] as $y) {
        $text = @file_get_contents(app_dir() . '/' . $y);
        if ($text && preg_match('/^version:\s*([0-9][\w.\-]*)/m', $text, $m)) return $m[1];
    }
    return null;
}

/** Размер файла на хостинге в мегабайтах (или null). */
function app_size_mb($os) {
    $f = app_local_file($os);
    return $f ? (int)round(filesize(app_dir() . '/' . $f) / 1048576) : null;
}
