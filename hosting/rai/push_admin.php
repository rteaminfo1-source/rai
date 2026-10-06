<?php
/*
 * Включить уведомления админ-панели на этом устройстве (телефон, компьютер). Сюда ведёт кнопка во вкладке
 * «Rai: уведомления» админ-панели: ссылка подписана ключом ADMIN_API_KEY и действует 1 час.
 * Приходят: новые нарушения правил, оплаты, новые пользователи — даже когда браузер закрыт.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/push.php';

$exp = (int)($_GET['exp'] ?? 0);
$back = (string)($_GET['back'] ?? '');
$t = (string)($_GET['t'] ?? '');
$admin = mb_substr((string)($_GET['admin'] ?? ''), 0, 40);
$back_ok = (bool)preg_match('~^https?://[^\s"<>]+$~', $back);
$valid = $back_ok && push_admin_token_ok($exp, $back, $t);
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');
page_head('Уведомления админ-панели — Rai');
?>
<main style="width:min(640px,100% - 32px);margin:40px auto 60px;">
  <section class="panel">
    <h2>🔔 Уведомления админ-панели</h2>
    <?php if (!push_ready()): ?>
      <p class="error">На хостинге rai.rteam.info нет PHP-расширений openssl или curl — push-уведомления не работают. Включите их в панели хостинга.</p>
    <?php elseif (!$valid): ?>
      <p class="error">Ссылка устарела или неверная. Откройте её заново: админ-панель → вкладка «Rai: уведомления» → «Получать на этом устройстве».</p>
      <?php if ($back_ok): ?><p><a class="btn ghost" href="<?= h($back) ?>?tab=rai_push">← В админ-панель</a></p><?php endif; ?>
    <?php else: ?>
      <p class="muted">Уведомления будут приходить на это устройство, даже когда браузер закрыт (на телефоне — и на заблокированный экран).
        Нажмёте на уведомление — откроется нужная вкладка админ-панели.</p>
      <fieldset style="border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:0">
        <legend class="muted" style="padding:0 6px">Что присылать</legend>
        <?php foreach (PUSH_ADMIN_EVENTS as $k => $label): ?>
          <label style="display:flex;gap:8px;align-items:center;margin:6px 0"><input type="checkbox" name="ev" value="<?= h($k) ?>" checked> <?= h($label) ?></label>
        <?php endforeach; ?>
      </fieldset>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn" id="on" type="button">🔔 Включить на этом устройстве</button>
        <button class="btn ghost" id="test" type="button" hidden>Отправить проверочное</button>
        <button class="btn ghost" id="off" type="button" hidden>Отключить</button>
      </div>
      <p id="state" class="muted" aria-live="polite"></p>
      <p class="muted" style="font-size:13px">На iPhone и iPad (iOS 16.4+): откройте эту страницу в Safari → «Поделиться» → «На экран „Домой“»,
        запустите Rai с экрана «Домой» и нажмите кнопку здесь ещё раз.</p>
      <p><a href="<?= h($back) ?>?tab=rai_push">← Вернуться в админ-панель</a></p>
      <script>
      (function () {
        "use strict";
        const CFG = <?= json_encode(['exp' => $exp, 'back' => $back, 't' => $t, 'admin' => $admin], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) ?>;
        const $ = (id) => document.getElementById(id);
        const say = (t) => { $("state").textContent = t; };
        const SCOPE = "./push_admin.php";   // своя регистрация — не мешает уведомлениям чата в этом же браузере
        function key(b64) {
          const raw = atob(b64.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((b64.length + 3) % 4));
          return Uint8Array.from(raw, (c) => c.charCodeAt(0));
        }
        async function post(data) {
          const r = await fetch("push_api.php", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
          const j = await r.json().catch(() => ({ok: false, error: "Сервер ответил с ошибкой " + r.status}));
          if (!j.ok) throw new Error(j.error || "Ошибка " + r.status);
          return j;
        }
        async function registration() {
          const reg = await navigator.serviceWorker.register("sw.php", {scope: SCOPE});
          if (reg.active) return reg;
          await new Promise((resolve) => {
            const w = reg.installing || reg.waiting;
            if (!w) return resolve();
            w.addEventListener("statechange", () => { if (w.state === "activated") resolve(); });
          });
          return reg;
        }
        async function current() {
          if (!("serviceWorker" in navigator)) return null;
          const reg = await navigator.serviceWorker.getRegistration(SCOPE);
          return reg ? reg.pushManager.getSubscription() : null;
        }
        function shown(on) { $("test").hidden = $("off").hidden = !on; $("on").textContent = on ? "🔔 Сохранить настройки" : "🔔 Включить на этом устройстве"; }
        $("on").addEventListener("click", async () => {
          $("on").disabled = true;
          try {
            if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
              throw new Error("Этот браузер не умеет push-уведомления. Подойдут Chrome, Edge, Firefox, Opera, Яндекс Браузер или Safari.");
            }
            const perm = await Notification.requestPermission();
            if (perm !== "granted") throw new Error("Уведомления запрещены. Разрешите их в настройках сайта (значок замка слева от адреса) и нажмите ещё раз.");
            say("Подключаю…");
            const reg = await registration();
            const info = await (await fetch("push_api.php", {cache: "no-store"})).json();
            if (!info.ready || !info.key) throw new Error("На сервере не включены уведомления.");
            let sub = await reg.pushManager.getSubscription();
            if (!sub) sub = await reg.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: key(info.key)});
            const events = Array.from(document.querySelectorAll("input[name=ev]:checked")).map((i) => i.value);
            await post(Object.assign({action: "admin_subscribe", subscription: sub.toJSON(), events: events}, CFG));
            say("✅ Готово: уведомления админ-панели включены на этом устройстве.");
            shown(true);
          } catch (e) { say("⚠️ " + e.message); } finally { $("on").disabled = false; }
        });
        $("test").addEventListener("click", async () => {
          try { const sub = await current(); await post({action: "test", endpoint: sub.endpoint}); say("Отправил — уведомление придёт через пару секунд."); }
          catch (e) { say("⚠️ " + e.message); }
        });
        $("off").addEventListener("click", async () => {
          try {
            const sub = await current();
            if (sub) { await post({action: "unsubscribe", endpoint: sub.endpoint}); await sub.unsubscribe(); }
            say("Уведомления на этом устройстве выключены."); shown(false);
          } catch (e) { say("⚠️ " + e.message); }
        });
        current().then((s) => { if (s) { shown(true); say("Уведомления на этом устройстве уже включены."); } }).catch(() => null);
      })();
      </script>
    <?php endif; ?>
  </section>
</main>
<?php page_foot();
