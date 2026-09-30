/* Rai Нейро — открытая нейросеть Qwen2.5-Coder прямо в браузере (WebLLM, WebGPU). Без API и ключей:
   модель один раз скачивается в браузер и дальше работает на компьютере посетителя.
   Страница подключает этот файл; всё управление — через window.RaiNeuro. */
(function () {
  "use strict";

  const LIB = "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.85/+esm";
  const STORE = "rai_neuro";
  // Модели из официального списка WebLLM. f16 быстрее, f32 — для видеокарт без поддержки half-float.
  const MODELS = {
    fast: {name: "Быстрая", size: "≈ 0,4 ГБ", memory: "1 ГБ", f16: "Qwen2.5-Coder-0.5B-Instruct-q4f16_1-MLC", f32: "Qwen2.5-Coder-0.5B-Instruct-q4f32_1-MLC",
           label: "Qwen2.5-Coder 0.5B"},
    normal: {name: "Обычная", size: "≈ 1 ГБ", memory: "1,6 ГБ", f16: "Qwen2.5-Coder-1.5B-Instruct-q4f16_1-MLC", f32: "Qwen2.5-Coder-1.5B-Instruct-q4f32_1-MLC",
             label: "Qwen2.5-Coder 1.5B"},
    strong: {name: "Сильная", size: "≈ 2 ГБ", memory: "2,5 ГБ", f16: "Qwen2.5-Coder-3B-Instruct-q4f16_1-MLC", f32: "Qwen2.5-Coder-3B-Instruct-q4f32_1-MLC",
             label: "Qwen2.5-Coder 3B"},
    max: {name: "Максимум", size: "≈ 4,5 ГБ", memory: "5 ГБ", f16: "Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC", f32: "Qwen2.5-Coder-7B-Instruct-q4f32_1-MLC",
          label: "Qwen2.5-Coder 7B"}
  };

  const SYSTEM = [
    "Ты — Rai, ИИ-ассистент команды Rteam. Отвечай на языке пользователя (по умолчанию по-русски), понятно и по делу.",
    "Оформляй ответы в Markdown: заголовки, списки, таблицы, **жирный**.",
    "Если просят программу, сайт, страницу или игру — пиши полный рабочий код целиком в одном блоке ```язык, без сокращений, «…» и заглушек.",
    "Сайты, страницы и браузерные игры делай одним файлом index.html: CSS и JavaScript внутри, без внешних библиотек, современный красивый дизайн, адаптивный под телефон.",
    "После кода коротко объясни, как им пользоваться. Не выдумывай факты: если не знаешь — честно скажи."
  ].join(" ");

  const CODE_SYSTEM = [
    "Ты — Rai Code, помощник программиста. Отвечай по-русски.",
    "Когда пишешь или исправляешь код — верни ВЕСЬ файл целиком в одном блоке ```язык, без сокращений и заглушек, затем 1–3 предложения о том, что сделано.",
    "Веб-страницы и игры — одним файлом index.html (CSS и JS внутри, без внешних библиотек)."
  ].join(" ");

  let engine = null, worker = null, loading = null, current = null, listeners = new Set();
  let status = {state: "off", text: "Нейросеть выключена", progress: 0};

  function emit(patch) {
    status = Object.assign({}, status, patch);
    for (const fn of listeners) { try { fn(status); } catch (e) { /* подписчик упал — не страшно */ } }
  }

  async function gpuInfo() {
    if (!navigator.gpu) return {ok: false, why: "В этом браузере нет WebGPU. Нужен свежий Chrome или Edge на компьютере (или Chrome на Android 121+)."};
    let adapter = null;
    try { adapter = await navigator.gpu.requestAdapter(); } catch (e) { adapter = null; }
    if (!adapter) return {ok: false, why: "WebGPU есть, но видеокарта недоступна (выключено ускорение или старый драйвер)."};
    return {ok: true, f16: adapter.features && adapter.features.has("shader-f16")};
  }

  function saved() {
    try { return localStorage.getItem(STORE); } catch (e) { return null; }
  }
  function remember(key) {
    try { if (key) localStorage.setItem(STORE, key); else localStorage.removeItem(STORE); } catch (e) { /* без запоминания */ }
  }

  /** Включить нейросеть: скачать модель (или взять из кэша браузера) и запустить в фоновом потоке. */
  async function enable(key) {
    key = MODELS[key] ? key : "normal";
    if (engine && current === key) return engine;
    if (loading) return loading;
    loading = (async () => {
      emit({state: "loading", text: "Проверяю видеокарту…", progress: 0, model: key});
      const gpu = window.RAI_NEURO_TEST ? {ok: true, f16: true} : await gpuInfo();
      if (!gpu.ok) throw new Error(gpu.why);
      const model = MODELS[key];
      const id = gpu.f16 ? model.f16 : model.f32;
      await disable(true);
      const onProgress = (r) => {
        const p = typeof r.progress === "number" ? r.progress : 0;
        emit({state: "loading", progress: p, text: "Загружаю нейросеть: " + Math.round(p * 100) + "%" +
             (r.text && /cache|кэш/i.test(r.text) ? " (из кэша)" : "")});
      };
      if (window.RAI_NEURO_TEST) {
        engine = await window.RAI_NEURO_TEST.create(id, onProgress);
      } else {
        const webllm = await import(LIB);
        const src = `import * as w from "${LIB}"; const h = new w.WebWorkerMLCEngineHandler(); self.onmessage = (m) => h.onmessage(m);`;
        worker = new Worker(URL.createObjectURL(new Blob([src], {type: "text/javascript"})), {type: "module"});
        engine = await webllm.CreateWebWorkerMLCEngine(worker, id, {initProgressCallback: onProgress},
                                                       {context_window_size: 8192});
      }
      current = key;
      remember(key);
      emit({state: "ready", progress: 1, text: "Нейросеть: " + model.label, model: key, label: model.label});
      return engine;
    })();
    try {
      return await loading;
    } catch (e) {
      engine = null; current = null;
      emit({state: "error", progress: 0, text: (e && e.message) || String(e)});
      throw e;
    } finally {
      loading = null;
    }
  }

  async function disable(keepChoice) {
    if (engine && engine.unload) { try { await engine.unload(); } catch (e) { /* уже выгружена */ } }
    if (worker) worker.terminate();
    engine = null; worker = null; current = null;
    if (!keepChoice) { remember(null); emit({state: "off", text: "Нейросеть выключена", progress: 0}); }
  }

  /**
   * Ответ нейросети по сообщениям [{role, content}]. onText(весь текст) вызывается по мере написания.
   * Возвращает полный текст. stop() прерывает ответ.
   */
  let generating = false;
  async function chat(messages, onText, opts) {
    if (!engine) throw new Error("Нейросеть не включена");
    generating = true;
    let text = "";
    try {
      const stream = await engine.chat.completions.create({
        messages: [{role: "system", content: (opts && opts.system) || SYSTEM}].concat(messages),
        stream: true, temperature: (opts && opts.temperature) ?? 0.4, top_p: 0.9, max_tokens: (opts && opts.maxTokens) || 3000
      });
      for await (const chunk of stream) {
        const delta = chunk.choices && chunk.choices[0] && chunk.choices[0].delta && chunk.choices[0].delta.content;
        if (delta) { text += delta; onText && onText(text); }
      }
    } finally {
      generating = false;
    }
    return text;
  }
  async function stop() {
    if (engine && generating && engine.interruptGenerate) {
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
    ready: () => !!engine && status.state === "ready",
    busy: () => generating,
    status: () => status,
    saved: saved,
    gpuInfo: gpuInfo,
    chat: chat,
    stop: stop,
    codeBlocks: codeBlocks,
    onChange: (fn) => { listeners.add(fn); fn(status); return () => listeners.delete(fn); }
  };
})();
