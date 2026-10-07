<?php /* Нейросеть AI Studio: сайты делает Rai Нейро прямо в браузере. Подключается в studio.php через include. */ ?>
<script>
/* AI Studio · нейросеть Rai Нейро (тот же движок, что в чате Rai, — работает на видеокарте посетителя, без серверов).
   Два способа сделать сайт (переключатель «Как делать», по умолчанию выбирается сам по силе модели):

   ▸ «Тексты нейросети + дизайн студии» — нейросеть придумывает сайт целиком: название, слоган, цвета, разделы и ВСЕ
     тексты (настоящие блюда, услуги, цены, отзывы, вопросы), а собирает его дизайн студии. Надёжно даже на слабой
     модели: маленькой нейросети проще написать хорошие тексты, чем красивую вёрстку.
       1) сайт в JSON — пишется вживую (черновик в предпросмотре);
       2) проверка: все ли разделы, которые просил клиент, на месте, хватает ли пунктов и текста, нет ли заглушек, есть ли цены;
       3) что не так — дописывает только недостающие и слабые разделы (а не весь сайт заново).

   ▸ «Нейросеть пишет весь код» (мощная видеокарта, модели Про / Код / Макс) — свой дизайн:
       1) план — название, стиль, цвета, разделы с конкретными текстами (JSON);
       2) один файл HTML со стилями по плану — пишется вживую в предпросмотре;
       3) код оборвался — дописывает с места остановки;
       4) проверка (всё из плана и запроса на месте, нет заглушек, адаптивность, контакты) — исправляет, берёт лучший вариант;
          совсем не вышло — собирает сайт первым способом, чтобы человек не остался ни с чем.

   Правки — точечно: нужный раздел, только оформление, новый раздел; простые («сделай синим», «убери отзывы»,
   «переименуй…») — мгновенно, без нейросети. Сервер (actions.php) сохраняет результат и ещё раз его очищает.
   Тариф и лимиты — как в чате Rai (limits.php на rai.rteam.info): одна генерация или правка = одно сообщение нейросети. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const N = () => window.RaiNeuro;
  const HOME = String(window.STUDIO_RAI || "https://rai.rteam.info").replace(/\/+$/, "");
  const MODE_KEY = "studio_ai_mode", MODEL_KEY = "studio_ai_model", HOW_KEY = "studio_ai_how";
  const YEAR = new Date().getFullYear();

  // ---------------------------------------------------------------- подсказки нейросети
  const KINDS = "Виды разделов (kind) и их поля:\n" +
    "- about, text: \"text\" — 2–4 живых предложения;\n" +
    "- services, features, courses, projects, products, posts: \"items\":[{\"title\":\"…\",\"text\":\"1–2 предложения\",\"price\":\"…\"}] — 3–6 карточек (price — если уместно);\n" +
    "- prices: \"items\":[{\"title\":\"тариф\",\"price\":\"990 ₽\",\"text\":\"что входит\"}] — 3 тарифа;\n" +
    "- menu, tracks: \"items\":[{\"title\":\"…\",\"text\":\"состав или описание\",\"price\":\"…\"}] — 4–8 позиций;\n" +
    "- reviews: \"items\":[{\"title\":\"имя\",\"text\":\"отзыв\"}] — 3 отзыва;\n" +
    "- faq: \"items\":[{\"title\":\"вопрос\",\"text\":\"ответ\"}] — 3–5;\n" +
    "- how, schedule: \"items\":[{\"title\":\"шаг или время\",\"text\":\"…\"}] — 3–5;\n" +
    "- team: \"items\":[{\"title\":\"имя\",\"text\":\"роль\"}] — 3–4;\n" +
    "- skills: \"tags\":[\"…\"] — 5–12 коротких слов;\n" +
    "- gallery: \"count\":6;\n" +
    "- contacts: \"text\" — приглашение связаться (всегда последний раздел).";
  const SPEC_SYSTEM = "Ты — сильный копирайтер и веб-дизайнер AI Studio Rteam. По описанию клиента придумай одностраничный сайт " +
    "и напиши ВСЕ его тексты. Ответь ТОЛЬКО JSON, без пояснений и без ```:\n" +
    "{\"title\":\"короткое название\",\"tagline\":\"слоган для главного экрана\",\"theme\":\"dark или light\",\"accent\":\"#RRGGBB\"," +
    "\"sections\":[{\"kind\":\"…\",\"title\":\"заголовок раздела\", …поля вида…}],\"contacts\":{\"email\":\"\",\"phone\":\"\",\"telegram\":\"\",\"address\":\"\"}}\n" +
    KINDS + "\nПравила:\n- 4–7 разделов; главный экран не пиши (он строится из title и tagline); последний раздел — contacts;\n" +
    "- тексты на русском, живые и конкретные именно для этого бизнеса: настоящие названия блюд, услуг, курсов, реальные цены в ₽, " +
    "имена людей; никаких «Товар 1», «Lorem ipsum», «описание услуги», «здесь будет»;\n" +
    "- учти ВСЁ, что просил клиент: разделы, тон, цвета, название, контакты (контакты — только те, что дал клиент, не выдумывай);\n" +
    "- theme: dark, если просили тёмный или чёрный стиль; accent — цвет из запроса или подходящий теме.";
  const SECTION_SYSTEM = "Ты — копирайтер AI Studio Rteam. Напиши ОДИН раздел сайта в JSON: {\"kind\":\"…\",\"title\":\"…\", …поля вида…}. " +
    "Ответь ТОЛЬКО JSON, без пояснений.\n" + KINDS + "\nТексты — на русском, конкретные, под тему сайта, без заглушек.";
  const SPEC_EDIT_SYSTEM = "Ты — редактор сайтов AI Studio Rteam. Тебе дают сайт в JSON и правку клиента. Внеси правку и верни ТОЛЬКО " +
    "полный JSON сайта той же структуры (title, tagline, theme, accent, sections, contacts), без пояснений. Всё, чего правка " +
    "не касается, оставь как было.\n" + KINDS + "\nТексты — на русском, конкретные, без заглушек.";

  const PLAN_SYSTEM = "Ты — арт-директор и веб-дизайнер AI Studio Rteam. По описанию клиента составь план одностраничного сайта. " +
    "Ответь ТОЛЬКО JSON, без пояснений и без ```: {\"title\":\"название\",\"tagline\":\"короткий слоган\",\"theme\":\"dark или light\"," +
    "\"accent\":\"#RRGGBB\",\"accent2\":\"#RRGGBB\",\"font\":\"название шрифта Google Fonts\",\"mood\":\"стиль в 3–5 словах\"," +
    "\"sections\":[{\"id\":\"латиницей\",\"title\":\"заголовок\",\"points\":[\"конкретный текст\",\"…\"]}]," +
    "\"contacts\":{\"email\":\"\",\"phone\":\"\",\"address\":\"\"}}. Правила: 5–7 разделов; первым — главный экран (hero), " +
    "последним — контакты; в points — живые конкретные тексты на русском (цены, факты, имена, преимущества), никаких «Lorem ipsum» " +
    "и «здесь будет текст»; учти ВСЕ пожелания клиента (цвета, разделы, тон, контакты) — их нельзя терять; цвета подбери под тему.";
  const SITE_SYSTEM = "Ты — лучший фронтенд-разработчик и дизайнер. Сделай ОДИН файл index.html — красивый современный адаптивный " +
    "одностраничный сайт строго по плану. Требования:\n" +
    "- <!DOCTYPE html>, <html lang=\"ru\">, <meta charset=\"utf-8\">, <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">, <title>;\n" +
    "- весь CSS в одном <style>: переменные цветов в :root, grid/flex, крупная типографика, отступы, тени, скругления, " +
    "плавные :hover и @keyframes-анимации появления, @media для телефона (360px) и планшета;\n" +
    "- шрифт из плана подключи через <link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=…&display=swap\">;\n" +
    "- шапка с логотипом-названием и меню-якорями на все разделы; главный экран с заголовком, слоганом и кнопкой; " +
    "каждый раздел плана — свой <section id=\"…\"> с карточками/списками/ценами/отзывами по смыслу; подвал с контактами и © " + YEAR + ";\n" +
    "- ВСЕ тексты из плана — дословно или лучше, на русском; никаких заглушек, lorem ipsum, «ваш текст», example.com;\n" +
    "- картинок-файлов нет: используй CSS-градиенты, эмодзи и простые inline <svg>;\n" +
    "- НИКАКОГО JavaScript и <script> (меню — на CSS);\n" +
    "Ответь только кодом HTML от <!DOCTYPE html> до </html>, без пояснений.";
  const PART_SYSTEM = "Ты — фронтенд-разработчик. Тебе дают фрагмент сайта (HTML) и правку. Перепиши фрагмент с учётом правки, " +
    "сохраняя классы и стиль сайта. Без <script> и JavaScript. Ответь ТОЛЬКО исправленным фрагментом HTML, без пояснений и без ```.";
  const CSS_SYSTEM = "Ты — веб-дизайнер. Тебе дают CSS сайта и правку оформления. Верни ПОЛНЫЙ исправленный CSS (без <style> и без пояснений).";

  // ---------------------------------------------------------------- помощники
  const noThink = (s) => String(s || "").replace(/<think>[\s\S]*?(<\/think>|$)/g, "");
  function extractHtml(raw) {
    let s = noThink(raw);
    const fence = s.match(/```(?:html)?[ \t]*\n?([\s\S]*?)(```|$)/i);
    if (fence && /<(!doctype|html|head|body|section|div|header|main|style)/i.test(fence[1])) s = fence[1];
    const start = s.search(/<!doctype html|<html[\s>]/i);
    if (start > 0) s = s.slice(start);
    return s.replace(/```\s*$/, "").trim();
  }
  function fragment(raw) {
    let s = noThink(raw);
    const fence = s.match(/```(?:html|css|json)?[ \t]*\n?([\s\S]*?)(```|$)/i);
    if (fence && fence[1].trim()) s = fence[1];
    return s.trim();
  }
  /** Закрыть оборванный JSON: незакрытую строку и все открытые { и [. */
  function closeJSON(s) {
    const stack = [];
    let str = false, esc = false;
    for (const ch of s) {
      if (str) { if (esc) esc = false; else if (ch === "\\") esc = true; else if (ch === '"') str = false; continue; }
      if (ch === '"') str = true;
      else if (ch === "{") stack.push("}");
      else if (ch === "[") stack.push("]");
      else if ((ch === "}" || ch === "]") && stack.length) stack.pop();
    }
    return (str ? s + '"' : s) + stack.reverse().join("");
  }
  const tidyJSON = (x) => x.replace(/,\s*([}\]])/g, "$1").replace(/[“”]/g, '"');
  /** JSON из ответа нейросети — даже с пояснениями вокруг, лишними запятыми или оборванный на середине. */
  function parseJSON(raw) {
    const s = fragment(raw);
    const a = s.indexOf("{"), b = s.lastIndexOf("}");
    if (a < 0) return null;
    if (b > a) {
      const body = s.slice(a, b + 1);
      for (const fix of [(x) => x, (x) => x.replace(/,\s*([}\]])/g, "$1"), tidyJSON]) {
        try { return JSON.parse(fix(body)); } catch (e) { /* следующая попытка */ }
      }
    }
    return partialJSON(s);
  }
  /** Сколько получится из оборванного JSON (пока нейросеть пишет): отрезаем недописанный хвост и закрываем скобки. */
  function partialJSON(raw) {
    let s = noThink(raw);
    const a = s.indexOf("{");
    if (a < 0) return null;
    s = s.slice(a);
    for (let i = 0; i < 80 && s.length > 1; i++) {
      try { return JSON.parse(closeJSON(s).replace(/,\s*([}\]])/g, "$1")); } catch (e) { /* режем дальше */ }
      const cut = Math.max(s.lastIndexOf(","), s.lastIndexOf("{") + 1, s.lastIndexOf("[") + 1);
      s = s.slice(0, cut >= s.length ? s.length - 1 : cut).replace(/\s*,\s*$/, "");
    }
    return null;
  }
  /** Без скриптов, обработчиков событий и javascript:-ссылок — и в живом предпросмотре, и перед сохранением
      (сервер всё равно чистит ещё раз: sg_clean_html). */
  function safe(html) {
    return String(html || "")
      .replace(/<(script|iframe|frame|object|embed|applet|noscript|template)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, "")
      .replace(/<\/?(script|iframe|frame|object|embed|applet|base|portal)\b[^>]*>/gi, "")
      .replace(/<meta\b[^>]*http-equiv\s*=\s*["']?\s*refresh[^>]*>/gi, "")
      .replace(/\s+on[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, "")
      .replace(/\s(href|src|action|formaction|xlink:href)\s*=\s*(["']?)\s*(javascript|vbscript|data:text\/html)[^"'>]*\2/gi, ' $1="#"');
  }
  const keyWords = (t) => (String(t || "").toLowerCase().match(/[a-zа-яё0-9]{4,}/g) || []).map((w) => w.slice(0, 5));
  const docOf = (html) => new DOMParser().parseFromString(html, "text/html");
  const serialize = (doc) => "<!DOCTYPE html>\n" + doc.documentElement.outerHTML;
  const tail = (s, n) => s.length > n ? s.slice(-n) : s;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

  // ---------------------------------------------------------------- остановка
  let stopped = false, working = false;
  class Stopped extends Error {}
  function checkStop() { if (stopped) throw new Stopped("Остановлено."); }
  async function stop() {
    stopped = true;
    if (N() && N().stop) await N().stop();
  }

  // ---------------------------------------------------------------- модель, тариф и свой сервер моделей
  function stored(key, def) { try { return localStorage.getItem(key) || def; } catch (e) { return def; } }
  function store(key, v) { try { localStorage.setItem(key, v); } catch (e) { /* без памяти браузера */ } }
  const chosenModel = () => stored(MODEL_KEY, "auto");

  // модели и библиотеки — с rai.rteam.info/ai.php (как в чате), если он есть
  async function findMirror() {
    if (typeof window.RAI_AI === "object") return window.RAI_AI;
    const root = HOME + "/ai.php";
    for (const [address, pathInfo] of [[root + "/ping", true], [root + "?ping=1", false]]) {
      try {
        const ctl = typeof AbortController === "function" ? new AbortController() : null;
        const timer = setTimeout(() => ctl && ctl.abort(), 3500);
        const r = await fetch(address, {cache: "no-store", signal: ctl && ctl.signal});
        clearTimeout(timer);
        const j = r.ok ? await r.json() : null;
        if (j && j.service === "rai-ai" && j.curl !== false) return {root: root, pathInfo: pathInfo && j.path_info === true};
      } catch (e) { /* нет своего сервера по этому адресу */ }
    }
    return null;
  }
  let limits = null;
  async function loadLimits() {
    try {
      const r = await fetch(HOME + "/limits.php", {credentials: "include", cache: "no-store"});
      if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) return null;
      limits = await r.json();
      if (N() && N().setAllowed) N().setAllowed(limits.models);
      renderModels();
      renderLeft();
    } catch (e) { limits = null; }
    return limits;
  }
  const ready = (window.RAI_NEURO_TEST && !window.RAI_NEURO_TEST.limits ? Promise.resolve(null) : Promise.all([
    findMirror().then((m) => { window.RAI_AI = m; if (m && N()) N().useMirror(m); return m; }),
    loadLimits()
  ])).catch(() => null);

  /** Засчитать одну генерацию или правку по тарифу Rai (как сообщение нейросети в чате). */
  async function takeLimit(retry) {
    if (!limits || !limits.csrf) return;
    let r, d;
    try {
      r = await fetch(HOME + "/limits.php", {method: "POST", credentials: "include", headers: {"X-CSRF-Token": limits.csrf}});
      d = await r.json().catch(() => null);
    } catch (e) { return; }   // сервер Rai не ответил — не мешаем работать
    if (r.status === 403 && d && d.banned) throw new Error(d.error);
    if (r.status === 403 && !retry) { await loadLimits(); return takeLimit(true); }
    if (d && d.plan) { Object.assign(limits, d); renderLeft(); }
    if (r.status === 429) {
      const e = new Error((d && d.error ? d.error + " " : "") + "Можно выбрать «⚡ Быстрые шаблоны» или тариф побольше: " + HOME + "/#pricing");
      e.limit = true;
      throw e;
    }
  }

  async function modelFor(choice) {
    if (choice && choice !== "auto") return choice;
    const p = await N().pick();
    // для сайтов на мощной видеокарте — модель для кода (Qwen2.5-Coder 7B), иначе лучшая по силам устройства
    const key = p.key === "strong" && p.gpu && p.gpu.buffer >= 4.5e9 ? "coder" : p.key;
    return N().permitted ? N().permitted(key) : key;
  }
  async function ensureModel(onStep) {
    if (!N()) throw new Error("нейросеть Rai не загрузилась — обновите страницу");
    await ready;
    if (N().ready()) return;
    onStep && onStep("Включаю нейросеть Rai (первый раз модель скачивается, дальше — из кэша браузера)…");
    await N().enable(await modelFor(chosenModel()));
  }
  const onCpu = () => !!(N() && N().backend && N().backend() === "cpu");
  const budget = (n) => onCpu() ? Math.min(n, 2600) : n;   // на процессоре окно модели меньше (4096 токенов)
  async function ask(system, user, onText, opts) {
    checkStop();
    const text = await N().chat([{role: "user", content: user}], onText,
                                Object.assign({system: system, temperature: 0.4}, opts || {}, {maxTokens: budget((opts && opts.maxTokens) || 6000)}));
    checkStop();
    return text;
  }

  /** Как делать сайт: "spec" (тексты нейросети + дизайн студии) или "code" (нейросеть пишет весь код). */
  function how() {
    if (onCpu()) return "spec";   // на процессоре целый сайт кодом писать слишком долго
    const choice = stored(HOW_KEY, "auto");
    if (choice === "spec" || choice === "code") return choice;
    const st = N() && N().status ? N().status() : {};
    return ["strong", "coder", "max"].includes(st.model) ? "code" : "spec";
  }

  // ---------------------------------------------------------------- тексты нейросети + дизайн студии
  const ITEM_KINDS = ["services", "features", "prices", "reviews", "menu", "products", "projects", "posts", "faq", "team",
                      "schedule", "courses", "how", "tracks"];
  const TITLES = {about: "О нас", services: "Услуги", prices: "Цены", reviews: "Отзывы", contacts: "Контакты", gallery: "Галерея",
                  menu: "Меню", products: "Товары", projects: "Проекты", skills: "Навыки", posts: "Статьи", faq: "Вопросы и ответы",
                  team: "Команда", schedule: "Расписание", courses: "Курсы", features: "Преимущества", how: "Как это работает", tracks: "Треки"};
  // разделы, которые клиент назвал словами, — их нельзя потерять
  const WANT = [["prices", /цен[аыуе]|тариф|прайс|стоимост/], ["reviews", /отзыв/], ["menu", /меню/], ["gallery", /галере/],
                ["faq", /вопрос|faq|чаво/], ["team", /команд[аыуе]|сотрудник/], ["schedule", /расписани|афиш|концерт/],
                ["courses", /курс[аыео]/], ["services", /услуг/], ["products", /товар|каталог/], ["projects", /проекты|кейс|портфолио/],
                ["skills", /навык/], ["how", /как это работает|этап/], ["features", /преимуществ|почему мы/], ["tracks", /трек|альбом/],
                ["posts", /блог|стать[иья]/]];
  const PLACEHOLDER = /lorem|ipsum|здесь будет|ваш текст|текст раздела|описание (товара|услуги|позиции|курса)|^(товар|услуга|позиция|проект|курс|отзыв|имя|вопрос|ответ)\s*\d*$|example\.com|placeholder|todo|^\.\.\.$|^…$/i;

  function normSpec(obj) {
    if (Array.isArray(obj)) obj = {sections: obj};
    if (!obj || typeof obj !== "object") return null;
    if (obj.site && typeof obj.site === "object") obj = obj.site;
    const sections = Array.isArray(obj.sections) ? obj.sections : Array.isArray(obj.blocks) ? obj.blocks : [];
    obj.sections = sections.filter((s) => s && typeof s === "object").map((s) => {
      const out = Object.assign({}, s);
      out.kind = String(s.kind || s.type || "").toLowerCase().trim();
      if (Array.isArray(out.items)) out.items = out.items.map((it) => typeof it === "string" ? {title: it} : it).filter((it) => it && typeof it === "object");
      return out;
    });
    return obj;
  }
  function sectionText(s) {
    return [s.title, s.text].concat((s.items || []).map((it) => [it.title, it.text, it.price].join(" ")), s.tags || []).join(" ");
  }
  function inspectSpec(spec, prompt) {
    const issues = [], weak = [], missing = [];
    const secs = (spec && spec.sections) || [];
    const low = String(prompt || "").toLowerCase();
    const real = secs.filter((s) => s.kind !== "contacts" && !/^(hero|main|intro|banner)$/.test(s.kind));
    if (!spec || !spec.title) issues.push("нет названия сайта");
    if (real.length < 3) issues.push("мало разделов (нужно 4–7)");
    let chars = 0;
    for (const s of real) {
      const items = Array.isArray(s.items) ? s.items : [];
      chars += sectionText(s).length;
      const why = [];
      if (ITEM_KINDS.includes(s.kind) && items.length < 2) why.push("мало пунктов");
      if (["about", "text"].includes(s.kind) && String(s.text || "").length < 60) why.push("слишком короткий текст");
      if (items.some((it) => PLACEHOLDER.test(String(it.title || "").trim()) || PLACEHOLDER.test(String(it.text || "").trim())) ||
          PLACEHOLDER.test(String(s.text || "").trim())) why.push("заглушки вместо текста");
      if (["prices", "menu"].includes(s.kind) && items.length && !items.some((it) => /\d/.test(String(it.price || "") + String(it.text || "")))) why.push("нет цен");
      if (why.length) { weak.push({section: s, why: why}); issues.push(`раздел «${s.title || s.kind}»: ${why.join(", ")}`); }
    }
    if (real.length && chars < 450) issues.push("слишком мало текста");
    for (const [kind, re] of WANT) {
      if (!re.test(low)) continue;
      if (!secs.some((s) => s.kind === kind || re.test(String(s.title || "").toLowerCase()))) { missing.push(kind); issues.push(`нет раздела «${TITLES[kind]}»`); }
    }
    const score = Math.max(0, 100 - issues.length * 14 - (chars < 900 ? 8 : 0));
    return {issues: issues, weak: weak, missing: missing, score: score, chars: chars,
            broken: !spec || real.length < 3 || chars < 250};
  }

  /** Черновик для предпросмотра, пока нейросеть пишет (настоящий сайт потом соберёт сервер студии). */
  function sketch(spec, live) {
    const dark = spec.theme === "dark";
    const accent = /^#[0-9a-f]{6}$/i.test(spec.accent || "") ? spec.accent : "#ff3d81";
    const bg = dark ? "#0c0c0e" : "#faf8f5", fg = dark ? "#f2f0f0" : "#1d1a17", card = dark ? "#17171a" : "#fff", line = dark ? "#2a2a30" : "#e7e2db";
    const secs = (spec.sections || []).map((s) => {
      const items = (s.items || []).map((it) => `<div class="c"><b>${esc(it.title)}</b>${it.price ? `<i>${esc(it.price)}</i>` : ""}<p>${esc(it.text || "")}</p></div>`).join("");
      const tags = (s.tags || []).map((t) => `<span class="t">${esc(t)}</span>`).join("");
      return `<section><h2>${esc(s.title || TITLES[s.kind] || "")}</h2>${s.text ? `<p>${esc(s.text)}</p>` : ""}${items ? `<div class="g">${items}</div>` : ""}${tags}</section>`;
    }).join("");
    return `<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>
body{margin:0;background:${bg};color:${fg};font:16px/1.55 system-ui,"Segoe UI",sans-serif}
.bar{position:sticky;top:0;background:${accent};color:#fff;font:600 13px/1.3 system-ui;padding:9px 16px;letter-spacing:.02em}
header{padding:56px 24px;border-bottom:1px solid ${line};background:linear-gradient(120deg,${accent}22,transparent)}
h1{font-size:clamp(30px,6vw,52px);margin:0 0 10px;line-height:1.05}header p{margin:0;font-size:19px;opacity:.85}
section{padding:34px 24px;border-bottom:1px solid ${line};animation:in .5s ease both}h2{margin:0 0 14px;font-size:26px}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.c{background:${card};border:1px solid ${line};border-radius:14px;padding:14px}.c b{display:block}.c i{font-style:normal;font-weight:700;color:${accent}}
.c p{margin:6px 0 0;opacity:.75;font-size:14px}.t{display:inline-block;border:1px solid ${accent};border-radius:99px;padding:5px 12px;margin:0 6px 6px 0}
@keyframes in{from{opacity:0;transform:translateY(8px)}}</style></head><body>
${live ? `<div class="bar">✦ Нейросеть Rai пишет сайт… это черновик, готовый сайт соберёт дизайн студии</div>` : ""}
<header><h1>${esc(spec.title || "…")}</h1><p>${esc(spec.tagline || "")}</p></header>${secs}</body></html>`;
  }

  async function askSection(spec, title, wish, ui) {
    ui.step(`Нейросеть пишет раздел «${title}»…`);
    const context = `Сайт: «${spec.title || ""}» — ${spec.tagline || ""}. Разделы: ${(spec.sections || []).map((s) => s.title).join(", ")}.`;
    const raw = await ask(SECTION_SYSTEM, context + "\nОписание клиента: " + (ui.prompt || "") + "\n\nНапиши раздел «" + title + "». " + (wish || ""),
                          null, {temperature: 0.6, maxTokens: 1500});
    const sec = normSpec({sections: [parseJSON(raw)]});
    const s = sec && sec.sections[0];
    if (!s || !(s.text || (s.items && s.items.length) || (s.tags && s.tags.length))) return null;
    if (!s.title) s.title = title;
    return s;
  }
  function insertBeforeContacts(spec, sec) {
    const at = spec.sections.findIndex((s) => s.kind === "contacts");
    if (at < 0) spec.sections.push(sec); else spec.sections.splice(at, 0, sec);
  }

  async function generateSpec(prompt, ui) {
    const t0 = Date.now();
    let best = null;
    const base = "Описание сайта от клиента: " + prompt;
    let request = base;
    for (let attempt = 0; attempt < 3; attempt++) {
      ui.step(attempt ? "Пишу сайт заново — прошлый вариант не получился…" : "Нейросеть придумывает сайт и пишет все тексты…");
      let shown = 0, count = 0;
      const raw = await ask(SPEC_SYSTEM, request, (t) => {
        if (Date.now() - shown < 600) return;
        shown = Date.now();
        const part = normSpec(partialJSON(t));
        if (!part) return;
        ui.code(sketch(part, true));
        if (part.sections.length !== count && part.sections.length) {
          count = part.sections.length;
          ui.step(`Пишу раздел ${count}: «${part.sections[count - 1].title || "…"}»…`);
        }
      }, {temperature: 0.6, maxTokens: 3600});
      const spec = normSpec(parseJSON(raw));
      const q = inspectSpec(spec, prompt);
      if (spec && (!best || q.score > best.q.score)) best = {spec: spec, q: q};
      if (spec && !q.broken) break;
      request = base + "\n\nВАЖНО: прошлый ответ не годится (" + (spec ? q.issues.join("; ") : "это был не JSON") +
        "). Ответь только JSON по схеме: 4–7 разделов с настоящими текстами.";
    }
    if (!best || !best.spec.sections.length) {
      throw new Error("Нейросеть не смогла написать сайт — попробуйте ещё раз, опишите сайт подробнее или выберите модель посильнее.");
    }
    // доработка: дописываем недостающие разделы и переписываем слабые — а не весь сайт заново
    const spec = best.spec;
    for (let round = 0; round < 2; round++) {
      const q = inspectSpec(spec, prompt);
      if (!q.missing.length && !q.weak.length) break;
      ui.step("Проверка нашла: " + q.issues.join("; ") + ". Дорабатываю…");
      for (const kind of q.missing) {
        const sec = await askSection(spec, TITLES[kind], `Вид раздела (kind): ${kind}.`, Object.assign({}, ui, {prompt: prompt}));
        if (sec) { sec.kind = sec.kind || kind; insertBeforeContacts(spec, sec); ui.code(sketch(spec, true)); }
      }
      for (const w of q.weak.slice(0, 4)) {
        const s = w.section;
        const fresh = await askSection(spec, s.title || TITLES[s.kind] || "Раздел",
          `Вид раздела (kind): ${s.kind}. Прошлый вариант был плохим (${w.why.join(", ")}): ${JSON.stringify(s).slice(0, 1200)}. Напиши лучше.`,
          Object.assign({}, ui, {prompt: prompt}));
        const at = spec.sections.indexOf(s);
        if (fresh && at >= 0) { fresh.kind = s.kind || fresh.kind; spec.sections[at] = fresh; ui.code(sketch(spec, true)); }
      }
    }
    const q = inspectSpec(spec, prompt);
    return {kind: "spec", spec: spec, report: {seconds: Math.round((Date.now() - t0) / 1000), issues: q.issues, score: q.score, how: "spec"}};
  }

  // ---------------------------------------------------------------- нейросеть пишет весь код
  function fallbackPlan(prompt) {
    const name = (prompt.match(/[«"]([^»"]{2,40})[»"]/) || [])[1] || prompt.split(/[,.!]/)[0].slice(0, 40);
    return {title: name, tagline: "", theme: /тёмн|темн|чёрн|черн|dark/i.test(prompt) ? "dark" : "light", accent: "#ff3d81", accent2: "#8b5cff",
            font: "Onest", sections: [{id: "hero", title: name, points: [prompt]}, {id: "about", title: "О нас", points: []},
            {id: "services", title: "Что мы предлагаем", points: []}, {id: "reviews", title: "Отзывы", points: []}, {id: "contacts", title: "Контакты", points: []}]};
  }
  async function makePlan(prompt, onStep) {
    onStep && onStep("Нейросеть составляет план сайта…");
    const raw = await ask(PLAN_SYSTEM, "Описание сайта от клиента: " + prompt, null, {temperature: 0.5, maxTokens: 1400});
    const plan = parseJSON(raw);
    if (!plan || !Array.isArray(plan.sections) || plan.sections.length < 3) return fallbackPlan(prompt);
    plan.sections = plan.sections.filter((s) => s && s.title).slice(0, 8);
    return plan;
  }

  async function writeHtml(userText, onCode, onStep) {
    let html = "";
    for (let round = 0; round < 4; round++) {
      if (round) onStep && onStep(`Код оборвался — нейросеть дописывает (${round})…`);
      const text = round === 0 ? userText : "Ты писал файл index.html и остановился. Вот последние строки уже написанного кода:\n" +
        tail(html, 2500) + "\n\nПродолжи код РОВНО с места остановки (не повторяй уже написанное, без пояснений) и закончи </html>.";
      let live = "", shown = 0;
      const raw = await ask(SITE_SYSTEM, text, (t) => {
        live = t;
        if (!onCode || Date.now() - shown < 500) return;
        shown = Date.now();
        onCode(safe(round === 0 ? extractHtml(t) : html + fragment(t)));
      });
      const piece = round === 0 ? extractHtml(raw || live) : fragment(raw || live);
      if (round && /<!doctype html/i.test(piece)) html = extractHtml(piece);   // начала заново — берём новый вариант целиком
      else html = round === 0 ? piece : html + piece.replace(/^<\/?(html|body)[^>]*>\s*/i, "");
      if (/<\/html>\s*$/i.test(html)) break;
    }
    return safe(html);
  }

  function inspect(html, plan, prompt) {
    const issues = [];
    const doc = docOf(html);
    const text = (doc.body ? doc.body.textContent : "").replace(/\s+/g, " ").trim();
    const low = text.toLowerCase();
    if (!/<\/html>\s*$/i.test(html)) issues.push("код оборван (нет </html>)");
    if (!/<style[\s>]/i.test(html)) issues.push("нет стилей <style>");
    if (!doc.querySelector('meta[name="viewport"]')) issues.push("нет адаптивности (meta viewport)");
    if (text.length < 900) issues.push("слишком мало текста — разделы почти пустые");
    if (/lorem ipsum|dolor sit amet|здесь будет|ваш текст|текст раздела|заголовок раздела|placeholder|example\.com|todo/i.test(text)) issues.push("остались заглушки вместо текстов");
    if (doc.querySelectorAll("section").length < 3) issues.push("меньше трёх разделов <section>");
    if (/<script/i.test(html)) issues.push("есть <script> — JavaScript в сайтах студии запрещён");
    for (const s of (plan && plan.sections) || []) {
      const words = keyWords(s.title);
      if (words.length && !words.some((w) => low.includes(w))) issues.push(`нет раздела «${s.title}»`);
    }
    for (const c of String(prompt || "").match(/[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s()-]{8,}\d/g) || []) {
      const plain = c.replace(/[\s()-]/g, "");
      if (!html.replace(/[\s()-]/g, "").includes(plain)) issues.push(`нет контакта ${c.trim()}`);
    }
    return {issues: issues, score: Math.max(0, 100 - issues.length * 14 - (text.length < 1500 ? 6 : 0)), chars: text.length};
  }

  const planText = (plan, prompt) => "Описание клиента: " + prompt + "\n\nПлан сайта (JSON):\n" + JSON.stringify(plan, null, 1);

  async function generateCode(prompt, ui) {
    const t0 = Date.now();
    const plan = await makePlan(prompt, ui.step);
    ui.step(`План готов: «${plan.title}» — ${plan.sections.map((s) => s.title).join(", ")}. Пишу код сайта…`);
    let best = null;
    let request = planText(plan, prompt);
    for (let attempt = 0; attempt < 3; attempt++) {
      const html = await writeHtml(request, ui.code, ui.step);
      const q = inspect(html, plan, prompt);
      if (!best || q.score > best.q.score) best = {html: html, q: q};
      if (!q.issues.length) break;
      if (attempt < 2) {
        ui.step("Проверка нашла: " + q.issues.join("; ") + ". Исправляю…");
        request = planText(plan, prompt) + "\n\nВАЖНО: прошлый вариант был с ошибками — " + q.issues.join("; ") +
          ". Исправь всё это: полный файл, все разделы плана с настоящими текстами, все контакты.";
      }
    }
    if (best.q.issues.some((x) => /оборван|меньше трёх|мало текста/.test(x))) {
      // свой дизайн не вышел — делаем надёжным способом, чтобы человек не остался ни с чем
      ui.step("Код получился неполным — собираю сайт надёжным способом: тексты нейросети + дизайн студии…");
      const r = await generateSpec(prompt, ui);
      r.report.note = "свой дизайн не получился, поэтому сайт собран дизайном студии";
      return r;
    }
    return {kind: "html", html: best.html, plan: plan, title: plan.title,
            report: {seconds: Math.round((Date.now() - t0) / 1000), issues: best.q.issues, score: best.q.score, how: "code"}};
  }

  /** Новый сайт. Возвращает {kind: "spec", spec, report} или {kind: "html", html, title, report}. */
  async function generate(prompt, ui) {
    stopped = false; working = true;
    try {
      await ensureModel(ui.step);
      await takeLimit();
      return how() === "code" ? await generateCode(prompt, ui) : await generateSpec(prompt, ui);
    } finally { working = false; }
  }

  // ---------------------------------------------------------------- правки
  const GLOBAL = /цвет|т[её]мн|светл|шрифт|стил|дизайн|фон|оформлен|анимац|красивее|современн|минимал|ярче|контраст/i;
  const ADD = /^(?:добавь|добавить|создай|вставь|нужен|нужна)\s+(?:ещё\s+)?(?:раздел|блок|секцию)?\s*[«"]?(.+?)[»"]?\s*$/i;
  const REMOVE = /^(?:убери|удали|удалить|убрать)\s+(?:раздел|блок|секцию)?\s*[«"]?(.+?)[»"]?\s*$/i;
  // такие правки студия делает сама мгновенно (без нейросети): цвет, тема, название, слоган, контакты, убрать раздел
  const COLOR = "т[её]мн|светл|ч[её]рн|бел|красн|алый|бордов|син|голуб|зел[её]н|ж[её]лт|оранж|фиолет|розов|бирюз|золот|коричн|сер";
  const SIMPLE = new RegExp("^(?:переименуй|назови|слоган|девиз|подзаголовок|убери|удали|скрой)|" +
    "^(?:сделай\\s+)?(?:сайт\\s+|фон\\s+|тему\\s+|цвет\\s+)?(?:" + COLOR + ")[а-яё]*(?:\\s+(?:тем[аоуы]й?|цвет[аом]?|фон[аом]?|сайт))?\\s*$|" +
    "^(?:поменяй\\s+|измени\\s+)?(?:цвет|акцент)\\s+(?:на\\s+)?(?:" + COLOR + ")[а-яё]*\\s*$|" +
    "^(?:добавь|укажи|поменяй|измени)\\s+(?:почту|телефон|адрес|телеграм|e-?mail|контакт)", "i");
  const EDIT_WORDS = /^(добав|убери|удал|измен|сдела|перепи|разде|блок|секци|поменя|замен|напиш)/;

  function sectionsOf(doc) {
    return Array.from(doc.querySelectorAll("section, header, footer")).map((el) => ({
      el: el, label: ((el.querySelector("h1,h2,h3") || {}).textContent || "") + " " + (el.id || "") + " " + el.tagName}));
  }
  function bestSection(doc, words) {
    let best = null, top = 0;
    for (const s of sectionsOf(doc)) {
      const label = s.label.toLowerCase();
      const score = words.filter((w) => label.includes(w)).length;
      if (score > top) { top = score; best = s.el; }
    }
    return best;
  }
  function specSection(spec, words) {
    let best = -1, top = 0;
    (spec.sections || []).forEach((s, i) => {
      const label = (String(s.title || "") + " " + s.kind + " " + (TITLES[s.kind] || "")).toLowerCase();
      const score = words.filter((w) => label.includes(w)).length;
      if (score > top) { top = score; best = i; }
    });
    return best;
  }

  async function editSpec(spec, instruction, ui) {
    spec = normSpec(JSON.parse(JSON.stringify(spec || {})));
    if (!spec || !spec.sections.length) throw new Error("Сначала создайте сайт.");
    const add = instruction.match(ADD);
    if (add) {
      const sec = await askSection(spec, add[1].slice(0, 60), instruction, ui);
      if (!sec) throw new Error("Нейросеть не написала раздел — попробуйте сказать иначе.");
      insertBeforeContacts(spec, sec);
      return {spec: spec, done: `добавил раздел «${sec.title}»`};
    }
    const words = keyWords(instruction).filter((w) => !EDIT_WORDS.test(w));
    const at = words.length && !/весь|всё|все\s|сайт|тексты/i.test(instruction) ? specSection(spec, words) : -1;
    if (at >= 0) {  // правка одного раздела
      const old = spec.sections[at];
      ui.step(`Нейросеть правит раздел «${old.title}»…`);
      const raw = await ask(SECTION_SYSTEM, `Сайт: «${spec.title}». Вот раздел в JSON:\n${JSON.stringify(old)}\n\nПравка клиента: ${instruction}\n` +
                            "Верни исправленный раздел JSON (тот же kind, если правка не просит другого).", null, {temperature: 0.5, maxTokens: 1800});
      const fresh = (normSpec({sections: [parseJSON(raw)]}) || {sections: []}).sections[0];
      if (fresh && (fresh.text || (fresh.items && fresh.items.length) || (fresh.tags && fresh.tags.length))) {
        fresh.kind = fresh.kind || old.kind;
        fresh.title = fresh.title || old.title;
        spec.sections[at] = fresh;
        return {spec: spec, done: `переписал раздел «${fresh.title}»`};
      }
    }
    ui.step("Нейросеть переписывает сайт с правкой…");
    const slim = {title: spec.title, tagline: spec.tagline, theme: spec.theme, accent: spec.accent, sections: spec.sections, contacts: spec.contacts};
    let shown = 0;
    const raw = await ask(SPEC_EDIT_SYSTEM, "Сайт (JSON):\n" + JSON.stringify(slim) + "\n\nПравка клиента: " + instruction, (t) => {
      if (Date.now() - shown < 700) return;
      shown = Date.now();
      const part = normSpec(partialJSON(t));
      if (part && part.sections.length) ui.code(sketch(part, true));
    }, {temperature: 0.4, maxTokens: 3600});
    const next = normSpec(parseJSON(raw));
    if (!next || next.sections.length < Math.min(2, spec.sections.length)) throw new Error("Нейросеть не справилась с правкой — попробуйте сказать иначе.");
    next.seed = spec.seed;
    return {spec: next, done: "переписал сайт с правкой"};
  }

  async function editHtml(html, instruction, ui) {
    const doc = docOf(html);
    const words = keyWords(instruction).filter((w) => !EDIT_WORDS.test(w));
    const rem = instruction.match(REMOVE);
    if (rem) {  // удалить раздел — без нейросети
      const el = bestSection(doc, keyWords(rem[1]));
      if (!el) throw new Error(`Не нашёл раздел «${rem[1]}».`);
      if (el.id) doc.querySelectorAll(`a[href="#${CSS.escape(el.id)}"]`).forEach((a) => a.remove());
      el.remove();
      return {html: serialize(doc), done: `убрал раздел «${rem[1]}»`};
    }
    const style = doc.querySelector("style");
    if (GLOBAL.test(instruction) && style) {  // оформление — переписываем только CSS (быстро и без потерь текста)
      ui.step("Нейросеть меняет оформление…");
      const css = fragment(await ask(CSS_SYSTEM, "CSS сайта:\n" + style.textContent.slice(0, 14000) + "\n\nПравка: " + instruction, null, {maxTokens: 5000}))
        .replace(/^<style[^>]*>|<\/style>$/gi, "");
      if (css.length > 200 && /[{}]/.test(css)) { style.textContent = css; return {html: serialize(doc), done: "обновил оформление"}; }
    }
    const add = instruction.match(ADD);
    if (add) {  // новый раздел в стиле сайта — перед подвалом
      ui.step(`Нейросеть пишет раздел «${add[1]}»…`);
      const classes = Array.from(new Set(Array.from(doc.querySelectorAll("[class]")).flatMap((e) => Array.from(e.classList)))).slice(0, 60).join(" ");
      const sample = (doc.querySelector("section") || {}).outerHTML || "";
      const part = fragment(await ask(PART_SYSTEM, `Пример раздела этого сайта (повтори стиль и классы):\n${sample.slice(0, 3500)}\n\nКлассы сайта: ${classes}\n\n` +
        `Правка: напиши НОВЫЙ раздел <section id="…"> «${add[1]}» с настоящими текстами по теме сайта «${(doc.title || "")}». ${instruction}`, null, {maxTokens: 2500}));
      const holder = doc.createElement("div");
      holder.innerHTML = part;
      const sec = holder.querySelector("section") || holder;
      if (!sec.id) sec.id = "s" + Date.now().toString(36);
      const footer = doc.querySelector("footer");
      (footer ? footer.parentNode : doc.body).insertBefore(sec, footer || null);
      const nav = doc.querySelector("nav");
      if (nav) { const a = doc.createElement("a"); a.href = "#" + sec.id; a.textContent = add[1].slice(0, 30); nav.append(a); }
      return {html: serialize(doc), done: `добавил раздел «${add[1]}»`};
    }
    const target = words.length ? bestSection(doc, words) : null;
    if (target) {  // правка одного раздела
      ui.step("Нейросеть правит раздел…");
      const part = fragment(await ask(PART_SYSTEM, "Фрагмент сайта:\n" + target.outerHTML.slice(0, 9000) + "\n\nПравка: " + instruction, null, {maxTokens: 3500}));
      const holder = doc.createElement("div");
      holder.innerHTML = part;
      if (holder.firstElementChild && holder.textContent.trim().length > 20) {
        target.replaceWith(...holder.childNodes);
        return {html: serialize(doc), done: "исправил раздел"};
      }
    }
    // правка всего сайта: если файл небольшой — целиком, иначе новый сайт с учётом правки
    ui.step("Нейросеть переписывает сайт с правкой…");
    const text = html.length < 9000 ? "Вот сайт:\n" + html + "\n\nПравка: " + instruction + ". Верни полный исправленный файл." :
      "Сделай сайт заново по описанию: " + (doc.title || "") + ". " + Array.from(doc.querySelectorAll("h1,h2")).map((h) => h.textContent).join(", ") +
      ". Обязательно учти правку: " + instruction;
    const next = await writeHtml(text, ui.code, ui.step);
    if (inspect(next, null, "").issues.some((x) => /оборван|меньше трёх/.test(x))) throw new Error("Нейросеть не справилась с правкой — попробуйте сказать иначе.");
    return {html: next, done: "переписал сайт с правкой"};
  }

  /**
   * Правка готового сайта. site: {mode, html, spec, prompt}. server(instruction) — быстрая правка студией (actions.php → edit).
   * Возвращает {server: ответ} (сделала студия сама), {kind: "spec", spec, done} или {kind: "html", html, done}.
   */
  async function edit(site, instruction, ui, server) {
    stopped = false; working = true;
    try {
      const code = !!(site && site.mode === "neuro");
      if (!code && SIMPLE.test(instruction) && server) {
        try { return {server: await server(instruction)}; } catch (e) { if (!/не понял/i.test(e.message)) throw e; }
      }
      const html = async () => { const r = await editHtml(site.html, instruction, ui); r.html = safe(r.html); return Object.assign({kind: "html"}, r); };
      if (code && REMOVE.test(instruction)) return await html();
      if (!code && !(site && site.spec)) throw new Error("Сначала создайте сайт: опишите его словами.");
      await ensureModel(ui.step);
      await takeLimit();
      if (!code) return Object.assign({kind: "spec"}, await editSpec(site.spec, instruction, Object.assign({}, ui, {prompt: site.prompt || ""})));
      return await html();
    } finally { working = false; }
  }

  // ---------------------------------------------------------------- интерфейс
  // По умолчанию — свой конструктор Rai (ничего не скачивает); внешняя нейросеть — только если её выбрали
  function mode() { return stored(MODE_KEY, "template"); }
  function setMode(m) {
    store(MODE_KEY, m);
    document.querySelectorAll("#aiMode button").forEach((b) => {
      b.classList.toggle("on", b.dataset.mode === m);
      b.setAttribute("aria-pressed", String(b.dataset.mode === m));
    });
    $("neuroBar").hidden = m !== "neuro";
    const gen = $("genBtn");
    if (gen) gen.textContent = m === "neuro" ? "Создать сайт нейросетью" : "Создать сайт";
  }
  function renderState(st) {
    const pill = $("neuroState");
    pill.textContent = st.state === "ready" ? `${st.label || "Нейросеть Rai"} готова` : st.state === "loading" ? (st.text || "Загружаю…") :
      st.state === "error" ? "Не включилась: " + (st.text || "") : "Нейросеть включится сама при создании сайта";
    pill.classList.toggle("on", st.state === "ready");
    pill.classList.toggle("bad", st.state === "error");
    $("neuroOn").hidden = st.state === "ready" || st.state === "loading";
    $("neuroProgress").hidden = st.state !== "loading";
    $("neuroProgressBar").style.width = Math.round((st.progress || 0) * 100) + "%";
    renderHow();
  }
  function renderHow() {
    const sel = $("neuroHow");
    if (!sel) return;
    const auto = sel.querySelector('option[value="auto"]');
    if (auto) auto.textContent = "Авто: " + (how() === "code" ? "нейросеть пишет весь код" : "тексты нейросети + дизайн студии");
    sel.disabled = onCpu();
    sel.title = onCpu() ? "На процессоре нейросеть пишет тексты, а дизайн собирает студия — так в разы быстрее" : "";
  }
  function renderModels() {
    const sel = $("neuroModel");
    if (!sel || !N()) return;
    const unlock = (limits && limits.unlock) || {};
    for (const o of sel.options) {
      if (o.value === "auto") continue;
      const m = N().MODELS[o.value];
      const locked = !!(limits && Array.isArray(limits.models) && !limits.models.includes(o.value));
      o.textContent = (m ? m.label + " · " + m.size : o.value) + (locked ? ` — тариф «${unlock[o.value] || "выше"}»` : "");
      o.disabled = locked;
    }
  }
  function renderLeft() {
    const box = $("neuroLeft");
    if (!box || !limits) return;
    box.hidden = false;
    box.textContent = limits.limit > 0 ? `Тариф «${limits.plan_name}»: осталось ${limits.left} из ${limits.limit} на сегодня` :
      `Тариф «${limits.plan_name}»: без ограничений`;
    if (limits.guest) {  // вход в Rai истёк — без входа нейросеть работает меньше
      const a = document.createElement("a");
      a.href = HOME + "/login.php"; a.target = "_blank"; a.rel = "noopener"; a.textContent = "Войти в Rai";
      box.append(" · ", a, " — будет больше");
    }
  }
  function init() {
    if (!$("aiMode")) return;
    document.querySelectorAll("#aiMode button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
    setMode(mode());
    if (!N()) { $("neuroState").textContent = "Нейросеть Rai не загрузилась — работают быстрые шаблоны"; setMode("template"); return; }
    const sel = $("neuroModel");
    renderModels();
    sel.value = chosenModel();
    if (!sel.value) sel.value = "auto";
    sel.addEventListener("change", async () => {
      store(MODEL_KEY, sel.value);
      if (N().ready() || N().status().state === "loading") {
        try { await N().enable(await modelFor(sel.value)); } catch (e) { /* причина — в строке состояния */ }
      }
    });
    const howSel = $("neuroHow");
    if (howSel) {
      howSel.value = stored(HOW_KEY, "auto");
      howSel.addEventListener("change", () => { store(HOW_KEY, howSel.value); renderHow(); });
    }
    N().onChange(renderState);
    $("neuroOn").addEventListener("click", () => ensureModel().catch((e) => renderState({state: "error", text: e.message})));
    if (!navigator.gpu && !window.RAI_NEURO_TEST) {
      $("neuroHint").textContent = "В этом браузере нет WebGPU — нейросеть будет работать на процессоре: тексты пишет она, дизайн собирает студия " +
        "(несколько минут). Быстрее — Chrome или Edge на компьютере с видеокартой. Или выберите «⚡ Быстрые шаблоны».";
    }
    // модель уже скачивали раньше (она в кэше браузера) — включаем сразу, чтобы первый сайт делался без ожидания
    ready.then(() => {
      const was = N().saved && N().saved();
      if (mode() === "neuro" && was && was !== "off") ensureModel().catch(() => null);
    });
  }

  window.StudioAI = {
    active: () => mode() === "neuro" && !!N(), how: how, busy: () => working, stop: stop, Stopped: Stopped,
    generate: generate, edit: edit,
    // для проверок
    inspect: inspect, inspectSpec: inspectSpec, extractHtml: extractHtml, parseJSON: parseJSON, partialJSON: partialJSON,
    writeHtml: writeHtml, sketch: sketch, safe: safe, SIMPLE: SIMPLE
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
</script>
