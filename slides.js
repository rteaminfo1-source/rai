/* Rai Слайды — редактор презентаций: создать по теме и цветам, править слайды, менять тему, показывать и скачивать.
   Страница подключает этот файл и вызывает RaiSlides.init(host) — см. index.html. */
(function () {
  "use strict";

  const STORE = "rai_slides_v1";
  const KINDS = {
    title: "Обложка", bullets: "Пункты", fact: "Факт", agenda: "План", summary: "Итоги", stats: "Цифры",
    timeline: "Хронология", quote: "Цитата", compare: "Сравнение", code: "Код", table: "Таблица", photo: "Фото", end: "Финал"
  };
  const TRANSITIONS = {fade: "Растворение", slide: "Сдвиг", zoom: "Приближение", wipe: "Шторка", rise: "Подъём"};
  const PRESETS = [
    ["Rteam", "#0b0b0c", "#f5f3f3", "#e10600", "#ff6a5c"], ["Океан", "#0b1f4d", "#f5f7ff", "#38bdf8", "#818cf8"],
    ["Лес", "#0f2418", "#f1f7f2", "#22c55e", "#a3e635"], ["Золото", "#111111", "#f7f3e8", "#c9a227", "#f5d67a"],
    ["Фиолет", "#1a1033", "#f5f3ff", "#a855f7", "#f472b6"], ["Светлая", "#ffffff", "#141414", "#e10600", "#1e5bff"],
    ["Песок", "#f7f1e6", "#2b2118", "#c2410c", "#0f766e"], ["Графит", "#1f2937", "#f9fafb", "#f59e0b", "#10b981"]
  ];

  let H = null, el = {}, state = null, k = 0, history = [], saveTimer = null, busy = false;

  // ---------------------------------------------------------------- цвета
  const hex = (c) => /^#[0-9a-f]{6}$/i.test(c || "") ? c.toLowerCase() : null;
  function mix(a, b, t) {
    const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16)), pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
    return "#" + pa.map((x, i) => Math.round(x + (pb[i] - x) * t).toString(16).padStart(2, "0")).join("");
  }
  function lum(c) {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16) / 255);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }
  /** Полная тема из четырёх цветов (как deck_theme в creative.py). */
  function makeTheme(bg, fg, accent, accent2, custom) {
    return {bg: bg, fg: fg, accent: accent, accent2: accent2, muted: mix(fg, bg, 0.42), surface: mix(bg, fg, 0.07),
            line: mix(bg, fg, 0.16), on_accent: lum(accent) > 0.6 ? "#111111" : "#ffffff", custom: custom !== false};
  }

  // ---------------------------------------------------------------- хранение
  function uid() { return "d" + Math.random().toString(36).slice(2, 9) + Date.now().toString(36); }
  function load() {
    try {
      const d = JSON.parse(localStorage.getItem(STORE) || "null");
      if (d && Array.isArray(d.decks)) state = d;
    } catch (e) { /* пусто */ }
    if (!state) state = {decks: [], current: null};
    if (!state.decks.some((d) => d.id === state.current)) state.current = state.decks[0] ? state.decks[0].id : null;
  }
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try { localStorage.setItem(STORE, JSON.stringify(state)); }
      catch (e) { H.toast("Не хватает места в браузере — скачайте презентацию и удалите старые"); }
    }, 400);
  }
  const deck = () => state.decks.find((d) => d.id === state.current) || null;
  function snapshot() {
    const d = deck();
    if (!d) return;
    const snap = JSON.stringify(d);
    if (history[history.length - 1] !== snap) history.push(snap);
    if (history.length > 40) history.shift();
  }
  function undo() {
    const snap = history.pop();
    if (!snap) { H.toast("Отменять нечего"); return; }
    const old = JSON.parse(snap);
    const i = state.decks.findIndex((d) => d.id === old.id);
    if (i >= 0) state.decks[i] = old;
    k = Math.min(k, old.slides.length - 1);
    save(); render();
  }

  // ---------------------------------------------------------------- разметка
  const ICON = (n) => `<svg class="i"><use href="#i-${n}"/></svg>`;
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  function build(root) {
    root.innerHTML = `
<div class="sl-top">
  <input id="slTopic" placeholder="Про что презентация? Например: космос, Python, история Рима" aria-label="Тема презентации">
  <input id="slColors" placeholder="Цвета: синие тона, чёрно-золотая, #7c3aed" aria-label="Цвета">
  <button class="tb run" id="slMake" type="button">${ICON("play")}<span class="lbl">Создать</span></button>
  <select id="slDecks" aria-label="Мои презентации"></select>
  <span class="spacer"></span>
  <button class="tb" id="slShow" type="button" title="Показ на весь экран (F5)">${ICON("full")}<span class="lbl">Показ</span></button>
  <button class="tb" id="slPptx" type="button" title="Скачать для PowerPoint, Google Slides, Keynote">${ICON("deck")}<span class="lbl">PowerPoint</span></button>
  <button class="tb" id="slHtml" type="button" title="Скачать одним HTML-файлом">${ICON("down")}<span class="lbl">HTML</span></button>
  <button class="tb" id="slZip" type="button" title="Скачать ZIP с картинками">${ICON("zip")}<span class="lbl">ZIP</span></button>
  <button class="tb" id="slPdf" type="button" title="Печать или сохранение в PDF">${ICON("book")}<span class="lbl">PDF</span></button>
</div>
<div class="sl-main">
  <nav class="sl-thumbs" id="slThumbs" aria-label="Слайды"></nav>
  <div class="sl-center">
    <div class="sl-stage-wrap"><div id="slStageBox"></div></div>
    <div class="sl-nav">
      <button class="tb" id="slPrev" type="button" aria-label="Предыдущий слайд">${ICON("left")}</button>
      <span class="count" id="slCount"></span>
      <button class="tb" id="slNext" type="button" aria-label="Следующий слайд">${ICON("right")}</button>
      <button class="tb" id="slUp" type="button" title="Переместить выше">↑</button>
      <button class="tb" id="slDown" type="button" title="Переместить ниже">↓</button>
      <button class="tb" id="slDup" type="button" title="Копия слайда">⧉</button>
      <button class="tb" id="slDel" type="button" title="Удалить слайд">${ICON("trash")}</button>
      <button class="tb" id="slUndo" type="button" title="Отменить (Ctrl+Z)">↶</button>
    </div>
  </div>
  <aside class="sl-side" id="slSide" aria-label="Настройки слайда"></aside>
</div>`;
    for (const id of ["slTopic", "slColors", "slMake", "slDecks", "slShow", "slPptx", "slHtml", "slZip", "slPdf", "slThumbs", "slStageBox",
                      "slPrev", "slNext", "slCount", "slUp", "slDown", "slDup", "slDel", "slUndo", "slSide"]) {
      el[id] = root.querySelector("#" + id);
    }
    el.root = root;
  }

  // ---------------------------------------------------------------- отрисовка
  function slideHTML(s, n, total, dir, play) {
    const html = H.deck.slideHTML(s, n, total, dir, deck().theme);
    return play ? html : html.replace(/class="slide play t-[a-z]+/, 'class="slide');
  }
  function render() {
    renderDecks();
    const d = deck();
    const has = !!(d && d.slides.length);
    for (const id of ["slShow", "slPptx", "slHtml", "slZip", "slPdf", "slPrev", "slNext", "slUp", "slDown", "slDup", "slDel"]) el[id].disabled = !has;
    if (!d) {
      el.slThumbs.innerHTML = "";
      el.slStageBox.innerHTML = `<div class="sl-empty"><b>Здесь делаются презентации.</b><br>Напишите тему сверху и, если хотите, цвета —
        Rai соберёт слайды с текстом, картинками и переходами. Потом правьте любой слайд справа, меняйте цвета и показывайте на весь экран.
        Презентацию из чата можно открыть здесь кнопкой «В Слайды».</div>`;
      el.slCount.textContent = "";
      el.slSide.innerHTML = "";
      return;
    }
    k = Math.max(0, Math.min(k, d.slides.length - 1));
    renderThumbs();
    showStage(1);
    renderSide();
  }
  function renderDecks() {
    const sel = el.slDecks;
    sel.innerHTML = state.decks.length
      ? state.decks.map((d) => `<option value="${esc(d.id)}"${d.id === state.current ? " selected" : ""}>${esc(d.title)} · ${d.slides.length}</option>`).join("") +
        `<option value="__del">— удалить эту презентацию</option>`
      : `<option value="">Презентаций пока нет</option>`;
    sel.disabled = !state.decks.length;
  }
  function renderThumbs() {
    const d = deck(), box = el.slThumbs;
    box.innerHTML = "";
    d.slides.forEach((s, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "sl-thumb" + (i === k ? " on" : "");
      b.setAttribute("aria-label", `Слайд ${i + 1}: ${s.title || KINDS[s.kind] || ""}`);
      b.innerHTML = `<span class="n">${i + 1}</span><div class="mini">${slideHTML(s, i + 1, d.slides.length, 1, false)}</div>`;
      b.addEventListener("click", () => { k = i; render(); });
      box.append(b);
    });
    const add = document.createElement("div");
    add.className = "sl-row";
    add.innerHTML = `<select aria-label="Тип нового слайда" class="sl-add" style="flex:1">${Object.entries(KINDS).map(([v, t]) => `<option value="${v}"${v === "bullets" ? " selected" : ""}>${t}</option>`).join("")}</select>` +
      `<button class="sl-add" type="button" aria-label="Добавить слайд">+</button>`;
    add.querySelector("button").addEventListener("click", () => addSlide(add.querySelector("select").value));
    box.append(add);
    const on = box.querySelector(".sl-thumb.on");
    if (on) on.scrollIntoView({block: "nearest", inline: "nearest"});
  }
  function showStage(dir) {
    const d = deck();
    el.slStageBox.className = "sl-stage";
    el.slStageBox.style.background = d.theme.bg;
    el.slStageBox.innerHTML = slideHTML(d.slides[k], k + 1, d.slides.length, dir, true);
    el.slCount.textContent = `${k + 1} / ${d.slides.length}`;
  }
  function refreshCurrent() {
    // быстрая перерисовка при наборе текста: сцена без анимации и одна миниатюра
    const d = deck(), s = d.slides[k];
    el.slStageBox.innerHTML = slideHTML(s, k + 1, d.slides.length, 1, false);
    const mini = el.slThumbs.querySelectorAll(".sl-thumb .mini")[k];
    if (mini) mini.innerHTML = slideHTML(s, k + 1, d.slides.length, 1, false);
    save();
  }

  // ---------------------------------------------------------------- правая панель
  const lines = (a) => (a || []).join("\n");
  const unlines = (t) => t.split("\n").map((x) => x.trim()).filter(Boolean);
  // «значение — подпись» для цифр и хронологии
  const PAIR = {stats: ["value", "label"], timeline: ["date", "text"]};
  const pairText = (x) => typeof x === "string" ? x : [x && x[0], x && x[1]].join(" — ");
  function toPairs(list, keys) {
    return (list || []).map((x) => {
      if (x && typeof x === "object" && !Array.isArray(x)) {
        if (keys[0] in x || keys[1] in x) return {[keys[0]]: String(x[keys[0]] || ""), [keys[1]]: String(x[keys[1]] || "")};
        const v = Object.values(x);
        return {[keys[0]]: String(v[0] || ""), [keys[1]]: String(v[1] || "")};
      }
      const t = String(x || ""), m = t.match(/^\s*(.+?)\s+[—–-]\s+(.+)$/) || t.match(/^\s*([\d.,]+\s*[%+×x]?|[\d.,]+\s*\S+)\s+(.+)$/);
      return m ? {[keys[0]]: m[1].trim(), [keys[1]]: m[2].trim()} : {[keys[0]]: "", [keys[1]]: t.trim()};
    }).filter((x) => x[keys[0]] || x[keys[1]]);
  }
  function plainItems(list) {
    return (list || []).map((x) => x && typeof x === "object" ? Object.values(x).filter(Boolean).join(" — ") : String(x || "")).filter(Boolean);
  }
  function field(label, html) { return `<label class="sl-field">${label}${html}</label>`; }
  function renderSide() {
    const d = deck(), s = d.slides[k], t = d.theme;
    let form = field("Тип слайда", `<select data-f="kind">${Object.entries(KINDS).map(([v, n]) => `<option value="${v}"${v === s.kind ? " selected" : ""}>${n}</option>`).join("")}</select>`);
    form += field("Заголовок", `<input data-f="title" value="${esc(s.title)}" maxlength="120">`);
    if (s.kind === "title" || s.kind === "end") form += field("Подзаголовок", `<input data-f="subtitle" value="${esc(s.subtitle)}" maxlength="160">`);
    if (s.kind === "bullets") form += field("Пункты — каждый с новой строки", `<textarea data-f="bullets">${esc(lines(s.bullets))}</textarea>`);
    if (s.kind === "fact") form += field("Текст факта", `<textarea data-f="text">${esc(s.text)}</textarea>`);
    if (s.kind === "agenda" || s.kind === "summary") form += field("Пункты — каждый с новой строки", `<textarea data-f="items">${esc(lines(s.items))}</textarea>`);
    if (PAIR[s.kind]) form += field(s.kind === "stats" ? "Цифры: «число — подпись», каждая с новой строки" : "События: «дата — что было», каждое с новой строки",
      `<textarea data-f="pairs">${esc((s.items || []).map((x) => pairText([x[PAIR[s.kind][0]], x[PAIR[s.kind][1]]])).join("\n"))}</textarea>`);
    if (s.kind === "quote") {
      form += field("Цитата", `<textarea data-f="text">${esc(s.text)}</textarea>`);
      form += field("Автор", `<input data-f="author" value="${esc(s.author)}" maxlength="120">`);
    }
    if (s.kind === "compare") {
      for (const [key, name] of [["left", "Слева"], ["right", "Справа"]]) {
        const c = s[key] || {};
        form += field(name + ": заголовок", `<input data-f="${key}.title" value="${esc(c.title)}" maxlength="80">`);
        form += field(name + ": пункты — каждый с новой строки", `<textarea data-f="${key}.items">${esc(lines(c.items))}</textarea>`);
      }
    }
    if (s.kind === "code") form += field("Код", `<textarea data-f="code" style="font-family:var(--font-mono);min-height:150px">${esc(s.code)}</textarea>`);
    if (s.kind === "table") form += field("Таблица: ячейки через «|», первая строка — заголовки",
      `<textarea data-f="rows">${esc((s.rows || []).map((r) => r.join(" | ")).join("\n"))}</textarea>`);
    if (s.kind === "photo") {
      form += field("Подпись", `<input data-f="caption" value="${esc(s.caption)}">`);
      form += field("Адрес фото (https://…)", `<input data-f="photo" value="${esc(s.photo)}" inputmode="url">`);
    }
    if (s.kind === "bullets") form += field("Картинка", `<select data-f="side"><option value="">без картинки</option><option value="right"${(s.image || s.pic) && s.side !== "left" ? " selected" : ""}>справа</option><option value="left"${(s.image || s.pic) && s.side === "left" ? " selected" : ""}>слева</option></select>`);
    if (s.kind === "fact" || s.kind === "title" || s.kind === "end" || s.kind === "quote") form += field("Картинка", `<select data-f="pic"><option value="">без картинки</option><option value="1"${s.image || s.pic ? " selected" : ""}>есть</option></select>`);
    form += field("Переход", `<select data-f="transition">${Object.entries(TRANSITIONS).map(([v, n]) => `<option value="${v}"${v === (s.transition || "fade") ? " selected" : ""}>${n}</option>`).join("")}</select>`);
    const picRow = s.image || s.pic ? `<div class="sl-row"><button class="tb" type="button" data-a="webpic">Фото из интернета</button>` +
      `<button class="tb" type="button" data-a="newpic">Рисунок</button></div>` : "";
    el.slSide.innerHTML = `
      <div class="sl-group"><h3>Слайд ${k + 1}</h3>${form}${picRow}</div>
      <div class="sl-group"><h3>Цвета презентации</h3>
        <div class="sl-colors">
          <label>Фон<input type="color" data-c="bg" value="${esc(t.bg)}"></label>
          <label>Текст<input type="color" data-c="fg" value="${esc(t.fg)}"></label>
          <label>Акцент<input type="color" data-c="accent" value="${esc(t.accent)}"></label>
          <label>Второй<input type="color" data-c="accent2" value="${esc(hex(t.accent2) || t.accent)}"></label>
        </div>
        <div class="sl-presets">${PRESETS.map((p, i) => `<button type="button" data-p="${i}" title="${p[0]}" style="background:linear-gradient(135deg,${p[1]} 50%,${p[3]} 50%)"></button>`).join("")}</div>
        <div class="sl-row"><button class="tb" type="button" data-a="recolor">Перекрасить картинки</button></div>
        <p class="sl-note">Или напишите цвета словами сверху («в зелёных тонах») и нажмите «Создать» — соберётся новая презентация.</p>
      </div>
      <div class="sl-group"><h3>Презентация</h3>
        ${field("Название", `<input data-deck="title" value="${esc(d.title)}" maxlength="120">`)}
        <p class="sl-note">Клавиши: ← → — листать, F5 — показ, Ctrl+Z — отменить.</p>
      </div>`;
    wireSide();
  }
  function wireSide() {
    const d = deck();
    el.slSide.querySelectorAll("[data-f]").forEach((inp) => {
      inp.addEventListener("focus", snapshot);
      const ev = inp.tagName === "SELECT" ? "change" : "input";
      inp.addEventListener(ev, () => {
        const s = d.slides[k], f = inp.dataset.f, v = inp.value;
        if (inp.tagName === "SELECT") snapshot();
        if (f === "bullets" || f === "items") s[f] = unlines(v);
        else if (f === "pairs") s.items = toPairs(unlines(v), PAIR[s.kind]);
        else if (f.includes(".")) { const [key, sub] = f.split("."); s[key] = s[key] || {title: "", items: []}; s[key][sub] = sub === "items" ? unlines(v) : v; }
        else if (f === "rows") s.rows = unlines(v).map((r) => r.split("|").map((c) => c.trim()));
        else if (f === "side") { if (!v) { delete s.image; delete s.pic; delete s.side; } else { s.side = v; if (!s.image && !s.pic) newPicture(s); } }
        else if (f === "pic") { if (!v) { delete s.image; delete s.pic; } else if (!s.image && !s.pic) newPicture(s); }
        else s[f] = v;
        if (f === "kind") { fillKind(s); render(); save(); return; }
        if (f === "side" || f === "pic" || f === "transition") { renderThumbs(); showStage(1); renderSide(); save(); return; }
        refreshCurrent();
      });
    });
    const title = el.slSide.querySelector("[data-deck=title]");
    title.addEventListener("focus", snapshot);
    title.addEventListener("input", () => { d.title = title.value; renderDecks(); save(); });
    el.slSide.querySelectorAll("[data-c]").forEach((inp) => {
      inp.addEventListener("focus", snapshot);
      inp.addEventListener("input", () => {
        const t = d.theme;
        t[inp.dataset.c] = inp.value;
        d.theme = makeTheme(t.bg, t.fg, t.accent, hex(t.accent2) || t.accent);
        renderThumbs(); showStage(1); save();
      });
    });
    el.slSide.querySelectorAll("[data-p]").forEach((b) => b.addEventListener("click", () => {
      snapshot();
      const p = PRESETS[+b.dataset.p];
      d.theme = makeTheme(p[1], p[2], p[3], p[4]);
      render(); save();
      recolor(true);
    }));
    el.slSide.querySelectorAll("[data-a]").forEach((b) => b.addEventListener("click", () => {
      if (b.dataset.a === "recolor") recolor(false);
      if (b.dataset.a === "newpic") { snapshot(); delete d.slides[k].pic; newPicture(d.slides[k], true); }
      if (b.dataset.a === "webpic") { snapshot(); webPicture(d.slides[k], b); }
    }));
  }
  /** Поля, которые нужны слайду нового типа. */
  function fillKind(s) {
    const base = () => Array.isArray(s.bullets) && s.bullets.length ? s.bullets : plainItems(s.items).length ? plainItems(s.items)
      : s.left || s.right ? plainItems([].concat((s.left || {}).items || [], (s.right || {}).items || [])) : (s.text ? [s.text] : []);
    if (s.kind === "bullets" && !Array.isArray(s.bullets)) s.bullets = base();
    if (s.kind === "agenda" || s.kind === "summary") s.items = plainItems(Array.isArray(s.items) ? s.items : base());
    if (PAIR[s.kind]) {
      const items = toPairs(Array.isArray(s.items) && s.items.length ? s.items : base(), PAIR[s.kind]);
      s.items = items.length ? items : s.kind === "stats" ? [{value: "90%", label: "подпись"}, {value: "3×", label: "подпись"}]
        : [{date: "2020", text: "событие"}, {date: "2024", text: "событие"}];
    }
    if (s.kind === "compare" && !s.left) {
      const all = base(), half = Math.ceil(all.length / 2);
      s.left = {title: "Было", items: all.slice(0, half)};
      s.right = {title: "Стало", items: all.slice(half)};
    }
    if ((s.kind === "fact" || s.kind === "quote") && !s.text) s.text = base()[0] || "";
    if (s.kind === "table" && !Array.isArray(s.rows)) s.rows = [["Столбец 1", "Столбец 2"], ["", ""]];
    if (s.kind === "code" && s.code == null) s.code = "";
  }

  // ---------------------------------------------------------------- картинки
  function imagePrompt(s) { return (deck().title + " " + (s.title || "")).trim(); }
  async function newPicture(s, random) {
    try {
      const r = await H.slides("image", {prompt: imagePrompt(s), seed: random ? Math.floor(Math.random() * 1e9) : (s.seed || Math.floor(Math.random() * 1e9)), theme: deck().theme});
      if (r && r.svg) { s.image = r.svg; renderThumbs(); showStage(1); save(); }
    } catch (e) { H.toast("Не удалось нарисовать картинку"); }
  }
  // Фото из интернета (Википедия): каждое нажатие — следующее фото по теме слайда
  const photoCache = {};
  async function webPicture(s, btn) {
    const query = (s.title && s.kind !== "title" && s.kind !== "end" ? s.title : deck().title) || deck().title;
    if (btn) btn.disabled = true;
    try {
      if (!photoCache[query]) photoCache[query] = (await H.slides("photos", {query: query})).photos || [];
      let list = photoCache[query];
      if (!list.length && query !== deck().title) list = photoCache[deck().title] = photoCache[deck().title] || (await H.slides("photos", {query: deck().title})).photos || [];
      if (!list.length) { H.toast("Фото в интернете не нашлось (или нет связи)"); return; }
      s.pic = list[(list.indexOf(s.pic) + 1) % list.length];
      renderThumbs(); showStage(1); renderSide(); save();
    } catch (e) {
      H.toast("Не удалось найти фото");
    } finally {
      if (btn) btn.disabled = false;
    }
  }
  async function recolor(quiet) {
    const d = deck();
    if (!d) return;
    const withPics = d.slides.filter((s) => s.image);
    if (!withPics.length) { if (!quiet) H.toast("В презентации нет картинок"); return; }
    if (!quiet) snapshot();
    let i = 0;
    for (const s of withPics) {
      s.seed = s.seed || (i + 1) * 7919;
      try {
        const r = await H.slides("image", {prompt: imagePrompt(s), seed: s.seed, theme: d.theme});
        if (r && r.svg) s.image = r.svg;
      } catch (e) { /* оставим старую картинку */ }
      i++;
    }
    renderThumbs(); showStage(1); save();
    if (!quiet) H.toast("Картинки перекрашены");
  }

  // ---------------------------------------------------------------- действия со слайдами
  function go(dir) {
    const d = deck();
    if (!d) return;
    const n = Math.max(0, Math.min(d.slides.length - 1, k + dir));
    if (n === k) return;
    k = n;
    el.slThumbs.querySelectorAll(".sl-thumb").forEach((t, i) => t.classList.toggle("on", i === k));
    const on = el.slThumbs.querySelector(".sl-thumb.on");
    if (on) on.scrollIntoView({block: "nearest", inline: "nearest"});
    showStage(dir);
    renderSide();
  }
  function addSlide(kind) {
    const d = deck();
    if (!d) return;
    snapshot();
    const s = {kind: kind, title: kind === "end" ? "Спасибо за внимание!" : "", transition: Object.keys(TRANSITIONS)[(k + 1) % 5]};
    fillKind(s);
    if (kind === "agenda") s.title = "План";
    if (kind === "summary") s.title = "Главное";
    d.slides.splice(k + 1, 0, s);
    k++;
    render(); save();
    const inp = el.slSide.querySelector("[data-f=title]");
    if (inp) inp.focus();
  }
  function moveSlide(dir) {
    const d = deck(), j = k + dir;
    if (!d || j < 0 || j >= d.slides.length) return;
    snapshot();
    [d.slides[k], d.slides[j]] = [d.slides[j], d.slides[k]];
    k = j;
    render(); save();
  }
  function duplicate() {
    const d = deck();
    if (!d) return;
    snapshot();
    d.slides.splice(k + 1, 0, JSON.parse(JSON.stringify(d.slides[k])));
    k++;
    render(); save();
  }
  function remove() {
    const d = deck();
    if (!d || d.slides.length <= 1) { H.toast("Последний слайд удалить нельзя"); return; }
    snapshot();
    d.slides.splice(k, 1);
    k = Math.min(k, d.slides.length - 1);
    render(); save();
    H.toast("Слайд удалён — Ctrl+Z вернёт");
  }

  // ---------------------------------------------------------------- создание и открытие
  function addDeck(att) {
    const d = {id: uid(), title: att.title || "Презентация", theme: att.theme || makeTheme("#0b0b0c", "#f5f3f3", "#e10600", "#ff6a5c", false),
               slides: JSON.parse(JSON.stringify(att.slides || [])), updated: Date.now()};
    if (!hex(d.theme.accent2)) d.theme.accent2 = d.theme.accent;
    state.decks.unshift(d);
    state.current = d.id;
    k = 0;
    history = [];
    save(); render();
    return d;
  }
  async function make() {
    const topic = el.slTopic.value.trim();
    if (!topic) { el.slTopic.focus(); H.toast("Напишите тему презентации"); return; }
    if (busy) return;
    busy = true;
    el.slMake.disabled = true;
    el.slMake.querySelector(".lbl").textContent = "Собираю…";
    try {
      const colors = el.slColors.value.trim();
      const data = await H.ask(`сделай презентацию про ${topic}${colors ? " " + (/^(в|во)\s|тон|цвет|#/.test(colors) ? colors : "в цветах " + colors) : ""}`,
                               (step) => { el.slMake.querySelector(".lbl").textContent = step.replace(/….*$/, "…"); });
      const att = (data.attachments || []).find((a) => a.type === "slides");
      if (att) { addDeck(att); H.toast(`Готово: ${att.slides.length} слайдов`); }
      else {
        el.slStageBox.className = "";
        el.slStageBox.innerHTML = `<div class="sl-empty">${H.md(data.answer || "Не получилось собрать презентацию.")}</div>`;
      }
    } catch (e) {
      H.toast("Не удалось собрать презентацию");
    }
    busy = false;
    el.slMake.disabled = false;
    el.slMake.querySelector(".lbl").textContent = "Создать";
  }

  // ---------------------------------------------------------------- показ и экспорт
  function present() {
    const d = deck();
    if (!d) return;
    let i = k;
    const wrap = document.createElement("div");
    wrap.className = "sl-show";
    wrap.innerHTML = `<div class="sl-stage"></div><div class="hint">← → листать · Esc — выход</div>`;
    const stage = wrap.querySelector(".sl-stage");
    stage.style.background = d.theme.bg;
    const show = (dir) => { stage.innerHTML = slideHTML(d.slides[i], i + 1, d.slides.length, dir, true); };
    const step = (dir) => { const n = Math.max(0, Math.min(d.slides.length - 1, i + dir)); if (n !== i) { i = n; show(dir); } };
    const close = () => {
      document.removeEventListener("keydown", keys, true);
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      wrap.remove();
      k = i; render();
    };
    function keys(e) {
      if (["ArrowRight", "PageDown", " ", "Enter"].includes(e.key)) { e.preventDefault(); step(1); }
      else if (["ArrowLeft", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); step(-1); }
      else if (e.key === "Escape") { e.preventDefault(); close(); }
      e.stopPropagation();
    }
    document.addEventListener("keydown", keys, true);
    wrap.addEventListener("click", (e) => step(e.clientX < innerWidth / 3 ? -1 : 1));
    document.addEventListener("fullscreenchange", function onFs() {
      if (!document.fullscreenElement && wrap.isConnected) { document.removeEventListener("fullscreenchange", onFs); close(); }
    });
    document.body.append(wrap);
    show(1);
    if (wrap.requestFullscreen) wrap.requestFullscreen().catch(() => {});
  }
  function exportDeck() {
    const d = deck();
    return {type: "slides", title: d.title, slides: d.slides, theme: d.theme};
  }
  function safeName(s) { return (s || "презентация").replace(/[\\/:*?"<>|«»]+/g, " ").trim().slice(0, 60) || "презентация"; }
  function printPdf() {
    const frame = document.createElement("iframe");
    frame.style.cssText = "position:fixed;width:0;height:0;border:0;right:0;bottom:0";
    frame.srcdoc = H.deck.deckFile(exportDeck());
    frame.onload = () => {
      try { frame.contentWindow.focus(); frame.contentWindow.print(); }
      catch (e) { H.toast("Печать здесь недоступна — скачайте HTML и распечатайте его (Ctrl+P → Сохранить как PDF)"); }
      setTimeout(() => frame.remove(), 60000);
    };
    document.body.append(frame);
  }

  // ---------------------------------------------------------------- инициализация
  function onKey(e) {
    if (el.root.hidden || document.querySelector(".sl-show")) return;
    const typing = /INPUT|TEXTAREA|SELECT/.test((e.target && e.target.tagName) || "");
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !typing) { e.preventDefault(); undo(); return; }
    if (typing) return;
    if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); go(1); }
    if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); go(-1); }
    if (e.key === "F5") { e.preventDefault(); present(); }
    if (e.key === "Delete") remove();
  }
  function init(host) {
    H = host;
    const root = document.getElementById("slidesView");
    build(root);
    load();
    el.slMake.addEventListener("click", make);
    for (const inp of [el.slTopic, el.slColors]) inp.addEventListener("keydown", (e) => { if (e.key === "Enter") make(); });
    el.slDecks.addEventListener("change", () => {
      const v = el.slDecks.value;
      if (v === "__del") {
        const d = deck();
        if (d && confirmDelete(d)) { state.decks = state.decks.filter((x) => x !== d); state.current = state.decks[0] ? state.decks[0].id : null; save(); }
      } else if (v) { state.current = v; k = 0; history = []; save(); }
      render();
    });
    el.slPrev.addEventListener("click", () => go(-1));
    el.slNext.addEventListener("click", () => go(1));
    el.slUp.addEventListener("click", () => moveSlide(-1));
    el.slDown.addEventListener("click", () => moveSlide(1));
    el.slDup.addEventListener("click", duplicate);
    el.slDel.addEventListener("click", remove);
    el.slUndo.addEventListener("click", undo);
    el.slShow.addEventListener("click", present);
    el.slPptx.addEventListener("click", () => H.pptx(exportDeck(), el.slPptx));
    el.slHtml.addEventListener("click", () => H.download(safeName(deck().title) + ".html", new Blob([H.deck.deckFile(exportDeck())], {type: "text/html"})));
    el.slZip.addEventListener("click", () => H.download(safeName(deck().title) + ".zip", H.zip(H.deck.deckFiles(exportDeck(), ""))));
    el.slPdf.addEventListener("click", printPdf);
    el.slStageBox.addEventListener("click", () => go(1));
    document.addEventListener("keydown", onKey);
    render();
  }
  function confirmDelete(d) {
    // Без системного confirm() (в песочницах он запрещён): удаление подтверждается повторным выбором
    if (confirmDelete.pending === d.id) { confirmDelete.pending = null; return true; }
    confirmDelete.pending = d.id;
    H.toast("Выберите «удалить» ещё раз, чтобы удалить «" + d.title + "»");
    return false;
  }

  window.RaiSlides = {
    init: init,
    open: (att) => addDeck(att),
    focus: () => { if (el.root) render(); }
  };
})();
