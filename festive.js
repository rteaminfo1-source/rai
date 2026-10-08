/* Праздничные и недельные темы Rai — разный дизайн под дату, включается сам.
   Праздники (Новый год, 8 Марта, День космонавтики…) важнее недельных тем; недели крутятся по номеру недели года
   (сейчас, например, «неделя космоса»). Тема меняет акцентный цвет, добавляет значок и лёгкое оформление, а в
   новом чате — праздничное приветствие. Всё в браузере, без сервера — работает и в приложении.
   Можно выключить: window.RaiFestive.setOff(true) (кнопка «✕» на плашке). Данные совпадают с festive.php на сайте. */
(function () {
  "use strict";

  // Праздники: [id, название, эмодзи, акцент, второй цвет градиента, украшение, приветствие, [месяц, день с], [месяц, день по]]
  const HOLIDAYS = [
    ["ny", "С Новым годом!", "🎄", "#2aa7e8", "#f5b800", "snow", "С наступающим! ❄️", [12, 20], [1, 8]],
    ["defender", "23 Февраля", "🎖", "#3a7d44", "#8bb174", "", "С Днём защитника Отечества!", [2, 20], [2, 23]],
    ["march8", "8 Марта", "🌷", "#ff4f93", "#ffa6c9", "petals", "С праздником весны! 🌷", [3, 5], [3, 8]],
    ["cosmo", "День космонавтики", "🚀", "#6a5cff", "#2aa7e8", "stars", "Поехали! 🚀", [4, 11], [4, 12]],
    ["victory", "9 Мая", "🎗", "#c62828", "#f5b800", "", "С Днём Победы!", [5, 7], [5, 9]],
    ["russia", "День России", "🇷🇺", "#1e5bff", "#e10600", "", "С Днём России!", [6, 11], [6, 12]],
    ["knowledge", "1 Сентября", "📚", "#1e5bff", "#2aa7e8", "", "С Днём знаний! 📚", [9, 1], [9, 1]],
    ["halloween", "Хэллоуин", "🎃", "#ff7a00", "#8b5cff", "bats", "Уютного Хэллоуина! 🎃", [10, 29], [10, 31]],
  ];

  // Недельные темы: [id, название, эмодзи, акцент, второй цвет, украшение, пример для чата]
  const WEEKS = [
    ["space", "Неделя космоса", "🚀", "#6a5cff", "#2aa7e8", "stars", ["Расскажи про чёрные дыры", "космос"]],
    ["science", "Неделя науки", "🔬", "#1e9d8b", "#2aa7e8", "", ["Как работает фотосинтез", "наука"]],
    ["nature", "Неделя природы", "🌿", "#1f9d55", "#8bc34a", "leaves", ["Какие бывают облака", "природа"]],
    ["art", "Неделя искусства", "🎨", "#e84c88", "#f5b800", "", ["Расскажи о картине «Мона Лиза»", "искусство"]],
    ["history", "Неделя истории", "🏛", "#b07a2e", "#c9a227", "", ["Почему произошла Первая мировая война", "история"]],
    ["music", "Неделя музыки", "🎵", "#8b5cff", "#ff3d81", "notes", ["Кто такой Моцарт", "музыка"]],
    ["tech", "Неделя технологий", "💻", "#1e5bff", "#14b8a6", "", ["Как работает компьютер", "технологии"]],
    ["cinema", "Неделя кино", "🎬", "#d4356b", "#6a5cff", "", ["Что за фильм «Интерстеллар»", "кино"]],
    ["books", "Неделя книг", "📚", "#b5553a", "#c9a227", "", ["Расскажи про роман «Война и мир»", "книги"]],
    ["sport", "Неделя спорта", "⚽", "#1f9d55", "#f5b800", "", ["Расскажи об истории Олимпийских игр", "спорт"]],
    ["travel", "Неделя путешествий", "✈️", "#0ea5b7", "#f5b800", "", ["Расскажи про Эйфелеву башню", "путешествия"]],
    ["health", "Неделя здоровья", "💪", "#16a34a", "#2aa7e8", "", ["Как вода влияет на организм", "здоровье"]],
  ];
  // Сдвиг подобран так, чтобы сейчас (неделя 41) была неделя космоса.
  const WEEK_OFFSET = 7;
  const OFF_KEY = "rai_festive_off";

  function isoWeek(d) {
    const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const day = t.getUTCDay() || 7;
    t.setUTCDate(t.getUTCDate() + 4 - day);
    const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
    return Math.ceil(((t - yearStart) / 86400000 + 1) / 7);
  }

  function inRange(d, from, to) {
    const md = (d.getMonth() + 1) * 100 + d.getDate(), a = from[0] * 100 + from[1], b = to[0] * 100 + to[1];
    return a <= b ? md >= a && md <= b : md >= a || md <= b;   // Новый год переходит через декабрь—январь
  }

  /** Тема на дату (по умолчанию сегодня): {id, kind, name, emoji, accent, grad, decor, hello, example} или null. */
  function current(date) {
    const d = date || new Date();
    for (const h of HOLIDAYS) {
      if (inRange(d, h[7], h[8])) {
        return {id: h[0], kind: "holiday", name: h[1], emoji: h[2], accent: h[3], grad2: h[4], decor: h[5], hello: h[6]};
      }
    }
    const w = WEEKS[(isoWeek(d) + WEEK_OFFSET) % WEEKS.length];
    return {id: w[0], kind: "week", name: w[1], emoji: w[2], accent: w[3], grad2: w[4], decor: w[5], example: w[6]};
  }

  function off() {
    try { return localStorage.getItem(OFF_KEY) === "1"; } catch (e) { return false; }
  }
  function setOff(v) {
    try { localStorage.setItem(OFF_KEY, v ? "1" : "0"); } catch (e) { /* не сохранится — не страшно */ }
    if (v) { clearDecor(); unapply(); } else { apply(); decorate(); }
  }

  const SAVED = {};
  const VARS = ["--red", "--red-hi", "--pink", "--grad", "--red-soft", "--glow"];
  function apply(theme) {
    theme = theme || current();
    const root = document.documentElement, st = root.style;
    if (!Object.keys(SAVED).length) for (const v of VARS) SAVED[v] = st.getPropertyValue(v);
    const a = theme.accent, b = theme.grad2 || theme.accent;
    st.setProperty("--red", a);
    st.setProperty("--red-hi", b);
    st.setProperty("--pink", b);
    st.setProperty("--grad", `linear-gradient(120deg, ${a} 0%, ${b} 100%)`);
    st.setProperty("--red-soft", hexA(a, 0.12));
    st.setProperty("--glow", `0 10px 30px -10px ${hexA(a, 0.7)}`);
    root.dataset.festive = theme.id;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta && !meta.dataset.festiveSaved) { meta.dataset.festiveSaved = meta.content; }
    return theme;
  }
  function unapply() {
    const st = document.documentElement.style;
    for (const v of VARS) { if (SAVED[v] !== undefined) st.setProperty(v, SAVED[v]); }
    delete document.documentElement.dataset.festive;
  }
  function hexA(hex, a) {
    const m = /^#([0-9a-f]{6})$/i.exec(hex);
    if (!m) return hex;
    const n = parseInt(m[1], 16);
    return `rgba(${n >> 16 & 255}, ${n >> 8 & 255}, ${n & 255}, ${a})`;
  }

  // ---- лёгкое оформление: падающие эмодзи (снег, звёзды, листья…). Выключено на телефоне и при reduced-motion.
  const DECOR = {snow: "❄", petals: "🌸", stars: "✦", leaves: "🍂", bats: "🦇", notes: "♪"};
  let layer = null;
  function clearDecor() { if (layer) { layer.remove(); layer = null; } }
  function decorate(theme) {
    clearDecor();
    theme = theme || current();
    if (off() || !theme.decor || !DECOR[theme.decor]) return;
    const phone = Math.min(screen.width || 0, screen.height || 0) < 600;
    const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (phone || reduce) return;
    layer = document.createElement("div");
    layer.className = "festive-decor";
    layer.setAttribute("aria-hidden", "true");
    const glyph = DECOR[theme.decor], star = theme.decor === "stars";
    for (let i = 0; i < 14; i++) {
      const s = document.createElement("span");
      s.textContent = glyph;
      const dur = 7 + Math.random() * 8, delay = -Math.random() * dur, size = 10 + Math.random() * 14;
      s.style.cssText = `left:${Math.random() * 100}%;font-size:${size}px;animation-duration:${dur}s;animation-delay:${delay}s;` +
        (star ? `opacity:.5;animation-name:festive-twinkle;top:${Math.random() * 100}%;` : "");
      layer.append(s);
    }
    document.body.append(layer);
    if (!document.getElementById("festive-style")) {
      const css = document.createElement("style");
      css.id = "festive-style";
      css.textContent =
        ".festive-decor{position:fixed;inset:0;pointer-events:none;z-index:1;overflow:hidden}" +
        ".festive-decor span{position:absolute;top:-6%;will-change:transform,opacity;animation:festive-fall linear infinite}" +
        "@keyframes festive-fall{0%{transform:translateY(-10vh) rotate(0);opacity:0}10%{opacity:.8}" +
        "100%{transform:translateY(110vh) rotate(260deg);opacity:.2}}" +
        "@keyframes festive-twinkle{0%,100%{opacity:.15}50%{opacity:.7}}";
      document.head.append(css);
    }
  }

  function init() {
    if (off()) return null;
    const theme = current();
    apply(theme);
    if (document.body) decorate(theme);
    else document.addEventListener("DOMContentLoaded", () => decorate(theme), {once: true});
    return theme;
  }

  window.RaiFestive = {current: current, apply: apply, decorate: decorate, init: init, off: off, setOff: setOff,
                       HOLIDAYS: HOLIDAYS, WEEKS: WEEKS};
  init();   // применяем акцент сразу (до отрисовки страницы — без мигания)
})();
