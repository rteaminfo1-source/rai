<?php
/*
 * Вкладка «Rai» админ-панели rteam.info: подписки Rai (rai.rteam.info).
 *   — статистика: пользователи, подписчики, доход, нейросеть сегодня;
 *   — выдать или снять подписку по логину пользователя Rai;
 *   — поиск пользователей, список подписчиков, платежи Platega, журнал;
 *   — цены, лимиты и описания тарифов.
 *
 * Положите этот файл рядом с admin.php. Связь с rai.rteam.info — через admin_api.php, каждый запрос подписан
 * ключом (HMAC-SHA256). Ключ — одинаковый в config.php на rai.rteam.info (ADMIN_API_KEY) и здесь
 * (вкладка «Rai» → «Подключение», хранится в settings.json; или константа RAI_ADMIN_KEY).
 *
 * Права: смотреть и выдавать подписки — «users.manage», подключение и тарифы — «settings.manage».
 */

const RAI_PLAN_KEYS = ['plus', 'premium', 'ultra'];
const RAI_DEFAULT_URL = 'https://rai.rteam.info/admin_api.php';

function rai_conf() {
    global $settings;
    $url = trim((string)($settings['rai_api_url'] ?? '')) ?: (defined('RAI_ADMIN_URL') ? RAI_ADMIN_URL : RAI_DEFAULT_URL);
    $key = trim((string)($settings['rai_api_key'] ?? '')) ?: (defined('RAI_ADMIN_KEY') ? RAI_ADMIN_KEY : (getenv('RAI_ADMIN_KEY') ?: ''));
    return ['url' => $url, 'key' => $key, 'ready' => strlen($key) >= 32];
}

/** Подписанный запрос к rai.rteam.info/admin_api.php. Возвращает массив ответа (ok, error, …). */
function rai_api($action, array $data = []) {
    global $user;
    $c = rai_conf();
    if (!$c['ready']) return ['ok' => false, 'error' => 'Не задан ключ подключения (от 32 символов).'];
    $body = json_encode(['action' => $action, 'nonce' => bin2hex(random_bytes(12)), 'admin' => (string)$user] + $data, JSON_UNESCAPED_UNICODE);
    $time = time();
    $headers = ['Content-Type: application/json', 'X-Rai-Time: ' . $time,
                'X-Rai-Signature: ' . hash_hmac('sha256', $time . "\n" . $body, $c['key'])];
    if (function_exists('curl_init')) {
        $ch = curl_init($c['url']);
        curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $body, CURLOPT_HTTPHEADER => $headers,
                                CURLOPT_RETURNTRANSFER => true, CURLOPT_CONNECTTIMEOUT => 6, CURLOPT_TIMEOUT => 15]);
        $raw = curl_exec($ch);
        $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err = curl_error($ch);
        curl_close($ch);
    } else {
        $ctx = stream_context_create(['http' => ['method' => 'POST', 'header' => implode("\r\n", $headers), 'content' => $body,
                                                 'timeout' => 15, 'ignore_errors' => true]]);
        $raw = @file_get_contents($c['url'], false, $ctx);
        $code = isset($http_response_header[0]) && preg_match('/\s(\d{3})\s/', $http_response_header[0], $m) ? (int)$m[1] : 0;
        $err = $raw === false ? 'нет связи' : '';
    }
    $res = json_decode((string)$raw, true);
    if (!is_array($res)) {
        return ['ok' => false, 'error' => $code ? "rai.rteam.info ответил кодом $code (нет admin_api.php или ошибка PHP)" : 'Нет связи с rai.rteam.info' . ($err ? ": $err" : '')];
    }
    return $res;
}

function rai_log($msg) {
    global $logs;
    $logs[] = ['time' => date('Y-m-d H:i:s'), 'type' => 'rai', 'msg' => $msg];
    save_json('logs.json', $logs);
}

function rai_back($extra = '') {
    header('Location: admin.php?tab=rai' . $extra);
    exit;
}

/** Обработка форм вкладки (вызывается из admin.php при POST на ?tab=rai). */
function rai_admin_post() {
    global $settings, $user;
    $action = (string)($_POST['action'] ?? '');

    if ($action === 'rai_save') {
        $url = trim((string)($_POST['rai_api_url'] ?? ''));
        if ($url !== '' && !preg_match('~^https?://[^\s]+$~', $url)) { flash('Адрес должен начинаться с https://', 'error'); rai_back(); }
        $settings['rai_api_url'] = $url;
        $key = trim((string)($_POST['rai_api_key'] ?? ''));
        if ($key !== '') {
            if (strlen($key) < 32) { flash('Ключ слишком короткий — нужно от 32 символов.', 'error'); rai_back(); }
            $settings['rai_api_key'] = $key;
        }
        if (!empty($_POST['clear_key'])) unset($settings['rai_api_key']);
        save_json('settings.json', $settings);
        $ping = rai_api('ping');
        rai_log("$user изменил подключение к Rai");
        flash($ping['ok'] ?? false ? '✅ Подключено к ' . ($ping['site'] ?? 'rai.rteam.info') : 'Сохранено, но связи нет: ' . ($ping['error'] ?? '?'), ($ping['ok'] ?? false) ? 'success' : 'error');
        rai_back();
    }

    if ($action === 'rai_check') {
        $ping = rai_api('ping');
        flash(($ping['ok'] ?? false) ? '✅ Связь есть. Platega: ' . (!empty($ping['platega']) ? 'подключена' : 'ещё не настроена') : 'Нет связи: ' . ($ping['error'] ?? '?'),
              ($ping['ok'] ?? false) ? 'success' : 'error');
        rai_back();
    }

    if ($action === 'rai_grant') {
        $login = strtolower(trim((string)($_POST['login'] ?? '')));
        $plan = (string)($_POST['plan'] ?? '');
        $days = (int)($_POST['days'] ?? 0) === -1 ? (int)($_POST['days_custom'] ?? 0) : (int)($_POST['days'] ?? 0);
        $note = trim((string)($_POST['note'] ?? ''));
        if ($login === '' || !in_array($plan, RAI_PLAN_KEYS, true) || $days < 1) { flash('Укажите логин, тариф и срок.', 'error'); rai_back(); }
        $r = rai_api('grant', ['login' => $login, 'plan' => $plan, 'days' => $days, 'note' => $note]);
        if (!empty($r['ok'])) {
            $u = $r['user'];
            rai_log("$user выдал подписку Rai «{$u['plan_name']}» пользователю {$u['login']} на $days дн." . ($note !== '' ? " ($note)" : ''));
            flash("🎁 {$u['login']}: «{$u['plan_name']}» до " . date('d.m.Y', (int)$u['until']), 'success');
        } else {
            flash($r['error'] ?? 'Не получилось выдать подписку', 'error');
        }
        rai_back('&q=' . urlencode($login));
    }

    if ($action === 'rai_revoke') {
        $login = strtolower(trim((string)($_POST['login'] ?? '')));
        $r = rai_api('revoke', ['login' => $login]);
        if (!empty($r['ok'])) { rai_log("$user снял подписку Rai у $login"); flash("Подписка $login снята — теперь тариф «Старт».", 'success'); }
        else flash($r['error'] ?? 'Не получилось', 'error');
        rai_back();
    }

    if ($action === 'rai_plans') {
        $in = [];
        foreach (array_merge(['free'], RAI_PLAN_KEYS) as $k) {
            $row = $_POST['plan'][$k] ?? null;
            if (!is_array($row)) continue;
            $in[$k] = [
                'name' => (string)($row['name'] ?? ''), 'tagline' => (string)($row['tagline'] ?? ''),
                'neuro_day' => (int)($row['neuro_day'] ?? 0),
                'features' => array_values(array_filter(array_map('trim', preg_split('/\R/', (string)($row['features'] ?? ''))))),
            ];
            if ($k !== 'free') $in[$k]['price'] = (int)($row['price'] ?? 0);
        }
        $r = rai_api('plans_save', ['plans' => $in]);
        if (!empty($r['ok'])) { rai_log("$user изменил тарифы Rai"); flash('Тарифы сохранены — на сайте уже новые цены.', 'success'); }
        else flash($r['error'] ?? 'Не получилось сохранить', 'error');
        rai_back('#plans');
    }

    if ($action === 'rai_plans_reset') {
        $r = rai_api('plans_reset');
        if (!empty($r['ok'])) { rai_log("$user сбросил тарифы Rai"); flash('Тарифы сброшены к стандартным.', 'success'); }
        else flash($r['error'] ?? 'Не получилось', 'error');
        rai_back('#plans');
    }

    rai_back();
}

function rai_h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
function rai_rub($n) { return number_format((int)$n, 0, ',', ' ') . ' ₽'; }
function rai_date($ts) { return $ts ? date('d.m.Y', (int)$ts) : '—'; }
function rai_left($ts) {
    if (!$ts) return '';
    $d = (int)ceil(((int)$ts - time()) / 86400);
    return $d <= 0 ? 'истекает сегодня' : 'ещё ' . $d . ' дн.';
}

/** Содержимое вкладки «Rai». */
function rai_admin_render() {
    $c = rai_conf();
    $can_users = can('users.manage');
    $can_settings = can('settings.manage');
    $stats = $c['ready'] ? rai_api('stats') : ['ok' => false, 'error' => null];
    $ok = !empty($stats['ok']);
    $plans = $ok ? $stats['plans'] : [];
    $q = trim((string)($_GET['q'] ?? ''));
    $found = ($ok && $q !== '') ? rai_api('search', ['q' => $q]) : null;
    $status_names = ['paid' => ['Оплачен', 'badge-acc'], 'pending' => ['Ждёт оплату', 'badge-warn'], 'new' => ['Создан', 'badge-viewed'],
                     'canceled' => ['Отменён', 'badge-dec'], 'error' => ['Ошибка', 'badge-dec'], 'refunded' => ['Возврат', 'badge-dec'],
                     'underpaid' => ['Недоплата', 'badge-warn']];
    $plan_name = function ($k) use ($plans) { return $plans[$k]['name'] ?? $k; };
    ?>
    <style>
      .rai-hero { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; padding: 18px 20px; border-radius: 16px; border: 1px solid var(--line);
        background: radial-gradient(120% 140% at 100% 0%, rgba(255, 45, 45, .18), transparent 55%), radial-gradient(100% 120% at 0% 100%, rgba(139, 92, 255, .14), transparent 60%), var(--panel); }
      .rai-logo { width: 52px; height: 52px; border-radius: 15px; display: grid; place-items: center; font-weight: 800; font-size: 24px; color: #fff;
        background: linear-gradient(135deg, #ff2d2d, #ff3d81 55%, #8b5cff); box-shadow: 0 10px 30px -10px rgba(255, 45, 45, .7); }
      .rai-hero h2 { margin: 0; } .rai-hero p { margin: 4px 0 0; }
      .rai-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
      .rai-grid .card { margin-top: 14px; }
      .rai-plans { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
      .rai-plan { border: 1px solid var(--line); border-radius: 12px; padding: 12px; background: var(--panel-2, #12121a); }
      .rai-plan textarea { min-height: 96px; }
      .rai-plan h4 { margin: 0 0 6px; }
      .rai-days { display: flex; gap: 6px; flex-wrap: wrap; margin: 4px 0 8px; }
      .rai-days label { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--line); cursor: pointer; font-size: 13px; }
      .rai-days input { width: auto; margin: 0; }
      .rai-days label:has(input:checked) { border-color: #ff3d81; background: rgba(255, 61, 129, .12); }
    </style>

    <div class="rai-hero">
      <div class="rai-logo">R</div>
      <div style="flex:1; min-width:220px;">
        <h2>Rai — подписки</h2>
        <p class="muted">rai.rteam.info: тарифы, оплата через Platega и выдача подписок вручную по логину Rai.</p>
      </div>
      <div class="chips">
        <span class="chip <?= $ok ? 'on' : '' ?>"><?= $ok ? '✓ Подключено' : ($c['ready'] ? '✗ Нет связи' : 'Не настроено') ?></span>
        <?php if ($ok): ?><span class="chip <?= !empty($stats['platega']) ? 'on' : '' ?>">Platega: <?= !empty($stats['platega']) ? 'подключена' : 'не настроена' ?></span><?php endif; ?>
        <a class="btn ghost sm" href="https://rai.rteam.info/" target="_blank" rel="noopener">Открыть сайт ↗</a>
      </div>
    </div>

    <?php if (!$c['ready']): ?>
      <div class="callout warn"><span class="c-ico">🔑</span><div><b>Подключите Rai.</b> Придумайте длинный случайный ключ (от 32 символов),
        впишите его в <code>config.php</code> на rai.rteam.info (<code>ADMIN_API_KEY</code>) и сюда — в «Подключение» ниже.</div></div>
    <?php elseif (!$ok): ?>
      <div class="callout danger"><span class="c-ico">⚠️</span><div><b>Нет связи с rai.rteam.info:</b> <?= rai_h($stats['error'] ?? '?') ?></div></div>
    <?php endif; ?>

    <?php if ($ok): ?>
      <div class="kpi-grid">
        <div class="kpi"><div class="k-ico">👤</div><div class="k-num"><?= (int)$stats['users'] ?></div><div class="k-lbl">аккаунтов · +<?= (int)$stats['new_week'] ?> за неделю</div></div>
        <div class="kpi hot"><div class="k-ico">⭐</div><div class="k-num"><?= (int)$stats['subscribers'] ?></div><div class="k-lbl">активных подписок</div></div>
        <div class="kpi"><div class="k-ico">📈</div><div class="k-num"><?= rai_rub($stats['mrr']) ?></div><div class="k-lbl">в месяц по текущим подпискам</div></div>
        <div class="kpi"><div class="k-ico">💳</div><div class="k-num"><?= rai_rub($stats['revenue_month']) ?></div><div class="k-lbl">оплачено в этом месяце · всего <?= rai_rub($stats['revenue_total']) ?></div></div>
        <div class="kpi"><div class="k-ico">🧠</div><div class="k-num"><?= (int)$stats['neuro_today'] ?></div><div class="k-lbl">сообщений нейросети сегодня · <?= (int)$stats['neuro_people_today'] ?> чел.</div></div>
        <?php foreach (RAI_PLAN_KEYS as $k): ?>
          <div class="kpi"><div class="k-ico"><?= ['plus' => '✦', 'premium' => '💎', 'ultra' => '🚀'][$k] ?></div><div class="k-num"><?= (int)($stats['by_plan'][$k] ?? 0) ?></div><div class="k-lbl">«<?= rai_h($plan_name($k)) ?>» · <?= rai_rub($plans[$k]['price'] ?? 0) ?>/мес</div></div>
        <?php endforeach; ?>
      </div>
    <?php endif; ?>

    <div class="rai-grid">
      <?php if ($ok && $can_users): ?>
      <div class="card">
        <h3>🎁 Выдать подписку</h3>
        <p class="meta">Логин — как в кабинете rai.rteam.info (или почта). Тот же тариф продлевается, другой — начинается сейчас.</p>
        <form method="POST" action="?tab=rai">
          <input type="hidden" name="action" value="rai_grant">
          <label>Логин пользователя Rai</label>
          <input type="text" name="login" value="<?= rai_h($q) ?>" placeholder="например: anya" required autocomplete="off" list="raiLogins">
          <label>Тариф</label>
          <select name="plan"><?php foreach (RAI_PLAN_KEYS as $k): ?><option value="<?= $k ?>"<?= $k === 'premium' ? ' selected' : '' ?>><?= rai_h($plan_name($k)) ?> — <?= rai_rub($plans[$k]['price'] ?? 0) ?>/мес · <?= !empty($plans[$k]['neuro_day']) ? (int)$plans[$k]['neuro_day'] . ' сообщ./день' : 'без лимита' ?></option><?php endforeach; ?></select>
          <label>Срок</label>
          <div class="rai-days">
            <?php foreach ([7 => '7 дней', 30 => 'Месяц', 90 => '3 месяца', 180 => 'Полгода', 365 => 'Год', -1 => 'Своё'] as $d => $l): ?>
              <label><input type="radio" name="days" value="<?= $d ?>"<?= $d === 30 ? ' checked' : '' ?>> <?= $l ?></label>
            <?php endforeach; ?>
          </div>
          <input type="number" name="days_custom" min="1" max="3660" placeholder="Своё: сколько дней">
          <label>Комментарий (видно в журнале)</label>
          <input type="text" name="note" maxlength="150" placeholder="например: победитель розыгрыша">
          <button class="btn primary" type="submit" style="margin-top:10px;">Выдать подписку</button>
        </form>
      </div>
      <?php endif; ?>

      <?php if ($ok): ?>
      <div class="card">
        <h3>🔎 Найти пользователя Rai</h3>
        <form method="GET" class="row" style="gap:8px;">
          <input type="hidden" name="tab" value="rai">
          <input type="text" name="q" value="<?= rai_h($q) ?>" placeholder="Логин, имя или почта" style="flex:1; margin:0;">
          <button class="btn ghost" type="submit" style="margin:0;">Найти</button>
        </form>
        <?php if ($found !== null): ?>
          <?php if (empty($found['ok'])): ?><p class="muted"><?= rai_h($found['error'] ?? 'Ошибка поиска') ?></p>
          <?php elseif (!$found['users']): ?><p class="muted">Никого не нашлось.</p>
          <?php else: ?>
            <ul class="list">
              <?php foreach ($found['users'] as $u): ?>
                <li><span><b><?= rai_h($u['login']) ?></b> <span class="muted">· <?= rai_h($u['name']) ?><?= $u['email'] ? ' · ' . rai_h($u['email']) : '' ?></span><br>
                  <span class="chip <?= $u['plan'] !== 'free' ? 'on' : '' ?>"><?= rai_h($u['plan_name']) ?><?= $u['until'] ? ' до ' . rai_date($u['until']) : '' ?></span>
                  <span class="muted" style="font-size:12px;">нейросеть сегодня: <?= (int)$u['neuro_today'] ?> · с <?= rai_date($u['created']) ?></span></span>
                  <?php if ($can_users): ?><span class="row" style="gap:6px;">
                    <form method="POST" action="?tab=rai" style="margin:0;"><input type="hidden" name="action" value="rai_grant"><input type="hidden" name="login" value="<?= rai_h($u['login']) ?>"><input type="hidden" name="plan" value="premium"><input type="hidden" name="days" value="30"><button class="btn ghost sm" type="submit" title="Выдать «Премиум» на 30 дней">+30 дн. Премиум</button></form>
                    <?php if ($u['plan'] !== 'free'): ?><form method="POST" action="?tab=rai" style="margin:0;" onsubmit="return confirm('Снять подписку у <?= rai_h($u['login']) ?>?');"><input type="hidden" name="action" value="rai_revoke"><input type="hidden" name="login" value="<?= rai_h($u['login']) ?>"><button class="btn ghost sm" type="submit">Снять</button></form><?php endif; ?>
                  </span><?php endif; ?></li>
              <?php endforeach; ?>
            </ul>
            <datalist id="raiLogins"><?php foreach ($found['users'] as $u): ?><option value="<?= rai_h($u['login']) ?>"><?php endforeach; ?></datalist>
          <?php endif; ?>
        <?php endif; ?>
      </div>
      <?php endif; ?>
    </div>

    <?php if ($ok): ?>
    <div class="card">
      <h3>⭐ Подписчики (<?= count($stats['subs']) ?>)</h3>
      <?php if (!$stats['subs']): ?><p class="muted">Пока никого — выдайте подписку или дождитесь первой оплаты.</p><?php else: ?>
      <input type="text" placeholder="Фильтр…" oninput="filterRows('raiSubs', this.value)" style="max-width:280px;">
      <div class="tbl-wrap"><table class="tbl" id="raiSubs">
        <thead><tr><th>Логин</th><th>Тариф</th><th>До</th><th>Откуда</th><th>Нейросеть сегодня</th><th></th></tr></thead>
        <tbody>
        <?php foreach ($stats['subs'] as $u): ?>
          <tr><td><b><?= rai_h($u['login']) ?></b><br><span class="muted" style="font-size:12px;"><?= rai_h($u['email'] ?: $u['name']) ?></span></td>
            <td><span class="badge badge-gold"><?= rai_h($u['plan_name']) ?></span></td>
            <td><?= rai_date($u['until']) ?><br><span class="muted" style="font-size:12px;"><?= rai_left($u['until']) ?></span></td>
            <td><?= $u['source'] === 'platega' ? '💳 оплата' : '🎁 выдано' ?><br><span class="muted" style="font-size:12px;"><?= rai_h($u['note']) ?></span></td>
            <td><?= (int)$u['neuro_today'] ?></td>
            <td><?php if ($can_users): ?><form method="POST" action="?tab=rai" style="margin:0;" onsubmit="return confirm('Снять подписку у <?= rai_h($u['login']) ?>?');"><input type="hidden" name="action" value="rai_revoke"><input type="hidden" name="login" value="<?= rai_h($u['login']) ?>"><button class="btn ghost sm" type="submit">Снять</button></form><?php endif; ?></td></tr>
        <?php endforeach; ?>
        </tbody></table></div>
      <?php endif; ?>
    </div>

    <div class="card">
      <h3>💳 Платежи Platega</h3>
      <?php if (!$stats['orders']): ?><p class="muted">Платежей ещё не было.</p><?php else: ?>
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr><th>Заказ</th><th>Логин</th><th>Тариф</th><th>Сумма</th><th>Статус</th><th>Дата</th></tr></thead>
        <tbody>
        <?php foreach ($stats['orders'] as $o): $st = $status_names[$o['status']] ?? [$o['status'], 'badge-viewed']; ?>
          <tr><td><code><?= rai_h($o['id']) ?></code></td><td><?= rai_h($o['login']) ?></td>
            <td><?= rai_h($plan_name($o['plan'])) ?> · <?= (int)$o['months'] >= 12 ? 'год' : 'месяц' ?></td>
            <td><?= rai_rub($o['amount']) ?></td><td><span class="badge <?= $st[1] ?>"><?= rai_h($st[0]) ?></span><?= !empty($o['error']) ? '<br><span class="muted" style="font-size:12px;">' . rai_h($o['error']) . '</span>' : '' ?></td>
            <td><?= date('d.m.Y H:i', (int)($o['paid_at'] ?? $o['created'])) ?></td></tr>
        <?php endforeach; ?>
        </tbody></table></div>
      <?php endif; ?>
    </div>

    <?php if ($stats['log']): ?>
    <div class="card">
      <h3>📜 Журнал подписок</h3>
      <ul class="list">
        <?php foreach ($stats['log'] as $l):
          $what = ['grant' => '🎁 Выдана', 'revoke' => '✖ Снята', 'payment' => '💳 Оплата', 'refund' => '↩ Возврат', 'plans' => '🏷 Тарифы'][$l['type']] ?? $l['type']; ?>
          <li><span><b><?= $what ?></b> <?= rai_h($l['login']) ?><?= $l['plan'] && $l['plan'] !== 'free' ? ' · «' . rai_h($plan_name($l['plan'])) . '»' : '' ?><?= $l['days'] ? ' · ' . (int)$l['days'] . ' дн.' : '' ?>
            <?= $l['note'] ? '<span class="muted"> — ' . rai_h($l['note']) . '</span>' : '' ?><?= $l['by'] ? '<span class="muted"> · ' . rai_h($l['by']) . '</span>' : '' ?></span>
            <span class="muted" style="font-size:12px; white-space:nowrap;"><?= date('d.m.Y H:i', (int)$l['time']) ?></span></li>
        <?php endforeach; ?>
      </ul>
    </div>
    <?php endif; ?>

    <?php if ($can_settings): ?>
    <div class="card" id="plans">
      <h3>🏷 Тарифы и лимиты</h3>
      <p class="meta">Цены — в рублях за месяц (год — со скидкой 25%). «Сообщений в день» — лимит нейросети, 0 — без ограничений. Без входа — <?= (int)$stats['guest_limit'] ?> в день.
        Одна строка в «Что входит» — один пункт на карточке тарифа.</p>
      <form method="POST" action="?tab=rai">
        <input type="hidden" name="action" value="rai_plans">
        <div class="rai-plans">
          <?php foreach (array_merge(['free'], RAI_PLAN_KEYS) as $k): $p = $plans[$k] ?? []; ?>
            <div class="rai-plan">
              <h4><?= $k === 'free' ? '🆓 Бесплатный' : ['plus' => '✦', 'premium' => '💎', 'ultra' => '🚀'][$k] . ' Платный' ?></h4>
              <label>Название</label><input type="text" name="plan[<?= $k ?>][name]" value="<?= rai_h($p['name'] ?? '') ?>" maxlength="30">
              <?php if ($k !== 'free'): ?><label>Цена, ₽ в месяц</label><input type="number" name="plan[<?= $k ?>][price]" value="<?= (int)($p['price'] ?? 0) ?>" min="1"><?php endif; ?>
              <label>Сообщений нейросети в день</label><input type="number" name="plan[<?= $k ?>][neuro_day]" value="<?= (int)($p['neuro_day'] ?? 0) ?>" min="0">
              <label>Подзаголовок</label><input type="text" name="plan[<?= $k ?>][tagline]" value="<?= rai_h($p['tagline'] ?? '') ?>" maxlength="80">
              <label>Что входит</label><textarea name="plan[<?= $k ?>][features]"><?= rai_h(implode("\n", $p['features'] ?? [])) ?></textarea>
            </div>
          <?php endforeach; ?>
        </div>
        <div class="row" style="gap:8px; margin-top:12px;">
          <button class="btn primary" type="submit">Сохранить тарифы</button>
          <button class="btn ghost" type="submit" form="raiReset">Сбросить к стандартным</button>
        </div>
      </form>
      <form method="POST" action="?tab=rai" id="raiReset" onsubmit="return confirm('Вернуть стандартные цены и описания?');"><input type="hidden" name="action" value="rai_plans_reset"></form>
    </div>
    <?php endif; ?>
    <?php endif; ?>

    <?php if ($can_settings): ?>
    <div class="card">
      <h3>⚙️ Подключение к rai.rteam.info</h3>
      <form method="POST" action="?tab=rai">
        <input type="hidden" name="action" value="rai_save">
        <label>Адрес API (пусто — <?= rai_h(RAI_DEFAULT_URL) ?>)</label>
        <input type="text" name="rai_api_url" value="<?= rai_h($GLOBALS['settings']['rai_api_url'] ?? '') ?>" placeholder="<?= rai_h(RAI_DEFAULT_URL) ?>">
        <label>Ключ (ADMIN_API_KEY из config.php на rai.rteam.info) <?= $c['ready'] ? '· ✓ задан' : '' ?></label>
        <input type="password" name="rai_api_key" value="" autocomplete="new-password" placeholder="<?= $c['ready'] ? 'оставьте пустым, чтобы не менять' : 'длинная случайная строка, от 32 символов' ?>">
        <?php if (!empty($GLOBALS['settings']['rai_api_key'])): ?><label class="switch-row" style="margin-top:6px;"><input type="checkbox" name="clear_key"> убрать ключ из админки</label><?php endif; ?>
        <div class="row" style="gap:8px; margin-top:10px;">
          <button class="btn primary" type="submit">Сохранить и проверить</button>
          <button class="btn ghost" type="submit" form="raiCheck">Проверить связь</button>
        </div>
      </form>
      <form method="POST" action="?tab=rai" id="raiCheck"><input type="hidden" name="action" value="rai_check"></form>
      <ol class="muted" style="margin:12px 0 0; padding-left:20px; line-height:1.6; font-size:13px;">
        <li>Придумайте ключ: 64 случайных символа (0-9, a-f).</li>
        <li>Впишите его в <code>config.php</code> на rai.rteam.info: <code>define('ADMIN_API_KEY', '…')</code>.</li>
        <li>Вставьте тот же ключ сюда и нажмите «Сохранить и проверить».</li>
        <li>Platega: впишите Merchant ID и секрет в тот же <code>config.php</code>, а в кабинете Platega укажите адрес уведомлений
          <code>https://rai.rteam.info/pay_callback.php</code>.</li>
      </ol>
    </div>
    <?php endif; ?>
    <?php
}
