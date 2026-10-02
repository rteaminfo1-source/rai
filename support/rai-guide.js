/*
 * Rai Guide — помощник по сайту rteam.info: кнопка ✨ в углу любой страницы.
 *
 * Видит страницу (заголовки, разделы, кнопки, ссылки), понимает вопросы через нейросеть Rai (rai-support.js)
 * и команды «нажми …», «открой …», «покажи где …», подсвечивает нужное, сам переходит на другие страницы
 * и нажимает безопасные кнопки, ведёт пользователя по шагам (карта сайта и подсказки — site.json).
 *
 * Подключение (сайт делает это сам через _roles.php → rt_rai_widget()):
 *   RaiGuide.init({ base: "https://raw.githubusercontent.com/<владелец>/rai/<ветка>/support/", user: "login" | null })
 *
 * Чего помощник не делает: не вводит пароли, не отправляет формы за пользователя (кроме явно разрешённых
 * в site.json шагов), не нажимает «Выйти», «Удалить», «Отвязать», «Оплатить», не уходит на чужие сайты.
 * Всё, что он видит на странице, остаётся в браузере.
 */
(function (root) {
  "use strict";
  if (root.RaiGuide) return;

  const K_CHAT = "rai-guide-chat", K_TOUR = "rai-guide-tour", K_OPEN = "rai-guide-open", K_HINT = "rai-guide-hint";
  const store = {
    get(k) { try { return JSON.parse(sessionStorage.getItem(k)); } catch (e) { return null; } },
    set(k, v) { try { v == null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* приватный режим */ } },
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const norm = (t) => String(t == null ? "" : t).toLowerCase().replace(/ё/g, "е");
  const STOP = new Set("как что где когда кто это для или так все уже еще есть нет мне меня вас вам нас наш ваш при про над под без его она они мой моя мои если чтобы можно нужно надо очень тоже только там тут какой какая какие пожалуйста на в во к ко по с со у о об от до из за и а но the".split(" "));
  const stems = (t) => (norm(t).match(/[a-zа-я0-9]+/g) || []).filter((w) => w.length > 1 && !STOP.has(w)).map((w) => w.slice(0, 5));
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let cfg = {}, site = null, host = null, sh = null, ui = {}, busy = false, spotState = null;

  /* ============================== страница */

  const pageName = () => decodeURIComponent(location.pathname.split("/").pop() || "index.php");
  function onPage(target) {
    const path = String(target || "").split(/[?#]/)[0];
    const cur = pageName();
    if (path === cur) return true;
    return path === "index.php" && (cur === "" || /^index[\w-]*\.php$/.test(cur));
  }
  const pageInfo = (path) => ((site && site.pages) || []).find((p) => p.path === String(path).split(/[?#]/)[0]);
  const currentPage = () => (site && site.pages || []).find((p) => onPage(p.path));

  function visible(el) {
    if (!el || !el.getClientRects || !el.getClientRects().length) return false;
    const r = el.getBoundingClientRect(), st = getComputedStyle(el);
    return r.width > 2 && r.height > 2 && st.visibility !== "hidden" && st.display !== "none";
  }
  const textOf = (el) => (el.getAttribute("aria-label") || el.innerText || el.value || el.getAttribute("title") ||
    el.getAttribute("placeholder") || "").replace(/\s+/g, " ").trim().slice(0, 90);

  function candidates() {
    return [...document.querySelectorAll("a[href], button, summary, [role=button], input[type=submit], input[type=button], select, h1, h2, h3")]
      .filter((el) => !(host && host.contains(el)) && visible(el) && textOf(el));
  }

  function scoreText(query, text) {
    const q = stems(query), t = new Set(stems(text));
    if (!q.length || !t.size) return 0;
    let hit = 0;
    for (const w of q) if (t.has(w)) hit++;
    let s = hit / q.length;
    const nq = norm(query).trim(), nt = norm(text).trim();
    if (nt === nq) s += 1; else if (hit && nt.includes(nq)) s += 0.4;
    return s - Math.min(0.25, t.size / 80);   // при равенстве — короче и точнее
  }

  function findElement(query, filter) {
    let best = null, bestScore = 0;
    for (const el of candidates()) {
      if (filter && !filter(el)) continue;
      const s = scoreText(query, textOf(el));
      if (s > bestScore) { best = el; bestScore = s; }
    }
    return bestScore >= 0.6 ? best : null;
  }

  function findSection(query) {
    const page = currentPage();
    let best = null, bestScore = 0;
    for (const sec of (page && page.sections) || []) {
      const el = document.getElementById(sec.id);
      if (!el) continue;
      for (const kw of [sec.title, ...(sec.keywords || [])]) {
        const s = scoreText(query, kw);
        if (s > bestScore) { best = { el, sec }; bestScore = s; }
      }
    }
    return bestScore >= 0.6 ? best : null;
  }

  function findPage(query) {
    let best = null, bestScore = 0;
    for (const p of (site && site.pages) || []) {
      for (const kw of [p.title, ...(p.keywords || [])]) {
        const s = scoreText(query, kw);
        if (s > bestScore) { best = p; bestScore = s; }
      }
    }
    return bestScore >= 0.6 ? best : null;
  }

  function findStep(f) {
    if (!f) return null;
    let list = f.selector ? [...document.querySelectorAll(f.selector)] : candidates();
    if (f.text) list = list.filter((el) => norm(textOf(el) || el.textContent).includes(norm(f.text)));
    return list.find(visible) || list[0] || null;
  }
  async function waitFor(f, ms = 2500) {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) { const el = findStep(f); if (el) return el; await sleep(150); }
    return null;
  }

  /* ============================== безопасные нажатия */

  const DANGER = /(выйти|выход|logout|удал|delete|отвяз|unlink|забан|разбан|\bban\b|оплат|купить|отправить|сохранить|сменить пароль|очистить|сброс|reset|закрыть тикет)/i;
  function safeToClick(el, allowSubmit) {
    const href = (el.getAttribute && el.getAttribute("href")) || "";
    if (DANGER.test(norm(textOf(el)) + " " + norm(href))) return false;
    if (/^(javascript:|mailto:|tel:)/i.test(href)) return false;
    if (href && el.origin && el.origin !== location.origin) return false;
    if (el.target === "_blank" && href) return false;
    const submit = (el.tagName === "BUTTON" && (el.getAttribute("type") || "submit") === "submit" && el.form) ||
      (el.tagName === "INPUT" && /^(submit|image)$/i.test(el.type));
    return !submit || !!allowSubmit;
  }

  function go(url) {
    const u = new URL(url, location.href);
    if (u.origin !== location.origin) return;
    if (u.pathname === location.pathname && u.search === location.search && u.hash) {
      const t = document.getElementById(u.hash.slice(1));
      if (t) { t.scrollIntoView({ behavior: "smooth", block: "start" }); return; }
    }
    location.href = u.href;
  }

  /* ============================== подсветка */

  function placeSpot() {
    if (!spotState) return;
    const { el } = spotState;
    if (!document.contains(el)) return hideSpot(false);
    const r = el.getBoundingClientRect(), pad = 6;
    Object.assign(ui.spot.style, { left: r.left - pad + "px", top: r.top - pad + "px", width: r.width + pad * 2 + "px", height: r.height + pad * 2 + "px" });
    const tw = Math.min(320, innerWidth - 32), th = ui.tip.offsetHeight || 120;
    let top = r.bottom + 14;
    if (top + th > innerHeight - 12) top = Math.max(12, r.top - th - 14);
    const left = Math.min(Math.max(16, r.left + r.width / 2 - tw / 2), innerWidth - tw - 16);
    Object.assign(ui.tip.style, { left: left + "px", top: top + "px", width: tw + "px" });
    spotState.raf = requestAnimationFrame(placeSpot);
  }

  function showSpot(el, text, opts = {}) {
    hideSpot(false);
    return new Promise((resolve) => {
      el.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
      ui.tipText.textContent = text || "";
      ui.tipNext.textContent = opts.next ? "Дальше →" : "Понятно";
      ui.tipNext.style.display = opts.auto ? "none" : "";
      ui.layer.classList.add("on");
      spotState = { el, resolve };
      placeSpot();
      if (opts.auto) setTimeout(() => { if (spotState && spotState.el === el) hideSpot(true); }, opts.auto);
    });
  }
  function hideSpot(result) {
    if (!spotState) return;
    cancelAnimationFrame(spotState.raf);
    const { resolve } = spotState;
    spotState = null;
    ui.layer.classList.remove("on");
    resolve(result);
  }

  /* Подсветить и вернуть окно помощника, если оно было открыто */
  async function spotlight(el, text, opts) {
    const wasOpen = ui.panel.classList.contains("on");
    minimize();
    const r = await showSpot(el, text, opts);
    if (wasOpen) open(false);
    return r;
  }

  /* ============================== пошаговые подсказки */

  async function runGuide(intent, mode, from = 0, prev = null) {
    const all = ((site && site.guides) || {})[intent];
    if (!all) return false;
    // шаги «when: guest / user» — для гостя и для вошедшего; выбор запоминаем на весь путь по страницам
    const who = (prev && prev.who) || (cfg.user ? "user" : cfg.user === null ? "guest" : "unknown");
    const steps = all.filter((s) => !s.when || s.when === who || (who === "unknown" && s.when === "guest"));
    const wasOpen = ui.panel.classList.contains("on");
    for (let i = from; i < steps.length; i++) {
      const st = steps[i];
      if (st.login && cfg.user === null) {
        store.set(K_TOUR, null);
        say("Для этого нужно войти в аккаунт. Откройте «Войти», а после входа снова спросите меня — продолжу.");
        const btn = findElement("войти", (el) => el.tagName === "A");
        if (btn) await spotlight(btn, "Сначала войдите в аккаунт");
        return true;
      }
      if (!onPage(st.page)) {
        const tries = prev && prev.step === i ? (prev.tries || 0) + 1 : 1;
        if (tries > 2) { store.set(K_TOUR, null); say("Не получилось открыть нужную страницу. Возможно, нужно войти в аккаунт."); return true; }
        store.set(K_TOUR, { intent, mode, step: i, tries, who });
        const p = pageInfo(st.page);
        say(`Перехожу: ${p ? p.title : st.page}…`);
        await sleep(450);
        go(st.page + (st.hash ? "#" + st.hash : ""));
        return true;
      }
      store.set(K_TOUR, null);
      if (st.hash) {
        const h = document.getElementById(st.hash);
        if (h) { h.scrollIntoView({ behavior: "smooth", block: "start" }); await sleep(400); }
      }
      if (!st.find) { say(st.say); continue; }
      const el = await waitFor(st.find);
      if (!el) { say(st.missing || st.say); continue; }
      const last = i === steps.length - 1;
      minimize();
      if (mode === "do" && st.click && safeToClick(el, true)) {
        await showSpot(el, st.say, { auto: 1400 });
        store.set(K_TOUR, { intent, mode, step: i + 1, tries: 0, who });   // если кнопка перезагрузит страницу — продолжим после
        el.click();
        await sleep(800);
        store.set(K_TOUR, null);
        continue;
      }
      if (st.focus) { try { el.focus({ preventScroll: true }); } catch (e) { /* не поле ввода */ } }
      say(st.say, null, true);
      const ok = await showSpot(el, st.say, { next: !last, auto: mode === "do" && !last ? 2600 : 0 });
      if (!ok) break;
    }
    store.set(K_TOUR, null);
    if (wasOpen) open(false);
    return true;
  }

  /* ============================== что на странице */

  function describePage() {
    const page = currentPage();
    const chips = [], seen = new Set();
    const add = (label, el) => {
      const key = norm(label);
      if (!label || seen.has(key) || chips.length >= 12) return;
      seen.add(key);
      chips.push([label, () => spotlight(el, label.replace(/^(§|👆) /, ""))]);
    };
    for (const sec of (page && page.sections) || []) {
      const el = document.getElementById(sec.id);
      if (el && el.getClientRects().length) add("§ " + sec.title, el);   // даже если страница ещё показывает заставку
    }
    for (const el of document.querySelectorAll("main h1, main h2, section h1, section h2, h1, h2")) {
      if (!(host && host.contains(el)) && visible(el)) add("§ " + textOf(el), el);
    }
    for (const el of candidates()) {
      if (/^(A|BUTTON|SUMMARY)$/.test(el.tagName) && !el.closest("nav") && safeToClick(el)) add("👆 " + textOf(el).slice(0, 40), el);
    }
    const title = page ? page.title : (document.title || "эта страница");
    say(`Это «${title}». ${page && page.tip ? page.tip + " " : ""}Нажмите на раздел или кнопку — покажу, где она.`, chips);
  }

  /* ============================== команды */

  const COMMANDS = [
    [/^(?:нажми|кликни|жми|тыкни|клацни|щелкни)(?:\s+(?:на|по))?\s+(.+)$/, "click"],
    [/^(?:открой|перейди|зайди|отправь меня|переведи меня|веди меня)(?:\s+(?:на|в|во|к))?\s+(.+)$/, "open"],
    [/^(?:покажи|подсвети|где|найди)(?:\s+мне)?(?:\s+где)?(?:\s+(?:находится|находятся|тут|здесь|на странице))?(?:\s+(?:кнопка|кнопку|раздел|ссылка|ссылку|страница|страницу))?\s+(.+)$/, "show"],
    [/^(?:прокрути|листай|промотай|мотай)\s*(?:(?:к|до|на)\s+)?(.*)$/, "scroll"],
  ];
  function parseCommand(text) {
    const t = norm(text).replace(/[?!.]+$/, "").trim();
    for (const [re, kind] of COMMANDS) {
      const m = t.match(re);
      if (m) return { kind, target: m[1].trim() };
    }
    return null;
  }

  async function guideFor(text, minP) {
    try {
      const R = await loadNN();
      const best = R.predict(text, 1)[0];
      return best.p >= minP && site.guides[best.id] ? best.id : null;
    } catch (e) { return null; }
  }

  async function command(cmd, raw) {
    const { kind, target } = cmd;
    if (kind === "scroll") {
      if (/^(вниз|ниже|down)?$/.test(target)) { scrollBy({ top: innerHeight * 0.8, behavior: "smooth" }); return say("Листаю вниз."); }
      if (/^(вверх|наверх|выше|в начало|up)$/.test(target)) { scrollTo({ top: 0, behavior: "smooth" }); return say("Наверх."); }
    }
    if (/^(как|что сделать чтобы)\s/.test(target)) {
      const g = await guideFor(target, 0.45);
      if (g) { say("Сейчас покажу по шагам."); return runGuide(g, kind === "show" ? "show" : "do"); }
    }
    const sec = findSection(target);
    if (sec && kind !== "click") { say(`Раздел «${sec.sec.title}».`); await spotlight(sec.el, sec.sec.title); return; }
    const clickable = (x) => /^(A|BUTTON|SUMMARY|INPUT|SELECT)$/.test(x.tagName) || x.getAttribute("role") === "button";
    const el = findElement(target, kind === "show" ? null : clickable);
    if (el) {
      if ((kind === "click" || kind === "open") && safeToClick(el)) {
        say(`Нажимаю «${textOf(el).slice(0, 50)}».`);
        minimize();
        await showSpot(el, "Нажимаю…", { auto: 900 });
        el.click();
        return;
      }
      if (kind === "click" || kind === "open") say(`Вот «${textOf(el).slice(0, 50)}». Эту кнопку нажмите сами — я не нажимаю то, что отправляет данные, удаляет или выходит из аккаунта.`);
      else say(`Вот «${textOf(el).slice(0, 50)}».`);
      await spotlight(el, textOf(el).slice(0, 80));
      return;
    }
    if (sec) { await spotlight(sec.el, sec.sec.title); return; }
    const page = findPage(target);
    if (page) {
      if (onPage(page.path)) return say(`Вы уже на странице «${page.title}».`);
      if (kind === "show") return say(`Это на странице «${page.title}».`, [["Открыть «" + page.title + "»", () => go(page.path)]]);
      say(`Открываю «${page.title}»…`);
      await sleep(400);
      return go(page.path);
    }
    const g = await guideFor(raw, 0.5);
    if (g) { say("Сейчас покажу по шагам."); return runGuide(g, kind === "show" ? "show" : "do"); }
    say("Не нашёл этого на странице. Спросите по-другому или нажмите «Что на этой странице?».", [["Что на этой странице?", describePage]]);
  }

  /* ============================== нейросеть */

  let nnLoading = null;
  function loadScript(url) {
    return fetch(url, { cache: "no-cache" }).then((r) => {
      if (!r.ok) throw new Error(url + ": HTTP " + r.status);
      return r.text();
    }).then((code) => new Promise((ok, fail) => {
      const s = document.createElement("script");
      s.src = URL.createObjectURL(new Blob([code], { type: "text/javascript" }));
      s.onload = ok; s.onerror = () => fail(new Error("не удалось запустить " + url));
      document.head.appendChild(s);
    }));
  }
  function loadNN() {
    if (root.RaiSupport && root.RaiSupport.model) return Promise.resolve(root.RaiSupport);
    if (!nnLoading) {
      nnLoading = (root.RaiSupport ? Promise.resolve() : loadScript(cfg.base + "rai-support.js"))
        .then(() => root.RaiSupport.load(cfg.base, { cache: "no-cache" }))
        .then(() => root.RaiSupport)
        .catch((e) => { nnLoading = null; throw e; });
    }
    return nnLoading;
  }
  function loadSite() {
    if (site) return Promise.resolve(site);
    return fetch(cfg.base + "site.json", { cache: "no-cache" }).then((r) => r.json()).then((j) => (site = j))
      .catch(() => (site = { pages: [], guides: {} }));
  }

  function toSupport(intent, text) {
    const topic = (site.support_topics || {})[intent];
    const msgs = (store.get(K_CHAT) || []).filter((m) => m.who === "me").map((m) => m.text).slice(-3);
    const body = (msgs.length ? msgs : [text]).join("\n").slice(0, 1500);
    go((cfg.support || "support.php") + "?new_ticket=1" + (topic ? "&topic=" + encodeURIComponent(topic) : "") + "&text=" + encodeURIComponent(body));
  }

  async function ask(text) {
    text = String(text || "").trim();
    if (!text || busy) return;
    say(text, null, false, "me");
    busy = true;
    try {
      await loadSite();
      const cmd = parseCommand(text);
      if (cmd) return await command(cmd, text);
      if (/^(что (на|тут|здесь)|что это за страниц|что есть на (этой )?странице)/.test(norm(text))) return describePage();
      typing(true);
      const R = await loadNN();
      const history = (store.get(K_CHAT) || []).slice(-12, -1).map((m) => ({ from: m.who === "me" ? "client" : "ai", text: m.text }));
      const pages = [...new Set([location.pathname + location.search, "/", "/team.php", "/projects.php"])];
      const r = await R.reply(text, { history, sitePages: pages, searchUrl: cfg.searchUrl });
      typing(false);
      if (r.intent === "page_help" && r.source.startsWith("nn:")) { say(r.reply); return describePage(); }
      if (r.intent === "close_ticket") {
        // здесь не тикет: закрыть можно в самом тикете — там Rai закроет его по просьбе клиента
        return say("Тикеты закрываются в поддержке: откройте свой тикет и напишите там «можно закрывать» — я закрою его.",
                   [["Открыть поддержку", () => go(cfg.support || "support.php")]]);
      }
      const actions = [];
      if (r.source.startsWith("nn:") && site.guides[r.intent]) {
        actions.push(["👀 Показать где", () => runGuide(r.intent, "show")]);
        actions.push(["⚡ Сделать за меня", () => runGuide(r.intent, "do")]);
      }
      if (r.handoff || ["human", "support_time"].includes(r.intent) || r.source === "fallback") {
        actions.push(["✉️ Написать в поддержку", () => toSupport(r.intent, text)]);
      }
      say(r.reply, actions);
    } catch (e) {
      typing(false);
      say("Не получилось загрузить нейросеть: " + (e && e.message || e) + ". Можно написать в поддержку.", [["✉️ Поддержка", () => go(cfg.support || "support.php")]]);
    } finally {
      busy = false;
    }
  }

  /* ============================== окно помощника */

  const CSS = `
:host { all: initial; }
* { box-sizing: border-box; font-family: Inter, "Segoe UI", system-ui, -apple-system, Arial, sans-serif; }
.fab { position: fixed; right: 20px; bottom: var(--rai-b, 20px); width: 58px; height: 58px; border-radius: 50%; border: 0; cursor: pointer; z-index: 3;
  background: linear-gradient(135deg, #8b5cf6, #ec4899); color: #fff; font-size: 25px; box-shadow: 0 12px 30px -8px rgba(139,92,246,.75), 0 0 0 1px rgba(255,255,255,.15) inset;
  transition: transform .18s; pointer-events: auto; }
.fab:hover { transform: scale(1.07); }
.fab::after { content: ""; position: absolute; inset: -4px; border-radius: 50%; border: 2px solid rgba(236,72,153,.6); animation: ring 2.4s infinite; }
@keyframes ring { 0% { opacity: .9; transform: scale(.92); } 100% { opacity: 0; transform: scale(1.35); } }
.hint { position: fixed; right: 88px; bottom: calc(var(--rai-b, 20px) + 10px); max-width: 240px; padding: 10px 14px; border-radius: 14px; font-size: 13.5px; color: #fff; pointer-events: auto; cursor: pointer;
  background: rgba(24,20,38,.97); border: 1px solid rgba(167,139,250,.45); box-shadow: 0 16px 40px -14px rgba(0,0,0,.8); display: none; animation: pop .3s ease both; }
.hint.on { display: block; }
.panel { position: fixed; right: 20px; bottom: calc(var(--rai-b, 20px) + 70px); width: 370px; height: min(560px, calc(100vh - 120px)); display: none; flex-direction: column; overflow: hidden; z-index: 3;
  border-radius: 20px; pointer-events: auto; color: #ececf2; font-size: 14px;
  background: linear-gradient(180deg, rgba(22,19,34,.98), rgba(12,11,19,.98)) padding-box, linear-gradient(160deg, rgba(167,139,250,.7), rgba(236,72,153,.35) 60%, rgba(255,255,255,.08)) border-box;
  border: 1px solid transparent; box-shadow: 0 30px 70px -20px rgba(0,0,0,.85); animation: pop .25s ease both; }
.panel.on { display: flex; }
@keyframes pop { from { opacity: 0; transform: translateY(8px) scale(.98); } to { opacity: 1; transform: none; } }
.head { display: flex; align-items: center; gap: 10px; padding: 14px 14px 12px; border-bottom: 1px solid rgba(255,255,255,.07); }
.ava { width: 34px; height: 34px; border-radius: 11px; display: grid; place-items: center; font-size: 17px; background: linear-gradient(135deg, #8b5cf6, #ec4899); flex: none; }
.ttl { flex: 1; min-width: 0; } .ttl b { display: block; color: #fff; font-size: 14.5px; } .ttl span { font-size: 12px; color: #a1a1b5; }
.x { width: 32px; height: 32px; border-radius: 9px; border: 1px solid rgba(255,255,255,.1); background: rgba(255,255,255,.04); color: #c9c9d6; cursor: pointer; font-size: 15px; }
.x:hover { background: rgba(255,255,255,.1); color: #fff; }
.msgs { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.15) transparent; }
.m { max-width: 88%; padding: 9px 12px; border-radius: 14px; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; animation: pop .2s ease both; }
.m.ai { align-self: flex-start; background: rgba(139,92,246,.12); border: 1px solid rgba(167,139,250,.28); border-bottom-left-radius: 5px; }
.m.me { align-self: flex-end; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); border-bottom-right-radius: 5px; }
.m.step { background: rgba(245,158,11,.08); border-color: rgba(245,158,11,.3); }
.m a { color: #c4b5fd; }
.acts { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; white-space: normal; }
.chip { border: 1px solid rgba(167,139,250,.4); background: rgba(139,92,246,.14); color: #e9d5ff; border-radius: 999px; padding: 6px 11px; font-size: 12.5px; cursor: pointer; text-align: left; }
.chip:hover { background: rgba(139,92,246,.28); color: #fff; }
.chip.main { background: linear-gradient(135deg, #8b5cf6, #db2777); border-color: transparent; color: #fff; font-weight: 600; }
.typing { align-self: flex-start; display: none; gap: 4px; padding: 11px 13px; border-radius: 14px; background: rgba(139,92,246,.12); }
.typing.on { display: inline-flex; } .typing i { width: 6px; height: 6px; border-radius: 50%; background: #c4b5fd; animation: blink 1.2s infinite both; }
.typing i:nth-child(2) { animation-delay: .2s; } .typing i:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 80%, 100% { opacity: .25; } 40% { opacity: 1; } }
.quick { display: flex; gap: 6px; overflow-x: auto; padding: 0 14px 10px; scrollbar-width: none; } .quick::-webkit-scrollbar { display: none; }
.quick .chip { flex: none; }
.row { display: flex; gap: 8px; padding: 10px 12px 12px; border-top: 1px solid rgba(255,255,255,.07); }
.row input { flex: 1; min-width: 0; border-radius: 12px; border: 1px solid rgba(255,255,255,.12); background: rgba(5,5,9,.7); color: #fff; padding: 10px 12px; font-size: 14px; outline: none; }
.row input:focus { border-color: rgba(167,139,250,.7); box-shadow: 0 0 0 3px rgba(139,92,246,.2); }
.row button { width: 42px; border-radius: 12px; border: 0; cursor: pointer; color: #fff; font-size: 16px; background: linear-gradient(135deg, #8b5cf6, #db2777); }
.layer { position: fixed; inset: 0; pointer-events: none; z-index: 2; display: none; }
.layer.on { display: block; }
.spot { position: fixed; border-radius: 12px; box-shadow: 0 0 0 3px #a78bfa, 0 0 22px 6px rgba(167,139,250,.6), 0 0 0 9999px rgba(5,5,12,.55);
  transition: left .25s, top .25s, width .25s, height .25s; animation: glow 1.6s ease-in-out infinite; }
@keyframes glow { 50% { box-shadow: 0 0 0 3px #f0abfc, 0 0 30px 10px rgba(236,72,153,.55), 0 0 0 9999px rgba(5,5,12,.55); } }
.tip { position: fixed; pointer-events: auto; padding: 12px 14px; border-radius: 14px; color: #fff; font-size: 13.5px; line-height: 1.45;
  background: rgba(24,20,38,.98); border: 1px solid rgba(167,139,250,.55); box-shadow: 0 18px 44px -14px rgba(0,0,0,.85); }
.tip .tb { display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px; }
.tip button { border: 0; border-radius: 9px; padding: 7px 12px; cursor: pointer; font-size: 12.5px; font-weight: 600; color: #fff; background: linear-gradient(135deg, #8b5cf6, #db2777); }
.tip button.ghost { background: rgba(255,255,255,.08); }
@media (max-width: 640px) {
  .panel { right: 8px; left: 8px; width: auto; bottom: calc(var(--rai-b, 14px) + 64px); height: min(72vh, calc(100vh - 100px)); }
  .fab { right: 14px; width: 54px; height: 54px; }
  .hint { right: 76px; }
}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
`;

  function linkify(t) {
    return esc(t).replace(/(https?:\/\/[^\s<]+|rteam\.info\/[^\s<]*)/g, (u) => {
      const href = u.startsWith("http") ? u : "/" + u.replace(/^rteam\.info\//, "");
      const clean = href.replace(/[.,;:)»]+$/, "");
      return `<a href="${clean}" ${clean.startsWith("/") ? "" : 'target="_blank" rel="noopener"'}>${u}</a>`;
    });
  }

  function say(text, actions, step, who) {
    who = who || "ai";
    const log = store.get(K_CHAT) || [];
    log.push({ who, text: String(text), step: !!step, t: Date.now() });
    store.set(K_CHAT, log.slice(-40));
    render(log.length - 1, actions);
  }

  function render(index, actions) {
    const log = store.get(K_CHAT) || [];
    const from = index == null ? 0 : index;
    if (index == null) ui.msgs.querySelectorAll(".m").forEach((n) => n.remove());
    for (let i = from; i < log.length; i++) {
      const m = log[i], div = document.createElement("div");
      div.className = "m " + m.who + (m.step ? " step" : "");
      div.innerHTML = linkify(m.text);
      if (i === log.length - 1 && actions && actions.length) {
        const box = document.createElement("div");
        box.className = "acts";
        actions.forEach(([label, fn], k) => {
          const b = document.createElement("button");
          b.className = "chip" + (k === 0 && /Показать|Сделать/.test(label) ? " main" : "");
          b.textContent = label;
          b.onclick = () => fn();
          box.appendChild(b);
        });
        div.appendChild(box);
      }
      ui.msgs.insertBefore(div, ui.typing);
    }
    ui.msgs.scrollTop = ui.msgs.scrollHeight;
  }

  function typing(on) { ui.typing.classList.toggle("on", on); ui.msgs.scrollTop = ui.msgs.scrollHeight; }
  function minimize() { ui.panel.classList.remove("on"); }

  function open(focus = true) {
    ui.panel.classList.add("on");
    ui.hint.classList.remove("on");
    store.set(K_OPEN, true);
    store.set(K_HINT, true);
    loadSite().then(() => {
      if (!(store.get(K_CHAT) || []).length) {
        const page = currentPage();
        say("Привет! Я Rai — помощник по сайту RTeam. Могу ответить на вопрос, показать, где что находится, и нажать нужную кнопку за вас." +
            (page && page.tip ? "\n\n" + page.tip : ""));
      }
      loadNN().catch(() => {});   // заранее, чтобы первый ответ был быстрым
    });
    if (focus) setTimeout(() => ui.input.focus(), 50);
  }
  function close() { ui.panel.classList.remove("on"); store.set(K_OPEN, false); }

  function build() {
    host = document.createElement("div");
    host.id = "rai-guide";
    host.style.cssText = "position:fixed;top:0;left:0;width:0;height:0;z-index:2147483000;";
    sh = host.attachShadow({ mode: "open" });
    sh.innerHTML = `<style>${CSS}</style>
      <div class="layer"><div class="spot"></div><div class="tip"><div class="tt"></div><div class="tb"><button class="ghost" data-x>Закрыть</button><button data-n>Дальше →</button></div></div></div>
      <div class="hint">Нужна помощь? Я покажу, где что, и нажму за вас ✨</div>
      <div class="panel" role="dialog" aria-label="Помощник Rai">
        <div class="head"><div class="ava">✨</div><div class="ttl"><b>Rai</b><span>помощник по сайту · своя нейросеть RTeam</span></div><button class="x" title="Закрыть">✕</button></div>
        <div class="msgs"><div class="typing"><i></i><i></i><i></i></div></div>
        <div class="quick"></div>
        <form class="row"><input placeholder="Спросите или скажите «открой кабинет»…" maxlength="500"><button title="Отправить">➤</button></form>
      </div>
      <button class="fab" aria-label="Помощник Rai">✨</button>`;
    const $ = (s) => sh.querySelector(s);
    ui = { layer: $(".layer"), spot: $(".spot"), tip: $(".tip"), tipText: $(".tt"), tipNext: $("[data-n]"), hint: $(".hint"),
           panel: $(".panel"), msgs: $(".msgs"), typing: $(".typing"), input: $(".row input"), quick: $(".quick") };
    $(".fab").onclick = () => (ui.panel.classList.contains("on") ? close() : open());
    $(".x").onclick = close;
    ui.hint.onclick = () => open();
    $("[data-x]").onclick = () => hideSpot(false);
    ui.tipNext.onclick = () => hideSpot(true);
    $(".row").onsubmit = (e) => { e.preventDefault(); const v = ui.input.value; ui.input.value = ""; ask(v); };
    [["Что на этой странице?", () => { loadSite().then(() => { say("Что на этой странице?", null, false, "me"); describePage(); }); }],
     ["Подать заявку", () => ask("как подать заявку в команду")],
     ["Привязать Telegram", () => ask("как привязать телеграм")],
     ["Сменить пароль", () => ask("как сменить пароль")],
     ["Позвать поддержку", () => ask("позовите администратора")]].forEach(([label, fn]) => {
      const b = document.createElement("button"); b.className = "chip"; b.textContent = label; b.onclick = fn; ui.quick.appendChild(b);
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideSpot(false); });
    document.body.appendChild(host);
    render(null);
  }

  /* Не закрывать свои кнопки сайта в углу («Наверх», праздничные): поднимаемся над ними */
  function avoidOverlap() {
    if (!host) return;
    const base = innerWidth <= 640 ? 14 : 20, x = innerWidth - base - 27;
    let bottom = base;
    for (let k = 0; k < 3; k++) {
      const y = innerHeight - bottom - 27;
      const hit = document.elementsFromPoint(x, y).find((el) => el !== host && !host.contains(el) &&
        getComputedStyle(el).position === "fixed" && visible(el) && el.getBoundingClientRect().height < innerHeight / 2);
      if (!hit) break;
      bottom = innerHeight - hit.getBoundingClientRect().top + 10;
    }
    host.style.setProperty("--rai-b", bottom + "px");
  }

  root.RaiGuide = {
    version: "1.0",
    async init(options) {
      if (host) return;
      cfg = Object.assign({ support: "support.php" }, options || {});
      cfg.base = String(cfg.base || "").replace(/\/?$/, "/");
      build();
      avoidOverlap();
      addEventListener("resize", avoidOverlap);
      setInterval(avoidOverlap, 2000);
      const tour = store.get(K_TOUR);
      if (tour) {
        await loadSite();
        if (store.get(K_OPEN)) open(false);
        runGuide(tour.intent, tour.mode, tour.step, tour);
      } else if (store.get(K_OPEN)) {
        open(false);
      } else if (!store.get(K_HINT)) {
        setTimeout(() => {
          if (store.get(K_HINT) || ui.panel.classList.contains("on")) return;
          store.set(K_HINT, true);
          ui.hint.classList.add("on");
          setTimeout(() => ui.hint.classList.remove("on"), 8000);
        }, 20000);
      }
    },
    open, close, ask, describePage, runGuide,
    _internal: { parseCommand, scoreText, safeToClick, findElement, findSection, findPage, onPage },
  };
})(typeof self !== "undefined" ? self : this);
