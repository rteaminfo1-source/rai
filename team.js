/* Команда моделей Rai: до 1000 моделей отвечают вместе и по-настоящему параллельно.

   Модель — движок Rai с выбранной версией (Pro, Fast, Plus, Sun, Quasar) и уровнем размышления (Low … Ultra).
   Поток — отдельный Web Worker со своим Python (Pyodide) и всеми знаниями Rai: потоки считают одновременно,
   на разных ядрах процессора. Модели стоят в очереди, свободный поток берёт следующую.

   Как выбирается ответ: похожие ответы объединяются в группы; модели, которые не нашли ответа, воздерживаются
   (тысяча «не знаю» не перевесит один настоящий ответ); голос весит больше у старших версий и уровней и у точных
   инструментов (калькулятор, функции, энциклопедия). Побеждает группа с наибольшим весом, рядом — доля согласных.

   Режимы: «Совет» — все решают один вопрос; «Конвейер» — каждая строка списка отдельная задача, модели делят
   задачи между собой (на каждую задачу — свой маленький совет).

   Работу видно в чате (живая карточка) и в отдельном окне: дорожки потоков во времени, плитки всех моделей,
   голосование, ответ любой модели и журнал. Если окно открыть нельзя — то же самое поверх чата. */
(function () {
  "use strict";

  const MAX = 1000;                    // больше моделей в команде не бывает
  const KEY = "rai_team_v1";           // настройки команды в браузере
  const IDLE_MS = 10 * 60 * 1000;      // потоки без работы 10 минут — закрываем, память компьютера не держим зря
  const JOB_LIMIT_MS = 90 * 1000;      // модель думает дольше полутора минут (зависла сеть) — перезапускаем поток
  const BOOT_LIMIT_MS = 120 * 1000;    // ни один поток не запустился за 2 минуты — работаем в основном движке
  const DIR = "/home/pyodide/rai";
  const CORES = Math.max(1, navigator.hardwareConcurrency || 4);
  const MEM = navigator.deviceMemory || 8;   // ГБ; браузер сообщает не больше 8
  const VER_SHORT = {"pro": "Pro", "pro-fast": "Fast", "pro-plus": "Plus", "pro-sun": "Sun", "pro-quasar": "Quasar"};
  // вес голоса: старшие версии и уровни думают глубже
  const W_LEVEL = {low: 0.9, medium: 1, high: 1.1, code: 1.05, extra: 1.15, ultra: 1.2};
  const W_VER = {"pro-fast": 0.9, "pro": 1, "pro-plus": 1.05, "pro-sun": 1.1, "pro-quasar": 1.15};
  // точные ответы: функции и калькулятор, энциклопедия, словарь, рассуждение Rai Разума, объяснения, код
  const SURE = /^(tool|skill|calc|encyclopedia|glossary|mind|explain|code|proglang|facts|weather|currency|translate|time|convert|capital)$/;
  // «не знаю» — модель воздерживается и не голосует против настоящего ответа
  const ABSTAIN = /не нашёл уверенного ответа|не хочу выдумывать|уверенного ответа[^.]{0,120}не наш|пока не знаю|не получилось (найти|получить|узнать|ответить)|нет связи с интернетом|не понял(а)? вопрос/i;
  // цвета групп ответов: 1-я (лидер) — розовая, дальше — фиолетовая, голубая, жёлтая, зелёная…
  const COLORS = ["#ff3d81", "#8b5cff", "#3cc8ff", "#ffd166", "#3ccf7a", "#ff8a3d", "#c084fc", "#7c8496"];
  const STATE_CODE = {skip: 0, queue: 0, run: 0, done: 1, abst: 2, err: 3};
  const STATE_OF = ["skip", "done", "abst", "err"];

  let page = null;        // связь со страницей чата (init)
  let boot = null;        // откуда брать Python и файлы Rai (setBoot)
  let S = load();
  let active = null;      // идущая работа команды
  let last = null;        // последняя работа — для окна наблюдения
  let mon = null;         // окно наблюдения (отдельное или поверх чата)
  let card = null;        // живая карточка в чате
  let ticker = 0;
  let runSeq = 0;
  const pool = {list: [], url: "", data: null, idleTimer: 0};

  // ---------------------------------------------------------------- настройки
  function load() {
    const def = {on: false, groups: [{n: 12, version: "*", level: "*"}], threads: 0, mode: "auto", ver: "*", lvl: "*"};
    try {
      const s = JSON.parse(localStorage.getItem(KEY) || "null");
      if (!s || !Array.isArray(s.groups)) return def;
      const groups = [];
      let left = MAX;
      for (const g of s.groups) {
        if (!g || typeof g.version !== "string" || typeof g.level !== "string") continue;
        const n = Math.min(left, Math.max(0, Math.floor(+g.n || 0)));
        if (n > 0) { groups.push({n: n, version: g.version, level: g.level}); left -= n; }
      }
      return {on: !!s.on, groups: groups, threads: Math.max(0, Math.floor(+s.threads || 0)),
              mode: ["auto", "council", "split"].includes(s.mode) ? s.mode : "auto",
              ver: typeof s.ver === "string" ? s.ver : "*", lvl: typeof s.lvl === "string" ? s.lvl : "*"};
    } catch (e) {
      return def;
    }
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* не сохранится — до перезагрузки */ } }
  function total() { return S.groups.reduce((a, g) => a + g.n, 0); }

  function versionIds() {
    const list = ((page && page.versions && page.versions()) || []).map((v) => v.id).filter(Boolean);
    return list.length ? list : [page ? page.chatVersion() : "pro"];
  }
  function levelIds() {
    const list = ((page && page.levels) || []).map((l) => l.id).filter((id) => !page.levelAllowed || page.levelAllowed(id));
    return list.length ? list : [page ? page.currentLevel() : "medium"];
  }
  function levelName(id) { const l = ((page && page.levels) || []).find((x) => x.id === id); return l ? l.name : id; }
  function cfgLabel(m) { return (VER_SHORT[m.version] || m.version || "?") + " · " + levelName(m.level); }
  function groupLabel(g) {
    const v = g.version === "*" ? "все версии по кругу" : g.version === "chat" ? "версия как в чате" : "Rai " + (VER_SHORT[g.version] || g.version);
    const l = g.level === "*" ? "все уровни по кругу" : g.level === "chat" ? "уровень как внизу чата" : levelName(g.level);
    return v + " · " + l;
  }

  // Список моделей команды: группа «все версии · все уровни» перебирает все сочетания по кругу
  function models() {
    const V = versionIds(), L = levelIds(), out = [];
    const chatV = page.chatVersion(), chatL = page.currentLevel();
    for (const g of S.groups) {
      for (let j = 0; j < g.n && out.length < MAX; j++) {
        const version = g.version === "*" ? V[j % V.length] : g.version === "chat" || !V.includes(g.version) ? chatV : g.version;
        const spin = g.version === "*" ? Math.floor(j / V.length) : j;
        let level = g.level === "*" ? L[spin % L.length] : g.level === "chat" ? chatL : g.level;
        if (!L.includes(level)) level = chatL;   // уровень не по тарифу — как выбрано внизу чата
        out.push({i: out.length, name: "Rai-" + (out.length + 1), version: version, level: level});
      }
    }
    return out;
  }

  // Сколько потоков: каждое ядро — один поток, но память не бесконечна (каждый поток — своя копия Rai)
  const isPhone = () => !!(page && page.device === "phone");
  function maxThreads() { return Math.max(1, Math.min(16, isPhone() ? 4 : CORES, Math.max(2, Math.floor(MEM * 1.5)))); }
  function autoThreads() { return Math.max(1, Math.min(isPhone() ? 2 : 6, CORES > 2 ? CORES - 1 : CORES, maxThreads())); }
  function threads() { return Math.max(1, Math.min(maxThreads(), S.threads || autoThreads())); }

  // «Конвейер»: пронумерованный список, пункты или несколько вопросов — по строке на задачу
  function splitTasks(text) {
    const lines = String(text || "").split(/\n+/).map((s) => s.trim()).filter(Boolean);
    if (lines.length < 2) return null;
    const item = /^(\d{1,4}[.)]|[-•*–—])\s+/;
    const marked = lines.filter((s) => item.test(s));
    if (marked.length >= 2 && marked.length >= lines.length - 1) {
      const list = marked.map((s) => s.replace(item, "").trim()).filter((s) => s.length > 1);
      return list.length >= 2 ? list.slice(0, MAX) : null;
    }
    if (lines.length >= 3 && lines.every((s) => s.length <= 300 && /[?？]$/.test(s))) return lines.slice(0, MAX);
    return null;
  }
  function tasksFor(text) {
    if (S.mode === "council") return [text];
    const list = splitTasks(text);
    if (S.mode === "split" && !list) {
      const lines = String(text).split(/\n+/).map((s) => s.trim()).filter(Boolean);
      return lines.length > 1 ? lines.slice(0, MAX) : [text];
    }
    return list || [text];
  }

  // ---------------------------------------------------------------- потоки: Web Worker с Python и знаниями Rai
  // Сообщения обрабатываются строго по очереди (chain): данные приходят, пока Python ещё загружается.
  const WORKER = `
let py = null, ask = null, fresh = null, share = null;
let chain = Promise.resolve();
self.onmessage = (e) => { chain = chain.then(() => handle(e.data || {})); };
async function handle(m) {
  if (m.type === "boot") {
    try {
      const t0 = performance.now();
      const mod = await import(m.base + "pyodide.mjs");
      const opts = {indexURL: m.base};
      if (m.stdlib) opts.stdLibURL = m.stdlib;
      py = await mod.loadPyodide(opts);
      py.FS.mkdirTree(m.dir);
      for (const [name, text] of m.files) py.FS.writeFile(m.dir + "/" + name, text);
      py.runPython(m.bridge);
      ask = py.globals.get("rai_ask");
      fresh = py.globals.get("rai_cache_new");
      share = py.globals.get("rai_cache_add");
      self.postMessage({type: "ready", ms: Math.round(performance.now() - t0)});
    } catch (err) {
      py = null;
      self.postMessage({type: "fail", error: String((err && err.message) || err).slice(0, 300)});
    }
    return;
  }
  if (!py) return;
  if (m.type === "data") {
    try { py.FS.writeFile(m.dir + "/" + m.name, m.text); py.runPython(m.code); }
    catch (err) { self.postMessage({type: "warn", error: m.name + ": " + String((err && err.message) || err).slice(0, 200)}); }
  } else if (m.type === "hello") {
    self.postMessage({type: "idle"});
  } else if (m.type === "cache") {
    try { share(m.json); } catch (err) { /* чужой кэш не подошёл — не страшно */ }
  } else if (m.type === "ask") {
    const t0 = performance.now();
    let data;
    try { data = JSON.parse(ask(m.version, m.message, m.session, m.history, m.profile, m.net)); }
    catch (err) { data = {answer: "", error: String((err && err.message) || err).slice(0, 300)}; }
    const ms = performance.now() - t0;
    let cache = null;
    try { const c = fresh(); if (c && c !== "[]") cache = c; } catch (err) { /* без обмена кэшем */ }
    self.postMessage({type: "done", id: m.id, data: data, ms: ms, cache: cache});
  }
}`;

  // Python внутри потока: тот же движок Rai, что и в чате. Найденное в интернете один поток отдаёт другим (кэш):
  // тысяча моделей не делает тысячу одинаковых запросов к сайту.
  const BRIDGE = [
    "import sys, json, time",
    "sys.path.insert(0, " + JSON.stringify(DIR) + ")",
    "import brain, versions, net",
    "_rai = brain.Brain(learned_path='/tmp/learned.json')",
    "_known = set(net._cache)",
    "",
    "def rai_ask(version_id, message, session_id, history_json, profile_json, net_json):",
    "    for k, v in json.loads(net_json or '{}').items():",
    "        if k in ('PROXY', 'SAME_ORIGIN', 'SANDBOX'):",
    "            setattr(net, k, v)",
    "    brain.PROFILE.clear()",
    "    brain.PROFILE.update({k: v for k, v in json.loads(profile_json or '{}').items()",
    "                          if k in ('name', 'region', 'level') and isinstance(v, str)})",
    "    v = versions.resolve(version_id)",
    "    if v is None:",
    "        return json.dumps({'answer': '', 'error': 'unknown_version'})",
    "    try:",
    "        return json.dumps(_rai.answer(v, message, session_id, json.loads(history_json or '[]')), ensure_ascii=False)",
    "    except brain.RaiError as e:",
    "        return json.dumps({'answer': str(e), 'error': 'rai_error'}, ensure_ascii=False)",
    "",
    "def rai_cache_new():",
    "    new = [k for k in list(net._cache) if k not in _known]",
    "    _known.update(new)",
    "    try:",
    "        return json.dumps([[k, net._cache[k][1]] for k in new], ensure_ascii=False)",
    "    except (TypeError, ValueError):",
    "        return '[]'",
    "",
    "def rai_cache_add(payload):",
    "    now = time.time()",
    "    for k, data in json.loads(payload or '[]'):",
    "        if k not in net._cache:",
    "            net._cache[k] = (now, data)",
    "            _known.add(k)",
  ].join("\n");

  function canThread() {
    return !!(boot && boot.base && boot.files && typeof Worker !== "undefined" && typeof Blob !== "undefined" && window.URL && URL.createObjectURL);
  }
  function workerUrl() {
    if (!pool.url) pool.url = URL.createObjectURL(new Blob([WORKER], {type: "text/javascript"}));
    return pool.url;
  }
  // Знания для потоков (энциклопедия, лекарства, глубокие знания, выученное) — читаем один раз на все потоки
  function dataOnce() {
    if (!pool.data) pool.data = Promise.resolve(boot.data ? boot.data() : {}).catch(() => ({}));
    return pool.data;
  }
  const pyStr = (s) => JSON.stringify(s);

  function spawn(n) {
    const w = {n: n, state: "boot", label: "запускаю Python…", job: null, run: null, done: 0, since: performance.now(), jobAt: 0, worker: null};
    try {
      w.worker = new Worker(workerUrl(), {type: "module", name: "Rai — поток " + n});
    } catch (e) {
      w.state = "dead";
      w.label = "браузер не дал создать поток";
      return w;
    }
    w.worker.onmessage = (e) => onMessage(w, e.data || {});
    w.worker.onerror = (e) => { if (e && e.preventDefault) e.preventDefault(); lost(w, (e && e.message) || "сбой потока", false); };
    w.worker.postMessage({type: "boot", base: boot.base, stdlib: boot.stdlib || null, dir: DIR, files: boot.files, bridge: BRIDGE});
    dataOnce().then((d) => {
      if (w.state === "dead") return;
      const send = (name, text, code) => { if (text) w.worker.postMessage({type: "data", dir: DIR, name: name, text: text, code: code}); };
      send("encyclopedia.json", d.kb, "import encyclopedia\nencyclopedia.load()");
      send("medicines.json", d.meds, "import json, meds\nmeds.load(json.load(open(" + pyStr(DIR + "/medicines.json") + ", encoding='utf-8')))");
      if (d.deep && d.deep.text) {
        send("deep_manifest.json", d.deep.text, "import deep\ndeep.URL = " + pyStr(d.deep.base) + "\ndeep.MAX_PARTS = 3\n" +
          "deep.load_manifest(open(" + pyStr(DIR + "/deep_manifest.json") + ", encoding='utf-8').read())");
      }
      if (d.learned) {
        send("learned_boot.json", JSON.stringify(d.learned), "import json, learning\nlearning.load(json.load(open(" +
          pyStr(DIR + "/learned_boot.json") + ", encoding='utf-8')))");
      }
      w.worker.postMessage({type: "hello"});
    });
    return w;
  }

  function onMessage(w, m) {
    if (w.state === "dead") return;
    if (m.type === "ready") { w.label = "загружаю знания Rai…"; w.bootMs = m.ms; return; }
    if (m.type === "idle") {
      w.state = "idle";
      w.label = "свободен";
      note(active, "Поток " + w.n + " готов за " + secs(performance.now() - w.since));
      pump();
      return;
    }
    if (m.type === "warn") { console.warn("Rai, команда:", m.error); return; }
    if (m.type === "fail") { lost(w, m.error || "Python не запустился", false); return; }
    if (m.type === "done") {
      const run = w.run, job = w.job;
      w.job = null;
      w.run = null;
      w.state = "idle";
      w.label = "свободен";
      w.done++;
      if (m.cache) for (const o of pool.list) if (o !== w && o.state !== "dead" && o.worker) o.worker.postMessage({type: "cache", json: m.cache});
      if (run && job && run === active && job.state === "run") finishJob(run, job, m.data, m.ms);
      pump();
    }
  }

  // Поток упал или завис: его задачу берёт другой поток (вторая неудача — ошибка у этой модели)
  function lost(w, why, respawn) {
    if (w.state === "dead") return;
    const job = w.job, run = w.run;
    w.state = "dead";
    w.label = String(why || "сбой").slice(0, 120);
    w.job = null;
    w.run = null;
    try { if (w.worker) w.worker.terminate(); } catch (e) { /* уже закрыт */ }
    if (run && job && job.state === "run" && run === active) {
      job.tries = (job.tries || 0) + 1;
      if (job.tries >= 2) {
        finishJob(run, job, {answer: "", error: why}, performance.now() - run.start - job.t0);
      } else {
        job.state = "queue";
        job.thread = -1;
        job.t0 = null;
        run.queue.unshift(job);
      }
    }
    note(run || active, "Поток " + w.n + ": " + w.label);
    if (respawn) {
      const k = pool.list.indexOf(w);
      if (k >= 0) pool.list[k] = spawn(w.n);
    }
    pump();
  }

  function ensurePool(n) {
    clearTimeout(pool.idleTimer);
    pool.list = pool.list.filter((w) => w.state !== "dead");
    while (pool.list.length > n) {
      const k = pool.list.findIndex((w) => w.state !== "busy");
      const w = pool.list.splice(k >= 0 ? k : pool.list.length - 1, 1)[0];
      try { w.worker.terminate(); } catch (e) { /* уже закрыт */ }
    }
    pool.list.forEach((w, k) => { w.n = k + 1; });
    while (pool.list.length < n) pool.list.push(spawn(pool.list.length + 1));
  }
  function shutdown() {
    if (active) return;
    for (const w of pool.list) { try { w.worker.terminate(); } catch (e) { /* уже закрыт */ } }
    pool.list = [];
    pool.data = null;   // знания из памяти — тоже
    renderDialog();
  }

  // ---------------------------------------------------------------- работа команды: очередь, потоки, голоса
  function plan(run) {
    const T = run.tasks.length, M = run.models.length;
    if (T <= M) {
      for (let j = 0; j < M; j++) run.jobs.push({id: j, m: j, task: j % T, state: "queue", thread: -1, t0: null, t1: null, ms: 0, cluster: -1});
    } else {
      for (let t = 0; t < T; t++) run.jobs.push({id: t, m: t % M, task: t, state: "queue", thread: -1, t0: null, t1: null, ms: 0, cluster: -1});
    }
    for (const j of run.jobs) run.tasks[j.task].total++;
    run.queue = run.jobs.slice();
  }

  function pump() {
    const run = active;
    if (!run) return;
    if (!run.stopped && !run.fallback) {
      const net = JSON.stringify(boot && boot.net ? boot.net() : {});
      for (const w of pool.list) {
        if (w.state !== "idle") continue;
        const job = run.queue.shift();
        if (!job) break;
        startJob(run, job, w.n - 1);
        w.state = "busy";
        w.job = job;
        w.run = run;
        w.jobAt = performance.now();
        const m = run.models[job.m];
        w.worker.postMessage({type: "ask", id: job.id, version: m.version, message: run.tasks[job.task].q,
          session: run.session + "-" + m.i, history: run.historyJson,
          profile: JSON.stringify(Object.assign({}, run.profile, {level: m.level})), net: net});
      }
      if (run.queue.length && pool.list.length && pool.list.every((w) => w.state === "dead")) startFallback(run, "потоки не запустились");
    }
    if (run.stopped || (!run.queue.length && !run.jobs.some((j) => j.state === "run"))) finishRun(run);
  }

  function startJob(run, job, lane) {
    job.state = "run";
    job.thread = lane;
    job.t0 = performance.now() - run.start;
    if (run.first == null) run.first = job.t0;
  }

  function judge(m, data) {
    const text = String((data && data.answer) || "").trim();
    if (!text || (data && data.error && data.error !== "rai_error")) return {kind: "err", w: 0};
    const intents = [].concat((data && data.intent) || []).filter(Boolean);
    const sure = intents.some((i) => SURE.test(i));
    if (!sure && ABSTAIN.test(text.slice(0, 400))) return {kind: "abst", w: 0};
    let w = (W_LEVEL[m.level] || 1) * (W_VER[m.version] || 1);
    if (sure) w *= 1.25;
    else if (intents.includes("mind_draft")) w *= 0.85;
    return {kind: "ok", w: w};
  }

  // Похожие ответы — одна группа: одинаковый текст или общие слова (Жаккар ≥ 0,6)
  function normText(s) {
    return String(s || "").toLowerCase().replace(/ё/g, "е").replace(/https?:\/\/\S+/g, " ")
      .replace(/[^0-9a-zа-я%.,=+\-\s]/g, " ").replace(/\s+/g, " ").trim().slice(0, 700);
  }
  function wordSet(key) { return new Set(key.split(" ").filter((w) => w.length > 2 || /\d/.test(w))); }
  function similar(a, b) {
    if (!a.size || !b.size) return 0;
    let both = 0;
    for (const w of a) if (b.has(w)) both++;
    return both / (a.size + b.size - both);
  }
  function place(task, job, data, w, m) {
    const text = String(data.answer || "");
    const key = normText(text);
    let c = task.byKey.get(key);
    if (!c) {
      const ws = wordSet(key);
      for (let k = 0; k < task.clusters.length && k < 300; k++) {
        if (similar(ws, task.clusters[k].ws) >= 0.6) { c = task.clusters[k]; break; }
      }
      if (!c) {
        c = {i: task.clusters.length, n: 0, s: 0, best: -1, text: text, data: null, by: null, ws: ws};
        task.clusters.push(c);
      }
      task.byKey.set(key, c);
    }
    c.n++;
    c.s += w;
    if (w > c.best || (w === c.best && text.length > c.text.length)) { c.best = w; c.text = text; c.data = data; c.by = m; }
    job.cluster = c.i;
  }
  function leader(task) { return task.clusters.reduce((a, c) => (!a || c.s > a.s ? c : a), null); }

  function finishJob(run, job, data, ms) {
    job.t1 = performance.now() - run.start;
    job.ms = Math.max(0, ms || 0);
    run.work += job.ms;
    run.lastEnd = Math.max(run.lastEnd || 0, job.t1);
    const m = run.models[job.m], task = run.tasks[job.task];
    const j = judge(m, data || {});
    job.answer = String((data && (data.answer || data.error)) || "").slice(0, 6000);
    job.intent = [].concat((data && data.intent) || []).filter(Boolean).join(", ");
    if (j.kind === "err") { job.state = "err"; task.err++; }
    else if (j.kind === "abst") { job.state = "abst"; task.abst++; if (!task.abstData) task.abstData = data; }
    else { job.state = "done"; place(task, job, data, j.w, m); }
    task.done++;
    note(run, m.name + " (" + cfgLabel(m) + ") → " + (job.state === "done" ? "ответ" : job.state === "abst" ? "воздержалась" : "ошибка") +
      " за " + secs(job.ms) + ", поток " + (job.thread + 1) + (run.tasks.length > 1 ? ", задача " + (job.task + 1) : ""));
  }

  // Потоки браузера недоступны: те же модели по очереди в основном движке (или параллельными запросами к серверу Rai)
  function startFallback(run, why) {
    if (run.fallback) return;
    run.fallback = true;
    Promise.resolve(page.engine ? page.engine() : null).catch(() => null).then((eng) => {
      const lanes = eng && eng.mode === "server" ? Math.min(threads(), 6) : 1;
      run.vlanes = Array.from({length: lanes}, (_, k) => ({n: k + 1, state: "idle", label: "свободен", done: 0, job: null, run: null, jobAt: 0}));
      note(run, (why ? why + ": " : "") + (lanes > 1 ? lanes + " запросов к серверу Rai одновременно" : "модели работают по очереди в основном движке Rai"));
      for (const ln of run.vlanes) {
        (async () => {
          while (!run.stopped && !run.finished && run.queue.length) {
            const job = run.queue.shift();
            startJob(run, job, ln.n - 1);
            ln.state = "busy"; ln.job = job; ln.run = run; ln.jobAt = performance.now();
            const m = run.models[job.m], t = performance.now();
            let data;
            try { data = await page.ask(m.version, run.tasks[job.task].q, run.session + "-" + m.i, run.history, m.level); }
            catch (e) { data = {answer: "", error: String((e && e.message) || e)}; }
            ln.state = "idle"; ln.job = null; ln.run = null; ln.done++;
            if (job.state === "run" && run === active) finishJob(run, job, data, performance.now() - t);
            await new Promise((r) => setTimeout(r, 0));   // дать странице перерисоваться
          }
          pump();
        })();
      }
    });
  }

  function finishRun(run) {
    if (run.finished) return;
    run.finished = true;
    run.live = false;
    run.end = performance.now() - run.start;
    for (const j of run.jobs) if (j.state === "queue" || j.state === "run") j.state = "skip";
    run.queue = [];
    note(run, run.stopped ? "Остановлено — голосуют модели, которые успели ответить" : "Готово: " + run.jobs.length + " " +
      plural(run.jobs.length, "ответ", "ответа", "ответов") + " за " + secs(run.end));
    if (active === run) active = null;
    clearTimeout(pool.idleTimer);
    pool.idleTimer = setTimeout(shutdown, IDLE_MS);
    if (run.resolve) run.resolve();
  }
  function stop(run) {
    if (!run || run.finished) return;
    run.stopped = true;
    finishRun(run);
  }

  // Ответ команды для чата: живая карточка в пузыре, потом — ответ-победитель и отчёт о работе
  function answer(opts) {
    const ms = models();
    if (!ms.length) ms.push({i: 0, name: "Rai-1", version: page.chatVersion(), level: page.currentLevel()});
    const tasks = tasksFor(opts.text);
    const run = {id: ++runSeq, question: String(opts.text || ""), models: ms, jobs: [], queue: [], live: true,
                 tasks: tasks.map((q) => ({q: q, clusters: [], byKey: new Map(), abst: 0, err: 0, done: 0, total: 0, abstData: null})),
                 start: performance.now(), first: null, lastEnd: 0, work: 0, log: [], logSeq: 0, stopped: false, finished: false, fallback: false,
                 session: "team-" + (opts.chatId || "chat"), history: opts.history || [], historyJson: JSON.stringify(opts.history || []),
                 profile: (page.profile && page.profile()) || {}};
    run.mode = run.tasks.length > 1 ? "split" : "council";
    plan(run);
    active = last = run;
    note(run, "Команда: " + ms.length + " " + plural(ms.length, "модель", "модели", "моделей") +
      (run.tasks.length > 1 ? ", " + run.tasks.length + " " + plural(run.tasks.length, "задача", "задачи", "задач") : "") +
      ", потоков: " + (canThread() ? threads() : 1));
    return new Promise((resolve) => {
      run.resolve = resolve;
      card = liveCard(opts.host, run);
      if (mon && mon.alive()) mon.attach(run);
      ensureTicker();
      if (canThread()) {
        ensurePool(threads());
        pump();
        setTimeout(() => {   // ни один поток так и не запустился — работаем в основном движке
          if (run === active && !run.fallback && !pool.list.some((w) => w.state === "idle" || w.state === "busy")) {
            for (const w of pool.list) if (w.state === "boot") lost(w, "слишком долгий запуск", false);
            startFallback(run, "потоки не успели запуститься");
          }
        }, BOOT_LIMIT_MS);
      } else {
        startFallback(run, boot ? "потоки браузера недоступны" : "движок Rai работает на сервере");
      }
    }).then(() => compose(run));
  }

  function compose(run) {
    const attachments = [];
    let text, win = null;
    if (run.tasks.length === 1) {
      const t = run.tasks[0];
      win = leader(t);
      if (win) {
        text = win.text;
        for (const a of (win.data && win.data.attachments) || []) attachments.push(a);
      } else {
        text = (t.abstData && t.abstData.answer) ||
          (run.stopped ? "Команду остановили раньше, чем модели успели ответить." : "Команда не смогла ответить: модели не нашли ответа. Попробуйте спросить иначе.");
      }
    } else {
      text = run.tasks.map((t, k) => {
        const best = leader(t), voters = t.clusters.reduce((a, c) => a + c.n, 0);
        const body = best ? best.text : (t.abstData && t.abstData.answer) || "_Нет ответа — модели не успели или не нашли._";
        const agree = best && voters > 1 ? "\n\n*Согласны " + best.n + " из " + voters + " " + plural(voters, "модели", "моделей", "моделей") + "*" : "";
        // «*» и «`» в самой задаче («2+2*2») сломали бы жирный заголовок — заменяем похожими значками
        return "**" + (k + 1) + ". " + t.q.replace(/\*/g, "∗").replace(/`/g, "ʹ") + "**\n\n" + body + agree;
      }).join("\n\n---\n\n");
    }
    const sum = summary(run);
    attachments.push(sum);
    return {text: text, attachments: attachments, data: win ? win.data : null,
            meta: "Команда Rai · " + sum.models + " " + plural(sum.models, "модель", "модели", "моделей") + " · " + sum.threads + " " +
              plural(sum.threads, "поток", "потока", "потоков") + " · " + secs(sum.ms)};
  }

  // Короткий отчёт — хранится в сообщении чата: по нему окно наблюдения показывает работу и после перезагрузки
  function summary(run) {
    const cfg = [], cfgIdx = new Map();
    const mc = run.models.map((m) => {
      const k = m.version + "|" + m.level;
      if (!cfgIdx.has(k)) { cfgIdx.set(k, cfg.length); cfg.push([m.version, m.level]); }
      return cfgIdx.get(k);
    });
    const ranks = [];
    const tasks = run.tasks.map((t) => {
      const sorted = t.clusters.slice().sort((a, b) => b.s - a.s);
      const top = sorted.slice(0, 6);
      ranks.push(new Map(top.map((c, k) => [c.i, k])));
      return {q: t.q.slice(0, 300), total: t.total, done: t.done, abst: t.abst, err: t.err,
              voters: sorted.reduce((a, c) => a + c.n, 0), score: round1(sorted.reduce((a, c) => a + c.s, 0)), groups: sorted.length,
              clusters: top.map((c) => ({n: c.n, s: round1(c.s), t: c.text.slice(0, 1500), by: c.by ? c.by.name + " · " + cfgLabel(c.by) : ""}))};
    });
    const jobs = run.jobs.map((j) => {
      const r = j.state === "done" ? ranks[j.task].get(j.cluster) : -1;
      return [j.m, j.task, j.thread, j.t0 == null ? -1 : Math.round(j.t0), j.t1 == null ? -1 : Math.round(j.t1), r == null ? 6 : r, STATE_CODE[j.state] || 0];
    });
    const used = new Set(run.jobs.filter((j) => j.thread >= 0 && j.t1 != null).map((j) => j.thread));
    return {type: "team", v: 1, q: run.question.slice(0, 300), mode: run.mode, models: run.models.length, threads: Math.max(1, used.size),
            ms: Math.round(run.end || 0), work: Math.round(run.work), first: Math.round(run.first || 0), lastEnd: Math.round(run.lastEnd || 0),
            fallback: !!run.fallback, stopped: !!run.stopped, cfg: cfg, mc: mc, tasks: tasks, jobs: jobs};
  }

  // Отчёт из сообщения → то же представление, что у идущей работы (для окна наблюдения)
  function fromSummary(a) {
    const cfg = a.cfg || [];
    const models = (a.mc || []).map((k, i) => ({i: i, name: "Rai-" + (i + 1), version: (cfg[k] || [])[0], level: (cfg[k] || [])[1]}));
    const tasks = (a.tasks || []).map((t) => ({q: t.q, abst: t.abst, err: t.err, done: t.done, total: t.total, others: Math.max(0, (t.groups || 0) - (t.clusters || []).length),
      clusters: (t.clusters || []).map((c, i) => ({i: i, n: c.n, s: c.s, text: c.t, by: c.by}))}));
    const jobs = (a.jobs || []).map((j, id) => ({id: id, m: j[0], task: j[1], thread: j[2], t0: j[3] < 0 ? null : j[3], t1: j[4] < 0 ? null : j[4],
      cluster: j[5], state: STATE_OF[j[6]] || "skip", ms: j[3] >= 0 && j[4] >= 0 ? j[4] - j[3] : 0}));
    return {saved: true, question: a.q || "", mode: a.mode, models: models, tasks: tasks, jobs: jobs, live: false, stopped: !!a.stopped,
            fallback: !!a.fallback, start: 0, end: a.ms || 0, first: a.first || 0, lastEnd: a.lastEnd || a.ms || 0, work: a.work || 0,
            lanes: Math.max(1, a.threads || 1, jobs.reduce((x, j) => Math.max(x, j.thread + 1), 0)), log: [], logSeq: 0};
  }

  // ---------------------------------------------------------------- общие мелочи
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[c]);
  }
  function plural(n, one, few, many) {
    const a = Math.abs(n) % 100, b = a % 10;
    return a > 10 && a < 20 ? many : b === 1 ? one : b >= 2 && b <= 4 ? few : many;
  }
  function secs(ms) {
    ms = Math.max(0, ms || 0);
    if (ms < 1000) return Math.round(ms) + " мс";
    if (ms < 60000) return (ms / 1000).toFixed(1).replace(".", ",") + " с";
    return Math.floor(ms / 60000) + " мин " + Math.round((ms % 60000) / 1000) + " с";
  }
  const round1 = (x) => Math.round(x * 10) / 10;
  const num = (x) => String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  function plain(md) {
    return String(md || "").replace(/```[\s\S]*?```/g, " [код] ").replace(/!\[[^\]]*\]\([^)]*\)/g, " ").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/[*_`#>|]/g, "").replace(/\s+/g, " ").trim();
  }
  function md(text) {
    try { if (page && page.md) return page.md(text); } catch (e) { /* ниже — простой текст */ }
    return esc(text).replace(/\n/g, "<br>");
  }
  function note(run, text) {
    if (!run) return;
    const d = new Date();
    const t = String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0") + ":" + String(d.getSeconds()).padStart(2, "0") +
      "." + String(d.getMilliseconds()).padStart(3, "0");
    run.log.push({k: ++run.logSeq, t: t, text: text});
    if (run.log.length > 400) run.log.splice(0, run.log.length - 300);
  }

  // Сводка для карточки и окна: сколько готово, сколько думают, скорость и выигрыш от параллельности
  function lanesOf(vm) {
    if (vm.saved) return [];
    const list = vm.fallback ? (vm.vlanes || []) : pool.list;
    const now = performance.now();
    return list.map((w) => {
      if (w.state === "busy" && w.job && w.run === vm) {
        const m = vm.models[w.job.m];
        return {n: w.n, state: "busy", text: m.name + " · " + cfgLabel(m) + (vm.tasks.length > 1 ? " · задача " + (w.job.task + 1) : ""), ms: now - w.jobAt, done: w.done};
      }
      if (w.state === "busy") return {n: w.n, state: "busy", text: "заканчивает прошлую работу", ms: now - w.jobAt, done: w.done};
      return {n: w.n, state: w.state, text: w.label, ms: 0, done: w.done};
    });
  }
  function stats(vm) {
    let ok = 0, abst = 0, err = 0, running = 0, queue = 0, skip = 0, work = 0;
    for (const j of vm.jobs) {
      if (j.state === "done") ok++;
      else if (j.state === "abst") abst++;
      else if (j.state === "err") err++;
      else if (j.state === "run") running++;
      else if (j.state === "queue") queue++;
      else skip++;
      if (j.ms) work += j.ms;
    }
    const elapsed = vm.live ? performance.now() - vm.start : vm.end;
    const span = (vm.live ? elapsed : vm.lastEnd || vm.end) - (vm.first || 0);
    const done = ok + abst + err;
    const lanes = lanesOf(vm);
    return {total: vm.jobs.length, done: done, ok: ok, abst: abst, err: err, running: running, queue: queue, skip: skip, elapsed: elapsed,
            speed: done / Math.max(elapsed / 1000, 0.001), boost: span > 50 && work > 0 ? work / span : 1, lanes: lanes,
            lanesUp: vm.saved ? vm.lanes : lanes.filter((l) => l.state === "idle" || l.state === "busy").length,
            lanesAll: vm.saved ? vm.lanes : lanes.length};
  }
  // Место группы ответов по весу голосов (0 — лидер): им окрашены плитки и полоски
  function rankMaps(vm) {
    return vm.tasks.map((t) => new Map(t.clusters.slice().sort((a, b) => b.s - a.s).map((c, k) => [c.i, k])));
  }
  function jobColor(j, maps, pulse) {
    if (j.state === "run") return "rgba(255, 209, 102, " + pulse.toFixed(2) + ")";
    if (j.state === "done") {
      const m = maps[j.task], r = m ? m.get(j.cluster) : null;
      return COLORS[r == null ? COLORS.length - 1 : Math.min(r, COLORS.length - 1)];
    }
    if (j.state === "abst") return "#4b4b5a";
    if (j.state === "err") return "#ff4d4d";
    if (j.state === "skip") return "rgba(255, 255, 255, .04)";
    return "rgba(255, 255, 255, .1)";
  }
  function stateText(j) {
    return ({queue: "ждёт поток", run: "думает", done: "ответила", abst: "воздержалась (не нашла ответа)", err: "ошибка", skip: "не успела — остановлено"})[j.state] || j.state;
  }

  // Плитки всех моделей на холсте (в карточке чата — быстро даже для тысячи)
  function drawTiles(cv, vm, maps) {
    const win = cv.ownerDocument.defaultView || window, dpr = win.devicePixelRatio || 1;
    const W = Math.max(120, cv.clientWidth || 480), n = vm.jobs.length;
    const s = n > 600 ? 6 : n > 250 ? 8 : n > 80 ? 11 : 15, g = 2;
    const cols = Math.max(1, Math.floor((W + g) / (s + g))), rows = Math.ceil(n / cols), H = Math.max(s, rows * (s + g) - g);
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) {
      cv.width = Math.round(W * dpr);
      cv.height = Math.round(H * dpr);
      cv.style.height = H + "px";
    }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const pulse = 0.55 + 0.45 * Math.sin(performance.now() / 150);
    for (let k = 0; k < n; k++) {
      ctx.fillStyle = jobColor(vm.jobs[k], maps, pulse);
      ctx.fillRect((k % cols) * (s + g), Math.floor(k / cols) * (s + g), s, s);
    }
  }

  // Дорожки потоков во времени: каждая полоска — одна модель, длина — сколько она думала
  function niceStep(x) {
    for (const s of [50, 100, 200, 250, 500, 1000, 2000, 5000, 10000, 15000, 30000, 60000, 120000, 300000, 600000]) if (s >= x) return s;
    return 1200000;
  }
  function drawGantt(cv, vm, lanes, maps) {
    const win = cv.ownerDocument.defaultView || window, dpr = win.devicePixelRatio || 1;
    const W = Math.max(240, cv.clientWidth || 800), LH = lanes > 12 ? 13 : lanes > 6 ? 18 : 24, top = 4, H = top + lanes * (LH + 3) + 20;
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) {
      cv.width = Math.round(W * dpr);
      cv.height = Math.round(H * dpr);
      cv.style.height = H + "px";
    }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const now = vm.live ? performance.now() - vm.start : vm.end;
    const T = Math.max(1000, now) * 1.02, X = 46, span = W - X - 8;
    ctx.font = "11px ui-monospace, Consolas, monospace";
    ctx.textBaseline = "middle";
    for (let l = 0; l < lanes; l++) {
      const y = top + l * (LH + 3);
      ctx.fillStyle = l % 2 ? "rgba(255, 255, 255, .03)" : "rgba(255, 255, 255, .055)";
      ctx.fillRect(X, y, span, LH);
      ctx.fillStyle = "#a1a1b0";
      ctx.fillText("П" + (l + 1), 6, y + LH / 2);
    }
    const pulse = 0.55 + 0.45 * Math.sin(performance.now() / 150);
    for (const j of vm.jobs) {
      if (j.thread == null || j.thread < 0 || j.t0 == null) continue;
      const l = Math.min(j.thread, lanes - 1), y = top + l * (LH + 3);
      const t1 = j.state === "run" || j.t1 == null ? now : j.t1;
      const x0 = X + (j.t0 / T) * span, x1 = X + (t1 / T) * span;
      ctx.fillStyle = jobColor(j, maps, pulse);
      ctx.fillRect(x0, y + 2, Math.max(1.5, x1 - x0 - 0.6), LH - 4);
    }
    const step = niceStep(T / 8);
    ctx.fillStyle = "#a1a1b0";
    for (let t = 0; t <= T; t += step) {
      const x = X + (t / T) * span;
      ctx.fillRect(x, H - 17, 1, 5);
      ctx.fillText(t >= 1000 ? (t / 1000).toFixed(t % 1000 ? 1 : 0).replace(".", ",") + " с" : t + " мс", x + 3, H - 8);
    }
    if (vm.live) {
      const x = X + (now / T) * span;
      ctx.fillStyle = "rgba(255, 61, 129, .8)";
      ctx.fillRect(x, top, 1.5, lanes * (LH + 3));
    }
  }

  // ---------------------------------------------------------------- живая карточка в чате
  function liveCard(host, run) {
    if (!host) return null;
    host.innerHTML = "";
    const msg = host.closest(".msg");
    if (msg) msg.classList.add("team-run");   // пузырь «Rai пишет…» — во всю ширину под карточку
    const el = document.createElement("div");
    el.className = "team-live";
    el.innerHTML = `<div class="tl-top"><b>👥 Команда Rai</b><span class="tl-sub"></span><span class="tl-time"></span></div>` +
      `<div class="tl-bar"><i></i></div><div class="tl-stat"></div><div class="tl-lanes"></div>` +
      `<canvas class="tl-tiles" aria-hidden="true"></canvas><div class="tl-lead"></div>` +
      `<div class="tl-acts"><button type="button" class="tl-btn watch">🔭 Смотреть в отдельном окне</button>` +
      `<button type="button" class="tl-btn stop">■ Остановить</button></div>`;
    host.append(el);
    el.querySelector(".watch").addEventListener("click", () => openMonitor(run));
    el.querySelector(".stop").addEventListener("click", () => stop(run));
    const q = (s) => el.querySelector(s);
    let laneRows = [];
    return {
      el: el, run: run,
      paint() {
        const st = stats(run), maps = rankMaps(run);
        q(".tl-sub").textContent = " · " + run.models.length + " " + plural(run.models.length, "модель", "модели", "моделей") +
          (run.tasks.length > 1 ? " · " + run.tasks.length + " " + plural(run.tasks.length, "задача", "задачи", "задач") : "") +
          " · " + (run.fallback ? (run.vlanes || []).length || 1 : st.lanesUp + " из " + st.lanesAll) + " " + plural(st.lanesAll || 1, "поток", "потока", "потоков");
        q(".tl-time").textContent = secs(st.elapsed);
        q(".tl-bar i").style.width = (st.total ? (st.done / st.total) * 100 : 0).toFixed(1) + "%";
        q(".tl-stat").textContent = "готово " + num(st.done) + " из " + num(st.total) + " · думают " + st.running + " · в очереди " + num(st.queue) +
          (st.done ? " · " + st.speed.toFixed(st.speed < 10 ? 1 : 0).replace(".", ",") + " отв/с" : "") +
          (st.boost >= 1.15 ? " · ×" + st.boost.toFixed(1).replace(".", ",") + " быстрее, чем по очереди" : "");
        const lanes = st.lanes.slice(0, 8);
        if (laneRows.length !== lanes.length) {
          q(".tl-lanes").innerHTML = lanes.map(() => `<div class="tl-lane"><b></b><i class="dot"></i><span></span><em></em></div>`).join("") +
            (st.lanes.length > 8 ? `<div class="tl-lane more">и ещё ${st.lanes.length - 8} ${plural(st.lanes.length - 8, "поток", "потока", "потоков")} — в отдельном окне</div>` : "");
          laneRows = Array.from(q(".tl-lanes").querySelectorAll(".tl-lane:not(.more)"));
        }
        lanes.forEach((l, k) => {
          const row = laneRows[k];
          row.children[0].textContent = "Поток " + l.n;
          row.children[1].className = "dot " + l.state;
          row.children[2].textContent = l.text;
          row.children[3].textContent = l.state === "busy" ? secs(l.ms) : l.done ? "сделал " + l.done : "";
        });
        drawTiles(q(".tl-tiles"), run, maps);
        let lead = "";
        if (run.tasks.length === 1) {
          const t = run.tasks[0], best = leader(t), voters = t.clusters.reduce((a, c) => a + c.n, 0);
          if (best) lead = `<b>Лидирует</b> (${best.n} из ${voters}): ${esc(plain(best.text).slice(0, 160))}${plain(best.text).length > 160 ? "…" : ""}`;
          else if (t.abst) lead = "Пока модели не нашли ответа — ждём остальных…";
        } else {
          const ready = run.tasks.filter((t) => t.done >= t.total).length;
          lead = `<b>Задачи:</b> готово ${ready} из ${run.tasks.length}`;
        }
        q(".tl-lead").innerHTML = lead;
      }
    };
  }

  // Отчёт в сообщении (после ответа): итог голосования и кнопка «Открыть в окне»
  function renderSummary(a) {
    const box = document.createElement("details");
    box.className = "team-sum";
    const vm = fromSummary(a);
    const t0 = vm.tasks[0] || {clusters: []};
    const voters = t0.clusters.reduce((x, c) => x + c.n, 0);
    const best = t0.clusters[0];
    const boost = a.lastEnd - a.first > 50 && a.work ? a.work / (a.lastEnd - a.first) : 1;
    const agree = vm.tasks.length === 1 && best && a.tasks[0].voters ? Math.round((best.n / a.tasks[0].voters) * 100) : null;
    box.innerHTML = `<summary><span class="ts-ic">👥</span><b>Команда Rai</b> · ${a.models} ${plural(a.models, "модель", "модели", "моделей")} · ` +
      `${a.threads} ${plural(a.threads, "поток", "потока", "потоков")} · ${secs(a.ms)}` +
      (boost >= 1.15 ? ` · ×${boost.toFixed(1).replace(".", ",")} быстрее` : "") + (agree != null ? ` · согласие ${agree}%` : "") +
      (a.stopped ? " · остановлено" : "") + `</summary><div class="ts-body"></div>`;
    const body = box.querySelector(".ts-body");
    if (vm.tasks.length === 1) {
      const all = a.tasks[0].score || 1;
      body.innerHTML = t0.clusters.map((c, k) => `<div class="ts-vote"><i style="background:${COLORS[Math.min(k, COLORS.length - 1)]}"></i>` +
        `<span class="ts-n">${c.n} ${plural(c.n, "модель", "модели", "моделей")} · ${Math.round((c.s / all) * 100)}%</span>` +
        `<span class="ts-t">${esc(plain(c.text).slice(0, 180))}${plain(c.text).length > 180 ? "…" : ""}</span></div>`).join("") +
        (voters ? "" : `<p class="ts-meta">Ни одна модель не нашла уверенного ответа.</p>`);
    } else {
      body.innerHTML = vm.tasks.map((t, k) => {
        const b = t.clusters[0], v = t.clusters.reduce((x, c) => x + c.n, 0);
        return `<div class="ts-vote"><i style="background:${COLORS[0]}"></i><span class="ts-n">${k + 1}. ${esc(t.q.slice(0, 70))}</span>` +
          `<span class="ts-t">${b ? "согласны " + b.n + " из " + v : "нет ответа"}</span></div>`;
      }).join("");
    }
    const tasks = a.tasks || [];
    const abst = tasks.reduce((x, t) => x + (t.abst || 0), 0), err = tasks.reduce((x, t) => x + (t.err || 0), 0);
    const meta = document.createElement("p");
    meta.className = "ts-meta";
    meta.textContent = "Ответили " + num(tasks.reduce((x, t) => x + (t.voters || 0), 0)) + " · воздержались " + num(abst) + (err ? " · ошибок " + err : "") +
      " · модели думали в сумме " + secs(a.work) + (a.fallback ? " · без отдельных потоков" : "");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tl-btn";
    btn.textContent = "🔭 Открыть работу команды в окне";
    btn.addEventListener("click", (e) => { e.preventDefault(); openMonitor(fromSummary(a)); });
    body.append(meta, btn);
    return box;
  }

  // ---------------------------------------------------------------- окно наблюдения
  const MON_CSS = `
.tm { --bg: #07070b; --panel: #12121a; --line: rgba(255,255,255,.09); --line-2: rgba(255,255,255,.16); --fg: #f5f5f7; --muted: #a1a1b0;
  --pink: #ff3d81; --grad: linear-gradient(120deg, #ff2d2d 0%, #ff3d81 45%, #8b5cff 100%);
  color: var(--fg); background: var(--bg); min-height: 100%; padding: 16px; box-sizing: border-box; display: grid; gap: 12px;
  font: 14px/1.5 "Onest", "Segoe UI", system-ui, -apple-system, sans-serif; text-align: left; }
.tm * { box-sizing: border-box; }
.tm-head { display: grid; gap: 10px; }
.tm-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 16px; }
.tm-logo { width: 30px; height: 30px; border-radius: 10px; background: var(--grad); display: grid; place-items: center; font-weight: 800; color: #fff; flex: none; }
.tm-live { font: 600 12px/1 ui-monospace, Consolas, monospace; color: var(--muted); }
.tm-live.on { color: #3ccf7a; }
.tm-live.on::before { content: "● "; animation: tmPulse 1s infinite; }
.tm-sp { flex: 1; }
.tm-btn { border: 1px solid var(--line-2); background: rgba(255,255,255,.06); color: var(--fg); border-radius: 999px; padding: 7px 14px;
  font: 500 13px/1.2 inherit; cursor: pointer; }
.tm-btn:hover { border-color: var(--pink); }
.tm-btn[hidden] { display: none; }
.tm-q { color: var(--muted); overflow-wrap: anywhere; max-height: 4.6em; overflow: auto; }
.tm-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: 8px; }
.tm-kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 9px 12px; min-width: 0; }
.tm-kpi b { display: block; font: 700 20px/1.25 ui-monospace, Consolas, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tm-kpi span { font-size: 12px; color: var(--muted); }
.tm-bar { height: 6px; border-radius: 999px; background: rgba(255,255,255,.08); overflow: hidden; }
.tm-bar i { display: block; height: 100%; width: 0; background: var(--grad); transition: width .2s; }
.tm-card { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 12px 14px; min-width: 0; }
.tm-card h3 { margin: 0 0 8px; font-size: 13.5px; font-weight: 600; display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.tm-card h3 small { color: var(--muted); font-weight: 400; font-size: 12px; }
.tm-gantt { width: 100%; display: block; }
.tm-lanes { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 3px 16px; margin-top: 8px; font: 12px/1.45 ui-monospace, Consolas, monospace; }
.tm-lane { display: flex; gap: 8px; align-items: center; min-width: 0; }
.tm-lane b { flex: none; color: var(--muted); font-weight: 500; }
.tm-lane span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
.tm-lane em { font-style: normal; color: var(--muted); flex: none; }
.tm .dot { width: 8px; height: 8px; border-radius: 50%; background: #4b4b5a; flex: none; }
.tm .dot.busy { background: #ffd166; animation: tmPulse .9s infinite; }
.tm .dot.idle { background: #3ccf7a; }
.tm .dot.dead { background: #ff4d4d; }
.tm-cols { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 12px; }
@media (max-width: 860px) { .tm-cols { grid-template-columns: 1fr; } }
.tm-side { display: grid; gap: 12px; align-content: start; min-width: 0; }
.tm-grid { display: flex; flex-wrap: wrap; gap: 3px; max-height: 56vh; overflow: auto; align-content: flex-start; }
.tm-grid .tt { width: 15px; height: 15px; border: 0; border-radius: 3px; padding: 0; cursor: pointer; background: rgba(255,255,255,.1); }
.tm-grid.small .tt { width: 10px; height: 10px; border-radius: 2px; }
.tm-grid .tt.run { background: #ffd166; animation: tmPulse .8s infinite; }
.tm-grid .tt.r0 { background: #ff3d81; } .tm-grid .tt.r1 { background: #8b5cff; } .tm-grid .tt.r2 { background: #3cc8ff; }
.tm-grid .tt.r3 { background: #ffd166; } .tm-grid .tt.r4 { background: #3ccf7a; } .tm-grid .tt.r5 { background: #ff8a3d; }
.tm-grid .tt.r6 { background: #c084fc; } .tm-grid .tt.r7 { background: #7c8496; }
.tm-grid .tt.abst { background: #4b4b5a; } .tm-grid .tt.err { background: #ff4d4d; } .tm-grid .tt.skip { background: rgba(255,255,255,.04); }
.tm-grid .tt.dim { opacity: .18; }
.tm-grid .tt.sel { outline: 2px solid #fff; outline-offset: 1px; }
.tm-legend { display: inline-flex; gap: 10px; flex-wrap: wrap; }
.tm-legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 4px; vertical-align: -1px; }
.tm-task { background: #0b0b10; color: var(--fg); border: 1px solid var(--line-2); border-radius: 8px; padding: 2px 6px; font: inherit; font-size: 12px; max-width: 100%; }
.tm-vote { display: grid; gap: 4px; padding: 8px; border-radius: 12px; cursor: pointer; border: 1px solid transparent; }
.tm-vote:hover, .tm-vote.on { border-color: var(--line-2); background: rgba(255,255,255,.03); }
.tm-vote .vh { display: flex; gap: 8px; align-items: center; font-size: 13px; }
.tm-vote .vd { width: 10px; height: 10px; border-radius: 3px; flex: none; }
.tm-vote .vh small { color: var(--muted); margin-left: auto; white-space: nowrap; }
.tm-vote .vb { height: 5px; border-radius: 999px; background: rgba(255,255,255,.08); overflow: hidden; }
.tm-vote .vb i { display: block; height: 100%; }
.tm-vote .vt { font-size: 12.5px; color: var(--muted); max-height: 4.4em; overflow: hidden; overflow-wrap: anywhere; }
.tm-votes .vz { color: var(--muted); font-size: 13px; }
.tm-detail { font-size: 13.5px; max-height: 46vh; overflow: auto; overflow-wrap: anywhere; color: var(--fg); }
.tm-detail .dm { color: var(--muted); font-size: 12.5px; margin-bottom: 6px; }
.tm-detail p { margin: .45em 0; } .tm-detail ul, .tm-detail ol { margin: .4em 0; padding-left: 1.3em; }
.tm-detail pre { white-space: pre-wrap; background: #0b0b10; padding: 8px 10px; border-radius: 10px; }
.tm-detail table { border-collapse: collapse; } .tm-detail td, .tm-detail th { border: 1px solid var(--line-2); padding: 3px 7px; }
.tm-detail a { color: #ff7aa8; } .tm-detail img { max-width: 100%; }
.tm-log { margin: 0; padding: 0; list-style: none; max-height: 220px; overflow: auto; font: 12px/1.55 ui-monospace, Consolas, monospace; color: var(--muted); }
.tm-log li b { color: var(--fg); font-weight: 500; }
@keyframes tmPulse { 50% { opacity: .45; } }
@media (prefers-reduced-motion: reduce) { .tm .dot.busy, .tm-grid .tt.run, .tm-live.on::before { animation: none; } }`;

  function monitorPage() {
    return `<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">` +
      `<title>Rai — команда моделей</title><style>html, body { margin: 0; background: #07070b; min-height: 100%; }${MON_CSS}</style></head>` +
      `<body><div class="tm"></div></body></html>`;
  }

  function makeMonitor(root, win, close) {
    const doc = root.ownerDocument;
    root.innerHTML = `<header class="tm-head">
        <div class="tm-title"><span class="tm-logo">R</span><b>Rai · Команда моделей</b><span class="tm-live"></span><span class="tm-sp"></span>
          <button type="button" class="tm-btn tm-stop">■ Остановить</button>${close ? `<button type="button" class="tm-btn tm-close">✕ Закрыть</button>` : ""}</div>
        <div class="tm-q"></div><div class="tm-kpis"></div><div class="tm-bar"><i></i></div></header>
      <section class="tm-card"><h3>Потоки — работают одновременно <small>каждая полоска — одна модель: где и сколько она думала</small></h3>
        <canvas class="tm-gantt"></canvas><div class="tm-lanes"></div></section>
      <div class="tm-cols">
        <section class="tm-card"><h3>Модели <small class="tm-legend"></small></h3><div class="tm-grid"></div></section>
        <aside class="tm-side">
          <section class="tm-card"><h3>Голосование <select class="tm-task" hidden aria-label="Задача"></select></h3><div class="tm-votes"></div></section>
          <section class="tm-card"><h3>Ответ модели</h3><div class="tm-detail">Нажмите на любую плитку — здесь появится ответ этой модели.</div></section>
        </aside>
      </div>
      <section class="tm-card"><h3>Журнал</h3><ol class="tm-log"></ol></section>`;
    const q = (s) => root.querySelector(s);
    const kpiDefs = [["models", "моделей"], ["threads", "потоков работают"], ["done", "готово"], ["running", "думают сейчас"],
                     ["queue", "в очереди"], ["time", "прошло"], ["speed", "ответов в секунду"], ["boost", "быстрее, чем по очереди"]];
    q(".tm-kpis").innerHTML = kpiDefs.map(([k, t]) => `<div class="tm-kpi"><b data-k="${k}">—</b><span>${t}</span></div>`).join("");
    q(".tm-legend").innerHTML = `<span><i style="background:#ff3d81"></i>лидер</span><span><i style="background:#8b5cff"></i>другие мнения</span>` +
      `<span><i style="background:#ffd166"></i>думает</span><span><i style="background:#4b4b5a"></i>воздержалась</span><span><i style="background:rgba(255,255,255,.12)"></i>ждёт</span>`;
    let vm = null, tiles = [], tileCls = [], sel = -1, hl = -1, taskSel = 0, logShown = 0, votesSig = "", detailSig = "", staticDone = false, laneRows = [];

    q(".tm-stop").addEventListener("click", () => { if (vm && vm.live) stop(vm); });
    if (close) q(".tm-close").addEventListener("click", close);
    q(".tm-grid").addEventListener("click", (e) => {
      const t = e.target.closest(".tt");
      if (!t) return;
      sel = +t.dataset.k;
      detailSig = "";
      staticDone = false;
      paint();
    });
    q(".tm-votes").addEventListener("click", (e) => {
      const v = e.target.closest(".tm-vote");
      if (!v) return;
      hl = hl === +v.dataset.r ? -1 : +v.dataset.r;
      const maps = rankMaps(vm);
      const first = vm.jobs.findIndex((j) => j.task === taskSel && j.state === "done" && maps[j.task].get(j.cluster) === hl);
      if (hl >= 0 && first >= 0) sel = first;
      votesSig = detailSig = "";
      staticDone = false;
      paint();
    });
    q(".tm-task").addEventListener("change", (e) => { taskSel = +e.target.value || 0; hl = -1; votesSig = ""; staticDone = false; paint(); });

    function attach(next) {
      vm = next;
      sel = -1; hl = -1; taskSel = 0; logShown = 0; votesSig = ""; detailSig = ""; staticDone = false;
      q(".tm-q").textContent = "«" + vm.question.slice(0, 600) + (vm.question.length > 600 ? "…" : "") + "»";
      const grid = q(".tm-grid");
      grid.classList.toggle("small", vm.jobs.length > 300);
      grid.innerHTML = vm.jobs.map((j, k) => `<button type="button" class="tt" data-k="${k}" aria-label="${esc((vm.models[j.m] || {}).name || "")}"></button>`).join("");
      tiles = Array.from(grid.children);
      tileCls = tiles.map(() => "");
      const sel2 = q(".tm-task");
      sel2.hidden = vm.tasks.length < 2;
      sel2.innerHTML = vm.tasks.map((t, k) => `<option value="${k}">${k + 1}. ${esc(t.q.slice(0, 60))}</option>`).join("");
      q(".tm-log").innerHTML = "";
      q(".tm-detail").textContent = "Нажмите на любую плитку — здесь появится ответ этой модели.";
      laneRows = [];
      q(".tm-lanes").innerHTML = "";
      if (vm.saved) {
        q(".tm-log").innerHTML = `<li>Это сохранённый отчёт: ответы отдельных моделей не хранятся — у каждой показан ответ её группы.</li>`;
      }
      paint();
    }

    function paint(force) {
      if (!vm || (staticDone && !vm.live && !force)) return;
      const st = stats(vm), maps = rankMaps(vm);
      const live = q(".tm-live");
      live.className = "tm-live" + (vm.live ? " on" : "");
      live.textContent = vm.live ? "идёт работа" : vm.stopped ? "остановлено" : vm.saved ? "сохранённый отчёт" : "готово";
      q(".tm-stop").hidden = !vm.live;
      const set = (k, v) => { const b = root.querySelector(`[data-k="${k}"]`); if (b && b.textContent !== v) b.textContent = v; };
      set("models", num(vm.models.length));
      set("threads", vm.saved ? String(vm.lanes) : vm.fallback ? String((vm.vlanes || []).length || 1) : st.lanesUp + " / " + st.lanesAll);
      set("done", num(st.done) + " / " + num(st.total));
      set("running", String(st.running));
      set("queue", num(st.queue));
      set("time", secs(st.elapsed));
      set("speed", st.done ? st.speed.toFixed(st.speed < 10 ? 1 : 0).replace(".", ",") : "—");
      set("boost", st.boost >= 1.05 ? "×" + st.boost.toFixed(1).replace(".", ",") : "×1");
      q(".tm-bar i").style.width = (st.total ? (st.done / st.total) * 100 : 0).toFixed(1) + "%";

      const lanesN = vm.saved ? vm.lanes : Math.max(1, st.lanesAll, vm.jobs.reduce((x, j) => Math.max(x, j.thread + 1), 0));
      drawGantt(q(".tm-gantt"), vm, lanesN, maps);
      if (!vm.saved) {
        if (laneRows.length !== st.lanes.length) {
          q(".tm-lanes").innerHTML = st.lanes.map(() => `<div class="tm-lane"><b></b><i class="dot"></i><span></span><em></em></div>`).join("");
          laneRows = Array.from(q(".tm-lanes").children);
        }
        st.lanes.forEach((l, k) => {
          const row = laneRows[k];
          row.children[0].textContent = "Поток " + l.n;
          row.children[1].className = "dot " + l.state;
          row.children[2].textContent = l.text;
          row.children[3].textContent = (l.state === "busy" ? secs(l.ms) + " · " : "") + "сделал " + num(l.done);
        });
      } else if (!laneRows.length) {
        q(".tm-lanes").innerHTML = `<div class="tm-lane"><span>Работало потоков: ${vm.lanes}${vm.fallback ? " (основной движок)" : ""}</span></div>`;
        laneRows = [null];
      }

      // плитки: меняем только те, что изменились
      for (let k = 0; k < tiles.length; k++) {
        const j = vm.jobs[k];
        let c = "tt";
        if (j.state === "done") {
          const r = maps[j.task] ? maps[j.task].get(j.cluster) : null;
          c += " r" + (r == null ? 7 : Math.min(r, 7));
          if (hl >= 0 && (j.task !== taskSel || r !== hl)) c += " dim";
        } else {
          c += " " + j.state;
          if (hl >= 0) c += " dim";
        }
        if (k === sel) c += " sel";
        if (c !== tileCls[k]) {
          tiles[k].className = c;
          tileCls[k] = c;
          const m = vm.models[j.m] || {name: "?"};
          tiles[k].title = m.name + " · " + cfgLabel(m) + (vm.tasks.length > 1 ? " · задача " + (j.task + 1) : "") + " — " + stateText(j) + (j.ms ? ", " + secs(j.ms) : "");
        }
      }

      // голосование по выбранной задаче
      const t = vm.tasks[taskSel] || vm.tasks[0];
      const sorted = t.clusters.slice().sort((a, b) => b.s - a.s);
      const all = sorted.reduce((x, c) => x + c.s, 0) || 1;
      const voters = sorted.reduce((x, c) => x + c.n, 0);
      const sig = sorted.slice(0, 8).map((c) => c.i + ":" + c.n + ":" + Math.round(c.s)).join("|") + "/" + t.abst + "/" + hl;
      if (sig !== votesSig) {
        votesSig = sig;
        q(".tm-votes").innerHTML = (sorted.length ? sorted.slice(0, 8).map((c, k) => {
          const color = COLORS[Math.min(k, COLORS.length - 1)], share = Math.round((c.s / all) * 100);
          return `<div class="tm-vote${hl === k ? " on" : ""}" data-r="${k}"><div class="vh"><i class="vd" style="background:${color}"></i>` +
            `<b>${k === 0 ? "Лидер" : "Мнение " + (k + 1)}</b><small>${num(c.n)} ${plural(c.n, "модель", "модели", "моделей")} · ${share}% веса</small></div>` +
            `<div class="vb"><i style="width:${share}%;background:${color}"></i></div>` +
            `<div class="vt">${esc(plain(c.text).slice(0, 260))}${plain(c.text).length > 260 ? "…" : ""}</div></div>`;
        }).join("") : `<p class="vz">Пока ни одна модель не дала ответа.</p>`) +
          `<p class="vz">Голосовали ${num(voters)}, воздержались ${num(t.abst || 0)}${t.err ? ", ошибок " + t.err : ""}` +
          (sorted.length > 8 || t.others ? `, ещё групп ответов: ${Math.max(sorted.length - 8, 0) + (t.others || 0)}` : "") +
          `. Модели, не нашедшие ответа, не голосуют против найденного.</p>`;
      }

      // ответ выбранной модели
      if (sel >= 0 && vm.jobs[sel]) {
        const j = vm.jobs[sel], m = vm.models[j.m] || {name: "?"};
        const dsig = sel + ":" + j.state + ":" + (j.answer ? j.answer.length : 0);
        if (dsig !== detailSig) {
          detailSig = dsig;
          let text = j.answer;
          if (text == null && vm.saved && j.state === "done") {
            const c = (vm.tasks[j.task] || {clusters: []}).clusters.find((x) => x.i === j.cluster);
            text = c ? c.text : "_Ответ этой модели попал в небольшую группу — в отчёте он не сохранён._";
          }
          q(".tm-detail").innerHTML = `<div class="dm"><b>${esc(m.name)}</b> · ${esc(cfgLabel(m))}` +
            (j.thread >= 0 ? " · поток " + (j.thread + 1) : "") + " · " + esc(stateText(j)) + (j.ms ? " · " + secs(j.ms) : "") +
            (vm.tasks.length > 1 ? " · задача " + (j.task + 1) : "") + (j.intent ? " · " + esc(j.intent) : "") +
            (vm.saved && j.state === "done" ? " · ответ её группы" : "") + `</div>` +
            (text ? `<div class="dmd">${md(text)}</div>` : `<div class="dm">${j.state === "queue" ? "Ждёт свободный поток…" : j.state === "run" ? "Думает…" : "Ответа нет."}</div>`);
        }
      }

      // журнал: новые записи — сверху
      const log = q(".tm-log");
      const fresh = vm.log.filter((e) => e.k > logShown);
      if (fresh.length) {
        logShown = fresh[fresh.length - 1].k;
        const frag = doc.createDocumentFragment();
        for (const e of fresh.slice(-60).reverse()) {
          const li = doc.createElement("li");
          li.innerHTML = `<b>${esc(e.t)}</b> ${esc(e.text)}`;
          frag.append(li);
        }
        log.insertBefore(frag, log.firstChild);
        while (log.children.length > 200) log.lastChild.remove();
      }
      if (!vm.live) staticDone = true;
    }

    return {
      attach: attach,
      paint: paint,
      alive: () => (win ? !win.closed : root.isConnected),
      focus: () => { try { if (win) win.focus(); } catch (e) { /* окно закрыто */ } },
      vm: () => vm
    };
  }

  function mountMonitorCss() {
    if (document.getElementById("team-mon-css")) return;
    const st = document.createElement("style");
    st.id = "team-mon-css";
    st.textContent = MON_CSS + `\n.tm-overlay { position: fixed; inset: 0; z-index: 9999; overflow: auto; background: #07070b; }`;
    document.head.append(st);
  }

  // Отдельное окно (как вкладка браузера), а если его не дали открыть — то же самое поверх чата
  function openMonitor(vm) {
    vm = vm || active || last;
    if (!vm) { if (page && page.toast) page.toast("Команда ещё не работала — задайте вопрос, и здесь будет видно, как модели думают"); return; }
    if (mon && mon.alive()) { mon.attach(vm); mon.focus(); ensureTicker(); return; }
    let win = null;
    // На телефоне отдельное окно — это новая вкладка, где чат не видно: там показываем поверх чата.
    // Старое приложение Rai для компьютера открыло бы вместо окна пустую страницу в браузере.
    const oldApp = window.RaiApp && window.RaiApp.isApp && !window.RaiApp.popups;
    if (!oldApp && !isPhone()) {
      try {
        const w = Math.min(1280, (screen.availWidth || 1280) - 40), h = Math.min(860, (screen.availHeight || 860) - 60);
        win = window.open("", "rai_team_monitor", `popup=yes,width=${w},height=${h},left=${Math.max(0, ((screen.availWidth || w) - w) >> 1)},top=40`);
      } catch (e) { win = null; }
    }
    let root = null;
    if (win) {
      try {
        win.document.open();
        win.document.write(monitorPage());
        win.document.close();
        root = win.document.querySelector(".tm");
      } catch (e) { root = null; }
      if (!root) { try { win.close(); } catch (e) { /* не наше окно */ } win = null; }
    }
    if (root) {
      mon = makeMonitor(root, win, null);
      win.addEventListener("resize", () => { if (mon) mon.paint(true); });
    } else {
      mountMonitorCss();
      const ov = document.createElement("div");
      ov.className = "tm-overlay";
      ov.setAttribute("role", "dialog");
      ov.setAttribute("aria-label", "Работа команды моделей");
      const box = document.createElement("div");
      box.className = "tm";
      ov.append(box);
      document.body.append(ov);
      const close = () => { ov.remove(); document.removeEventListener("keydown", onKey); mon = null; };
      const onKey = (e) => { if (e.key === "Escape") close(); };
      document.addEventListener("keydown", onKey);
      mon = makeMonitor(box, null, close);
    }
    mon.attach(vm);
    ensureTicker();
  }

  function ensureTicker() { if (!ticker) ticker = setInterval(tick, 100); }
  function tick() {
    const now = performance.now();
    for (const w of pool.list) {   // модель думает слишком долго (зависла сеть) — поток перезапускаем, задачу берёт другой
      if (w.state === "busy" && now - w.jobAt > JOB_LIMIT_MS) lost(w, "модель думала дольше " + secs(JOB_LIMIT_MS) + " — поток перезапущен", true);
    }
    if (card) { if (card.el.isConnected) card.paint(); else if (!active) card = null; }
    if (mon) { if (mon.alive()) { try { mon.paint(); } catch (e) { console.warn("Rai, окно команды:", e); } } else mon = null; }
    if (!active && !mon && !card) { clearInterval(ticker); ticker = 0; }
  }

  // ---------------------------------------------------------------- настройки: окно «Команда моделей»
  function dialogEl() { return document.getElementById("teamDialog"); }
  function buildDialog() {
    const dlg = document.createElement("dialog");
    dlg.id = "teamDialog";
    dlg.className = "team-dlg";
    dlg.setAttribute("aria-labelledby", "teamTitle");
    dlg.innerHTML = `<div class="td-card">
      <div class="td-head"><h2 id="teamTitle">👥 Команда моделей</h2>
        <button class="icon-btn td-x" type="button" aria-label="Закрыть"><svg class="i" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>
      <p class="td-lead">До <b>1000 моделей Rai</b> отвечают вместе и <b>параллельно</b> — в нескольких потоках вашего компьютера.
        Похожие ответы объединяются, модели голосуют, побеждает лучший ответ. Как они работают, видно в чате и в отдельном окне.</p>
      <label class="td-switch"><input type="checkbox" id="tdOn"><span>Отвечать командой</span></label>
      <div class="td-count"><b id="tdN">0</b><span>из 1000 моделей</span></div>
      <div class="td-add">
        <label>Версия <select id="tdVer"></select></label>
        <label>Уровень <select id="tdLvl"></select></label>
      </div>
      <div class="td-quick" role="group" aria-label="Добавить или убрать модели">
        <button type="button" class="tl-btn" data-add="1">+1</button><button type="button" class="tl-btn" data-add="10">+10</button>
        <button type="button" class="tl-btn" data-add="100">+100</button><button type="button" class="tl-btn" data-add="max">До 1000</button>
        <button type="button" class="tl-btn" data-add="-1">−1</button><button type="button" class="tl-btn" data-add="-10">−10</button>
        <button type="button" class="tl-btn" data-add="clear">Убрать всех</button>
      </div>
      <div class="td-groups" id="tdGroups"></div>
      <label class="td-row">Потоков одновременно <input type="range" id="tdThr" min="0" max="16" step="1"><b id="tdThrV"></b></label>
      <label class="td-row">Режим <select id="tdMode">
        <option value="auto">Авто: список задач — делят, один вопрос — решают вместе</option>
        <option value="council">Совет: все модели решают один вопрос</option>
        <option value="split">Конвейер: каждая строка — отдельная задача</option></select></label>
      <p class="td-note" id="tdNote"></p>
      <div class="td-actions"><button class="btn" type="button" id="tdWatch">🔭 Окно наблюдения</button>
        <button class="btn" type="button" id="tdFree">Освободить память</button>
        <button class="btn red" type="button" id="tdDone">Готово</button></div>
    </div>`;
    document.body.append(dlg);
    const $ = (id) => dlg.querySelector("#" + id);
    const close = () => { if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); };
    dlg.querySelector(".td-x").addEventListener("click", close);
    $("tdDone").addEventListener("click", close);
    dlg.addEventListener("click", (e) => { if (e.target === dlg) close(); });
    $("tdOn").addEventListener("change", (e) => { S.on = e.target.checked; if (S.on && !total()) addModels(12); save(); renderDialog(); renderChip(); });
    $("tdVer").addEventListener("change", (e) => { S.ver = e.target.value; save(); });
    $("tdLvl").addEventListener("change", (e) => { S.lvl = e.target.value; save(); });
    dlg.querySelector(".td-quick").addEventListener("click", (e) => {
      const b = e.target.closest("[data-add]");
      if (!b) return;
      const v = b.dataset.add;
      if (v === "clear") S.groups = [];
      else if (v === "max") addModels(MAX - total());
      else if (+v > 0) addModels(+v);
      else removeModels(-v);
      if (total() && !S.on && +v > 0) S.on = true;   // добавили модели — команда включается
      save(); renderDialog(); renderChip();
    });
    $("tdGroups").addEventListener("click", (e) => {
      const b = e.target.closest("[data-g]");
      if (!b) return;
      const g = S.groups[+b.dataset.g];
      if (!g) return;
      const d = b.dataset.d;
      if (d === "del") S.groups.splice(+b.dataset.g, 1);
      else g.n = Math.max(1, Math.min(g.n + (+d), g.n + MAX - total()));
      save(); renderDialog(); renderChip();
    });
    $("tdThr").addEventListener("input", (e) => { S.threads = +e.target.value || 0; save(); renderDialog(); });
    $("tdMode").addEventListener("change", (e) => { S.mode = e.target.value; save(); });
    $("tdWatch").addEventListener("click", () => { close(); openMonitor(); });
    $("tdFree").addEventListener("click", () => {
      if (active) { if (page && page.toast) page.toast("Команда сейчас работает — сначала остановите её"); return; }
      shutdown();
      if (page && page.toast) page.toast("Потоки закрыты — память свободна. При следующем вопросе они запустятся снова");
    });
    return dlg;
  }
  function addModels(n) {
    n = Math.max(0, Math.min(n, MAX - total()));
    if (!n) return;
    const lastG = S.groups[S.groups.length - 1];
    if (lastG && lastG.version === S.ver && lastG.level === S.lvl) lastG.n += n;
    else S.groups.push({n: n, version: S.ver || "*", level: S.lvl || "*"});
  }
  function removeModels(n) {
    while (n > 0 && S.groups.length) {
      const g = S.groups[S.groups.length - 1], take = Math.min(n, g.n);
      g.n -= take;
      n -= take;
      if (!g.n) S.groups.pop();
    }
  }
  function renderDialog() {
    const dlg = dialogEl();
    if (!dlg || !page) return;
    const $ = (id) => dlg.querySelector("#" + id);
    const n = total();
    $("tdOn").checked = S.on && n > 0;
    $("tdN").textContent = num(n);
    const vers = ((page.versions && page.versions()) || []);
    $("tdVer").innerHTML = `<option value="*">Все версии по кругу</option><option value="chat">Как в чате</option>` +
      vers.map((v) => `<option value="${esc(v.id)}">${esc(v.name || v.id)}</option>`).join("");
    $("tdVer").value = vers.some((v) => v.id === S.ver) || S.ver === "chat" ? S.ver : "*";
    const lv = (page.levels || []);
    $("tdLvl").innerHTML = `<option value="*">Все уровни по кругу</option><option value="chat">Как внизу чата</option>` +
      lv.map((l) => `<option value="${esc(l.id)}"${page.levelAllowed && !page.levelAllowed(l.id) ? " disabled" : ""}>${esc(l.icon + " " + l.name)}` +
        `${page.levelAllowed && !page.levelAllowed(l.id) ? " 🔒" : ""}</option>`).join("");
    $("tdLvl").value = lv.some((l) => l.id === S.lvl) || S.lvl === "chat" ? S.lvl : "*";
    $("tdGroups").innerHTML = S.groups.length ? S.groups.map((g, k) => `<div class="td-group"><b>${num(g.n)} ×</b><span>${esc(groupLabel(g))}</span>` +
      `<button type="button" class="tl-btn" data-g="${k}" data-d="-10" aria-label="Убрать 10">−10</button>` +
      `<button type="button" class="tl-btn" data-g="${k}" data-d="10" aria-label="Добавить 10">+10</button>` +
      `<button type="button" class="tl-btn" data-g="${k}" data-d="del" aria-label="Убрать группу">✕</button></div>`).join("") :
      `<p class="td-note">Моделей нет — добавьте кнопками выше.</p>`;
    const mx = maxThreads();
    $("tdThr").max = String(mx);
    $("tdThr").value = String(Math.min(S.threads || 0, mx));
    $("tdThrV").textContent = S.threads ? String(Math.min(S.threads, mx)) : "авто (" + autoThreads() + ")";
    $("tdMode").value = S.mode;
    const up = pool.list.filter((w) => w.state === "idle" || w.state === "busy").length;
    $("tdNote").textContent = "Ваше устройство: " + CORES + " " + plural(CORES, "ядро", "ядра", "ядер") + " — до " + mx + " " + plural(mx, "потока", "потоков", "потоков") +
      " одновременно. Каждый поток — отдельная копия Rai со всеми знаниями (около 200–300 МБ памяти); первый запуск потоков — несколько секунд. " +
      (up ? "Сейчас запущено потоков: " + up + ". " : "") +
      (n > 200 ? "Тысяча моделей на " + threads() + " " + plural(threads(), "потоке", "потоках", "потоках") + " отвечает примерно за " +
        Math.max(5, Math.round((n * 0.15) / threads())) + " с и больше — зависит от вопроса." : "");
  }
  function openSettings() {
    const dlg = dialogEl() || buildDialog();
    renderDialog();
    if (dlg.showModal) { if (!dlg.open) dlg.showModal(); } else dlg.setAttribute("open", "");
  }

  // Кнопка «👥 Команда» рядом с выбором модели и уровня
  function mountChip() {
    const bar = document.getElementById("pickers");
    if (!bar || document.getElementById("teamBtn")) return;
    const pick = document.createElement("div");
    pick.className = "pick";
    pick.innerHTML = `<button type="button" class="pick-btn team-chip" id="teamBtn" aria-pressed="false" ` +
      `title="Команда моделей: до 1000 моделей Rai отвечают вместе и параллельно"><span class="pk-ic lv" aria-hidden="true">👥</span>` +
      `<span class="pk-name" id="teamName">Команда</span></button>`;
    bar.insertBefore(pick, document.getElementById("pickNote"));
    pick.querySelector("button").addEventListener("click", openSettings);
    renderChip();
  }
  function renderChip() {
    const b = document.getElementById("teamBtn");
    if (!b) return;
    const on = S.on && total() > 0;
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", String(on));
    document.getElementById("teamName").textContent = on ? "Команда · " + num(total()) : "Команда";
  }

  function mountCss() {
    if (document.getElementById("team-css")) return;
    const st = document.createElement("style");
    st.id = "team-css";
    st.textContent = `
  .pick-btn.team-chip.on { border-color: rgba(255, 61, 129, .75); background: rgba(255, 61, 129, .14); }
  .msg.team-run .bubble { display: block; color: var(--fg); }
  .team-live { display: grid; gap: 8px; width: min(680px, 100%); color: var(--fg); }
  .team-live .tl-top { display: flex; align-items: baseline; gap: 4px; flex-wrap: wrap; }
  .team-live .tl-sub { color: var(--muted); font-size: 13px; }
  .team-live .tl-time { margin-left: auto; font: 600 13px/1 var(--font-mono); color: var(--pink, #ff3d81); }
  .team-live .tl-bar { height: 6px; border-radius: 999px; background: rgba(255, 255, 255, .08); overflow: hidden; }
  .team-live .tl-bar i { display: block; height: 100%; width: 0; background: var(--grad, linear-gradient(90deg, #ff2d2d, #ff3d81, #8b5cff)); transition: width .2s; }
  .team-live .tl-stat { font-size: 12.5px; color: var(--muted); }
  .team-live .tl-lanes { display: grid; gap: 2px; font: 12px/1.45 var(--font-mono); }
  .tl-lane { display: flex; gap: 8px; align-items: center; min-width: 0; }
  .tl-lane b { flex: none; width: 66px; color: var(--muted); font-weight: 500; }
  .tl-lane.more { color: var(--muted); }
  .tl-lane span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 1; }
  .tl-lane em { font-style: normal; color: var(--muted); flex: none; }
  .tl-lane .dot { width: 8px; height: 8px; border-radius: 50%; background: #4b4b5a; flex: none; }
  .tl-lane .dot.busy { background: #ffd166; animation: tlPulse .9s infinite; }
  .tl-lane .dot.idle { background: #3ccf7a; }
  .tl-lane .dot.dead { background: #ff4d4d; }
  .team-live canvas.tl-tiles { width: 100%; display: block; }
  .team-live .tl-lead { font-size: 13px; overflow-wrap: anywhere; }
  .tl-acts { display: flex; gap: 8px; flex-wrap: wrap; }
  .tl-btn { border: 1px solid var(--line-2, #3a3a40); background: var(--glass-2, #1d1d20); color: var(--fg); border-radius: 999px; padding: 6px 12px;
    font: 500 13px/1.2 var(--font-body); cursor: pointer; transition: border-color .2s; }
  .tl-btn:hover { border-color: var(--pink, #ff3d81); }
  @keyframes tlPulse { 50% { opacity: .4; } }
  details.team-sum { margin-top: 8px; border: 1px solid var(--line); border-radius: 14px; background: var(--glass, rgba(255, 255, 255, .03)); }
  details.team-sum > summary { cursor: pointer; padding: 9px 12px; font-size: 13px; color: var(--muted); list-style: none; }
  details.team-sum > summary::-webkit-details-marker { display: none; }
  details.team-sum > summary b { color: var(--fg); }
  details.team-sum .ts-ic { margin-right: 6px; }
  details.team-sum .ts-body { padding: 0 12px 12px; display: grid; gap: 6px; justify-items: start; }
  .ts-vote { display: grid; grid-template-columns: 10px auto 1fr; gap: 4px 8px; align-items: baseline; font-size: 12.5px; width: 100%; }
  .ts-vote i { width: 10px; height: 10px; border-radius: 3px; align-self: center; }
  .ts-vote .ts-n { white-space: nowrap; color: var(--fg); }
  .ts-vote .ts-t { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .ts-meta { margin: 2px 0; font-size: 12px; color: var(--muted); }
  dialog.team-dlg { width: min(620px, calc(100vw - 24px)); max-height: calc(100vh - 32px); padding: 0; border: 1px solid var(--line-2); border-radius: 22px;
    color: var(--fg); background: radial-gradient(120% 80% at 100% 0%, rgba(255, 45, 45, .14), transparent 60%), var(--panel); }
  dialog.team-dlg::backdrop { background: rgba(0, 0, 0, .55); backdrop-filter: blur(4px); }
  .td-card { padding: 18px 20px 20px; display: grid; gap: 12px; }
  .td-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .td-head h2 { margin: 0; font: 700 19px/1.2 var(--font-display, sans-serif); }
  .td-lead, .td-note { margin: 0; font-size: 13px; color: var(--muted); line-height: 1.5; }
  .td-switch { display: flex; align-items: center; gap: 10px; font-weight: 600; cursor: pointer; }
  .td-switch input { width: 18px; height: 18px; accent-color: #ff3d81; }
  .td-count { display: flex; align-items: baseline; gap: 8px; }
  .td-count b { font: 800 34px/1 var(--font-display, sans-serif); background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .td-count span { color: var(--muted); font-size: 13px; }
  .td-add { display: flex; gap: 10px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }
  .td-add label { display: grid; gap: 4px; flex: 1 1 200px; }
  .team-dlg select { background: var(--panel-2); color: var(--fg); border: 1px solid var(--line-2); border-radius: 10px; padding: 7px 9px; font: inherit; font-size: 13.5px; min-width: 0; }
  .td-quick { display: flex; gap: 6px; flex-wrap: wrap; }
  .td-groups { display: grid; gap: 6px; max-height: 190px; overflow: auto; }
  .td-group { display: flex; align-items: center; gap: 6px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 12px; font-size: 13px; }
  .td-group b { white-space: nowrap; }
  .td-group span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }
  .td-group .tl-btn { padding: 3px 9px; font-size: 12px; }
  .td-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }
  .td-row input[type=range] { flex: 1 1 160px; accent-color: #ff3d81; }
  .td-row select { flex: 1 1 260px; }
  .td-row b { color: var(--fg); min-width: 64px; }
  .td-actions { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
  html[data-device="phone"] dialog.team-dlg { width: calc(100vw - 12px); border-radius: 18px; }
  @media (prefers-reduced-motion: reduce) { .tl-lane .dot.busy { animation: none; } }`;
    document.head.append(st);
  }

  window.RaiTeam = {
    MAX: MAX,
    // page: {versions(), levels, levelAllowed(id), currentLevel(), chatVersion(), device, md(text), toast(text), profile(),
    //        engine() → Promise движка, ask(version, message, session, history, level) — запасной путь без потоков}
    init(p) {
      page = p;
      mountCss();
      mountChip();
    },
    // boot: {base, stdlib, files: [[имя, текст]], net() → {PROXY, SAME_ORIGIN, SANDBOX}, data() → Promise<{kb, meds, deep, learned}>}
    setBoot(b) { boot = b; },
    active() { return !!(S.on && total() > 0); },
    running() { return !!active; },
    answer: answer,
    stop() { if (active) stop(active); },
    renderSummary: renderSummary,
    openSettings: openSettings,
    openMonitor() { openMonitor(); },
    refresh() { renderChip(); renderDialog(); },
    // для проверок: состав, потоки и прямые настройки
    configure(o) {
      if (o && Array.isArray(o.groups)) S.groups = o.groups.map((g) => ({n: Math.max(1, Math.min(MAX, g.n | 0)), version: g.version || "*", level: g.level || "*"}));
      for (const k of ["on", "threads", "mode"]) if (o && k in o) S[k] = o[k];
      while (total() > MAX) removeModels(total() - MAX);
      save(); renderChip(); renderDialog();
    },
    // для тестов (test_app.py): разбор задач, оценка ответов, голосование и отчёт без браузера
    _internals: {splitTasks: splitTasks, judge: judge, place: place, leader: leader, summary: summary, fromSummary: fromSummary, plan: plan},
    state() {
      return {settings: JSON.parse(JSON.stringify(S)), models: total(), threads: threads(), maxThreads: maxThreads(),
              pool: pool.list.map((w) => ({n: w.n, state: w.state, done: w.done, label: w.label})), running: !!active};
    }
  };
})();
