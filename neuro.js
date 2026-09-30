/* Rai Нейро — открытая нейросеть прямо в браузере. Без API и ключей: модель один раз загружается в браузер
   (сама, в фоне) и дальше работает на компьютере посетителя, сообщения никуда не уходят.
   - Есть видеокарта с WebGPU — WebLLM и модели Qwen3.5 (быстро).
   - Нет WebGPU — wllama (llama.cpp на WebAssembly) и модель поменьше на процессоре (медленнее, но работает везде).
   Страница подключает этот файл; всё управление — через window.RaiNeuro. */
(function () {
  "use strict";

  const GPU_LIB = "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm";
  const CPU_LIB = "https://cdn.jsdelivr.net/npm/@wllama/wllama@3.6.1/esm/index.js";
  const CPU_WASM = "https://cdn.jsdelivr.net/npm/@wllama/wllama@3.6.1/esm/wasm/wllama.wasm";
  const STORE = "rai_neuro";
  // gpu: модели из официального списка WebLLM (f16 быстрее, f32 — для видеокарт без half-float);
  // cpu: те же по уровню модели в формате GGUF для процессора (Hugging Face, открытые веса Qwen).
  const MODELS = {
    fast: {name: "Быстрая", label: "Qwen3.5 0.8B", size: "≈ 0,6 ГБ", memory: "2 ГБ",
           f16: "Qwen3.5-0.8B-q4f16_1-MLC", f32: "Qwen3.5-0.8B-q4f32_1-MLC",
           cpu: {repo: "Qwen/Qwen2.5-0.5B-Instruct-GGUF", file: "qwen2.5-0.5b-instruct-q4_k_m.gguf", label: "Qwen2.5 0.5B", size: "≈ 0,4 ГБ"}},
    normal: {name: "Умная", label: "Qwen3.5 2B", size: "≈ 1,4 ГБ", memory: "2,6 ГБ",
             f16: "Qwen3.5-2B-q4f16_1-MLC", f32: "Qwen3.5-2B-q4f32_1-MLC",
             cpu: {repo: "Qwen/Qwen2.5-1.5B-Instruct-GGUF", file: "qwen2.5-1.5b-instruct-q4_k_m.gguf", label: "Qwen2.5 1.5B", size: "≈ 1,1 ГБ"}},
    strong: {name: "Очень умная", label: "Qwen3.5 4B", size: "≈ 2,6 ГБ", memory: "4,7 ГБ",
             f16: "Qwen3.5-4B-q4f16_1-MLC", f32: "Qwen3.5-4B-q4f32_1-MLC",
             cpu: {repo: "Qwen/Qwen2.5-3B-Instruct-GGUF", file: "qwen2.5-3b-instruct-q4_k_m.gguf", label: "Qwen2.5 3B", size: "≈ 2 ГБ"}},
    max: {name: "Максимум", label: "Qwen3.5 9B", size: "≈ 5,5 ГБ", memory: "7,5 ГБ",
          f16: "Qwen3.5-9B-q4f16_1-MLC", f32: "Qwen3.5-9B-q4f32_1-MLC"},
    coder: {name: "Программист", label: "Qwen2.5-Coder 7B", size: "≈ 4,5 ГБ", memory: "5 ГБ",
            f16: "Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC", f32: "Qwen2.5-Coder-7B-Instruct-q4f32_1-MLC"}
  };

  const SYSTEM = [
    "Ты — Rai, умный ИИ-ассистент команды Rteam. Отвечай на языке пользователя (по умолчанию по-русски), понятно, точно и по делу.",
    "Думай шаг за шагом, но пиши только итог. Оформляй ответы в Markdown: заголовки, списки, таблицы, **жирный**.",
    "Если в сообщении есть «Сведения из интернета» — опирайся на них, это свежие данные, и ставь ссылки на источники в виде [название](адрес).",
    "Если просят программу, сайт, страницу или игру — пиши полный рабочий код целиком в одном блоке ```язык, без сокращений, «…» и заглушек.",
    "Сайты, страницы и браузерные игры делай одним файлом index.html: CSS и JavaScript внутри, без внешних библиотек, современный красивый дизайн, адаптивный под телефон.",
    "После кода коротко объясни, как им пользоваться. Не выдумывай факты: если не знаешь и в сведениях этого нет — честно скажи."
  ].join(" ");

  const CODE_SYSTEM = [
    "Ты — Rai Code, помощник программиста. Отвечай по-русски.",
    "Когда пишешь или исправляешь код — верни ВЕСЬ файл целиком в одном блоке ```язык, без сокращений и заглушек, затем 1–3 предложения о том, что сделано.",
    "Веб-страницы и игры — одним файлом index.html (CSS и JS внутри, без внешних библиотек)."
  ].join(" ");

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
    return {ok: true, f16: !!(adapter.features && adapter.features.has("shader-f16")), buffer: limits.maxBufferSize || 0};
  }

  function saved() {
    try { return localStorage.getItem(STORE); } catch (e) { return null; }
  }
  function remember(key) {
    try { if (key) localStorage.setItem(STORE, key); else localStorage.removeItem(STORE); } catch (e) { /* без запоминания */ }
  }
  const mobile = () => /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "");
  const saveData = () => !!(navigator.connection && navigator.connection.saveData);

  /** Какую модель взять самому: по памяти устройства и видеокарте. */
  async function pick() {
    const gpu = window.RAI_NEURO_TEST ? {ok: true, f16: true, buffer: 4e9} : await gpuInfo();
    const ram = navigator.deviceMemory || 4;
    if (!gpu.ok) return {key: ram >= 8 && !mobile() ? "normal" : "fast", gpu: gpu};
    if (mobile() || ram < 8) return {key: "fast", gpu: gpu};
    return {key: "normal", gpu: gpu};
  }

  /** Включить нейросеть: скачать модель (или взять из кэша браузера) и запустить в фоновом потоке. */
  async function enable(key) {
    key = MODELS[key] ? key : (await pick()).key;
    if (engine && current === key) return engine;
    if (loading) return loading;
    loading = (async () => {
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
          engine = await window.RAI_NEURO_TEST.create(id, progress);
        } else {
          const webllm = await import(GPU_LIB);
          const src = `import * as w from "${GPU_LIB}"; const h = new w.WebWorkerMLCEngineHandler(); self.onmessage = (m) => h.onmessage(m);`;
          worker = new Worker(URL.createObjectURL(new Blob([src], {type: "text/javascript"})), {type: "module"});
          engine = await webllm.CreateWebWorkerMLCEngine(worker, id, {initProgressCallback: progress}, {context_window_size: 8192});
        }
        backend = "gpu";
        current = key;
        emit({label: model.label});
      } else {
        // Без видеокарты — на процессоре (WebAssembly). Самые большие модели здесь не потянуть.
        const cpu = model.cpu || MODELS.normal.cpu;
        emit({text: "Видеокарты нет — запускаю нейросеть на процессоре…"});
        if (window.RAI_NEURO_TEST) {
          engine = await window.RAI_NEURO_TEST.create(cpu.file, (r) => onProgress(r.progress || 0));
        } else {
          const {Wllama} = await import(CPU_LIB);
          const w = new Wllama({default: CPU_WASM}, {logger: {debug() {}, log() {}, warn: console.warn, error: console.error}});
          await w.loadModelFromHF({repo: cpu.repo, file: cpu.file},
            {n_ctx: 4096, progressCallback: ({loaded, total}) => onProgress(total ? loaded / total : 0)});
          engine = {
            wllama: w,
            unload: () => w.exit(),
            chat: {completions: {create: (opts) => w.createChatCompletion(Object.assign({}, opts, {abortSignal: abort && abort.signal}))}}
          };
        }
        backend = "cpu";
        current = model.cpu ? key : "normal";
        emit({label: cpu.label + " · процессор"});
      }
      remember(key);
      emit({state: "ready", progress: 1, text: "Нейросеть: " + status.label, model: key, backend: backend});
      return engine;
    })();
    try {
      return await loading;
    } catch (e) {
      engine = null; current = null; backend = null;
      emit({state: "error", progress: 0, text: (e && e.message) || String(e)});
      throw e;
    } finally {
      loading = null;
    }
  }

  async function disable(keepChoice) {
    if (engine && engine.unload) { try { await engine.unload(); } catch (e) { /* уже выгружена */ } }
    if (worker) worker.terminate();
    engine = null; worker = null; current = null; backend = null;
    if (!keepChoice) { remember("off"); emit({state: "off", text: "Нейросеть выключена", progress: 0, label: ""}); }
  }

  /** Сам включить нейросеть при открытии страницы: на компьютере — да, на телефоне и в режиме экономии трафика — только если её уже включали. */
  async function auto() {
    const choice = saved();
    if (choice === "off") return null;
    if (choice && MODELS[choice]) return enable(choice).catch(() => null);
    if (saveData() || mobile()) return null;
    const {key} = await pick();
    return enable(key).catch(() => null);
  }

  // Модели Qwen3/3.5 умеют «размышлять» вслух — в ответ это не пускаем.
  function clean(text) {
    return String(text || "").replace(/<think>[\s\S]*?(?:<\/think>|$)/g, "").replace(/^\s+/, "");
  }

  /**
   * Ответ нейросети по сообщениям [{role, content}]. onText(весь текст) вызывается по мере написания.
   * Возвращает полный текст. stop() прерывает ответ.
   */
  let generating = false;
  async function chat(messages, onText, opts) {
    if (!engine) throw new Error("Нейросеть не включена");
    generating = true;
    abort = typeof AbortController === "function" ? new AbortController() : null;
    let raw = "";
    try {
      const stream = await engine.chat.completions.create({
        messages: [{role: "system", content: (opts && opts.system) || SYSTEM}].concat(messages),
        stream: true, temperature: (opts && opts.temperature) ?? 0.5, top_p: 0.9,
        max_tokens: (opts && opts.maxTokens) || 3000,
        extra_body: {enable_thinking: false}
      });
      for await (const chunk of stream) {
        const delta = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
        if (delta) { raw += delta; onText && onText(clean(raw)); }
      }
    } catch (e) {
      if (!(abort && abort.signal.aborted)) throw e;  // остановили кнопкой — это не ошибка
    } finally {
      generating = false;
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
    MODELS: MODELS,
    SYSTEM: SYSTEM,
    CODE_SYSTEM: CODE_SYSTEM,
    enable: enable,
    disable: () => disable(false),
    auto: auto,
    pick: pick,
    ready: () => !!engine && status.state === "ready",
    busy: () => generating,
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
