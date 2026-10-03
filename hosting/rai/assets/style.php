<?php /* Стили страниц входа и кабинета Rai (чёрно-красные). Подключается в страницы через include. */ ?>
<style>
/* Rteam — чёрно-красный стиль, как у Rai и AI Studio */
:root {
  --bg: #0b0b0c; --panel: #141416; --panel-2: #1c1c1f; --line: #2a2a2e; --fg: #f3f1f1; --muted: #9b9599;
  --red: #e10600; --red-hi: #ff2a2a; --red-soft: #2b0b0b; --ink: #fff; --ok: #3ccf7a; --gold: #f0b23c;
  --display: "Unbounded", "Arial Black", system-ui, sans-serif;
  --body: "Onest", "Segoe UI", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
  color-scheme: dark;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html, body { margin: 0; }
body { background: var(--bg); color: var(--fg); font: 16px/1.55 var(--body); min-height: 100vh; display: flex; flex-direction: column; }
main { flex: 1; width: 100%; max-width: 1120px; margin: 0 auto; padding: 32px 20px 48px; display: flex; flex-direction: column; gap: 28px; }
a { color: var(--red-hi); }
:focus-visible { outline: 2px solid var(--red-hi); outline-offset: 2px; }
button, input { font: inherit; color: inherit; }
h1, h2 { font-family: var(--display); letter-spacing: -.01em; margin: 0; }
.muted { color: var(--muted); margin: 0; }
.small { font-size: 14px; }
.row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }

/* шапка */
.topbar { display: flex; align-items: center; gap: 16px; padding: 12px 20px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }
.brand { font: 800 21px/1 var(--display); color: var(--red); text-decoration: none; }
.brand span { color: var(--fg); }
.topbar nav { display: flex; gap: 16px; flex-wrap: wrap; margin-left: auto; align-items: center; }
.topbar nav a { color: var(--fg); text-decoration: none; font-weight: 500; }
.topbar nav a:not(.btn):hover { color: var(--red-hi); }
.me { display: inline-flex; align-items: center; gap: 8px; }
.ava { width: 32px; height: 32px; border-radius: 50%; background: var(--red); color: var(--ink); display: inline-grid; place-items: center; font-weight: 700; overflow: hidden; flex: none; }
.ava img { width: 100%; height: 100%; object-fit: cover; }
.ava.big { width: 64px; height: 64px; font-size: 26px; }

/* кнопки */
.btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 18px; border-radius: 10px;
  border: 1px solid var(--red); background: var(--red); color: var(--ink) !important; font-weight: 600; cursor: pointer; text-decoration: none; }
.btn:hover { background: var(--red-hi); }
.btn.big { padding: 14px 24px; font-size: 17px; }
.btn.small { padding: 7px 14px; font-size: 14px; }
.btn.ghost { background: transparent; color: var(--fg) !important; border-color: var(--line); }
.btn.ghost:hover { border-color: var(--red); background: var(--red-soft); }
.btn.google { background: #fff; color: #1f1f1f !important; border-color: #fff; }
.btn.google:hover { background: #ececec; }
.btn.danger { background: transparent; border-color: var(--red); color: var(--red-hi) !important; }
.btn.danger:hover { background: var(--red); color: var(--ink) !important; }

/* главная */
.hero { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, .85fr); gap: 40px; align-items: center; padding-top: 24px; }
.kicker { font: 500 12px/1 var(--mono); color: var(--red-hi); letter-spacing: .14em; text-transform: uppercase; margin: 0 0 14px; }
.hero h1 { font-size: clamp(34px, 5.4vw, 60px); line-height: 1.03; letter-spacing: -.025em; margin-bottom: 18px; text-wrap: balance; }
.hero h1 span { color: var(--red); }
.lead { font-size: 18px; color: var(--muted); max-width: 56ch; margin: 0 0 24px; }
.hero .muted { margin-top: 14px; }
.hero-art { display: flex; flex-direction: column; gap: 10px; padding: 22px; border-radius: 20px; border: 1px solid var(--line);
  background: radial-gradient(120% 90% at 100% 0%, rgba(225, 6, 0, .22), transparent 60%), var(--panel); }
.bubble { padding: 10px 14px; border-radius: 14px; font-size: 14.5px; max-width: 88%; }
.bubble.q { align-self: flex-end; background: var(--red-soft); border: 1px solid #4a1111; }
.bubble.a { background: var(--panel-2); border: 1px solid var(--line); }
.bubble.code { font: 13px/1.5 var(--mono); color: #9fe29a; }
.bubble.code span { color: #fff; background: #15803d; border-radius: 6px; padding: 2px 8px; margin-left: 6px; font-family: var(--body); }

.cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.card { display: flex; flex-direction: column; gap: 10px; padding: 22px; border-radius: 16px; border: 1px solid var(--line); background: var(--panel);
  color: var(--fg); text-decoration: none; transition: border-color .15s, transform .15s; }
.card:hover { border-color: var(--red); transform: translateY(-2px); }
.card h2 { font-size: 22px; }
.card p { margin: 0; color: var(--muted); font-size: 15px; flex: 1; }
.card .tag { align-self: flex-start; font: 500 11px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--red-hi);
  border: 1px solid #4a1111; background: var(--red-soft); padding: 5px 8px; border-radius: 6px; }
.card .go { font-weight: 600; color: var(--red-hi); }

.models h2 { font-size: 22px; margin-bottom: 14px; }
.table-scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 15px; }
th { text-align: left; color: var(--red-hi); background: var(--panel-2); border-bottom: 2px solid var(--red); font-weight: 600; }
th, td { padding: 10px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
tr:last-child td { border-bottom: 0; }
td:first-child { white-space: nowrap; font-weight: 600; }
tr.top td { background: linear-gradient(90deg, rgba(225, 6, 0, .14), transparent); }
tr.top td:first-child { color: var(--gold); }

/* формы */
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 22px; display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.panel h2 { font-size: 17px; }
.auth { align-items: center; justify-content: center; }
.auth .panel { width: min(440px, 100%); }
.auth h1 { font-size: 24px; }
.tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; background: var(--bg); padding: 4px; border-radius: 10px; }
.tabs a { text-align: center; padding: 9px; border-radius: 8px; color: var(--muted); text-decoration: none; font-weight: 600; }
.tabs a[aria-selected="true"] { background: var(--red); color: var(--ink); }
.or { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 13px; }
.or::before, .or::after { content: ""; flex: 1; border-top: 1px solid var(--line); }
.form { display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 5px; font-size: 13.5px; color: var(--muted); }
.field small { font-size: 12px; }
.field input { padding: 11px 12px; border-radius: 10px; border: 1px solid var(--line); background: var(--bg); color: var(--fg); font-size: 15px; }
.field input:focus { border-color: var(--red); outline: none; }
.error { color: var(--red-hi); margin: 0; }
.okmsg { color: var(--ok); margin: 0; }

/* кабинет */
.profile-head { flex-direction: row; align-items: center; gap: 16px; flex-wrap: wrap; }
.profile-head h1 { font-size: 24px; }
.profile-head > div { flex: 1; min-width: 200px; }
.logout { margin: 0; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.panel.danger { border-color: #4a1111; }

/* подписка в кабинете и оплата */
.plan-box { flex-direction: row; align-items: center; gap: 18px; flex-wrap: wrap;
  background: radial-gradient(120% 140% at 100% 0%, rgba(225, 6, 0, .18), transparent 60%), var(--panel); }
.plan-box > div { flex: 1; min-width: 220px; }
.plan-box h2 { font-size: 20px; }
.meter { height: 8px; border-radius: 99px; background: var(--bg); overflow: hidden; margin-top: 10px; }
.meter i { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--red), #ff3d81); }
.pay .panel { width: min(520px, 100%); }
.pay .tag { align-self: flex-start; font: 500 11px/1 var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--red-hi);
  border: 1px solid #4a1111; background: var(--red-soft); padding: 5px 8px; border-radius: 6px; }
.pay h1 { font-size: 28px; }
.checks { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.checks li { padding-left: 28px; position: relative; }
.checks li::before { content: "✓"; position: absolute; left: 0; top: 0; width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center;
  background: rgba(60, 207, 122, .15); color: var(--ok); font-size: 12px; font-weight: 700; }
.periods { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.periods a { display: flex; flex-direction: column; gap: 2px; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--line); text-decoration: none; color: var(--fg); background: var(--bg); }
.periods a span { color: var(--muted); font-size: 14px; }
.periods a[aria-checked="true"] { border-color: var(--red); background: var(--red-soft); }
.result { align-items: center; text-align: center; }
.result-icon { width: 84px; height: 84px; border-radius: 50%; display: grid; place-items: center; font: 800 40px/1 var(--display); color: #fff;
  background: var(--red); animation: popin .6s cubic-bezier(.2, 1.4, .4, 1) both; }
.result.ok .result-icon { background: var(--ok); box-shadow: 0 0 0 0 rgba(60, 207, 122, .5); animation: popin .6s cubic-bezier(.2, 1.4, .4, 1) both, ring 2s 0.6s infinite; }
.result.wait .result-icon { background: var(--panel-2); border: 2px solid var(--line); animation: spinwait 1.2s linear infinite; }
@keyframes popin { from { transform: scale(.3); opacity: 0; } }
@keyframes ring { 70% { box-shadow: 0 0 0 22px rgba(60, 207, 122, 0); } }
@keyframes spinwait { to { transform: rotate(360deg); } }

.foot { display: flex; gap: 18px; flex-wrap: wrap; padding: 18px 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 14px; }
.foot a { color: var(--muted); }

@media (max-width: 860px) {
  .hero, .cards, .grid2 { grid-template-columns: minmax(0, 1fr); }
  .hero { gap: 24px; padding-top: 0; }
  .topbar nav { gap: 12px; margin-left: 0; width: 100%; }
  main { padding: 20px 16px 36px; }
}
@media (prefers-reduced-motion: reduce) { .card { transition: none; } .card:hover { transform: none; } }
</style>
