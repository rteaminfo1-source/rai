/* Rai Нейро — своя нейросеть Rai прямо в браузере. Без API и ключей: модель один раз загружается в браузер
   (сама, в фоне) и дальше работает на компьютере посетителя, сообщения никуда не уходят.
   - Есть видеокарта с WebGPU — WebLLM (быстро). Нет — wllama (llama.cpp на WebAssembly) на процессоре.
   - Модели, библиотеки и программы для видеокарты берутся С ВАШЕГО САЙТА (ai.php на rai.rteam.info хранит копии);
     если своего сервера нет — с исходных серверов (jsdelivr, Hugging Face, GitHub).
   - В основе — открытые модели Qwen3.5 (лицензия Apache 2.0), под именем Rai Нейро.
   Страница подключает этот файл; всё управление — через window.RaiNeuro. */
(function () {
  "use strict";

  const WEBLLM = "0.2.85", WLLAMA = "3.6.1";
  const UP = {
    gpuLib: `https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@${WEBLLM}/lib/index.js`,  // один файл, без зависимостей
    cpuLib: `https://cdn.jsdelivr.net/npm/@wllama/wllama@${WLLAMA}/esm/index.js`,
    cpuWasm: `https://cdn.jsdelivr.net/npm/@wllama/wllama@${WLLAMA}/esm/wasm/wllama.wasm`
  };
  const STORE = "rai_neuro";
  // gpu: модели WebLLM (f16 быстрее, f32 — для видеокарт без half-float);
  // cpu: модели в формате GGUF для процессора (открытые веса Qwen3 — умнее прежних Qwen2.5 того же размера).
  const HF = "https://huggingface.co/";
  const MODELS = {
    fast: {name: "Лайт", label: "Rai Нейро Лайт", base: "Qwen3.5 0.8B", size: "≈ 0,6 ГБ", memory: "1,7 ГБ",
           f16: "Qwen3.5-0.8B-q4f16_1-MLC", f32: "Qwen3.5-0.8B-q4f32_1-MLC",
           cpu: {url: HF + "Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf", base: "Qwen3 0.6B", size: "≈ 0,6 ГБ"}},
    normal: {name: "Стандарт", label: "Rai Нейро", base: "Qwen3.5 2B", size: "≈ 1,4 ГБ", memory: "2,3 ГБ",
             f16: "Qwen3.5-2B-q4f16_1-MLC", f32: "Qwen3.5-2B-q4f32_1-MLC",
             cpu: {url: HF + "unsloth/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf", base: "Qwen3 1.7B", size: "≈ 1,1 ГБ"}},
    strong: {name: "Про", label: "Rai Нейро Про", base: "Qwen3.5 4B", size: "≈ 2,6 ГБ", memory: "3,9 ГБ",
             f16: "Qwen3.5-4B-q4f16_1-MLC", f32: "Qwen3.5-4B-q4f32_1-MLC",
             cpu: {url: HF + "Qwen/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-Q4_K_M.gguf", base: "Qwen3 4B", size: "≈ 2,4 ГБ"}},
    max: {name: "Макс", label: "Rai Нейро Макс", base: "Qwen3.5 9B", size: "≈ 5,5 ГБ", memory: "6,5 ГБ",
          f16: "Qwen3.5-9B-q4f16_1-MLC", f32: "Qwen3.5-9B-q4f32_1-MLC"},
    coder: {name: "Код", label: "Rai Нейро Код", base: "Qwen2.5-Coder 7B", size: "≈ 4,5 ГБ", memory: "5,1 ГБ",
            f16: "Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC", f32: "Qwen2.5-Coder-7B-Instruct-q4f32_1-MLC"}
  };

  const SYSTEM = `Ты — Rai, собственная нейросеть команды Rteam (сайт rai.rteam.info). Ты умный, внимательный и честный помощник.
Отвечаешь на языке пользователя (по умолчанию — по-русски), грамотно и естественно.

Как отвечать:
- Сначала пойми, что именно спрашивают. На простой вопрос — коротко (1–3 предложения), на сложный — развёрнуто и по порядку.
- Объясняй простыми словами, приводи примеры. В задачах — решение по шагам и чёткий итог: **Ответ: …**
- Оформляй в Markdown: заголовки ##, списки, таблицы для сравнений, **жирный** для главного.
- Считай аккуратно; всё сложнее устного счёта проверяй кодом.
- Факты: если в сообщении есть «Сведения из интернета» — опирайся на них и ставь ссылки [название](адрес).
  Никогда не выдумывай ссылки, цифры, цитаты и даты; не уверен — найди или честно скажи, что не знаешь.
- Код: полный рабочий файл целиком в одном блоке \`\`\`язык, без «…» и заглушек. Сайты и браузерные игры — одним файлом
  index.html (CSS и JavaScript внутри, без внешних библиотек), современный адаптивный дизайн. После кода — как запустить.
- Помни весь разговор и то, что знаешь о пользователе; обращайся по имени, если знаешь его.
- Ты — Rai. Если спросят, на чём ты основан: на открытой модели Qwen3.5, работаешь прямо в браузере пользователя.
- Не помогай с тем, что может навредить людям.`;

  const CODE_SYSTEM = `Ты — Rai Code, сильный программист-помощник. Отвечаешь по-русски.
- Когда пишешь или исправляешь код — верни ВЕСЬ файл целиком в одном блоке \`\`\`язык, без сокращений и заглушек,
  затем 1–3 предложения о том, что сделано.
- Пиши чистый, рабочий код с понятными именами; обрабатывай ошибки ввода; не используй несуществующие функции.
- Веб-страницы и игры — одним файлом index.html (CSS и JS внутри, без внешних библиотек).`;

  // Свой сервер нейросети (ai.php на сайте): страница сообщает его адрес через useMirror()
  let mirror = null;  // {root: "https://сайт/ai.php", pathInfo: true/false}
  const SOURCES = [["https://cdn.jsdelivr.net/npm/", "npm/"], [HF, "hf/"], ["https://raw.githubusercontent.com/", "gh/"]];
  /** Адрес файла на своём сайте (или исходный, если своего сервера нет). */
  function own(url) {
    if (!mirror) return url;
    for (const [from, to] of SOURCES) {
      if (url.startsWith(from)) return mirror.pathInfo ? mirror.root + "/" + to + url.slice(from.length) : mirror.root + "?p=" + to + url.slice(from.length);
    }
    return url;
  }

  let engine = null, backend = null, worker = null, loading = null, current = null, abort = null;
  const listeners = new Set();
  let status = {state: "off", text: "Нейросеть выключена", progress: 0};

  function emit(patch) {
    status = Object.assign({}, status, patch);
    for (const fn of listeners) { try { fn(status); } catch (e) { /* подписчик упал — не страшно */ } }
  }

  async function gpuInfo() {
    if (!navigator.gpu) return {ok: false, why: "В этом браузере нет WebGPU — нейросеть будет работать на процессоре (медленнее)."};
    let adapter = null;
    try { adapter = await navigator.gpu.requestAdapter(); } catch (e) { adapter = null; }
    if (!adapter) return {ok: false, why: "WebGPU есть, но видеокарта недоступна — нейросеть будет работать на процессоре."};
    const limits = adapter.limits || {};
    let info = adapter.info || null;
    if (!info && adapter.requestAdapterInfo) { try { info = await adapter.requestAdapterInfo(); } catch (e) { info = null; } }
    const name = ((info && (info.vendor + " " + (info.architecture || "") + " " + (info.description || ""))) || "").toLowerCase();
    return {ok: true, f16: !!(adapter.features && adapter.features.has("shader-f16")), buffer: limits.maxBufferSize || 0, name: name};
  }

  function saved() {
    try { return localStorage.getItem(STORE); } catch (e) { return null; }
  }
  function remember(key) {
    try { if (key) localStorage.setItem(STORE, key); else localStorage.removeItem(STORE); } catch (e) { /* без запоминания */ }
  }
  const mobile = () => /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "");
  const saveData = () => !!(navigator.connection && navigator.connection.saveData);

  /**
   * Какую модель взять самому — самую умную, которая потянет устройство:
   * отдельная видеокарта (NVIDIA, AMD) или Apple M с 8+ ГБ — «Про» (4B), встроенная — «Стандарт» (2B), телефон — «Лайт».
   */
  async function pick() {
    const gpu = window.RAI_NEURO_TEST ? Object.assign({ok: true, f16: true, buffer: 4e9, name: ""}, window.RAI_NEURO_TEST.gpu || {}) : await gpuInfo();
    const ram = navigator.deviceMemory || 4;
    if (!gpu.ok) return {key: ram >= 8 && !mobile() ? "normal" : "fast", gpu: gpu};
    if (mobile() || ram < 4) return {key: "fast", gpu: gpu};
    const discrete = /nvidia|geforce|rtx|radeon|amd|ati\b|rdna|ampere|ada|lovelace|turing|blackwell/.test(gpu.name || "");
    const apple = /apple|metal-3|m[1-9]\b/.test(gpu.name || "");
    if ((discrete || apple) && ram >= 8 && gpu.buffer >= 1e9) return {key: "strong", gpu: gpu};
    return {key: "normal", gpu: gpu};
  }

  // Какие модели разрешены тарифом (null — все). Недоступная модель заменяется ближайшей разрешённой послабее.
  let allowed = null;
  const RANK = {fast: 0, normal: 1, strong: 2, coder: 3, max: 4};
  function permitted(key) {
    if (!allowed || !allowed.length || allowed.includes(key)) return key;
    const ok = allowed.filter((k) => MODELS[k] && RANK[k] <= RANK[key]).sort((a, b) => RANK[b] - RANK[a]);
    return ok[0] || allowed.filter((k) => MODELS[k]).sort((a, b) => RANK[a] - RANK[b])[0] || key;
  }
  function setAllowed(list) {
    allowed = Array.isArray(list) ? list.slice() : null;
    if (current && permitted(current) !== current) enable(permitted(current)).catch(() => null);  // тариф закончился — модель попроще
  }

  /** Включить нейросеть: скачать модель (или взять из кэша браузера) и запустить в фоновом потоке. */
  async function enable(key) {
    key = permitted(MODELS[key] ? key : (await pick()).key);
    if (engine && current === key) return engine;
    if (loading) return loading;
    loading = (async () => {
      let from = "upstream";
      emit({state: "loading", text: "Проверяю видеокарту…", progress: 0, model: key});
      const gpu = window.RAI_NEURO_TEST ? {ok: !window.RAI_NEURO_TEST.cpu, f16: true} : await gpuInfo();
      const model = MODELS[key];
      await disable(true);
      const onProgress = (p, fromCache) => emit({state: "loading", progress: p,
        text: "Загружаю нейросеть: " + Math.round(p * 100) + "%" + (fromCache ? " (из кэша)" : "")});
      if (gpu.ok) {
        const id = gpu.f16 ? model.f16 : model.f32;
        const progress = (r) => onProgress(typeof r.progress === "number" ? r.progress : 0, r.text && /cache|кэш/i.test(r.text));
        if (window.RAI_NEURO_TEST) {
          engine = await window.RAI_NEURO_TEST.create(id, progress, own(HF + "mlc-ai/" + id));
          from = mirror ? "site" : "upstream";
        } else {
          // Библиотека: сначала со своего сайта, если не вышло — с CDN
          let lib = own(UP.gpuLib), webllm;
          try { webllm = await import(lib); } catch (e) { if (lib === UP.gpuLib) throw e; lib = UP.gpuLib; webllm = await import(lib); }
          const start = async (appConfig) => {
            const src = `import * as w from "${lib}"; const h = new w.WebWorkerMLCEngineHandler(); self.onmessage = (m) => h.onmessage(m);`;
            worker = new Worker(URL.createObjectURL(new Blob([src], {type: "text/javascript"})), {type: "module"});
            const cfg = {initProgressCallback: progress};
            if (appConfig) cfg.appConfig = appConfig;
            return webllm.CreateWebWorkerMLCEngine(worker, id, cfg, {context_window_size: 8192});
          };
          // Модель и её программа для видеокарты — со своего сайта (ai.php), иначе — с Hugging Face и GitHub
          const rec = (webllm.prebuiltAppConfig.model_list || []).find((r) => r.model_id === id);
          const mine = rec && mirror && mirror.pathInfo ? {model_list: [Object.assign({}, rec, {model: own(rec.model), model_lib: own(rec.model_lib)})]} : null;
          try {
            engine = await start(mine);
            from = mine ? "site" : "upstream";
          } catch (e) {
            if (!mine) throw e;
            if (worker) worker.terminate();
            emit({text: "С вашего сайта модель не загрузилась — беру с исходного сервера…"});
            engine = await start(null);
            from = "upstream";
          }
        }
        backend = "gpu";
        current = key;
        emit({label: model.label});
      } else {
        // Без видеокарты — на процессоре (WebAssembly). Самые большие модели здесь не потянуть.
        const cpu = model.cpu || MODELS.normal.cpu;
        emit({text: "Видеокарты нет — запускаю нейросеть на процессоре…"});
        if (window.RAI_NEURO_TEST) {
          engine = await window.RAI_NEURO_TEST.create(cpu.url.split("/").pop(), (r) => onProgress(r.progress || 0), own(cpu.url));
          from = mirror ? "site" : "upstream";
        } else {
          let lib = own(UP.cpuLib), mod;
          try { mod = await import(lib); } catch (e) { if (lib === UP.cpuLib) throw e; lib = UP.cpuLib; mod = await import(lib); }
          const w = new mod.Wllama({default: lib === UP.cpuLib ? UP.cpuWasm : own(UP.cpuWasm)},
                                   {logger: {debug() {}, log() {}, warn: console.warn, error: console.error}});
          const load = (url) => w.loadModelFromUrl(url, {n_ctx: 4096, progressCallback: ({loaded, total}) => onProgress(total ? loaded / total : 0)});
          try { await load(own(cpu.url)); from = mirror ? "site" : "upstream"; }
          catch (e) { if (own(cpu.url) === cpu.url) throw e; await load(cpu.url); from = "upstream"; }
          engine = {
            wllama: w,
            unload: () => w.exit(),
            chat: {completions: {create: (opts) => w.createChatCompletion(Object.assign({}, opts, {abortSignal: abort && abort.signal}))}}
          };
        }
        backend = "cpu";
        current = model.cpu ? key : "normal";
        emit({label: MODELS[current].label + " · процессор"});
      }
      remember(key);
      emit({state: "ready", progress: 1, model: key, backend: backend, from: from,
            text: status.label + " — " + (from === "site" ? "загружена с вашего сайта" : "загружена с исходного сервера")});
      return engine;
    })();
    try {
      return await loading;
    } catch (e) {
      engine = null; current = null; backend = null;
      const why = friendly(e);
      emit({state: "error", progress: 0, text: why});
      throw new Error(why);
    } finally {
      loading = null;
    }
  }

  /** Понятная причина, почему нейросеть не запустилась. */
  function friendly(e) {
    const m = (e && e.message) || String(e);
    if (window.RAI_SANDBOX) return "В этом окне просмотра интернет закрыт, поэтому модель не скачать. Откройте Rai на сайте rai.rteam.info — там нейросеть работает.";
    if (/failed to fetch|networkerror|network error|load failed|err_|fetch/i.test(m)) {
      return "Не удалось скачать модель: нет связи с сервером моделей. Проверьте интернет и нажмите «Включить» ещё раз.";
    }
    if (/out of memory|oom|device (was )?lost|allocat|exceed.*(limit|memory)|maxBufferSize/i.test(m)) {
      return "Видеокарте не хватило памяти для этой модели — выберите модель поменьше (Лайт или Стандарт).";
    }
    if (/quota|storage/i.test(m)) return "В браузере не хватило места для модели — освободите место на диске или выберите модель поменьше.";
    return m;
  }

  async function disable(keepChoice) {
    if (engine && engine.unload) { try { await engine.unload(); } catch (e) { /* уже выгружена */ } }
    if (worker) worker.terminate();
    engine = null; worker = null; current = null; backend = null;
    if (!keepChoice) { remember("off"); emit({state: "off", text: "Нейросеть выключена", progress: 0, label: ""}); }
  }

  /** Сам включить нейросеть при открытии страницы (кроме режима экономии трафика и телефона без видеокарты или по мобильной сети). */
  async function auto() {
    const choice = saved();
    if (choice === "off" || window.RAI_SANDBOX) return null;  // в окне просмотра модель всё равно не скачать
    if (choice && MODELS[choice]) return enable(choice).catch(() => null);
    if (saveData()) return null;
    const {key, gpu} = await pick();
    // на телефоне — только с видеокартой и не по мобильному интернету (модель весит сотни мегабайт)
    const cellular = navigator.connection && /cellular/.test(navigator.connection.type || "");
    if (mobile() && (!gpu.ok || cellular)) return null;
    return enable(key).catch(() => null);
  }

  // Модели Qwen3/3.5 умеют «размышлять» вслух — в ответ это не пускаем, а показываем отдельно («Ход мыслей»).
  function clean(text) {
    return String(text || "").replace(/<think>[\s\S]*?(?:<\/think>|$)/g, "").replace(/^\s+/, "");
  }
  function thoughtOf(text) {
    const m = String(text || "").match(/<think>([\s\S]*?)(?:<\/think>|$)/);
    return m ? m[1].trim() : "";
  }
  let lastThought = "";

  /**
   * Ответ нейросети по сообщениям [{role, content}]. onText(весь текст) вызывается по мере написания.
   * Возвращает полный текст. stop() прерывает ответ.
   * opts: system, temperature, maxTokens, thinking (думать перед ответом), onThink(ход мыслей по мере написания).
   */
  let generating = false;
  async function chat(messages, onText, opts) {
    if (!engine) throw new Error("Нейросеть не включена");
    generating = true;
    abort = typeof AbortController === "function" ? new AbortController() : null;
    let raw = "";
    const thinking = !!(opts && opts.thinking) && backend === "gpu";
    lastThought = "";
    try {
      const msgs = messages.map((m) => ({role: m.role, content: m.content}));
      // На процессоре Qwen3 отвечает без долгого «размышления» (иначе ответ ждать в разы дольше)
      const last = msgs.length - 1;
      if (backend === "cpu" && last >= 0 && msgs[last].role === "user" && !/\/no_think\s*$/.test(msgs[last].content)) {
        msgs[last] = {role: "user", content: msgs[last].content + " /no_think"};
      }
      const stream = await engine.chat.completions.create({
        messages: [{role: "system", content: (opts && opts.system) || SYSTEM}].concat(msgs),
        // рекомендованные для Qwen3.5 настройки: с размышлением 0.6/0.95, без — 0.7/0.8 (код — точнее, 0.2)
        stream: true, temperature: (opts && opts.temperature) ?? (thinking ? 0.6 : 0.7), top_p: thinking ? 0.95 : 0.8,
        max_tokens: ((opts && opts.maxTokens) || 3000) + (thinking ? 3000 : 0),
        extra_body: {enable_thinking: thinking}
      });
      for await (const chunk of stream) {
        const delta = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
        if (!delta) continue;
        raw += delta;
        if (thinking && opts.onThink && /<think>/.test(raw) && !/<\/think>/.test(raw)) opts.onThink(thoughtOf(raw));
        else if (onText) onText(clean(raw));
      }
    } catch (e) {
      if (!(abort && abort.signal.aborted)) throw e;  // остановили кнопкой — это не ошибка
    } finally {
      generating = false;
      lastThought = thoughtOf(raw);
    }
    return clean(raw);
  }
  async function stop() {
    if (!generating) return;
    if (abort) abort.abort();
    if (engine && engine.interruptGenerate) {
      try { await engine.interruptGenerate(); } catch (e) { /* уже остановлена */ }
    }
  }

  /** Блоки кода из ответа: [{lang, code}]. */
  function codeBlocks(text) {
    const out = [], re = /```([\w#+.-]*)[^\n]*\n([\s\S]*?)(?:```|$)/g;
    let m;
    while ((m = re.exec(text || ""))) if (m[2].trim()) out.push({lang: (m[1] || "").toLowerCase(), code: m[2].replace(/\s+$/, "") + "\n"});
    return out;
  }

  window.RaiNeuro = {
    useMirror: (m) => { mirror = m && m.root ? {root: m.root.replace(/\/+$/, ""), pathInfo: !!m.pathInfo} : null; },
    mirror: () => mirror,
    own: own,
    MODELS: MODELS,
    SYSTEM: SYSTEM,
    CODE_SYSTEM: CODE_SYSTEM,
    enable: enable,
    disable: () => disable(false),
    auto: auto,
    pick: pick,
    ready: () => !!engine && status.state === "ready",
    busy: () => generating,
    lastThought: () => lastThought,
    canThink: () => backend === "gpu",
    setAllowed: setAllowed,
    permitted: permitted,
    backend: () => backend,
    status: () => status,
    saved: saved,
    gpuInfo: gpuInfo,
    chat: chat,
    stop: stop,
    codeBlocks: codeBlocks,
    onChange: (fn) => { listeners.add(fn); fn(status); return () => listeners.delete(fn); }
  };
})();
