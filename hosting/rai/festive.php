<?php
/*
 * Праздничные и недельные темы Rai на сервере — для главной страницы (index.php). Разный дизайн под дату,
 * включается сам. То же, что festive.js в чате (данные держим одинаковыми).
 * Праздники важнее недельных тем; недели крутятся по номеру недели года (сейчас, например, неделя космоса).
 */

// [id, название, эмодзи, акцент, второй цвет градиента, [месяц, день с], [месяц, день по]]
const FESTIVE_HOLIDAYS = [
    ['ny',        'С Новым годом!',       '🎄', '#2aa7e8', '#f5b800', [12, 20], [1, 8]],
    ['defender',  '23 Февраля',           '🎖', '#3a7d44', '#8bb174', [2, 20], [2, 23]],
    ['march8',    '8 Марта',              '🌷', '#ff4f93', '#ffa6c9', [3, 5],  [3, 8]],
    ['cosmo',     'День космонавтики',    '🚀', '#6a5cff', '#2aa7e8', [4, 11], [4, 12]],
    ['victory',   '9 Мая',                '🎗', '#c62828', '#f5b800', [5, 7],  [5, 9]],
    ['russia',    'День России',          '🇷🇺', '#1e5bff', '#e10600', [6, 11], [6, 12]],
    ['knowledge', '1 Сентября',           '📚', '#1e5bff', '#2aa7e8', [9, 1],  [9, 1]],
    ['halloween', 'Хэллоуин',             '🎃', '#ff7a00', '#8b5cff', [10, 29], [10, 31]],
];
// [id, название, эмодзи, акцент, второй цвет]
const FESTIVE_WEEKS = [
    ['space',   'Неделя космоса',       '🚀', '#6a5cff', '#2aa7e8'],
    ['science', 'Неделя науки',         '🔬', '#1e9d8b', '#2aa7e8'],
    ['nature',  'Неделя природы',       '🌿', '#1f9d55', '#8bc34a'],
    ['art',     'Неделя искусства',     '🎨', '#e84c88', '#f5b800'],
    ['history', 'Неделя истории',       '🏛', '#b07a2e', '#c9a227'],
    ['music',   'Неделя музыки',        '🎵', '#8b5cff', '#ff3d81'],
    ['tech',    'Неделя технологий',    '💻', '#1e5bff', '#14b8a6'],
    ['cinema',  'Неделя кино',          '🎬', '#d4356b', '#6a5cff'],
    ['books',   'Неделя книг',          '📚', '#b5553a', '#c9a227'],
    ['sport',   'Неделя спорта',        '⚽', '#1f9d55', '#f5b800'],
    ['travel',  'Неделя путешествий',   '✈️', '#0ea5b7', '#f5b800'],
    ['health',  'Неделя здоровья',      '💪', '#16a34a', '#2aa7e8'],
];
const FESTIVE_WEEK_OFFSET = 7;   // чтобы сейчас (неделя 41) была неделя космоса

function festive_in_range($t, $from, $to) {
    $md = ((int)date('n', $t)) * 100 + (int)date('j', $t);
    $a = $from[0] * 100 + $from[1];
    $b = $to[0] * 100 + $to[1];
    return $a <= $b ? ($md >= $a && $md <= $b) : ($md >= $a || $md <= $b);
}

/** Тема на сейчас: ['id','kind','name','emoji','accent','grad2'] или null, если оформление выключать нечем. */
function festive_current($t = null) {
    $t = $t ?: time();
    foreach (FESTIVE_HOLIDAYS as $h) {
        if (festive_in_range($t, $h[5], $h[6])) {
            return ['id' => $h[0], 'kind' => 'holiday', 'name' => $h[1], 'emoji' => $h[2], 'accent' => $h[3], 'grad2' => $h[4]];
        }
    }
    $week = (int)date('W', $t);
    $w = FESTIVE_WEEKS[($week + FESTIVE_WEEK_OFFSET) % count(FESTIVE_WEEKS)];
    return ['id' => $w[0], 'kind' => 'week', 'name' => $w[1], 'emoji' => $w[2], 'accent' => $w[3], 'grad2' => $w[4]];
}

/** #rrggbb -> rgba(...) с заданной прозрачностью (для мягкого свечения фона). */
function festive_rgba($hex, $alpha) {
    if (!preg_match('/^#([0-9a-fA-F]{6})$/', $hex, $m)) return $hex;
    $n = hexdec($m[1]);
    return 'rgba(' . (($n >> 16) & 255) . ',' . (($n >> 8) & 255) . ',' . ($n & 255) . ',' . $alpha . ')';
}

/** Красивый фон под праздник: два-три мягких цветных свечения в цвет темы (как в чате). */
function festive_bg($fest) {
    $a = $fest['accent'];
    $b = $fest['grad2'];
    return 'radial-gradient(1200px 680px at 12% -12%, ' . festive_rgba($a, 0.22) . ', transparent 60%),'
         . 'radial-gradient(1000px 560px at 100% 0%, ' . festive_rgba($b, 0.16) . ', transparent 58%),'
         . 'radial-gradient(900px 700px at 50% 120%, ' . festive_rgba($a, 0.10) . ', transparent 60%)';
}

/** CSS-переменные акцента + праздничный фон — вставляется в <style> главной страницы. */
function festive_css($fest) {
    $a = $fest['accent'];
    $b = $fest['grad2'];
    $bg = festive_bg($fest);
    return ":root{--red:$a;--red2:$b;--pink:$b;--grad:linear-gradient(120deg,$a 0%,$b 100%);}"
         . "body{background-image:$bg;background-attachment:fixed;}";
}
