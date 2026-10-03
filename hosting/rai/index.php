<?php
/*
 * Главная rai.rteam.info: что умеет Rai, тарифы и оплата. Сам Rai (чат, Code, Слайды) — chat.html.
 */
require __DIR__ . '/config.php';
require __DIR__ . '/plans.php';

$user = current_user();
$mine = $user ? user_plan($user) : ['key' => 'free', 'until' => 0];
$plans = plans();
$free = $plans['free'];
$pricing = [];
foreach ($plans as $key => $p) {
    $pricing[$key] = ['month' => plan_price($key, 1), 'year' => plan_price($key, 12), 'year_month' => (int)round(plan_price($key, 12) / 12)];
}
?><!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rai — свой ИИ-помощник</title>
<meta name="description" content="Rai — ИИ-помощник команды Rteam: нейросеть прямо в браузере, код на 17 языках, презентации, погода, перевод и анализ соцсетей. Бесплатно и по подписке.">
<meta name="theme-color" content="#07070b">
<meta property="og:title" content="Rai — свой ИИ-помощник">
<meta property="og:description" content="Нейросеть в браузере, код, презентации, перевод и анализ соцсетей. Начните бесплатно.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23e10600'/%3E%3Ctext x='16' y='23' font-size='19' font-family='Arial' font-weight='900' text-anchor='middle' fill='white'%3ER%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;700;800&family=Onest:wght@400;500;600;700&display=swap">
<style>
:root {
  --bg: #07070b; --bg2: #0d0d14; --card: rgba(255,255,255,.035); --card2: rgba(255,255,255,.06);
  --line: rgba(255,255,255,.09); --line2: rgba(255,255,255,.16);
  --text: #f5f5f7; --muted: #a1a1b0; --dim: #6f6f80;
  --red: #ff2d2d; --red2: #e10600; --pink: #ff3d81; --orange: #ff8a3d; --violet: #8b5cff; --green: #3ddc97;
  --grad: linear-gradient(120deg, #ff2d2d 0%, #ff3d81 45%, #8b5cff 100%);
  --radius: 22px; --ease: cubic-bezier(.2,.8,.2,1);
  --head: "Unbounded", system-ui, sans-serif; --body: "Onest", system-ui, -apple-system, "Segoe UI", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--bg); color: var(--text); font: 16px/1.6 var(--body); overflow-x: hidden; -webkit-font-smoothing: antialiased; }
a { color: inherit; text-decoration: none; }
img, svg { display: block; }
:focus-visible { outline: 2px solid var(--pink); outline-offset: 3px; border-radius: 8px; }
.wrap { width: min(1180px, 100% - 32px); margin-inline: auto; }
.grad-text { background: var(--grad); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent; animation: shine 6s linear infinite; }
@keyframes shine { to { background-position: 200% center; } }

/* ---------- фон: светящиеся пятна и сетка */
.bg { position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }
.orb { position: absolute; border-radius: 50%; filter: blur(90px); opacity: .5; will-change: transform; }
.orb.a { width: 560px; height: 560px; background: #ff2d2d; top: -180px; left: -160px; animation: float1 18s ease-in-out infinite; opacity: .28; }
.orb.b { width: 520px; height: 520px; background: #8b5cff; top: 10%; right: -200px; animation: float2 22s ease-in-out infinite; opacity: .26; }
.orb.c { width: 420px; height: 420px; background: #ff3d81; bottom: -160px; left: 30%; animation: float3 26s ease-in-out infinite; opacity: .18; }
@keyframes float1 { 50% { transform: translate(120px, 80px) scale(1.1); } }
@keyframes float2 { 50% { transform: translate(-140px, 120px) scale(.9); } }
@keyframes float3 { 50% { transform: translate(100px, -120px) scale(1.15); } }
.grid { position: absolute; inset: 0; background-image: linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size: 64px 64px; mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 75%); -webkit-mask-image: radial-gradient(ellipse 70% 55% at 50% 0%, #000 30%, transparent 75%); opacity: .5; }

/* ---------- шапка */
.nav { position: sticky; top: 0; z-index: 50; transition: background .3s, border-color .3s, backdrop-filter .3s; border-bottom: 1px solid transparent; }
.nav.scrolled { background: rgba(7,7,11,.72); backdrop-filter: blur(18px) saturate(1.4); -webkit-backdrop-filter: blur(18px) saturate(1.4); border-color: var(--line); }
.nav .wrap { display: flex; align-items: center; gap: 24px; height: 72px; }
.logo { display: flex; align-items: center; gap: 10px; font: 800 22px/1 var(--head); letter-spacing: -.02em; }
.logo i { width: 34px; height: 34px; border-radius: 10px; background: var(--grad); display: grid; place-items: center; font-style: normal; font-size: 18px; color: #fff; box-shadow: 0 6px 24px rgba(255,45,45,.45); }
.links { display: flex; gap: 6px; margin-left: 12px; }
.links a { padding: 8px 14px; border-radius: 999px; color: var(--muted); font-weight: 500; font-size: 15px; transition: color .2s, background .2s; }
.links a:hover { color: var(--text); background: var(--card2); }
.nav .right { margin-left: auto; display: flex; gap: 10px; align-items: center; }
.me { display: flex; align-items: center; gap: 8px; padding: 4px 12px 4px 4px; border-radius: 999px; background: var(--card); border: 1px solid var(--line); font-weight: 600; font-size: 14px; }
.me .ava { width: 30px; height: 30px; border-radius: 50%; background: var(--grad); display: grid; place-items: center; overflow: hidden; font-weight: 700; }
.me .ava img { width: 100%; height: 100%; object-fit: cover; }
.me small { color: var(--muted); font-weight: 500; }

/* ---------- кнопки */
.btn { position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 22px; border-radius: 999px; font: 600 15px/1 var(--body);
  border: 1px solid var(--line2); background: var(--card); color: var(--text); cursor: pointer; transition: transform .25s var(--ease), background .25s, border-color .25s, box-shadow .25s; white-space: nowrap; }
.btn:hover { transform: translateY(-2px); background: var(--card2); border-color: rgba(255,255,255,.28); }
.btn.primary { border: 0; background: var(--grad); background-size: 160% auto; color: #fff; box-shadow: 0 10px 34px -8px rgba(255,45,45,.65); }
.btn.primary:hover { background-position: right center; box-shadow: 0 16px 44px -8px rgba(255,61,129,.75); }
.btn.big { padding: 17px 30px; font-size: 16px; }
.btn .arrow { transition: transform .25s var(--ease); }
.btn:hover .arrow { transform: translateX(4px); }

/* ---------- первый экран */
.hero { padding: 72px 0 40px; }
.hero .wrap { display: grid; grid-template-columns: 1.05fr .95fr; gap: 56px; align-items: center; }
.badge { display: inline-flex; align-items: center; gap: 10px; padding: 7px 14px 7px 8px; border-radius: 999px; background: var(--card); border: 1px solid var(--line); font-size: 14px; color: var(--muted); }
.badge b { padding: 3px 9px; border-radius: 999px; background: var(--grad); color: #fff; font-size: 12px; letter-spacing: .02em; }
h1 { font: 800 clamp(38px, 5.6vw, 68px)/1.04 var(--head); letter-spacing: -.035em; margin: 22px 0 20px; }
h1 .line { display: block; overflow: hidden; }
h1 .line span { display: inline-block; transform: translateY(105%); animation: rise .9s var(--ease) forwards; }
h1 .line:nth-child(2) span { animation-delay: .12s; } h1 .line:nth-child(3) span { animation-delay: .24s; }
@keyframes rise { to { transform: none; } }
.lead { font-size: clamp(17px, 1.6vw, 19px); color: var(--muted); max-width: 560px; margin: 0 0 30px; }
.cta { display: flex; gap: 12px; flex-wrap: wrap; }
.trust { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 26px; color: var(--dim); font-size: 14px; }
.trust span { display: inline-flex; align-items: center; gap: 7px; }
.trust span::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 12px var(--green); }
.fade { opacity: 0; transform: translateY(18px); animation: fadeup .9s var(--ease) forwards; }
.d1 { animation-delay: .35s; } .d2 { animation-delay: .5s; } .d3 { animation-delay: .65s; } .d4 { animation-delay: .8s; }
@keyframes fadeup { to { opacity: 1; transform: none; } }

/* ---------- живой чат на первом экране */
.demo { position: relative; perspective: 1200px; }
.demo-card { position: relative; border-radius: 26px; padding: 1px; background: conic-gradient(from var(--a, 0deg), rgba(255,45,45,.9), rgba(139,92,255,.6), rgba(255,61,129,.9), rgba(255,255,255,.08) 70%, rgba(255,45,45,.9));
  animation: spin 8s linear infinite; transform-style: preserve-3d; transition: transform .4s var(--ease); box-shadow: 0 40px 120px -30px rgba(255,45,45,.45); }
@property --a { syntax: "<angle>"; initial-value: 0deg; inherits: false; }
@keyframes spin { to { --a: 360deg; } }
.demo-in { border-radius: 25px; background: rgba(13,13,20,.94); padding: 18px; min-height: 420px; display: flex; flex-direction: column; }
.demo-top { display: flex; align-items: center; gap: 8px; padding-bottom: 14px; border-bottom: 1px solid var(--line); margin-bottom: 16px; }
.dot { width: 11px; height: 11px; border-radius: 50%; background: #ff5f57; } .dot:nth-child(2) { background: #febc2e; } .dot:nth-child(3) { background: #28c840; }
.demo-top b { margin-left: 10px; font: 700 14px var(--head); } .demo-top em { margin-left: auto; font-style: normal; font-size: 12px; color: var(--green); display: flex; align-items: center; gap: 6px; }
.demo-top em::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--green); animation: pulse 1.6s infinite; }
@keyframes pulse { 50% { opacity: .3; } }
.msgs { display: flex; flex-direction: column; gap: 12px; flex: 1; }
.msg { max-width: 88%; padding: 12px 15px; border-radius: 18px; font-size: 14.5px; line-height: 1.5; animation: pop .45s var(--ease) both; white-space: pre-line; }
.msg.u { align-self: flex-end; background: var(--grad); color: #fff; border-bottom-right-radius: 6px; }
.msg.r { align-self: flex-start; background: var(--card2); border: 1px solid var(--line); border-bottom-left-radius: 6px; }
.msg.r code { font-family: ui-monospace, Menlo, monospace; font-size: 13px; color: #ffb3c7; }
.caret { display: inline-block; width: 8px; height: 16px; background: var(--pink); vertical-align: -3px; margin-left: 2px; animation: blink 1s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }
@keyframes pop { from { opacity: 0; transform: translateY(10px) scale(.97); } }
.demo-input { margin-top: 16px; display: flex; gap: 10px; align-items: center; padding: 10px 10px 10px 16px; border-radius: 16px; background: var(--card); border: 1px solid var(--line); color: var(--dim); font-size: 14px; }
.demo-input span { flex: 1; } .demo-input i { width: 34px; height: 34px; border-radius: 11px; background: var(--grad); display: grid; place-items: center; font-style: normal; color: #fff; }
.chip-float { position: absolute; padding: 10px 14px; border-radius: 14px; background: rgba(20,20,30,.85); border: 1px solid var(--line2); backdrop-filter: blur(10px); font-size: 13px; font-weight: 600; box-shadow: 0 20px 50px -20px #000; animation: bob 6s ease-in-out infinite; }
.chip-float small { display: block; color: var(--muted); font-weight: 500; }
.chip-float.one { top: -58px; right: 18px; } .chip-float.two { bottom: -30px; left: -30px; animation-delay: -3s; }
@keyframes bob { 50% { transform: translateY(-12px); } }

/* ---------- бегущая строка */
.marquee { margin: 40px 0 10px; border-block: 1px solid var(--line); padding: 18px 0; overflow: hidden; mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent); -webkit-mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent); }
.track { display: flex; gap: 46px; width: max-content; animation: scroll 40s linear infinite; }
.track span { font: 600 18px var(--head); color: var(--dim); white-space: nowrap; display: flex; align-items: center; gap: 46px; }
.track span::after { content: "✦"; color: var(--red); font-size: 14px; }
@keyframes scroll { to { transform: translateX(-50%); } }

/* ---------- разделы */
section { padding: 90px 0; }
section[id] { scroll-margin-top: 64px; }
.kicker { display: inline-block; font: 600 13px var(--body); letter-spacing: .14em; text-transform: uppercase; color: var(--pink); margin-bottom: 14px; }
h2 { font: 800 clamp(30px, 4vw, 48px)/1.1 var(--head); letter-spacing: -.03em; margin: 0 0 16px; }
.sub { color: var(--muted); font-size: 18px; max-width: 620px; margin: 0 0 48px; }
.center { text-align: center; } .center .sub { margin-inline: auto; }
.reveal { opacity: 0; transform: translateY(34px); transition: opacity .9s var(--ease), transform .9s var(--ease); transition-delay: var(--d, 0s); }
.reveal.in { opacity: 1; transform: none; }

/* ---------- цифры */
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat { padding: 28px 24px; border-radius: var(--radius); background: var(--card); border: 1px solid var(--line); }
.stat b { display: block; font: 800 clamp(34px, 4vw, 46px)/1 var(--head); letter-spacing: -.03em; margin-bottom: 8px; }
.stat span { color: var(--muted); font-size: 15px; }

/* ---------- возможности (bento) */
.bento { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
.f { --x: 50%; --y: 50%; position: relative; grid-column: span 2; padding: 28px; border-radius: var(--radius); background: var(--card); border: 1px solid var(--line); overflow: hidden; transition: transform .4s var(--ease), border-color .3s; isolation: isolate; }
.f::before { content: ""; position: absolute; inset: 0; z-index: -1; background: radial-gradient(420px circle at var(--x) var(--y), rgba(255,61,129,.16), transparent 45%); opacity: 0; transition: opacity .3s; }
.f:hover { transform: translateY(-4px); border-color: var(--line2); } .f:hover::before { opacity: 1; }
.f.wide { grid-column: span 3; } .f.tall { grid-row: span 2; display: flex; flex-direction: column; }
.f.tall .bars { margin-top: auto; height: 150px; padding-top: 24px; }
.f .ico { width: 48px; height: 48px; border-radius: 14px; display: grid; place-items: center; background: linear-gradient(140deg, rgba(255,45,45,.22), rgba(139,92,255,.22)); border: 1px solid var(--line2); margin-bottom: 18px; }
.f h3 { font: 700 20px/1.25 var(--head); letter-spacing: -.02em; margin: 0 0 8px; }
.f p { color: var(--muted); margin: 0; font-size: 15.5px; }
.f .tag { position: absolute; top: 22px; right: 22px; font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; background: rgba(61,220,151,.12); color: var(--green); border: 1px solid rgba(61,220,151,.25); }
.code { margin-top: 20px; padding: 16px; border-radius: 14px; background: rgba(0,0,0,.45); border: 1px solid var(--line); font: 13px/1.6 ui-monospace, Menlo, Consolas, monospace; color: #cfd0dc; overflow: hidden; }
.code .k { color: #ff7ab0; } .code .s { color: #9be29b; } .code .c { color: var(--dim); } .code .n { color: #ffb86b; }
.bars { display: flex; align-items: flex-end; gap: 8px; height: 96px; margin-top: 22px; }
.bars i { flex: 1; border-radius: 8px 8px 3px 3px; background: var(--grad); opacity: .85; transform-origin: bottom; transform: scaleY(0); transition: transform 1.1s var(--ease); }
.in .bars i { transform: scaleY(1); }
.slides { position: relative; height: 120px; margin-top: 22px; }
.slides div { position: absolute; inset: 0 30px 0 0; border-radius: 14px; border: 1px solid var(--line2); background: linear-gradient(140deg, #1d1b2e, #2a1420); padding: 16px; font: 700 15px var(--head); transition: transform .6s var(--ease); }
.slides div:nth-child(1) { transform: translate(24px, 14px) rotate(4deg); opacity: .5; } .slides div:nth-child(2) { transform: translate(12px, 7px) rotate(2deg); opacity: .75; }
.f:hover .slides div:nth-child(1) { transform: translate(40px, 18px) rotate(8deg); } .f:hover .slides div:nth-child(2) { transform: translate(20px, 9px) rotate(4deg); }
.slides small { display: block; font: 500 12px var(--body); color: var(--muted); margin-top: 6px; }

/* ---------- как это работает */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; counter-reset: s; position: relative; }
.step { padding: 30px 26px; border-radius: var(--radius); background: var(--card); border: 1px solid var(--line); position: relative; }
.step::before { counter-increment: s; content: "0" counter(s); font: 800 44px/1 var(--head); background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; display: block; margin-bottom: 16px; }
.step h3 { font: 700 19px var(--head); margin: 0 0 8px; } .step p { margin: 0; color: var(--muted); }

/* ---------- тарифы */
.toggle { display: inline-flex; position: relative; padding: 5px; border-radius: 999px; background: var(--card); border: 1px solid var(--line); margin-bottom: 44px; }
.toggle button { position: relative; z-index: 1; border: 0; background: none; color: var(--muted); font: 600 15px var(--body); padding: 10px 22px; border-radius: 999px; cursor: pointer; transition: color .3s; }
.toggle button[aria-pressed="true"] { color: #fff; }
.toggle .pill { position: absolute; top: 5px; bottom: 5px; left: 5px; border-radius: 999px; background: var(--grad); transition: transform .45s var(--ease), width .45s var(--ease); box-shadow: 0 6px 20px -6px rgba(255,45,45,.7); }
.toggle em { font-style: normal; font-size: 12px; padding: 2px 7px; border-radius: 999px; background: rgba(61,220,151,.16); color: var(--green); margin-left: 6px; }
.prices { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; align-items: stretch; text-align: left; }
.plan { position: relative; display: flex; flex-direction: column; padding: 30px 26px; border-radius: 26px; background: var(--card); border: 1px solid var(--line); transition: transform .4s var(--ease), border-color .3s, box-shadow .4s; }
.plan:hover { transform: translateY(-6px); border-color: var(--line2); box-shadow: 0 30px 80px -40px rgba(0,0,0,.9); }
.plan.popular { background: linear-gradient(var(--bg2), var(--bg2)) padding-box, conic-gradient(from var(--a, 0deg), #ff2d2d, #8b5cff, #ff3d81, #ff2d2d) border-box; border: 1.5px solid transparent; animation: spin 6s linear infinite; box-shadow: 0 30px 90px -40px rgba(255,45,45,.6); }
.plan .ribbon { position: absolute; top: -13px; left: 50%; transform: translateX(-50%); padding: 5px 14px; border-radius: 999px; background: var(--grad); font-size: 12.5px; font-weight: 700; color: #fff; white-space: nowrap; box-shadow: 0 8px 24px -8px rgba(255,61,129,.8); }
.plan .ribbon.mine { background: var(--green); color: #052b1b; box-shadow: none; }
.plan h3 { font: 700 21px var(--head); margin: 0 0 4px; }
.plan .tl { color: var(--muted); font-size: 14.5px; margin: 0 0 22px; min-height: 22px; }
.price { display: flex; align-items: baseline; gap: 6px; margin-bottom: 4px; }
.price b { font: 800 40px/1 var(--head); letter-spacing: -.03em; transition: opacity .25s; }
.price span { color: var(--muted); font-size: 15px; }
.per { color: var(--dim); font-size: 13.5px; min-height: 20px; margin-bottom: 22px; }
.per s { color: var(--dim); } .per em { font-style: normal; color: var(--green); }
.plan ul { list-style: none; padding: 0; margin: 0 0 26px; display: grid; gap: 11px; flex: 1; align-content: start; }
.plan li { display: flex; gap: 10px; font-size: 15px; color: #d9d9e2; }
.plan li::before { content: ""; flex: none; width: 20px; height: 20px; margin-top: 1px; border-radius: 50%; background: rgba(61,220,151,.14) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20'%3E%3Cpath d='M6 10.5l2.5 2.5L14 7.5' fill='none' stroke='%233ddc97' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center/18px no-repeat; }
.plan .btn { width: 100%; }
.until { margin-top: 10px; text-align: center; color: var(--muted); font-size: 13px; }
.note { margin-top: 26px; color: var(--dim); font-size: 14px; }

/* ---------- вопросы */
.faq { max-width: 820px; margin: 0 auto; display: grid; gap: 12px; }
.faq details { border-radius: 18px; background: var(--card); border: 1px solid var(--line); transition: border-color .3s, background .3s; }
.faq details[open] { border-color: var(--line2); background: var(--card2); }
.faq summary { list-style: none; cursor: pointer; padding: 20px 24px; font-weight: 600; font-size: 17px; display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.faq summary::-webkit-details-marker { display: none; }
.faq summary::after { content: "+"; flex: none; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; background: var(--card2); font-size: 20px; transition: transform .35s var(--ease), background .3s; }
.faq details[open] summary::after { transform: rotate(45deg); background: var(--grad); }
.faq .ans { padding: 0 24px 20px; color: var(--muted); animation: fadeup .45s var(--ease); }

/* ---------- финал */
.final { position: relative; border-radius: 32px; padding: 64px 32px; text-align: center; overflow: hidden; background: linear-gradient(135deg, rgba(255,45,45,.22), rgba(139,92,255,.2)); border: 1px solid var(--line2); }
.final::before { content: ""; position: absolute; width: 600px; height: 600px; left: 50%; top: -340px; transform: translateX(-50%); background: radial-gradient(circle, rgba(255,61,129,.5), transparent 60%); filter: blur(30px); animation: breathe 6s ease-in-out infinite; }
@keyframes breathe { 50% { transform: translateX(-50%) scale(1.2); opacity: .7; } }
.final > * { position: relative; }
.final p { color: #d6d6e0; font-size: 18px; margin: 0 auto 30px; max-width: 560px; }
footer { padding: 40px 0 50px; color: var(--dim); font-size: 14px; }
footer .wrap { display: flex; gap: 22px; flex-wrap: wrap; align-items: center; border-top: 1px solid var(--line); padding-top: 28px; }
footer a:hover { color: var(--text); }
footer .sp { margin-left: auto; }

/* ---------- телефоны и планшеты */
@media (max-width: 1020px) {
  .hero .wrap { grid-template-columns: 1fr; gap: 48px; }
  .prices { grid-template-columns: repeat(2, 1fr); }
  .bento { grid-template-columns: repeat(2, 1fr); } .f, .f.wide { grid-column: span 1; } .f.tall { grid-row: auto; }
  .chip-float.two { left: -8px; }
}
@media (max-width: 760px) {
  .links, .me small { display: none; }
  .nav .wrap { gap: 12px; height: 64px; } .nav .btn { padding: 10px 16px; font-size: 14px; }
  section { padding: 64px 0; } .hero { padding-top: 40px; }
  .stats, .steps { grid-template-columns: 1fr 1fr; } .steps { grid-template-columns: 1fr; }
  .prices, .bento { grid-template-columns: 1fr; }
  .chip-float { display: none; } .demo-in { min-height: 360px; }
  footer .sp { margin-left: 0; }
}
@media (max-width: 420px) { .stats { grid-template-columns: 1fr; } .me span:not(.ava) { display: none; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
  .reveal, .fade, h1 .line span { opacity: 1; transform: none; }
}
</style>
</head>
<body>
<div class="bg" aria-hidden="true"><div class="grid"></div><div class="orb a"></div><div class="orb b"></div><div class="orb c"></div></div>

<header class="nav" id="nav">
  <div class="wrap">
    <a class="logo" href="./" aria-label="Rai — на главную"><i>R</i>Rai</a>
    <nav class="links" aria-label="Разделы">
      <a href="#features">Возможности</a><a href="#how">Как это работает</a><a href="#pricing">Тарифы</a><a href="#faq">Вопросы</a>
    </nav>
    <div class="right">
      <?php if ($user): ?>
        <a class="me" href="account.php"><?= avatar_html($user) ?><span><?= h($user['name'] ?: $user['login']) ?></span>
          <small><?= h($plans[$mine['key']]['name']) ?></small></a>
      <?php else: ?>
        <a class="btn" href="login.php?next=<?= rawurlencode(CHAT_URL) ?>">Войти</a>
      <?php endif; ?>
      <a class="btn primary" href="<?= CHAT_URL ?>">Открыть Rai</a>
    </div>
  </div>
</header>

<main>
  <div class="hero">
    <div class="wrap">
      <div>
        <span class="badge fade"><b>Новое</b> Своя нейросеть Rai Нейро — прямо в браузере</span>
        <h1><span class="line"><span>Ваш умный</span></span><span class="line"><span>помощник —</span></span><span class="line"><span class="grad-text">Rai</span></span></h1>
        <p class="lead fade d1">Отвечает на вопросы, пишет и исправляет код на 17 языках, делает презентации, переводит, знает погоду
          в любом посёлке и разбирает TikTok, YouTube и Telegram по ссылке. Ничего не нужно устанавливать.</p>
        <div class="cta fade d2">
          <a class="btn primary big" href="<?= CHAT_URL ?>">Начать бесплатно <span class="arrow">→</span></a>
          <a class="btn big" href="#pricing">Тарифы</a>
        </div>
        <div class="trust fade d3"><span>Без карты</span><span><?= (int)$free['neuro_day'] ?> сообщений нейросети в день бесплатно</span><span>Без автосписаний</span></div>
      </div>
      <div class="demo fade d2">
        <div class="demo-card" id="tilt">
          <div class="demo-in">
            <div class="demo-top"><span class="dot"></span><span class="dot"></span><span class="dot"></span><b>Rai</b><em>Rai Нейро в сети</em></div>
            <div class="msgs" id="msgs" aria-live="polite"></div>
            <div class="demo-input"><span>Спросите что угодно…</span><i>↑</i></div>
          </div>
        </div>
        <div class="chip-float one">⚡ Ответ за секунды<small>нейросеть работает у вас</small></div>
        <div class="chip-float two">🔒 Приватно<small>вопросы не уходят в чужие API</small></div>
      </div>
    </div>
    <div class="marquee" aria-hidden="true"><div class="track">
      <?php $items = ['Нейросеть в браузере', 'Код на 17 языках', 'Презентации и PPTX', 'Погода в любом посёлке', 'Курсы валют', 'Перевод', 'Анализ TikTok и YouTube', 'Стихи', 'Мемы', 'Картинки', 'Даты и единицы', 'AI Studio — сайты'];
      for ($i = 0; $i < 2; $i++) foreach ($items as $it) echo '<span>' . h($it) . '</span>'; ?>
    </div></div>
  </div>

  <section aria-label="Rai в цифрах">
    <div class="wrap stats">
      <div class="stat reveal"><b data-count="17">0</b><span>языков программирования с примерами</span></div>
      <div class="stat reveal" style="--d:.08s"><b data-count="5">0</b><span>моделей нейросети — от Лайт до Макс</span></div>
      <div class="stat reveal" style="--d:.16s"><b data-count="100" data-suffix="%">0</b><span>работает в браузере, без установки</span></div>
      <div class="stat reveal" style="--d:.24s"><b>0 ₽</b><span>чтобы начать — бесплатный тариф навсегда</span></div>
    </div>
  </section>

  <section id="features">
    <div class="wrap">
      <div class="center reveal"><span class="kicker">Возможности</span><h2>Один помощник — <span class="grad-text">все задачи</span></h2>
        <p class="sub">Учёба, работа, код и соцсети. Rai сам понимает, что нужно: посчитать, найти в интернете, написать программу или сделать слайды.</p></div>
      <div class="bento">
        <article class="f wide tall reveal">
          <span class="tag">Своя</span>
          <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round"><path d="M12 3a4 4 0 0 0-4 4v1a4 4 0 0 0-3 6.5A4 4 0 0 0 9 21h.5M12 3a4 4 0 0 1 4 4v1a4 4 0 0 1 3 6.5A4 4 0 0 1 15 21h-.5M12 3v18"/></svg></div>
          <h3>Rai Нейро — нейросеть прямо у вас</h3>
          <p>Пять моделей: от быстрой Лайт до мощной Макс и Код. Думает над сложными задачами, ищет в интернете, проверяет расчёты кодом и помнит, что вы рассказывали.</p>
          <div class="bars" aria-hidden="true"><i style="height:30%"></i><i style="height:48%;transition-delay:.08s"></i><i style="height:62%;transition-delay:.16s"></i><i style="height:84%;transition-delay:.24s"></i><i style="height:100%;transition-delay:.32s"></i></div>
        </article>
        <article class="f wide reveal" style="--d:.08s">
          <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/></svg></div>
          <h3>Rai Code</h3>
          <p>Пишет, запускает и сам исправляет программы. Сайты и игры — одним файлом.</p>
          <div class="code" aria-hidden="true"><span class="k">def</span> <span class="n">greet</span>(name):<br>&nbsp;&nbsp;&nbsp;&nbsp;<span class="k">return</span> <span class="s">f"Привет, {name}!"</span> <span class="c"># ✓ проверено</span></div>
        </article>
        <article class="f wide reveal" style="--d:.16s">
          <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg></div>
          <h3>Презентации за минуту</h3>
          <p>Тема — и готовы слайды с текстом и фото из интернета. Скачать в PPTX.</p>
          <div class="slides" aria-hidden="true"><div></div><div></div><div>Космос<small>Слайд 1 · Солнечная система</small></div></div>
        </article>
        <article class="f reveal">
          <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg></div>
          <h3>Интернет</h3><p>Погода в любом городе и деревне, курсы валют, перевод и поиск.</p>
        </article>
        <article class="f reveal" style="--d:.08s">
          <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></svg></div>
          <h3>Анализ соцсетей</h3><p>Ссылка на TikTok, YouTube, Telegram или сайт — цифры и советы для роста.</p>
        </article>
        <article class="f reveal" style="--d:.16s">
          <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l2.4 6.9L21 9.3l-5.2 4.4L17.5 21 12 17.3 6.5 21l1.7-7.3L3 9.3l6.6-.4z"/></svg></div>
          <h3>AI Studio</h3><p>Сайт по описанию за пару минут — с вашим адресом и API-ключами.</p>
        </article>
      </div>
    </div>
  </section>

  <section id="how">
    <div class="wrap">
      <div class="center reveal"><span class="kicker">Как это работает</span><h2>Три шага до ответа</h2>
        <p class="sub">Никаких установок и ключей — откройте сайт и спрашивайте.</p></div>
      <div class="steps">
        <div class="step reveal"><h3>Откройте Rai</h3><p>Чат работает сразу. Нейросеть загрузится в фоне и запомнится браузером.</p></div>
        <div class="step reveal" style="--d:.1s"><h3>Спросите что угодно</h3><p>Текстом или голосом. Прикрепите скриншот — Rai прочитает, что на нём.</p></div>
        <div class="step reveal" style="--d:.2s"><h3>Получите результат</h3><p>Ответ, код, презентацию или картинку — скачайте или продолжите разговор.</p></div>
      </div>
    </div>
  </section>

  <section id="pricing">
    <div class="wrap center">
      <div class="reveal"><span class="kicker">Тарифы</span><h2>Выберите <span class="grad-text">свой Rai</span></h2>
        <p class="sub">Движок Rai бесплатен всегда. Подписка добавляет сообщения нейросети, модели посильнее и режим «Думать глубже».</p></div>
      <div class="toggle reveal" role="group" aria-label="Срок подписки">
        <span class="pill" id="pill"></span>
        <button type="button" aria-pressed="true" data-period="month">Месяц</button>
        <button type="button" aria-pressed="false" data-period="year">Год <em>−<?= YEAR_DISCOUNT ?>%</em></button>
      </div>
      <div class="prices">
        <?php $i = 0; foreach ($plans as $key => $p): $is_mine = $user && $mine['key'] === $key; $i++; ?>
          <article class="plan reveal<?= !empty($p['popular']) ? ' popular' : '' ?>" style="--d:<?= ($i - 1) * 0.08 ?>s" data-plan="<?= h($key) ?>">
            <?php if ($is_mine): ?><span class="ribbon mine">Ваш тариф</span>
            <?php elseif (!empty($p['popular'])): ?><span class="ribbon">Популярный</span><?php endif; ?>
            <h3><?= h($p['name']) ?></h3>
            <p class="tl"><?= h($p['tagline']) ?></p>
            <div class="price"><b data-price><?= $key === 'free' ? '0 ₽' : rub($pricing[$key]['month']) ?></b><span><?= $key === 'free' ? 'навсегда' : '/ мес' ?></span></div>
            <div class="per" data-per><?= $key === 'free' ? 'Без карты и подписки' : 'Оплата за месяц' ?></div>
            <ul><?php foreach ($p['features'] as $f): ?><li><?= h($f) ?></li><?php endforeach; ?></ul>
            <?php if ($key === 'free'): ?>
              <a class="btn" href="<?= $user ? CHAT_URL : 'login.php?tab=register&amp;next=' . rawurlencode(CHAT_URL) ?>"><?= $user ? 'Открыть Rai' : 'Начать бесплатно' ?></a>
            <?php else: ?>
              <a class="btn<?= !empty($p['popular']) ? ' primary' : '' ?>" data-buy href="pay.php?plan=<?= h($key) ?>&amp;months=1"><?= $is_mine ? 'Продлить' : 'Подключить' ?> <span class="arrow">→</span></a>
              <?php if ($is_mine): ?><div class="until">Действует до <?= ru_date($mine['until']) ?></div><?php endif; ?>
            <?php endif; ?>
          </article>
        <?php endforeach; ?>
      </div>
      <p class="note reveal">Оплата через Platega: СБП и банковские карты. Подписка не продлевается сама — никаких скрытых списаний.
        Без входа нейросеть отвечает <?= guest_limit() ?> раз в день.</p>
    </div>
  </section>

  <section id="faq">
    <div class="wrap">
      <div class="center reveal"><span class="kicker">Вопросы</span><h2>Часто спрашивают</h2></div>
      <div class="faq">
        <details class="reveal"><summary>Что такое Rai Нейро?</summary><div class="ans">Своя нейросеть Rai на открытой модели Qwen. Она загружается в браузер и работает на вашей видеокарте или процессоре — вопросы не отправляются в чужие сервисы.</div></details>
        <details class="reveal"><summary>Нужно ли что-то устанавливать?</summary><div class="ans">Нет. Откройте rai.rteam.info в Chrome, Edge или Safari. Первая загрузка модели занимает от минуты, потом она берётся из памяти браузера.</div></details>
        <details class="reveal"><summary>Что будет, когда закончатся сообщения нейросети?</summary><div class="ans">Rai продолжит отвечать своим движком: погода, курсы, перевод, код, презентации, расчёты — всё работает. Лимит нейросети обновляется каждый день в полночь (по Москве).</div></details>
        <details class="reveal"><summary>Как оплатить и когда включится подписка?</summary><div class="ans">Выберите тариф, войдите или зарегистрируйтесь и оплатите через Platega — СБП или картой. Подписка включается сразу после оплаты.</div></details>
        <details class="reveal"><summary>Подписка продлевается автоматически?</summary><div class="ans">Нет. Вы платите за месяц или год, и всё. Продлить можно в любой момент — новое время добавится к оставшемуся.</div></details>
        <details class="reveal"><summary>Можно ли вернуть деньги?</summary><div class="ans">Если что-то пошло не так — напишите нам в течение 14 дней после оплаты, разберёмся и вернём деньги за неиспользованное время.</div></details>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="final reveal">
        <h2>Попробуйте Rai <span class="grad-text">прямо сейчас</span></h2>
        <p>Бесплатно, без карты и установки. Первый ответ — через пару секунд.</p>
        <a class="btn primary big" href="<?= CHAT_URL ?>">Открыть Rai <span class="arrow">→</span></a>
      </div>
    </div>
  </section>
</main>

<footer><div class="wrap">
  <a class="logo" href="./"><i>R</i>Rai</a><span>© <?= date('Y') ?> Rteam</span>
  <a href="<?= CHAT_URL ?>">Чат</a><a href="<?= CHAT_URL ?>#code">Code</a><a href="<?= CHAT_URL ?>#slides">Слайды</a>
  <a href="<?= h(STUDIO_URL) ?>/">AI Studio</a><a href="<?= $user ? 'account.php' : 'login.php' ?>"><?= $user ? 'Кабинет' : 'Вход' ?></a>
  <a class="sp" href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>
</div></footer>

<script>
(() => {
  const PRICES = <?= json_encode($pricing) ?>;
  const DISCOUNT = <?= (int)YEAR_DISCOUNT ?>;
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const rub = (n) => n.toLocaleString("ru-RU").replace(/ /g, " ") + " ₽";

  // шапка становится стеклянной при прокрутке
  const nav = document.getElementById("nav");
  const onScroll = () => nav.classList.toggle("scrolled", scrollY > 10);
  addEventListener("scroll", onScroll, {passive: true}); onScroll();

  // появление блоков и счётчики
  const counters = (root) => root.querySelectorAll("[data-count]").forEach((el) => {
    const end = +el.dataset.count, suffix = el.dataset.suffix || "", t0 = performance.now(), dur = still ? 1 : 1400;
    const tick = (t) => { const k = Math.min(1, (t - t0) / dur); el.textContent = Math.round(end * (1 - Math.pow(1 - k, 3))) + suffix; if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  });
  const io = "IntersectionObserver" in window ? new IntersectionObserver((list) => list.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in"); counters(e.target); io.unobserve(e.target);
  }), {threshold: .15, rootMargin: "0px 0px -40px 0px"}) : null;
  document.querySelectorAll(".reveal").forEach((el) => io ? io.observe(el) : (el.classList.add("in"), counters(el)));

  // подсветка карточек за курсором
  document.querySelectorAll(".f").forEach((card) => card.addEventListener("pointermove", (e) => {
    const r = card.getBoundingClientRect();
    card.style.setProperty("--x", (e.clientX - r.left) + "px"); card.style.setProperty("--y", (e.clientY - r.top) + "px");
  }));

  // лёгкий 3D-наклон живого чата
  const tilt = document.getElementById("tilt");
  if (tilt && !still && matchMedia("(pointer: fine)").matches) {
    const box = tilt.parentElement;
    box.addEventListener("pointermove", (e) => {
      const r = box.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      tilt.style.transform = `rotateY(${x * 8}deg) rotateX(${-y * 8}deg)`;
    });
    box.addEventListener("pointerleave", () => { tilt.style.transform = ""; });
  }

  // живой чат: Rai печатает ответы по кругу
  const DEMO = [
    ["Погода в Малиновке завтра?", "Малиновка, Минская обл. 🌤\nЗавтра +14°, без осадков, ветер 3 м/с. Зонт не понадобится."],
    ["Напиши цикл на JavaScript", "Пожалуйста:\n<code>for (let i = 0; i < 5; i++) console.log(i);</code>\nВыведет числа от 0 до 4."],
    ["Сколько дней до Нового года?", <?= json_encode((function () {
        $d = (int)round((mktime(0, 0, 0, 1, 1, (int)date('Y') + 1) - strtotime('today')) / 86400);
        $w = function ($n, $a, $b, $c) { $n %= 100; if ($n >= 11 && $n <= 14) return $c; $n %= 10; return $n === 1 ? $a : ($n >= 2 && $n <= 4 ? $b : $c); };
        return 'До Нового года осталось ' . $d . ' ' . $w($d, 'день', 'дня', 'дней') . ' 🎄 Можно уже выбирать подарки!';
    })(), JSON_UNESCAPED_UNICODE) ?>],
    ["Придумай стих про кота", "Кот на солнышке лежит,\nЩурит хитрые глаза,\nВажно усом шевелит —\nТронуть, видно, нам нельзя."],
  ];
  const box = document.getElementById("msgs");
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const add = (cls, html) => { const d = document.createElement("div"); d.className = "msg " + cls; d.innerHTML = html; box.appendChild(d); return d; };
  async function play() {
    for (let i = 0; ; i = (i + 1) % DEMO.length) {
      if (box.children.length > 3) { box.firstElementChild.remove(); box.firstElementChild.remove(); }
      const [q, a] = DEMO[i];
      add("u", q.replace(/</g, "&lt;"));
      await sleep(still ? 50 : 650);
      const r = add("r", '<span class="caret"></span>');
      if (still) r.innerHTML = a; else {
        // печатаем по символу, теги вставляем целиком
        const parts = a.match(/<[^>]+>|[^<]/g);
        let out = "";
        for (const p of parts) { out += p; r.innerHTML = out + '<span class="caret"></span>'; if (p.length === 1) await sleep(p === "\n" ? 120 : 22); }
        r.innerHTML = out;
      }
      await sleep(still ? 4000 : 2600);
    }
  }
  play();

  // тарифы: месяц или год
  const pill = document.getElementById("pill"), buttons = [...document.querySelectorAll(".toggle button")];
  function setPeriod(period) {
    buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.period === period)));
    const on = buttons.find((b) => b.dataset.period === period);
    pill.style.width = on.offsetWidth + "px"; pill.style.transform = `translateX(${on.offsetLeft - 5}px)`;
    document.querySelectorAll(".plan").forEach((card) => {
      const key = card.dataset.plan, p = PRICES[key];
      if (!p || key === "free") return;
      const price = card.querySelector("[data-price]"), per = card.querySelector("[data-per]"), buy = card.querySelector("[data-buy]");
      price.style.opacity = 0;
      setTimeout(() => {
        price.textContent = rub(period === "year" ? p.year_month : p.month);
        per.innerHTML = period === "year" ? `<s>${rub(p.month * 12)}</s> <em>${rub(p.year)} за год · −${DISCOUNT}%</em>` : "Оплата за месяц";
        price.style.opacity = 1;
      }, still ? 0 : 180);
      if (buy) buy.href = `pay.php?plan=${encodeURIComponent(key)}&months=${period === "year" ? 12 : 1}`;
    });
  }
  buttons.forEach((b) => b.addEventListener("click", () => setPeriod(b.dataset.period)));
  addEventListener("resize", () => {  // при изменении размера окна — только сдвинуть «таблетку»
    const on = buttons.find((b) => b.getAttribute("aria-pressed") === "true");
    pill.style.width = on.offsetWidth + "px"; pill.style.transform = `translateX(${on.offsetLeft - 5}px)`;
  });
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => setPeriod("month"));
})();
</script>
</body>
</html>
