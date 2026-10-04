<?php /* Стили AI Studio. Подключается в страницы через include. */ ?>
<style>
/* AI Studio Rteam — в одном стиле с главной rai.rteam.info: тёмный фон со светящимися пятнами и сеткой,
   градиент красный → розовый → фиолетовый, стеклянные карточки, круглые кнопки */
:root {
  --bg: #07070b; --bg2: #0d0d14; --card: rgba(255,255,255,.035); --card2: rgba(255,255,255,.06);
  --line: rgba(255,255,255,.09); --line2: rgba(255,255,255,.16);
  --fg: #f5f5f7; --muted: #a1a1b0; --dim: #6f6f80;
  --red: #ff2d2d; --pink: #ff3d81; --violet: #8b5cff; --ok: #3ddc97;
  --grad: linear-gradient(120deg, #ff2d2d 0%, #ff3d81 45%, #8b5cff 100%);
  --radius: 22px; --ease: cubic-bezier(.2,.8,.2,1);
  --display: "Unbounded", "Arial Black", system-ui, sans-serif;
  --body: "Onest", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
  color-scheme: dark;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html, body { margin: 0; }
body { background: var(--bg); color: var(--fg); font: 15.5px/1.6 var(--body); min-height: 100vh; overflow-x: hidden; -webkit-font-smoothing: antialiased; }
/* фон: светящиеся пятна и сетка, как на главной */
body::before { content: ""; position: fixed; inset: -20%; z-index: -2; pointer-events: none;
  background: radial-gradient(520px circle at 8% 4%, rgba(255,45,45,.30), transparent 60%),
              radial-gradient(520px circle at 96% 18%, rgba(139,92,255,.26), transparent 60%),
              radial-gradient(460px circle at 40% 104%, rgba(255,61,129,.18), transparent 60%);
  filter: blur(20px); animation: drift 24s ease-in-out infinite alternate; }
body::after { content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none; opacity: .5;
  background-image: linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 64px 64px;
  -webkit-mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 75%); mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 75%); }
@keyframes drift { to { transform: translate(40px, 30px) scale(1.06); } }
a { color: var(--pink); text-decoration: none; }
a:hover { text-decoration: underline; }
:focus-visible { outline: 2px solid var(--pink); outline-offset: 3px; border-radius: 8px; }
button, input, textarea { font: inherit; color: inherit; }
.grad-text { background: var(--grad); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent; animation: shine 6s linear infinite; }
@keyframes shine { to { background-position: 200% center; } }

/* шапка */
.topbar { position: sticky; top: 0; z-index: 50; display: flex; align-items: center; gap: 16px; padding: 14px max(16px, calc((100% - 1180px) / 2)); flex-wrap: wrap;
  background: rgba(7,7,11,.72); backdrop-filter: blur(18px) saturate(1.4); -webkit-backdrop-filter: blur(18px) saturate(1.4); border-bottom: 1px solid var(--line); }
.studio-page .topbar { padding-inline: 20px; }
.brand { display: flex; align-items: center; gap: 10px; font: 800 20px/1 var(--display); color: var(--fg); letter-spacing: -.02em; }
.brand:hover { text-decoration: none; }
.brand i { width: 34px; height: 34px; border-radius: 10px; background: var(--grad); display: grid; place-items: center; font-style: normal; font-size: 16px; color: #fff; box-shadow: 0 6px 24px rgba(255,45,45,.45); }
.brand span { background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
.topbar nav { display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; align-items: center; }
.topbar nav > a { padding: 8px 14px; border-radius: 999px; color: var(--muted); font-weight: 500; transition: color .2s, background .2s; }
.topbar nav > a:hover { color: var(--fg); background: var(--card2); text-decoration: none; }
.me { display: flex; align-items: center; gap: 8px; padding: 4px 12px 4px 4px; border-radius: 999px; background: var(--card); border: 1px solid var(--line); font-weight: 600; font-size: 14px; color: var(--fg); }
.ava { width: 30px; height: 30px; border-radius: 50%; background: var(--grad); color: #fff; display: grid; place-items: center; font-weight: 700; overflow: hidden; }
.ava img { width: 100%; height: 100%; object-fit: cover; }

/* кнопки: главная — градиентная, остальные — стеклянные */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 22px; border-radius: 999px; border: 0;
  background: var(--grad); background-size: 160% auto; color: #fff; font: 600 15px/1 var(--body); cursor: pointer; white-space: nowrap;
  box-shadow: 0 10px 34px -10px rgba(255,45,45,.65); transition: transform .25s var(--ease), background-position .25s, box-shadow .25s; }
.btn:hover { transform: translateY(-2px); background-position: right center; box-shadow: 0 16px 44px -10px rgba(255,61,129,.75); text-decoration: none; }
.btn.ghost { background: var(--card); color: var(--fg); border: 1px solid var(--line2); box-shadow: none; }
.btn.ghost:hover { background: var(--card2); border-color: rgba(255,255,255,.28); }
.btn.small { padding: 8px 14px; font-size: 13px; }
.btn:disabled { opacity: .55; cursor: progress; transform: none; }
.google { background: #fff; color: #1f1f1f; box-shadow: none; }
.google:hover { background: #eee; }

/* карточки и поля */
.panel { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 22px; display: flex; flex-direction: column; gap: 14px; min-width: 0;
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); transition: border-color .3s; }
.panel:hover { border-color: var(--line2); }
.panel h2 { margin: 0; font: 700 18px/1.3 var(--display); letter-spacing: -.02em; }
.muted { color: var(--muted); }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--muted); }
.field input, textarea, .input { padding: 12px 14px; border-radius: 14px; border: 1px solid var(--line2); background: rgba(0,0,0,.35); color: var(--fg); transition: border-color .2s, box-shadow .2s; }
.field input:focus, textarea:focus, .input:focus { border-color: var(--pink); box-shadow: 0 0 0 4px rgba(255,61,129,.15); outline: none; }
textarea { resize: vertical; min-height: 100px; }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chips button { border: 1px solid var(--line); background: var(--card); border-radius: 999px; padding: 7px 13px; cursor: pointer; font-size: 13px; color: var(--muted); transition: color .2s, border-color .2s, background .2s; }
.chips button:hover { color: var(--fg); border-color: rgba(255,61,129,.55); background: rgba(255,61,129,.08); }
.error { color: #ff6b8b; margin: 0; }
.okmsg { color: var(--ok); margin: 0; }
code, .mono { font-family: var(--mono); font-size: 13px; }
pre { background: rgba(0,0,0,.45); border: 1px solid var(--line); border-radius: 14px; padding: 14px; overflow-x: auto; margin: 0; color: #cfd0dc; }
.url { font-family: var(--mono); word-break: break-all; }
details summary { cursor: pointer; color: var(--muted); }
details summary:hover { color: var(--fg); }

/* главная студии */
.landing { width: min(1180px, 100% - 32px); margin: 0 auto; padding: 72px 0 56px; display: grid; grid-template-columns: 1.1fr .9fr; gap: 56px; align-items: center; }
.badge { display: inline-flex; align-items: center; gap: 10px; padding: 7px 14px 7px 8px; border-radius: 999px; background: var(--card); border: 1px solid var(--line); font-size: 14px; color: var(--muted); }
.badge b { padding: 3px 9px; border-radius: 999px; background: var(--grad); color: #fff; font-size: 12px; letter-spacing: .02em; }
.landing h1 { font: 800 clamp(36px, 5.4vw, 64px)/1.04 var(--display); margin: 22px 0 18px; letter-spacing: -.035em; }
.landing .lead { font-size: clamp(16px, 1.6vw, 19px); color: var(--muted); max-width: 56ch; margin: 0; }
.steps { list-style: none; padding: 0; margin: 28px 0 0; display: grid; gap: 10px; counter-reset: s; }
.steps li { counter-increment: s; display: flex; gap: 14px; align-items: flex-start; padding: 14px 16px; border-radius: 16px; background: var(--card); border: 1px solid var(--line); }
.steps li::before { content: counter(s, decimal-leading-zero); font: 800 15px/1.5 var(--display); background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; flex: none; }
/* карточка входа — со светящейся рамкой, как живой чат на главной */
.sso { position: relative; border: 0; padding: 26px; background: rgba(13,13,20,.9); box-shadow: 0 40px 120px -30px rgba(255,45,45,.45); }
.sso::before { content: ""; position: absolute; inset: -1px; z-index: -1; border-radius: calc(var(--radius) + 1px); padding: 1px;
  background: conic-gradient(from var(--a, 0deg), rgba(255,45,45,.9), rgba(139,92,255,.6), rgba(255,61,129,.9), rgba(255,255,255,.08) 70%, rgba(255,45,45,.9));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
  animation: spin 8s linear infinite; }
@property --a { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
@keyframes spin { to { --a: 360deg; } }
.sso .btn { width: 100%; padding: 15px 22px; }
.tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; background: rgba(0,0,0,.35); padding: 4px; border-radius: 999px; }
.tabs a { text-align: center; padding: 9px; border-radius: 999px; color: var(--muted); font-weight: 600; }
.tabs a.on { background: var(--grad); color: #fff; }
.or { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 12px; }
.or::before, .or::after { content: ""; flex: 1; border-top: 1px solid var(--line); }

/* студия */
.studio { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, .9fr); gap: 18px; padding: 20px; }
.work { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.preview { width: 100%; height: 560px; border: 1px solid var(--line2); border-radius: 16px; background: #fff; }
.log { display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto; }
.log p { margin: 0; padding: 10px 14px; border-radius: 16px; background: var(--card2); border: 1px solid var(--line); border-bottom-left-radius: 6px; align-self: flex-start; max-width: 92%; }
.log p.me { background: var(--grad); color: #fff; border: 0; align-self: flex-end; border-bottom-left-radius: 16px; border-bottom-right-radius: 6px; }
.chat { position: sticky; top: 84px; height: calc(100vh - 104px); min-height: 520px; padding: 0; overflow: hidden; gap: 0; }
.chat .head { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid var(--line); }
.chat iframe { width: 100%; height: 100%; border: 0; flex: 1; background: var(--bg); }
.table-scroll { overflow-x: auto; }
table.keys { width: 100%; border-collapse: collapse; font-size: 13px; }
table.keys th, table.keys td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); }
table.keys th { color: var(--pink); font-weight: 600; }
.newkey { border: 1px solid rgba(255,61,129,.5); background: rgba(255,61,129,.08); border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
.status-pill { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; color: var(--muted); padding: 5px 12px; border-radius: 999px; background: var(--card); border: 1px solid var(--line); }
.status-pill::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--dim); }
.status-pill.on { color: var(--fg); }
.status-pill.on::before { background: var(--ok); box-shadow: 0 0 12px var(--ok); }
footer.foot { padding: 22px max(16px, calc((100% - 1180px) / 2)); color: var(--dim); font-size: 13px; border-top: 1px solid var(--line); display: flex; gap: 18px; flex-wrap: wrap; }
footer.foot a { color: var(--muted); }

.fade { opacity: 0; transform: translateY(18px); animation: fadeup .9s var(--ease) forwards; }
.d1 { animation-delay: .15s; } .d2 { animation-delay: .3s; } .d3 { animation-delay: .45s; }
@keyframes fadeup { to { opacity: 1; transform: none; } }

@media (max-width: 900px) {
  .landing, .studio { grid-template-columns: minmax(0, 1fr); }
  .landing { padding-top: 40px; gap: 32px; }
  .studio { padding: 14px; }
  .chat { position: static; height: 640px; }
  .preview { height: 460px; }
  .topbar { gap: 10px; }
  .topbar nav { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; margin: 0 -16px; padding: 0 16px 2px; width: calc(100% + 32px); }
  .topbar nav::-webkit-scrollbar { display: none; }
  .topbar nav > * { flex: none; }
  .topbar nav > a { padding: 6px 10px; }
  .studio-page .topbar nav { margin: 0 -20px; padding: 0 20px 2px; width: calc(100% + 40px); }
}
@media (prefers-reduced-motion: reduce) {
  body::before, .grad-text, .sso::before, .fade { animation: none; }
  .fade { opacity: 1; transform: none; }
}
</style>
