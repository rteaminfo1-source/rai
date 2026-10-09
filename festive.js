/* Праздничные и недельные темы Rai — разный дизайн под дату, включается сам.
   Праздники (Новый год, 8 Марта, День космонавтики…) важнее недельных тем; недели крутятся по номеру недели года
   (сейчас, например, «неделя космоса»). Тема меняет акцентный цвет, красивый фон под праздник, лёгкое оформление,
   тематические вопросы к Rai (в том числе «нарисуй…» — Rai рисует картинку) и праздничное приветствие.
   Всё в браузере, без сервера — работает и в приложении. Выключить: крестик на плашке (window.RaiFestive.setOff).
   Данные совпадают с festive.php на сайте. */
(function () {
  "use strict";

  // Праздники: {id,name,emoji,accent,grad2,decor,hello,[мес,день с],[мес,день по],examples:[[вопрос,подпись],…]}
  const HOLIDAYS = [
    {id: "ny", name: "С Новым годом!", emoji: "🎄", accent: "#2aa7e8", grad2: "#f5b800", decor: "snow",
     hello: "С наступающим! ❄️", from: [12, 20], to: [1, 8],
     examples: [["Когда наступит Новый год?", "🎄 сколько осталось"], ["Нарисуй зимний лес со снегом", "🎨 картинка"], ["Расскажи про планету Земля", "интересное"]]},
    {id: "defender", name: "23 Февраля", emoji: "🎖", accent: "#3a7d44", grad2: "#8bb174", decor: "",
     hello: "С Днём защитника Отечества!", from: [2, 20], to: [2, 23],
     examples: [["Почему 23 февраля — День защитника Отечества", "история"], ["Нарисуй горы на рассвете", "🎨 картинка"]]},
    {id: "march8", name: "8 Марта", emoji: "🌷", accent: "#ff4f93", grad2: "#ffa6c9", decor: "petals",
     hello: "С праздником весны! 🌷", from: [3, 5], to: [3, 8],
     examples: [["Нарисуй цветы", "🌷 картинка"], ["Расскажи про тюльпаны", "цветы"]]},
    {id: "cosmo", name: "День космонавтики", emoji: "🚀", accent: "#6a5cff", grad2: "#2aa7e8", decor: "stars",
     hello: "Поехали! 🚀", from: [4, 11], to: [4, 12],
     examples: [["Расскажи про историю космонавтики", "🚀 история"], ["Нарисуй космос", "🎨 картинка"], ["Расскажи про Юрия Гагарина", "биография"]]},
    {id: "victory", name: "9 Мая", emoji: "🎗", accent: "#c62828", grad2: "#f5b800", decor: "",
     hello: "С Днём Победы!", from: [5, 7], to: [5, 9],
     examples: [["Когда закончилась Великая Отечественная война", "история"], ["Расскажи про День Победы", "история"]]},
    {id: "russia", name: "День России", emoji: "🇷🇺", accent: "#1e5bff", grad2: "#e10600", decor: "",
     hello: "С Днём России!", from: [6, 11], to: [6, 12],
     examples: [["Расскажи про День России", "история"], ["Нарисуй закат над морем", "🎨 картинка"]]},
    {id: "knowledge", name: "1 Сентября", emoji: "📚", accent: "#1e5bff", grad2: "#2aa7e8", decor: "",
     hello: "С Днём знаний! 📚", from: [9, 1], to: [9, 1],
     examples: [["Расскажи про День знаний", "история"], ["Нарисуй лес", "🎨 картинка"]]},
    {id: "halloween", name: "Хэллоуин", emoji: "🎃", accent: "#ff7a00", grad2: "#8b5cff", decor: "bats",
     hello: "Уютного Хэллоуина! 🎃", from: [10, 29], to: [10, 31],
     examples: [["Расскажи историю Хэллоуина", "история"], ["Нарисуй ночь с луной", "🎨 картинка"]]},
  ];

  // Недельные темы: {id,name,emoji,accent,grad2,decor,examples:[[вопрос,подпись],…]}
  const WEEKS = [
    {id: "space", name: "Неделя космоса", emoji: "🚀", accent: "#6a5cff", grad2: "#2aa7e8", decor: "stars",
     examples: [["Расскажи про чёрные дыры", "🚀 тема недели"], ["Нарисуй космос", "🎨 картинка"]]},
    {id: "science", name: "Неделя науки", emoji: "🔬", accent: "#1e9d8b", grad2: "#2aa7e8", decor: "",
     examples: [["Как работает фотосинтез", "🔬 тема недели"], ["Почему небо голубое", "наука"]]},
    {id: "nature", name: "Неделя природы", emoji: "🌿", accent: "#1f9d55", grad2: "#8bc34a", decor: "leaves",
     examples: [["Какие бывают облака", "🌿 тема недели"], ["Нарисуй лес", "🎨 картинка"]]},
    {id: "art", name: "Неделя искусства", emoji: "🎨", accent: "#e84c88", grad2: "#f5b800", decor: "",
     examples: [["Расскажи о картине «Мона Лиза»", "🎨 тема недели"], ["Нарисуй абстракцию", "картинка"]]},
    {id: "history", name: "Неделя истории", emoji: "🏛", accent: "#b07a2e", grad2: "#c9a227", decor: "",
     examples: [["Почему произошла Первая мировая война", "🏛 тема недели"], ["Расскажи про Древний Рим", "история"]]},
    {id: "music", name: "Неделя музыки", emoji: "🎵", accent: "#8b5cff", grad2: "#ff3d81", decor: "notes",
     examples: [["Кто такой Моцарт", "🎵 тема недели"], ["Расскажи про историю рок-музыки", "музыка"]]},
    {id: "tech", name: "Неделя технологий", emoji: "💻", accent: "#1e5bff", grad2: "#14b8a6", decor: "",
     examples: [["Как работает компьютер", "💻 тема недели"], ["Что такое искусственный интеллект", "технологии"]]},
    {id: "cinema", name: "Неделя кино", emoji: "🎬", accent: "#d4356b", grad2: "#6a5cff", decor: "",
     examples: [["Что за фильм «Интерстеллар»", "🎬 тема недели"], ["Расскажи про Кристофера Нолана", "кино"]]},
    {id: "books", name: "Неделя книг", emoji: "📚", accent: "#b5553a", grad2: "#c9a227", decor: "",
     examples: [["Расскажи про роман «Война и мир»", "📚 тема недели"], ["Кто написал «Гарри Поттера»", "книги"]]},
    {id: "sport", name: "Неделя спорта", emoji: "⚽", accent: "#1f9d55", grad2: "#f5b800", decor: "",
     examples: [["Расскажи об истории Олимпийских игр", "⚽ тема недели"], ["Когда появился футбол", "спорт"]]},
    {id: "travel", name: "Неделя путешествий", emoji: "✈️", accent: "#0ea5b7", grad2: "#f5b800", decor: "",
     examples: [["Расскажи про Эйфелеву башню", "✈️ тема недели"], ["Нарисуй горы", "🎨 картинка"]]},
    {id: "health", name: "Неделя здоровья", emoji: "💪", accent: "#16a34a", grad2: "#2aa7e8", decor: "",
     examples: [["Как вода влияет на организм", "💪 тема недели"], ["Сколько нужно спать человеку", "здоровье"]]},
  ];
  const WEEK_OFFSET = 7;   // чтобы сейчас (неделя 41) была неделя космоса
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

  /** Тема на дату (по умолчанию сегодня): {id, kind, name, emoji, accent, grad2, decor, hello?, examples, bg}. */
  function current(date) {
    const d = date || new Date();
    let t = null, kind = "week";
    for (const h of HOLIDAYS) {
      if (inRange(d, h.from, h.to)) { t = h; kind = "holiday"; break; }
    }
    if (!t) t = WEEKS[(isoWeek(d) + WEEK_OFFSET) % WEEKS.length];
    return {id: t.id, kind: kind, name: t.name, emoji: t.emoji, accent: t.accent, grad2: t.grad2,
            decor: t.decor, hello: t.hello || "", examples: t.examples || [], bg: bgFor(t.accent, t.grad2)};
  }

  // Красивый фон под праздник: несколько мягких цветных свечений в цвет темы + лёгкая дымка поверх тёмного фона.
  function bgFor(a, b) {
    return `radial-gradient(1300px 720px at 10% -14%, ${hexA(a, 0.26)}, transparent 60%), ` +
           `radial-gradient(1100px 600px at 100% -4%, ${hexA(b, 0.20)}, transparent 58%), ` +
           `radial-gradient(820px 820px at 86% 110%, ${hexA(b, 0.14)}, transparent 62%), ` +
           `radial-gradient(900px 760px at 20% 118%, ${hexA(a, 0.12)}, transparent 62%), ` +
           `linear-gradient(180deg, ${hexA(a, 0.05)}, transparent 32%)`;
  }

  function off() {
    try { return localStorage.getItem(OFF_KEY) === "1"; } catch (e) { return false; }
  }
  function setOff(v) {
    try { localStorage.setItem(OFF_KEY, v ? "1" : "0"); } catch (e) { /* не сохранится — не страшно */ }
    if (v) { clearDecor(); clearBg(); unapply(); } else { apply(); background(); decorate(); }
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

  // ---- красивый фон под праздник: мягкое цветное свечение прямо на фоне страницы (под всем содержимым)
  let bgSaved = null;
  function clearBg() {
    if (bgSaved !== null && document.body) { document.body.style.backgroundImage = bgSaved; bgSaved = null; }
  }
  function background(theme) {
    theme = theme || current();
    if (off() || !document.body) return;
    if (bgSaved === null) bgSaved = document.body.style.backgroundImage || "";
    document.body.style.backgroundImage = theme.bg;
    document.body.style.backgroundAttachment = "fixed";
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
    const n = star ? 20 : 16;
    const glow = hexA(theme.accent, 0.8);
    for (let i = 0; i < n; i++) {
      const s = document.createElement("span");
      s.textContent = glyph;
      const dur = 7 + Math.random() * 9, delay = -Math.random() * dur, size = 10 + Math.random() * 16;
      const sway = (Math.random() * 40 - 20).toFixed(0);
      s.style.cssText = `left:${Math.random() * 100}%;font-size:${size}px;animation-duration:${dur}s;animation-delay:${delay}s;` +
        `--sway:${sway}px;` +
        (star ? `opacity:.5;animation-name:festive-twinkle;top:${Math.random() * 100}%;color:${theme.accent};text-shadow:0 0 6px ${glow};`
              : `filter:drop-shadow(0 2px 6px ${hexA(theme.accent, 0.35)});`);
      layer.append(s);
    }
    document.body.append(layer);
    if (!document.getElementById("festive-style")) {
      const css = document.createElement("style");
      css.id = "festive-style";
      css.textContent =
        ".festive-decor{position:fixed;inset:0;pointer-events:none;z-index:1;overflow:hidden}" +
        ".festive-decor span{position:absolute;top:-6%;will-change:transform,opacity;animation:festive-fall linear infinite}" +
        "@keyframes festive-fall{0%{transform:translateY(-10vh) translateX(0) rotate(0);opacity:0}" +
        "10%{opacity:.85}50%{transform:translateY(55vh) translateX(var(--sway,0)) rotate(140deg)}" +
        "100%{transform:translateY(112vh) translateX(0) rotate(300deg);opacity:.15}}" +
        "@keyframes festive-twinkle{0%,100%{opacity:.12;transform:scale(.85)}50%{opacity:.85;transform:scale(1.15)}}";
      document.head.append(css);
    }
  }

  function init() {
    if (off()) return null;
    const theme = current();
    apply(theme);
    const paint = () => { background(theme); decorate(theme); };
    if (document.body) paint();
    else document.addEventListener("DOMContentLoaded", paint, {once: true});
    return theme;
  }

  window.RaiFestive = {current: current, apply: apply, decorate: decorate, background: background, init: init,
                       off: off, setOff: setOff, HOLIDAYS: HOLIDAYS, WEEKS: WEEKS};
  init();   // применяем акцент сразу (до отрисовки страницы — без мигания)
})();
