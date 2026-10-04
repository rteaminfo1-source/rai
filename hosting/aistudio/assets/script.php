<?php /* Скрипт студии: кнопки, предпросмотр, API-ключи. Подключается в страницы через include. */ ?>
<script>
/* AI Studio: кнопки студии -> actions.php */
(function () {
  "use strict";
  const csrf = document.querySelector('meta[name="csrf"]').content;
  const $ = (id) => document.getElementById(id);

  function say(text, mine) {
    const p = document.createElement("p");
    if (mine) p.className = "me";
    p.textContent = text;
    $("log").append(p);
    $("log").scrollTop = $("log").scrollHeight;
  }

  async function call(action, fields) {
    const body = new URLSearchParams(Object.assign({a: action, csrf: csrf}, fields || {}));
    const r = await fetch("actions.php", {method: "POST", body: body, credentials: "same-origin",
                                          headers: {"X-CSRF-Token": csrf}});
    const data = await r.json().catch(() => ({error: "Сервер ответил не JSON (" + r.status + ")"}));
    if (!r.ok || data.error) throw new Error(data.error || "Ошибка " + r.status);
    return data;
  }

  // что сейчас за сайт: mode — template (шаблон), neuro-spec (тексты нейросети + дизайн студии), neuro (код написала нейросеть)
  const site = {mode: null, html: null, spec: null, prompt: ""};
  function remember(d) {
    if (!d) return;
    for (const k of ["mode", "html", "spec"]) if (k in d) site[k] = d[k];
    if (d.prompt) site.prompt = d.prompt;
  }
  function step(text) {
    const el = $("aiStep");
    if (!el) return;
    el.hidden = !text;
    el.textContent = text || "";
  }
  const took = (s) => s >= 60 ? Math.floor(s / 60) + " мин " + (s % 60) + " с" : (s || 1) + " с";

  function showPreview(html) {
    $("preview").srcdoc = html || "<p style='font:16px sans-serif;padding:24px;color:#666'>Здесь появится ваш сайт.</p>";
  }
  function setPublished(on) {
    $("pubState").textContent = on ? "Опубликован" : "Не опубликован";
    $("pubState").classList.toggle("on", on);
    $("openBtn").hidden = !on;
    $("unpubBtn").hidden = !on;
  }

  function renderKeys(keys) {
    const tb = $("keys");
    tb.textContent = "";
    if (!keys.length) { tb.innerHTML = '<tr><td colspan="5" class="muted">Ключей пока нет.</td></tr>'; return; }
    for (const k of keys) {
      const tr = document.createElement("tr");
      for (const v of [k.prefix + "…", k.label || "—", k.created, k.last_used || "ещё нет"]) {
        const td = document.createElement("td"); td.textContent = v; tr.append(td);
      }
      const td = document.createElement("td");
      const b = document.createElement("button");
      b.className = "btn ghost small"; b.type = "button"; b.textContent = "Отозвать";
      b.addEventListener("click", async () => {
        if (b.dataset.sure !== "1") { b.dataset.sure = "1"; b.textContent = "Точно отозвать?"; return; }
        await call("key_revoke", {id: k.id}); load();
      });
      td.append(b); tr.append(td); tb.append(tr);
    }
  }

  async function load() {
    const r = await fetch("actions.php?a=state", {credentials: "same-origin"});
    if (r.status === 401) { location.href = "index.php"; return; }
    const d = await r.json();
    remember(d);
    showPreview(d.html);
    setPublished(d.published);
    renderKeys(d.keys || []);
  }

  async function busy(btn, fn) {
    btn.disabled = true;
    try { await fn(); } catch (e) { say(e.message); } finally { btn.disabled = false; }
  }

  // ---------------------------------------------------------------- нейросеть Rai (assets/studio_ai.php)
  const AI = () => window.StudioAI;
  const ui = {step: step, code: (html) => showPreview(html)};
  /** Работа нейросети: кнопка «Остановить», строка «что делает сейчас»; остановили — сайт остаётся прежним. */
  async function neuro(fn) {
    $("stopBtn").hidden = false;
    $("genBtn").disabled = $("editBtn").disabled = true;
    try {
      return await fn();
    } catch (e) {
      if (e instanceof AI().Stopped) { say("Остановлено — сайт остался прежним."); showPreview(site.html); return null; }
      showPreview(site.html);
      throw e;
    } finally {
      $("stopBtn").hidden = true;
      $("genBtn").disabled = $("editBtn").disabled = false;
      step("");
    }
  }
  function save(r, prompt, fresh) {
    step("Сохраняю сайт…");
    return r.kind === "spec" ? call("save_spec", {spec: JSON.stringify(r.spec), prompt: prompt, fresh: fresh ? "1" : "0"})
                             : call("save_html", {html: r.html, prompt: prompt, title: r.title || ""});
  }
  $("stopBtn").addEventListener("click", () => { step("Останавливаю…"); AI() && AI().stop(); });
  window.addEventListener("beforeunload", (e) => { if (AI() && AI().busy()) { e.preventDefault(); e.returnValue = ""; } });

  $("genBtn").addEventListener("click", () => busy($("genBtn"), async () => {
    const prompt = $("prompt").value.trim();
    if (!prompt) { $("prompt").focus(); return; }
    say(prompt, true);
    if (AI() && AI().active()) {
      const out = await neuro(async () => {
        const r = await AI().generate(prompt, ui);
        return {r: r, d: await save(r, prompt, true)};
      });
      if (!out) return;
      const rep = out.r.report || {};
      remember(Object.assign({prompt: prompt}, out.d));
      showPreview(out.d.html);
      say("🧠 " + out.d.message + " Нейросеть справилась за " + took(rep.seconds) + (rep.note ? " (" + rep.note + ")" : "") +
          (rep.issues && rep.issues.length ? ". Недочёты: " + rep.issues.join("; ") + " — их можно поправить словами ниже." : ", проверка пройдена.") +
          " Посмотрите предпросмотр и нажмите «Опубликовать».");
      return;
    }
    const d = await call("generate", {prompt: prompt});
    remember(Object.assign({prompt: prompt}, d));
    say(d.message + " Посмотрите предпросмотр и нажмите «Опубликовать».");
    showPreview(d.html);
  }));
  $("editBtn").addEventListener("click", () => busy($("editBtn"), async () => {
    const text = $("edit").value.trim();
    if (!text) { $("edit").focus(); return; }
    say(text, true);
    // сайт, код которого написала нейросеть, правится только ею — даже если выбраны быстрые шаблоны
    if (AI() && (AI().active() || site.mode === "neuro")) {
      const out = await neuro(async () => {
        const r = await AI().edit(site, text, ui, (instruction) => call("edit", {instruction: instruction}));
        if (r.server) return {d: r.server, done: null};
        return {d: await save(r, site.prompt || "", false), done: r.done};
      });
      if (!out) return;
      remember(out.d);
      showPreview(out.d.html);
      say(out.done ? "🧠 Сделано: " + out.done + "." : out.d.message);
      $("edit").value = "";
      return;
    }
    const d = await call("edit", {instruction: text});
    remember(d);
    say(d.message);
    showPreview(d.html);
    $("edit").value = "";
  }));
  $("edit").addEventListener("keydown", (e) => { if (e.key === "Enter") $("editBtn").click(); });
  $("pubBtn").addEventListener("click", () => busy($("pubBtn"), async () => {
    const d = await call("publish");
    say(d.message + " " + d.url);
    setPublished(true);
  }));
  $("unpubBtn").addEventListener("click", () => busy($("unpubBtn"), async () => {
    const d = await call("unpublish");
    say(d.message);
    setPublished(false);
  }));
  $("keyBtn").addEventListener("click", () => busy($("keyBtn"), async () => {
    const d = await call("key_create", {label: $("keyLabel").value.trim()});
    const box = $("newKey");
    box.hidden = false;
    box.innerHTML = "<b>Ваш новый ключ — скопируйте его сейчас, потом он не покажется:</b>";
    const code = document.createElement("code"); code.className = "url"; code.textContent = d.key;
    const copy = document.createElement("button"); copy.className = "btn small"; copy.type = "button"; copy.textContent = "Копировать";
    copy.addEventListener("click", () => navigator.clipboard.writeText(d.key).then(() => { copy.textContent = "Скопировано"; },
      () => { const r = document.createRange(); r.selectNodeContents(code); getSelection().removeAllRanges(); getSelection().addRange(r); }));
    box.append(code, copy);
    $("keyLabel").value = "";
    load();
  }));
  for (const b of $("examples").querySelectorAll("button")) {
    b.addEventListener("click", () => { $("prompt").value = b.textContent; $("prompt").focus(); });
  }
  load();
})();
</script>
