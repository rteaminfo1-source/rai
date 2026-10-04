<?php
/*
 * Правила Rai: нарушения в чате и блокировки. Подключается после config.php.
 *   data/violations.json — нарушения (страница Rai сообщает о них через report.php);
 *   data/bans.json       — заблокированные аккаунты и IP-адреса гостей (блокирует администратор в admin.php).
 * Заблокированному Rai не отвечает (me.php → banned), войти в аккаунт он тоже не может.
 */

const RULE_LABELS = [
    'мат' => 'нецензурная брань',
    '18+' => 'темы 18+',
    'наркотики' => 'наркотики',
    'насилие' => 'насилие и опасные действия',
    'взлом' => 'взлом и мошенничество',
    'экстремизм' => 'экстремизм и оскорбления по национальности',
];
const VIOLATIONS_KEEP = 3000;

/** Дата по-русски: «4 октября 2026 г.» (для документов — всегда сегодняшняя). */
function legal_date($ts = null) {
    $months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
    $ts = $ts ?: time();
    return (int)date('j', $ts) . ' ' . $months[(int)date('n', $ts) - 1] . ' ' . date('Y', $ts) . ' г.';
}

function rai_bans() {
    $b = load_json('bans.json', ['users' => [], 'ips' => []]);
    return ['users' => (array)($b['users'] ?? []), 'ips' => (array)($b['ips'] ?? [])];
}

/** Действующая блокировка аккаунта или IP: ['reason', 'until' (0 — навсегда), 'at', 'by'] или null. */
function rai_ban_of($login, $ip) {
    $b = rai_bans();
    foreach ([[$b['users'], $login], [$b['ips'], $ip]] as $pair) {
        list($list, $key) = $pair;
        if ($key && isset($list[$key])) {
            $ban = $list[$key];
            if (empty($ban['until']) || $ban['until'] > time()) return $ban;
        }
    }
    return null;
}

function rai_current_ban($user = null) {
    $user = $user ?: current_user();
    return rai_ban_of($user['login'] ?? null, client_ip());
}

/** Для страницы: только то, что можно показать человеку. */
function rai_ban_public($ban) {
    return $ban ? ['reason' => (string)($ban['reason'] ?? ''), 'until' => (int)($ban['until'] ?? 0)] : null;
}

function rai_violation_add(array $v) {
    $id = '';
    update_json('violations.json', function (&$list) use ($v, &$id) {
        $id = bin2hex(random_bytes(6));
        $list[] = ['id' => $id, 'time' => time(), 'seen' => false] + $v;
        if (count($list) > VIOLATIONS_KEEP) $list = array_slice($list, -VIOLATIONS_KEEP);
    });
    return $id;
}

function rai_violations() { return load_json('violations.json', []); }
