"""Ещё программы для Rai Code: игры и приложения для браузера, боты, утилиты.

Подключаются в codelib: register(task) добавляет задачи в общую библиотеку.
Браузерные программы — один index.html, работают сразу во вкладке «Просмотр».
"""

HTML_FIRST = ("tetris", "pong", "breakout", "g2048", "paint", "piano", "memory", "gallery", "bmi", "currency_app", "weather_app")

_HEAD = '''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg: #0b0b0c; --fg: #f3f1f1; --muted: #9b9599; --accent: #e10600; --card: #151517; --line: #2a2a2e; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, "Segoe UI", sans-serif;
         display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 20px; }}
  h1 {{ margin: 0; font-size: 26px; }}
  button {{ font: inherit; cursor: pointer; border: 1px solid var(--line); background: var(--card); color: var(--fg); border-radius: 10px; padding: 9px 16px; }}
  button:hover {{ border-color: var(--accent); }}
  button.main {{ background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }}
  input, select {{ font: inherit; color: var(--fg); background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 9px 12px; }}
  .muted {{ color: var(--muted); font-size: 14px; }}
{css}
</style>
</head>
<body>
'''


def page(title, css, body):
    return _HEAD.format(title=title, css=css) + body.strip() + "\n</body>\n</html>\n"


TETRIS = page("Тетрис", r'''
  .game { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; justify-content: center; }
  canvas { background: #111114; border: 2px solid var(--line); border-radius: 8px; display: block; }
  .side { display: flex; flex-direction: column; gap: 10px; min-width: 130px; }
  .stat b { font-size: 22px; display: block; }
  .pad { display: grid; grid-template-columns: repeat(3, 56px); gap: 6px; }
  .pad button { padding: 12px 0; }
''', r'''
<h1>Тетрис</h1>
<div class="game">
  <canvas id="board" width="240" height="480" aria-label="Поле тетриса"></canvas>
  <div class="side">
    <div class="stat">Счёт<b id="score">0</b></div>
    <div class="stat">Линии<b id="lines">0</b></div>
    <div class="stat">Уровень<b id="level">1</b></div>
    <div class="muted">Следующая</div>
    <canvas id="next" width="96" height="96"></canvas>
    <button class="main" id="start">Старт</button>
  </div>
</div>
<div class="pad" aria-label="Управление">
  <span></span><button data-k="rotate">⟳</button><span></span>
  <button data-k="left">←</button><button data-k="drop">⤓</button><button data-k="right">→</button>
</div>
<p class="muted">← → — двигать, ↑ — повернуть, ↓ — быстрее, пробел — уронить, P — пауза</p>
<script>
const COLS = 10, ROWS = 20, S = 24;
const ctx = document.getElementById("board").getContext("2d");
const nctx = document.getElementById("next").getContext("2d");
const SHAPES = {
  I: [[1, 1, 1, 1]], O: [[1, 1], [1, 1]], T: [[0, 1, 0], [1, 1, 1]], S: [[0, 1, 1], [1, 1, 0]],
  Z: [[1, 1, 0], [0, 1, 1]], J: [[1, 0, 0], [1, 1, 1]], L: [[0, 0, 1], [1, 1, 1]]
};
const COLORS = {I: "#22d3ee", O: "#facc15", T: "#a855f7", S: "#22c55e", Z: "#ef4444", J: "#3b82f6", L: "#f97316"};
let board, piece, next, score, lines, level, timer = null, paused = false, over = true;

function newPiece() {
  const keys = Object.keys(SHAPES), k = keys[Math.floor(Math.random() * keys.length)];
  return {k: k, m: SHAPES[k].map((r) => r.slice()), x: 3, y: 0};
}
function collide(p, dx = 0, dy = 0, m = p.m) {
  return m.some((row, y) => row.some((v, x) => {
    if (!v) return false;
    const nx = p.x + x + dx, ny = p.y + y + dy;
    return nx < 0 || nx >= COLS || ny >= ROWS || (ny >= 0 && board[ny][nx]);
  }));
}
function rotate() {
  const m = piece.m[0].map((_, i) => piece.m.map((row) => row[i]).reverse());
  for (const kick of [0, -1, 1, -2, 2]) {
    if (!collide(piece, kick, 0, m)) { piece.m = m; piece.x += kick; return; }
  }
}
function merge() {
  piece.m.forEach((row, y) => row.forEach((v, x) => { if (v && piece.y + y >= 0) board[piece.y + y][piece.x + x] = piece.k; }));
  let cleared = 0;
  for (let y = ROWS - 1; y >= 0; y--) {
    if (board[y].every(Boolean)) { board.splice(y, 1); board.unshift(Array(COLS).fill(null)); cleared++; y++; }
  }
  if (cleared) {
    lines += cleared;
    score += [0, 100, 300, 500, 800][cleared] * level;
    level = 1 + Math.floor(lines / 10);
    restartTimer();
  }
  piece = next; next = newPiece();
  if (collide(piece)) { over = true; clearInterval(timer); draw(); }
}
function step() {
  if (paused || over) return;
  if (!collide(piece, 0, 1)) piece.y++; else merge();
  draw();
}
function cell(c, x, y, color, size = S) {
  c.fillStyle = color;
  c.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);
}
function draw() {
  ctx.fillStyle = "#111114"; ctx.fillRect(0, 0, COLS * S, ROWS * S);
  board.forEach((row, y) => row.forEach((k, x) => { if (k) cell(ctx, x, y, COLORS[k]); }));
  if (!over) {
    let gy = 0;
    while (!collide(piece, 0, gy + 1)) gy++;
    piece.m.forEach((row, y) => row.forEach((v, x) => { if (v) cell(ctx, piece.x + x, piece.y + y + gy, "rgba(255,255,255,.12)"); }));
    piece.m.forEach((row, y) => row.forEach((v, x) => { if (v) cell(ctx, piece.x + x, piece.y + y, COLORS[piece.k]); }));
  }
  nctx.fillStyle = "#111114"; nctx.fillRect(0, 0, 96, 96);
  next.m.forEach((row, y) => row.forEach((v, x) => { if (v) cell(nctx, x + 0.5, y + 1, COLORS[next.k], 20); }));
  document.getElementById("score").textContent = score;
  document.getElementById("lines").textContent = lines;
  document.getElementById("level").textContent = level;
  if (over && score) {
    ctx.fillStyle = "rgba(0,0,0,.7)"; ctx.fillRect(0, 190, COLS * S, 90);
    ctx.fillStyle = "#fff"; ctx.font = "bold 22px system-ui"; ctx.textAlign = "center";
    ctx.fillText("Игра окончена", COLS * S / 2, 230); ctx.font = "16px system-ui"; ctx.fillText("Счёт: " + score, COLS * S / 2, 258);
  }
}
function restartTimer() { clearInterval(timer); timer = setInterval(step, Math.max(90, 650 - (level - 1) * 60)); }
function start() {
  board = Array.from({length: ROWS}, () => Array(COLS).fill(null));
  score = 0; lines = 0; level = 1; over = false; paused = false;
  piece = newPiece(); next = newPiece();
  restartTimer(); draw();
}
function act(k) {
  if (over) return;
  if (k === "left" && !collide(piece, -1, 0)) piece.x--;
  if (k === "right" && !collide(piece, 1, 0)) piece.x++;
  if (k === "down") step();
  if (k === "rotate") rotate();
  if (k === "drop") { while (!collide(piece, 0, 1)) { piece.y++; score += 2; } merge(); }
  draw();
}
document.addEventListener("keydown", (e) => {
  const map = {ArrowLeft: "left", ArrowRight: "right", ArrowDown: "down", ArrowUp: "rotate", " ": "drop"};
  if (map[e.key]) { e.preventDefault(); act(map[e.key]); }
  if (e.key === "p" || e.key === "P" || e.key === "з") paused = !paused;
});
document.querySelectorAll("[data-k]").forEach((b) => b.addEventListener("click", () => act(b.dataset.k)));
document.getElementById("start").addEventListener("click", start);
board = Array.from({length: ROWS}, () => Array(COLS).fill(null)); piece = newPiece(); next = newPiece(); score = lines = 0; level = 1; draw();
</script>
''')

PONG = page("Пинг-понг", r'''
  canvas { background: #111114; border: 2px solid var(--line); border-radius: 10px; max-width: 100%; touch-action: none; }
''', r'''
<h1>Пинг-понг</h1>
<canvas id="c" width="720" height="420" aria-label="Поле для пинг-понга"></canvas>
<p class="muted">Ракетка — мышью, пальцем или клавишами ↑ ↓ (W S). Игра до 7 очков. Пробел — старт/пауза.</p>
<script>
const cv = document.getElementById("c"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
const P = {w: 12, h: 80}, WIN = 7;
let me = H / 2, ai = H / 2, ball, sc = [0, 0], running = false, keys = {};
function serve(dir) { ball = {x: W / 2, y: H / 2, vx: 5 * dir, vy: (Math.random() * 4 - 2), r: 8}; }
function reset() { sc = [0, 0]; serve(Math.random() < .5 ? 1 : -1); }
function bounce(py, dir) {
  const hit = (ball.y - py) / (P.h / 2);
  const speed = Math.min(14, Math.hypot(ball.vx, ball.vy) * 1.05);
  ball.vx = dir * speed * Math.cos(hit * 0.9);
  ball.vy = speed * Math.sin(hit * 0.9);
}
function update() {
  if (keys.up) me -= 7;
  if (keys.down) me += 7;
  me = Math.max(P.h / 2, Math.min(H - P.h / 2, me));
  ai += Math.max(-5, Math.min(5, ball.y - ai)) * 0.9;
  ball.x += ball.vx; ball.y += ball.vy;
  if (ball.y < ball.r || ball.y > H - ball.r) ball.vy *= -1;
  if (ball.x - ball.r < 20 + P.w && Math.abs(ball.y - me) < P.h / 2 + ball.r && ball.vx < 0) bounce(me, 1);
  if (ball.x + ball.r > W - 20 - P.w && Math.abs(ball.y - ai) < P.h / 2 + ball.r && ball.vx > 0) bounce(ai, -1);
  if (ball.x < 0) { sc[1]++; serve(1); }
  if (ball.x > W) { sc[0]++; serve(-1); }
  if (sc[0] >= WIN || sc[1] >= WIN) running = false;
}
function draw() {
  ctx.fillStyle = "#111114"; ctx.fillRect(0, 0, W, H);
  ctx.setLineDash([8, 12]); ctx.strokeStyle = "#2a2a2e"; ctx.beginPath(); ctx.moveTo(W / 2, 0); ctx.lineTo(W / 2, H); ctx.stroke(); ctx.setLineDash([]);
  ctx.fillStyle = "#f3f1f1"; ctx.font = "bold 48px system-ui"; ctx.textAlign = "center";
  ctx.fillText(sc[0], W / 2 - 60, 60); ctx.fillText(sc[1], W / 2 + 60, 60);
  ctx.fillStyle = "#e10600"; ctx.fillRect(20, me - P.h / 2, P.w, P.h);
  ctx.fillStyle = "#9b9599"; ctx.fillRect(W - 20 - P.w, ai - P.h / 2, P.w, P.h);
  ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2); ctx.fill();
  if (!running) {
    ctx.font = "22px system-ui";
    const msg = sc[0] >= WIN ? "Вы победили! Пробел — ещё раз" : sc[1] >= WIN ? "Компьютер победил. Пробел — ещё раз" : "Пробел или касание — старт";
    ctx.fillText(msg, W / 2, H / 2 + 60);
  }
}
function loop() { if (running) update(); draw(); requestAnimationFrame(loop); }
function toggle() { if (sc[0] >= WIN || sc[1] >= WIN) reset(); running = !running; }
function pointer(e) { const r = cv.getBoundingClientRect(); me = (e.clientY - r.top) * (H / r.height); }
cv.addEventListener("pointermove", pointer);
cv.addEventListener("pointerdown", (e) => { pointer(e); if (!running) toggle(); });
document.addEventListener("keydown", (e) => {
  if (e.key === " ") { e.preventDefault(); toggle(); }
  if (e.key === "ArrowUp" || e.key === "w" || e.key === "ц") keys.up = true;
  if (e.key === "ArrowDown" || e.key === "s" || e.key === "ы") keys.down = true;
});
document.addEventListener("keyup", () => { keys = {}; });
reset(); loop();
</script>
''')

BREAKOUT = page("Арканоид", r'''
  canvas { background: #111114; border: 2px solid var(--line); border-radius: 10px; max-width: 100%; touch-action: none; }
''', r'''
<h1>Арканоид</h1>
<canvas id="c" width="640" height="480" aria-label="Поле арканоида"></canvas>
<p class="muted">Платформа — мышью, пальцем или ← →. Пробел или касание — запустить мяч.</p>
<script>
const cv = document.getElementById("c"), ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
const ROWS = 6, COLS = 10, BW = 58, BH = 20, GAP = 4, TOP = 50;
const COLORS = ["#ef4444", "#f97316", "#facc15", "#22c55e", "#3b82f6", "#a855f7"];
let bricks, pad, ball, lives, score, stuck, keys = {};
function reset() {
  bricks = [];
  for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) bricks.push({x: 12 + c * (BW + GAP), y: TOP + r * (BH + GAP), color: COLORS[r], alive: true});
  pad = {x: W / 2, w: 90}; lives = 3; score = 0; newBall();
}
function newBall() { ball = {x: pad.x, y: H - 42, vx: 3.5, vy: -4.5, r: 7}; stuck = true; }
function update() {
  if (keys.left) pad.x -= 8;
  if (keys.right) pad.x += 8;
  pad.x = Math.max(pad.w / 2, Math.min(W - pad.w / 2, pad.x));
  if (stuck) { ball.x = pad.x; return; }
  ball.x += ball.vx; ball.y += ball.vy;
  if (ball.x < ball.r || ball.x > W - ball.r) ball.vx *= -1;
  if (ball.y < ball.r) ball.vy *= -1;
  if (ball.y > H - 30 - ball.r && ball.y < H - 20 && Math.abs(ball.x - pad.x) < pad.w / 2 + ball.r && ball.vy > 0) {
    const hit = (ball.x - pad.x) / (pad.w / 2), speed = Math.hypot(ball.vx, ball.vy);
    ball.vx = speed * Math.sin(hit * 1.05); ball.vy = -speed * Math.cos(hit * 1.05);
  }
  for (const b of bricks) {
    if (b.alive && ball.x > b.x - ball.r && ball.x < b.x + BW + ball.r && ball.y > b.y - ball.r && ball.y < b.y + BH + ball.r) {
      b.alive = false; score += 10; ball.vy *= -1;
      ball.vx *= 1.01; ball.vy *= 1.01;
      break;
    }
  }
  if (ball.y > H) { lives--; if (lives > 0) newBall(); }
}
function draw() {
  ctx.fillStyle = "#111114"; ctx.fillRect(0, 0, W, H);
  for (const b of bricks) if (b.alive) { ctx.fillStyle = b.color; ctx.fillRect(b.x, b.y, BW, BH); }
  ctx.fillStyle = "#e10600"; ctx.fillRect(pad.x - pad.w / 2, H - 30, pad.w, 10);
  ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r, 0, Math.PI * 2); ctx.fill();
  ctx.font = "16px system-ui"; ctx.textAlign = "left"; ctx.fillText("Очки: " + score, 12, 28);
  ctx.textAlign = "right"; ctx.fillText("Жизни: " + "❤".repeat(Math.max(0, lives)), W - 12, 28);
  const won = bricks.every((b) => !b.alive);
  if (lives <= 0 || won) {
    ctx.textAlign = "center"; ctx.font = "bold 30px system-ui";
    ctx.fillText(won ? "Победа!" : "Игра окончена", W / 2, H / 2);
    ctx.font = "18px system-ui"; ctx.fillText("Пробел или касание — заново", W / 2, H / 2 + 34);
  }
}
function loop() { if (lives > 0 && bricks.some((b) => b.alive)) update(); draw(); requestAnimationFrame(loop); }
function launch() { if (lives <= 0 || bricks.every((b) => !b.alive)) reset(); else stuck = false; }
cv.addEventListener("pointermove", (e) => { const r = cv.getBoundingClientRect(); pad.x = (e.clientX - r.left) * (W / r.width); });
cv.addEventListener("pointerdown", launch);
document.addEventListener("keydown", (e) => {
  if (e.key === " ") { e.preventDefault(); launch(); }
  if (e.key === "ArrowLeft") keys.left = true;
  if (e.key === "ArrowRight") keys.right = true;
});
document.addEventListener("keyup", () => { keys = {}; });
reset(); loop();
</script>
''')

G2048 = page("2048", r'''
  .top { display: flex; gap: 10px; align-items: center; }
  .score { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 6px 14px; text-align: center; }
  .score b { display: block; font-size: 20px; }
  #grid { display: grid; grid-template-columns: repeat(4, 76px); gap: 10px; background: #1d1d20; padding: 10px; border-radius: 14px; touch-action: none; }
  .t { width: 76px; height: 76px; border-radius: 10px; display: grid; place-items: center; font-weight: 800; font-size: 28px; background: #2a2a2e; transition: transform .1s; }
  .t.pop { transform: scale(1.1); }
''', r'''
<h1>2048</h1>
<div class="top">
  <div class="score">Счёт<b id="score">0</b></div>
  <div class="score">Рекорд<b id="best">0</b></div>
  <button class="main" id="new">Новая игра</button>
</div>
<div id="grid" aria-label="Поле 4 на 4"></div>
<p class="muted" id="msg">Стрелки или свайп — сдвинуть плитки. Соединяйте одинаковые числа, чтобы получить 2048!</p>
<script>
const N = 4, gridEl = document.getElementById("grid");
const COLORS = {2: "#eee4da", 4: "#ede0c8", 8: "#f2b179", 16: "#f59563", 32: "#f67c5f", 64: "#f65e3b", 128: "#edcf72",
                256: "#edcc61", 512: "#edc850", 1024: "#edc53f", 2048: "#edc22e"};
let g, score, best = 0;
try { best = +localStorage.getItem("best2048") || 0; } catch (e) { /* без сохранения рекорда */ }
function add() {
  const free = [];
  g.forEach((row, y) => row.forEach((v, x) => { if (!v) free.push([y, x]); }));
  if (!free.length) return;
  const [y, x] = free[Math.floor(Math.random() * free.length)];
  g[y][x] = Math.random() < 0.9 ? 2 : 4;
}
function start() { g = Array.from({length: N}, () => Array(N).fill(0)); score = 0; add(); add(); draw(); }
function slide(row) {
  const a = row.filter(Boolean);
  for (let i = 0; i < a.length - 1; i++) if (a[i] === a[i + 1]) { a[i] *= 2; score += a[i]; a.splice(i + 1, 1); }
  while (a.length < N) a.push(0);
  return a;
}
function move(dir) {
  const before = JSON.stringify(g);
  const rot = (m) => m[0].map((_, i) => m.map((r) => r[i]).reverse());
  let times = {left: 0, down: 1, right: 2, up: 3}[dir];
  for (let i = 0; i < times; i++) g = rot(g);
  g = g.map(slide);
  for (let i = 0; i < (4 - times) % 4; i++) g = rot(g);
  if (JSON.stringify(g) !== before) { add(); draw(); }
}
function canMove() {
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    if (!g[y][x] || (x < N - 1 && g[y][x] === g[y][x + 1]) || (y < N - 1 && g[y][x] === g[y + 1][x])) return true;
  }
  return false;
}
function draw() {
  gridEl.innerHTML = "";
  g.flat().forEach((v) => {
    const t = document.createElement("div");
    t.className = "t";
    t.textContent = v || "";
    if (v) { t.style.background = COLORS[v] || "#3c3a32"; t.style.color = v <= 4 ? "#776e65" : "#fff"; if (v >= 1024) t.style.fontSize = "22px"; }
    gridEl.append(t);
  });
  if (score > best) { best = score; try { localStorage.setItem("best2048", best); } catch (e) { /* ничего */ } }
  document.getElementById("score").textContent = score;
  document.getElementById("best").textContent = best;
  const won = g.flat().includes(2048);
  document.getElementById("msg").textContent = won ? "Победа! 2048 собрано 🎉" : canMove() ? "Стрелки или свайп — сдвинуть плитки." : "Ходов больше нет. Новая игра?";
}
document.addEventListener("keydown", (e) => {
  const d = {ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down"}[e.key];
  if (d) { e.preventDefault(); move(d); }
});
let sx, sy;
gridEl.addEventListener("pointerdown", (e) => { sx = e.clientX; sy = e.clientY; });
gridEl.addEventListener("pointerup", (e) => {
  const dx = e.clientX - sx, dy = e.clientY - sy;
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 30) return;
  move(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
});
document.getElementById("new").addEventListener("click", start);
start();
</script>
''')

PAINT = page("Рисовалка", r'''
  .tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; justify-content: center; }
  .tools label { display: flex; align-items: center; gap: 6px; font-size: 14px; }
  input[type=color] { width: 44px; height: 38px; padding: 2px; }
  button.on { background: var(--accent); border-color: var(--accent); }
  canvas { background: #fff; border-radius: 10px; max-width: 100%; touch-action: none; cursor: crosshair; }
''', r'''
<h1>Рисовалка</h1>
<div class="tools">
  <label>Цвет <input type="color" id="color" value="#e10600"></label>
  <label>Толщина <input type="range" id="size" min="1" max="60" value="8"></label>
  <button id="brush" class="on">Кисть</button><button id="eraser">Ластик</button>
  <button id="undo">Отменить</button><button id="clear">Очистить</button><button class="main" id="save">Сохранить PNG</button>
</div>
<canvas id="c" width="900" height="560" aria-label="Холст"></canvas>
<p class="muted">Рисуйте мышью или пальцем. Ctrl+Z — отменить.</p>
<script>
const cv = document.getElementById("c"), ctx = cv.getContext("2d");
let drawing = false, erase = false, last = null, history = [];
ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cv.width, cv.height);
ctx.lineCap = "round"; ctx.lineJoin = "round";
function pos(e) { const r = cv.getBoundingClientRect(); return {x: (e.clientX - r.left) * cv.width / r.width, y: (e.clientY - r.top) * cv.height / r.height}; }
cv.addEventListener("pointerdown", (e) => {
  drawing = true; last = pos(e); cv.setPointerCapture(e.pointerId);
  history.push(ctx.getImageData(0, 0, cv.width, cv.height)); if (history.length > 30) history.shift();
  line(last, last);
});
cv.addEventListener("pointermove", (e) => { if (!drawing) return; const p = pos(e); line(last, p); last = p; });
cv.addEventListener("pointerup", () => { drawing = false; });
function line(a, b) {
  ctx.strokeStyle = erase ? "#fff" : document.getElementById("color").value;
  ctx.lineWidth = +document.getElementById("size").value;
  ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
}
function setTool(isErase) {
  erase = isErase;
  document.getElementById("brush").classList.toggle("on", !erase);
  document.getElementById("eraser").classList.toggle("on", erase);
}
function undo() { const img = history.pop(); if (img) ctx.putImageData(img, 0, 0); }
document.getElementById("brush").onclick = () => setTool(false);
document.getElementById("eraser").onclick = () => setTool(true);
document.getElementById("undo").onclick = undo;
document.getElementById("clear").onclick = () => { history.push(ctx.getImageData(0, 0, cv.width, cv.height)); ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, cv.width, cv.height); };
document.getElementById("save").onclick = () => { const a = document.createElement("a"); a.download = "рисунок.png"; a.href = cv.toDataURL("image/png"); a.click(); };
document.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); undo(); } });
</script>
''')

PIANO = page("Пианино", r'''
  .piano { position: relative; display: flex; user-select: none; touch-action: none; }
  .w { width: 48px; height: 200px; background: #fafafa; border: 1px solid #333; border-radius: 0 0 8px 8px; color: #777;
       display: flex; align-items: flex-end; justify-content: center; padding-bottom: 8px; font-size: 13px; cursor: pointer; }
  .b { position: absolute; width: 30px; height: 124px; background: #111; border-radius: 0 0 6px 6px; z-index: 2; color: #aaa;
       display: flex; align-items: flex-end; justify-content: center; padding-bottom: 6px; font-size: 11px; cursor: pointer; }
  .w.on { background: #ffd0cc; } .b.on { background: var(--accent); }
''', r'''
<h1>Пианино</h1>
<label class="muted">Звук <select id="wave"><option value="triangle">мягкий</option><option value="sine">чистый</option><option value="square">8-бит</option><option value="sawtooth">яркий</option></select></label>
<div class="piano" id="piano" aria-label="Клавиши пианино"></div>
<p class="muted">Играйте мышью, пальцем или клавиатурой: белые — A S D F G H J K L, чёрные — W E T Y U O P</p>
<script>
const NOTES = [
  ["C4", 261.63, "A"], ["C#4", 277.18, "W"], ["D4", 293.66, "S"], ["D#4", 311.13, "E"], ["E4", 329.63, "D"],
  ["F4", 349.23, "F"], ["F#4", 369.99, "T"], ["G4", 392.0, "G"], ["G#4", 415.3, "Y"], ["A4", 440.0, "H"],
  ["A#4", 466.16, "U"], ["B4", 493.88, "J"], ["C5", 523.25, "K"], ["C#5", 554.37, "O"], ["D5", 587.33, "L"], ["D#5", 622.25, "P"], ["E5", 659.25, ";"]
];
let audio = null;
const piano = document.getElementById("piano"), byKey = {};
let whiteIndex = 0;
for (const [name, freq, key] of NOTES) {
  const black = name.includes("#");
  const el = document.createElement("div");
  el.className = black ? "b" : "w";
  el.textContent = key;
  if (black) el.style.left = (whiteIndex * 48 - 15) + "px"; else whiteIndex++;
  el.addEventListener("pointerdown", (e) => { e.preventDefault(); play(freq, el); });
  piano.append(el);
  byKey[key.toLowerCase()] = [freq, el];
}
function play(freq, el) {
  audio = audio || new (window.AudioContext || window.webkitAudioContext)();
  const osc = audio.createOscillator(), gain = audio.createGain(), t = audio.currentTime;
  osc.type = document.getElementById("wave").value;
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(0.35, t + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + 1.2);
  osc.connect(gain).connect(audio.destination);
  osc.start(t); osc.stop(t + 1.25);
  el.classList.add("on"); setTimeout(() => el.classList.remove("on"), 180);
}
const RU = {"ф": "a", "ы": "s", "в": "d", "а": "f", "п": "g", "р": "h", "о": "j", "л": "k", "д": "l", "ц": "w", "у": "e", "е": "t", "н": "y", "г": "u", "щ": "o", "з": "p", "ж": ";"};
document.addEventListener("keydown", (e) => {
  if (e.repeat) return;
  const k = RU[e.key.toLowerCase()] || e.key.toLowerCase();
  if (byKey[k]) play(...byKey[k]);
});
</script>
''')

MEMORY = page("Найди пару", r'''
  #board { display: grid; grid-template-columns: repeat(4, 76px); gap: 10px; }
  .card { width: 76px; height: 76px; border-radius: 12px; font-size: 36px; display: grid; place-items: center; background: var(--accent); border: 0; }
  .card.open, .card.done { background: var(--card); border: 1px solid var(--line); }
  .card.done { opacity: .5; }
''', r'''
<h1>Найди пару</h1>
<p class="muted">Ходы: <b id="moves">0</b> · Время: <b id="time">0</b> с</p>
<div id="board" aria-label="Карточки"></div>
<button class="main" id="new">Новая игра</button>
<script>
const EMOJI = ["🍎", "🚀", "🐱", "🎸", "⚽", "🌈", "🍕", "🎲"];
let first = null, lock = false, moves = 0, found = 0, t0 = 0, timer = null;
function start() {
  const deck = EMOJI.concat(EMOJI).sort(() => Math.random() - 0.5);
  const board = document.getElementById("board");
  board.innerHTML = ""; first = null; lock = false; moves = 0; found = 0;
  document.getElementById("moves").textContent = 0;
  clearInterval(timer); t0 = 0; document.getElementById("time").textContent = 0;
  deck.forEach((e) => {
    const c = document.createElement("button");
    c.className = "card"; c.dataset.e = e; c.setAttribute("aria-label", "Карточка");
    c.onclick = () => flip(c);
    board.append(c);
  });
}
function flip(c) {
  if (lock || c === first || c.classList.contains("done")) return;
  if (!t0) { t0 = Date.now(); timer = setInterval(() => { document.getElementById("time").textContent = Math.round((Date.now() - t0) / 1000); }, 500); }
  c.classList.add("open"); c.textContent = c.dataset.e;
  if (!first) { first = c; return; }
  moves++; document.getElementById("moves").textContent = moves;
  if (first.dataset.e === c.dataset.e) {
    first.classList.add("done"); c.classList.add("done"); first = null; found++;
    if (found === EMOJI.length) { clearInterval(timer); setTimeout(() => alert("Победа! Ходов: " + moves), 200); }
  } else {
    lock = true;
    setTimeout(() => { [first, c].forEach((x) => { x.classList.remove("open"); x.textContent = ""; }); first = null; lock = false; }, 700);
  }
}
document.getElementById("new").onclick = start;
start();
</script>
''')

GALLERY = page("Фотогалерея", r'''
  .bar { display: flex; gap: 8px; }
  .grid { width: min(1000px, 100%); display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
  .grid button { padding: 0; border: 0; border-radius: 12px; overflow: hidden; aspect-ratio: 4 / 3; background: var(--card); }
  .grid img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .3s; }
  .grid button:hover img { transform: scale(1.05); }
  .lb { position: fixed; inset: 0; background: rgba(0,0,0,.9); display: none; align-items: center; justify-content: center; gap: 10px; }
  .lb.on { display: flex; }
  .lb img { max-width: 84vw; max-height: 86vh; border-radius: 10px; }
  .lb button { font-size: 26px; background: transparent; border: 0; }
''', r'''
<h1>Фотогалерея</h1>
<div class="bar"><button class="main" id="add">Добавить фото</button><input type="file" id="file" accept="image/*" multiple hidden></div>
<div class="grid" id="grid"></div>
<div class="lb" id="lb" role="dialog" aria-label="Просмотр фото">
  <button id="prev" aria-label="Предыдущее">‹</button><img id="big" alt=""><button id="next" aria-label="Следующее">›</button>
</div>
<p class="muted">Нажмите на фото, чтобы открыть. Стрелки — листать, Esc — закрыть. Свои фото добавляются кнопкой сверху.</p>
<script>
const photos = [];
function demo(i) {
  const c = document.createElement("canvas"); c.width = 800; c.height = 600;
  const x = c.getContext("2d"), h = (i * 47) % 360, g = x.createLinearGradient(0, 0, 800, 600);
  g.addColorStop(0, `hsl(${h} 80% 55%)`); g.addColorStop(1, `hsl(${(h + 60) % 360} 70% 25%)`);
  x.fillStyle = g; x.fillRect(0, 0, 800, 600);
  x.fillStyle = "rgba(255,255,255,.85)"; x.font = "bold 64px system-ui"; x.fillText("Фото " + (i + 1), 40, 560);
  return c.toDataURL("image/jpeg", 0.85);
}
for (let i = 0; i < 8; i++) photos.push(demo(i));
let cur = 0;
function render() {
  const grid = document.getElementById("grid"); grid.innerHTML = "";
  photos.forEach((src, i) => {
    const b = document.createElement("button"); b.innerHTML = `<img alt="Фото ${i + 1}" src="${src}">`;
    b.onclick = () => open(i); grid.append(b);
  });
}
function open(i) { cur = (i + photos.length) % photos.length; document.getElementById("big").src = photos[cur]; document.getElementById("lb").classList.add("on"); }
function close() { document.getElementById("lb").classList.remove("on"); }
document.getElementById("prev").onclick = (e) => { e.stopPropagation(); open(cur - 1); };
document.getElementById("next").onclick = (e) => { e.stopPropagation(); open(cur + 1); };
document.getElementById("lb").onclick = close;
document.addEventListener("keydown", (e) => {
  if (!document.getElementById("lb").classList.contains("on")) return;
  if (e.key === "Escape") close(); if (e.key === "ArrowLeft") open(cur - 1); if (e.key === "ArrowRight") open(cur + 1);
});
document.getElementById("add").onclick = () => document.getElementById("file").click();
document.getElementById("file").onchange = (e) => {
  for (const f of e.target.files) { const r = new FileReader(); r.onload = () => { photos.unshift(r.result); render(); }; r.readAsDataURL(f); }
};
render();
</script>
''')

BMI_HTML = page("Калькулятор ИМТ", r'''
  form { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; display: grid; gap: 12px; width: min(380px, 100%); }
  label { display: grid; gap: 4px; font-size: 14px; color: var(--muted); }
  #res { font-size: 20px; text-align: center; min-height: 60px; }
  #res b { font-size: 40px; display: block; }
''', r'''
<h1>Индекс массы тела</h1>
<form id="f">
  <label>Рост, см <input id="h" type="number" min="50" max="250" value="175" required></label>
  <label>Вес, кг <input id="w" type="number" min="10" max="400" step="0.1" value="70" required></label>
  <button class="main">Рассчитать</button>
  <div id="res" aria-live="polite"></div>
</form>
<p class="muted">ИМТ = вес / рост² (в метрах). Это ориентир, а не диагноз.</p>
<script>
document.getElementById("f").onsubmit = (e) => {
  e.preventDefault();
  const h = +document.getElementById("h").value / 100, w = +document.getElementById("w").value;
  if (!h || !w) return;
  const bmi = w / (h * h);
  const [text, color] = bmi < 18.5 ? ["Недостаток веса", "#3b82f6"] : bmi < 25 ? ["Норма", "#22c55e"] : bmi < 30 ? ["Избыточный вес", "#f59e0b"] : ["Ожирение", "#ef4444"];
  document.getElementById("res").innerHTML = `<b style="color:${color}">${bmi.toFixed(1)}</b>${text}`;
};
</script>
''')

BMI_PY = '''# Калькулятор индекса массы тела (ИМТ)


def bmi(weight_kg, height_cm):
    """ИМТ = вес / рост² (рост в метрах)."""
    h = height_cm / 100
    return weight_kg / (h * h)


def verdict(value):
    if value < 18.5:
        return "недостаток веса"
    if value < 25:
        return "норма"
    if value < 30:
        return "избыточный вес"
    return "ожирение"


height = float(input("Рост, см: "))
weight = float(input("Вес, кг: "))
value = bmi(weight, height)
print(f"ИМТ: {value:.1f} — {verdict(value)}")
'''

CURRENCY_HTML = page("Конвертер валют", r'''
  .box { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; display: grid; gap: 12px; width: min(440px, 100%); }
  .row { display: flex; gap: 8px; } .row > * { flex: 1; min-width: 0; }
  #out { font-size: 28px; font-weight: 700; text-align: center; }
''', r'''
<h1>Конвертер валют</h1>
<div class="box">
  <input id="amount" type="number" value="100" min="0" step="any" aria-label="Сумма">
  <div class="row">
    <select id="from" aria-label="Из валюты"></select>
    <button id="swap" aria-label="Поменять местами">⇄</button>
    <select id="to" aria-label="В валюту"></select>
  </div>
  <div id="out" aria-live="polite">…</div>
  <div class="muted" id="info">Загружаю курсы…</div>
</div>
<script>
const NAMES = {USD: "Доллар США", EUR: "Евро", RUB: "Рубль", CNY: "Юань", GBP: "Фунт", JPY: "Иена", KZT: "Тенге", BYN: "Бел. рубль",
               UAH: "Гривна", TRY: "Лира", AED: "Дирхам", CHF: "Франк", KRW: "Вона", INR: "Рупия", GEL: "Лари", AMD: "Драм", UZS: "Сум"};
let rates = null;
const $ = (id) => document.getElementById(id);
function fill() {
  for (const sel of [$("from"), $("to")]) {
    sel.innerHTML = Object.keys(NAMES).filter((c) => rates[c]).map((c) => `<option value="${c}">${c} — ${NAMES[c]}</option>`).join("");
  }
  $("from").value = "USD"; $("to").value = "RUB";
}
function calc() {
  if (!rates) return;
  const a = +$("amount").value || 0, from = $("from").value, to = $("to").value;
  const result = a / rates[from] * rates[to];
  $("out").textContent = `${a.toLocaleString("ru-RU")} ${from} = ${result.toLocaleString("ru-RU", {maximumFractionDigits: 2})} ${to}`;
}
fetch("https://open.er-api.com/v6/latest/USD")
  .then((r) => r.json())
  .then((d) => {
    rates = d.rates; fill(); calc();
    $("info").textContent = "Курсы на " + new Date(d.time_last_update_unix * 1000).toLocaleString("ru-RU") + " (open.er-api.com)";
  })
  .catch(() => { $("info").textContent = "Не удалось загрузить курсы — проверьте интернет."; $("out").textContent = "—"; });
["amount", "from", "to"].forEach((id) => $(id).addEventListener("input", calc));
$("swap").onclick = () => { const f = $("from").value; $("from").value = $("to").value; $("to").value = f; calc(); };
</script>
''')

CURRENCY_PY = '''# Конвертер валют по свежему курсу (бесплатный сервис open.er-api.com, без ключа)
import json
import urllib.request


def rates(base="USD"):
    with urllib.request.urlopen(f"https://open.er-api.com/v6/latest/{base}", timeout=10) as r:
        return json.load(r)["rates"]


amount = float(input("Сумма: "))
src = input("Из валюты (например, USD): ").strip().upper() or "USD"
dst = input("В валюту (например, RUB): ").strip().upper() or "RUB"
table = rates(src)
if dst not in table:
    print("Не знаю такую валюту:", dst)
else:
    print(f"{amount:g} {src} = {amount * table[dst]:,.2f} {dst}".replace(",", " "))
'''

WEATHER_HTML = page("Погода", r'''
  form { display: flex; gap: 8px; width: min(460px, 100%); } form input { flex: 1; min-width: 0; }
  .now { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; width: min(460px, 100%); text-align: center; }
  .now .t { font-size: 64px; font-weight: 800; line-height: 1; } .now .e { font-size: 56px; }
  .days { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px; width: min(640px, 100%); }
  .day { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 10px; text-align: center; font-size: 14px; }
  .day .e { font-size: 28px; }
''', r'''
<h1>Погода</h1>
<form id="f"><input id="city" value="Москва" aria-label="Город" required><button class="main">Показать</button></form>
<div class="now" id="now" aria-live="polite">Загрузка…</div>
<div class="days" id="days"></div>
<p class="muted">Данные: Open-Meteo (бесплатно, без ключа).</p>
<script>
const CODES = {0: ["☀️", "ясно"], 1: ["🌤️", "в основном ясно"], 2: ["⛅", "переменная облачность"], 3: ["☁️", "пасмурно"], 45: ["🌫️", "туман"], 48: ["🌫️", "изморозь"],
  51: ["🌦️", "морось"], 53: ["🌦️", "морось"], 55: ["🌧️", "сильная морось"], 61: ["🌧️", "небольшой дождь"], 63: ["🌧️", "дождь"], 65: ["🌧️", "ливень"],
  71: ["🌨️", "небольшой снег"], 73: ["🌨️", "снег"], 75: ["❄️", "сильный снег"], 80: ["🌦️", "ливни"], 81: ["🌧️", "ливни"], 82: ["⛈️", "сильные ливни"],
  95: ["⛈️", "гроза"], 96: ["⛈️", "гроза с градом"], 99: ["⛈️", "гроза с градом"]};
const code = (c) => CODES[c] || ["🌡️", "—"];
async function show(city) {
  const now = document.getElementById("now"), days = document.getElementById("days");
  now.textContent = "Загрузка…"; days.innerHTML = "";
  try {
    const geo = await (await fetch("https://geocoding-api.open-meteo.com/v1/search?count=1&language=ru&name=" + encodeURIComponent(city))).json();
    if (!geo.results) { now.textContent = "Город не найден."; return; }
    const p = geo.results[0];
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${p.latitude}&longitude=${p.longitude}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=7`;
    const w = await (await fetch(url)).json(), c = w.current, [e, text] = code(c.weather_code);
    now.innerHTML = `<div>${p.name}${p.country ? ", " + p.country : ""}</div><div class="e">${e}</div><div class="t">${Math.round(c.temperature_2m)}°</div>
      <div>${text}, ощущается как ${Math.round(c.apparent_temperature)}°</div><div class="muted">Ветер ${Math.round(c.wind_speed_10m)} км/ч · влажность ${c.relative_humidity_2m}%</div>`;
    w.daily.time.forEach((d, i) => {
      const [de] = code(w.daily.weather_code[i]);
      const name = new Date(d).toLocaleDateString("ru-RU", {weekday: "short", day: "numeric"});
      days.insertAdjacentHTML("beforeend", `<div class="day">${name}<div class="e">${de}</div><b>${Math.round(w.daily.temperature_2m_max[i])}°</b> / ${Math.round(w.daily.temperature_2m_min[i])}°</div>`);
    });
  } catch (err) { now.textContent = "Не удалось загрузить погоду — проверьте интернет."; }
}
document.getElementById("f").onsubmit = (e) => { e.preventDefault(); show(document.getElementById("city").value); };
show("Москва");
</script>
''')

WEATHER_PY = '''# Погода в любом городе (бесплатный сервис Open-Meteo, без ключа)
import json
import urllib.parse
import urllib.request

CODES = {0: "ясно", 1: "в основном ясно", 2: "переменная облачность", 3: "пасмурно", 45: "туман", 61: "небольшой дождь",
         63: "дождь", 65: "ливень", 71: "небольшой снег", 73: "снег", 75: "сильный снег", 80: "ливни", 95: "гроза"}


def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


city = input("Город: ").strip() or "Москва"
geo = get("https://geocoding-api.open-meteo.com/v1/search?count=1&language=ru&name=" + urllib.parse.quote(city))
if not geo.get("results"):
    print("Город не найден")
else:
    p = geo["results"][0]
    w = get(f"https://api.open-meteo.com/v1/forecast?latitude={p['latitude']}&longitude={p['longitude']}"
            "&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto")["current"]
    print(f"{p['name']}: {w['temperature_2m']:+.0f}°, {CODES.get(w['weather_code'], 'осадки')}, ветер {w['wind_speed_10m']:.0f} км/ч")
'''

DISCORD_PY = '''import os

import discord  # pip install discord.py
from discord.ext import commands

# Токен бота: discord.com/developers → Applications → Bot. Храните его в переменной окружения.
TOKEN = os.environ.get("DISCORD_TOKEN", "")

intents = discord.Intents.default()
intents.message_content = True  # включите «Message Content Intent» в настройках бота
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен")


@bot.command(help="Поздороваться")
async def привет(ctx):
    await ctx.send(f"Привет, {ctx.author.display_name}!")


@bot.command(help="Сложить числа: !сумма 2 3 4")
async def сумма(ctx, *numbers: float):
    await ctx.send(f"Сумма: {sum(numbers):g}")


@bot.command(help="Бросить кубик")
async def кубик(ctx):
    import random
    await ctx.send(f"🎲 Выпало {random.randint(1, 6)}")


if not TOKEN:
    print("Задайте переменную окружения DISCORD_TOKEN")
else:
    bot.run(TOKEN)
'''

MULT = {
    "python": '''# Таблица умножения
n = int(input("До какого числа (например, 9): ") or 9)
print("    " + "".join(f"{j:4}" for j in range(1, n + 1)))
for i in range(1, n + 1):
    print(f"{i:3} " + "".join(f"{i * j:4}" for j in range(1, n + 1)))
''',
    "javascript": '''// Таблица умножения
const n = 9;
const pad = (x) => String(x).padStart(4);
console.log("    " + Array.from({length: n}, (_, j) => pad(j + 1)).join(""));
for (let i = 1; i <= n; i++) {
  console.log(String(i).padStart(3) + " " + Array.from({length: n}, (_, j) => pad(i * (j + 1))).join(""));
}
''',
    "cpp": '''// Таблица умножения
#include <iomanip>
#include <iostream>

int main() {
    int n = 9;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) std::cout << std::setw(4) << i * j;
        std::cout << "\\n";
    }
    return 0;
}
''',
}


def register(task):
    task("tetris", r"тетрис|tetris", "Тетрис", "классический тетрис: повороты, призрак фигуры, уровни, очки и следующая фигура. "
         "Работает с клавиатуры и с телефона.", html=TETRIS)
    task("pong", r"пинг.?понг|ping.?pong|\bpong\b|\bпонг", "Пинг-понг", "игра против компьютера до 7 очков: мышь, палец или клавиши.",
         html=PONG)
    task("breakout", r"арканоид|breakout|разбей кирпич", "Арканоид", "разбейте все кирпичи мячом: 3 жизни, ускорение мяча.",
         html=BREAKOUT)
    task("g2048", r"\b2048\b", "Игра 2048", "соединяйте плитки, свайпы и стрелки, рекорд сохраняется.", html=G2048)
    task("paint", r"рисовалк|paint|холст|рисовани|рисовать мышк|графическ\w* редактор", "Рисовалка",
         "холст с кистью, ластиком, отменой и сохранением в PNG. Рисовать можно пальцем.", html=PAINT)
    task("piano", r"пианино|piano|синтезатор|фортепиан", "Пианино", "клавиши с настоящим звуком (Web Audio): мышь, палец или клавиатура.",
         html=PIANO)
    task("memory", r"найди пару|мемори|memory|карточк\w* парам|игр\w* на память", "Игра «Найди пару»",
         "16 карточек, счётчик ходов и время.", html=MEMORY)
    task("gallery", r"галере|gallery|слайдер фото|фотоальбом", "Фотогалерея",
         "сетка фото с просмотром на весь экран, листанием и добавлением своих фотографий.", html=GALLERY)
    task("bmi", r"\bимт\b|индекс массы|bmi", "Калькулятор ИМТ", "считает индекс массы тела и подсказывает, в норме ли вес.",
         html=BMI_HTML, python=BMI_PY)
    task("currency_app", r"конвертер валют|валют\w* конвертер|курс\w* валют|обменник|currency", "Конвертер валют",
         "свежие курсы из open.er-api.com (бесплатно, без ключа), 17 валют.", html=CURRENCY_HTML, python=CURRENCY_PY)
    task("weather_app", r"погод|weather|прогноз", "Приложение погоды",
         "текущая погода и прогноз на неделю из Open-Meteo (бесплатно, без ключа) для любого города.", html=WEATHER_HTML, python=WEATHER_PY)
    task("discord", r"дискорд|discord", "Discord-бот", "бот с командами !привет, !сумма и !кубик. Установите: pip install discord.py.",
         python=DISCORD_PY)
    task("multiplication", r"таблиц\w* умножен", "Таблица умножения", "выводит таблицу умножения ровными столбцами.", **MULT)


ORDER_FIRST = ["tetris", "pong", "breakout", "g2048", "paint", "piano", "memory", "gallery", "bmi", "currency_app",
               "weather_app", "discord", "multiplication"]
