/* Rai: скриншоты и запись экрана. Картинки прикрепляются к сообщению, текст на них распознаётся прямо
   в браузере (Tesseract, файлы лежат в папке ocr/ рядом со страницей), а Rai отвечает на вопросы с экрана.
   Страница вызывает RaiScreen.init(host) — см. index.html. */
(function () {
  "use strict";

  const MAX_ITEMS = 6, MAX_FRAMES = 8, FRAME_EVERY = 3000;
  let H = null, el = {}, items = [], rec = null, ocrWorker = null;

  // ---------------------------------------------------------------- картинки
  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("не удалось открыть картинку"));
      img.src = src;
    });
  }
  function toCanvas(source, maxSide) {
    const w = source.videoWidth || source.naturalWidth || source.width, h = source.videoHeight || source.naturalHeight || source.height;
    const scale = Math.min(1, maxSide / Math.max(w, h));
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(w * scale));
    c.height = Math.max(1, Math.round(h * scale));
    c.getContext("2d").drawImage(source, 0, 0, c.width, c.height);
    return c;
  }
  async function addImage(src, name) {
    if (items.length >= MAX_ITEMS) { H.toast(`Можно прикрепить до ${MAX_ITEMS} файлов`); return; }
    const img = await loadImage(src);
    items.push({type: "image", name: name || "скриншот.png", full: toCanvas(img, 2600).toDataURL("image/png"),
                thumb: toCanvas(img, 360).toDataURL("image/jpeg", 0.72)});
    render();
  }
  function addFiles(files) {
    for (const f of files) {
      if (!f.type.startsWith("image/")) { H.toast(f.name + ": это не картинка"); continue; }
      if (f.size > 15 * 1024 * 1024) { H.toast(f.name + ": файл больше 15 МБ"); continue; }
      const r = new FileReader();
      r.onload = () => addImage(r.result, f.name).catch((e) => H.toast(e.message));
      r.readAsDataURL(f);
    }
  }

  // ---------------------------------------------------------------- экран
  const canCapture = () => !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
  function captureError(e) {
    if (e && e.name === "NotAllowedError") H.toast("Доступ к экрану не разрешён");
    else if (e && e.name === "NotReadableError") H.toast("Не удалось захватить экран — закройте другие программы записи и попробуйте ещё раз");
    else H.toast("Снимать экран здесь нельзя — откройте Rai в отдельной вкладке браузера на компьютере");
  }
  async function snapshot() {
    closeMenu();
    if (!canCapture()) { captureError(); return; }
    let stream;
    try { stream = await navigator.mediaDevices.getDisplayMedia({video: true, audio: false}); }
    catch (e) { captureError(e); return; }
    try {
      const video = document.createElement("video");
      video.muted = true; video.playsInline = true; video.srcObject = stream;
      await video.play();
      await new Promise((r) => setTimeout(r, 400));
      await addImage(toCanvas(video, 2600).toDataURL("image/png"), "снимок-экрана.png");
      H.toast("Снимок экрана прикреплён");
    } finally {
      stream.getTracks().forEach((t) => t.stop());
    }
  }
  function pickMime() {
    for (const m of ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm", "video/mp4"]) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(m)) return m;
    }
    return "";
  }
  async function startRecording() {
    closeMenu();
    if (rec) return;
    if (!canCapture() || !window.MediaRecorder) { captureError(); return; }
    let stream;
    try { stream = await navigator.mediaDevices.getDisplayMedia({video: true, audio: true}); }
    catch (e) { captureError(e); return; }
    if (!stream.getVideoTracks().length) { stream.getTracks().forEach((t) => t.stop()); captureError(); return; }
    const mime = pickMime();
    const recorder = new MediaRecorder(stream, mime ? {mimeType: mime} : undefined);
    const video = document.createElement("video");
    video.muted = true; video.playsInline = true; video.srcObject = stream;
    video.play().catch(() => {});
    rec = {recorder, stream, video, chunks: [], frames: [], t0: Date.now(), mime: mime || "video/webm"};
    const grab = () => {
      if (!rec || !video.videoWidth) return;
      const url = toCanvas(video, 2200).toDataURL("image/jpeg", 0.85);
      rec.frames.push(url);
      if (rec.frames.length > MAX_FRAMES) rec.frames.splice(1, 1);  // первый кадр оставляем, остальные — самые свежие
    };
    rec.grabTimer = setInterval(grab, FRAME_EVERY);
    setTimeout(grab, 700);
    rec.tick = setInterval(renderRec, 500);
    recorder.ondataavailable = (e) => { if (e.data && e.data.size) rec.chunks.push(e.data); };
    recorder.onstop = finishRecording;
    stream.getVideoTracks()[0].addEventListener("ended", stopRecording);  // «Закрыть доступ» в браузере
    recorder.start(1000);
    renderRec();
  }
  function stopRecording() {
    if (!rec || rec.stopping) return;
    rec.stopping = true;
    try {
      if (rec.video.videoWidth) rec.frames.push(toCanvas(rec.video, 2200).toDataURL("image/jpeg", 0.85));
      if (rec.frames.length > MAX_FRAMES) rec.frames.splice(1, rec.frames.length - MAX_FRAMES);
    } catch (e) { /* без последнего кадра */ }
    clearInterval(rec.grabTimer);
    clearInterval(rec.tick);
    if (rec.recorder.state !== "inactive") rec.recorder.stop(); else finishRecording();
  }
  function finishRecording() {
    const r = rec;
    rec = null;
    if (!r) return;
    r.stream.getTracks().forEach((t) => t.stop());
    renderRec();
    const blob = new Blob(r.chunks, {type: r.mime.split(";")[0]});
    const seconds = Math.round((Date.now() - r.t0) / 1000);
    if (!blob.size) { H.toast("Запись пустая"); return; }
    const ext = r.mime.includes("mp4") ? "mp4" : "webm";
    items.push({type: "video", name: `запись-экрана-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-")}.${ext}`,
                url: URL.createObjectURL(blob), blob: blob, size: blob.size, seconds: seconds, frames: r.frames,
                thumb: r.frames[0] ? r.frames[0] : null});
    render();
    H.toast(`Запись готова (${seconds} с). Отправьте — Rai разберёт текст на экране`);
  }

  // ---------------------------------------------------------------- распознавание текста
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src; s.onload = resolve; s.onerror = () => reject(new Error("нет " + src));
      document.head.append(s);
    });
  }
  const SOURCES = () => [
    {lib: new URL("ocr/", location.href).href, core: new URL("ocr/core/", location.href).href, lang: new URL("ocr/lang/", location.href).href},
    // те же языки под именем .wasm — для хостингов, которые не отдают .gz (например, просмотр в claude.ai)
    {lib: new URL("ocr/", location.href).href, core: new URL("ocr/core/", location.href).href,
     files: {rus: new URL("ocr/lang/rus.traineddata.wasm", location.href).href, eng: new URL("ocr/lang/eng.traineddata.wasm", location.href).href}},
    // запасной вариант — CDN; языки Tesseract тогда берёт сам (у каждого языка свой пакет)
    {lib: "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/", core: "https://cdn.jsdelivr.net/npm/tesseract.js-core@5.1.1/"}
  ];
  let progressCb = null;
  async function getWorker() {
    if (ocrWorker) return ocrWorker;
    const problems = [];
    // RAI_OCR_LOCAL = false — рядом со страницей нет папки ocr/ (хостинг только с PHP и HTML), сразу CDN
    const sources = SOURCES().filter((src) => window.RAI_OCR_LOCAL !== false || /^https:\/\/cdn\./.test(src.lib));
    // свой сайт (ai.php хранит копию распознавания) — раньше CDN
    const mine = window.RAI_OCR_MIRROR ? [window.RAI_OCR_MIRROR] : [];
    const ordered = sources.filter((x) => !/^https:\/\/cdn\./.test(x.lib)).concat(mine, sources.filter((x) => /^https:\/\/cdn\./.test(x.lib)));
    for (const src of (H.ocrBase ? [H.ocrBase] : []).concat(ordered)) {
      try {
        if (!window.Tesseract) await loadScript(src.lib + "tesseract.min.js");
        const opts = {workerPath: src.lib + "worker.min.js", corePath: src.core, cacheMethod: "none",
                      logger: (m) => { if (progressCb && m && typeof m.progress === "number") progressCb(m.status, m.progress); }};
        if (src.lang) {
          // Tesseract не сообщает об ошибке, если файла языка нет, а просто зависает — проверяем заранее
          const head = await fetch(src.lang + "rus.traineddata.gz", {method: "HEAD"});
          if (!head.ok) throw new Error("нет " + src.lang + "rus.traineddata.gz");
          opts.langPath = src.lang;
        }
        if (src.files) {
          // Кладём языки в кэш Tesseract (IndexedDB) — оттуда он читает их раньше, чем пытается скачать
          for (const [code, url] of Object.entries(src.files)) await cachePut(`./${code}.traineddata`, await gunzipFetch(url));
          opts.cacheMethod = "readOnly";
          opts.langPath = src.lib;
        }
        ocrWorker = await Promise.race([window.Tesseract.createWorker(["rus", "eng"], 1, opts),
          new Promise((_, reject) => setTimeout(() => reject(new Error("распознавание не загрузилось за 90 с")), 90000))]);
        return ocrWorker;
      } catch (e) {
        problems.push((e && e.message) || String(e));
        try { delete window.Tesseract; } catch (_) { window.Tesseract = undefined; }
      }
    }
    throw new Error("не удалось загрузить распознавание текста: " + problems.join("; "));
  }
  /** Записать в хранилище, которое читает Tesseract (idb-keyval: база «keyval-store», таблица «keyval»). */
  function cachePut(key, value) {
    return new Promise((resolve, reject) => {
      const open = indexedDB.open("keyval-store");
      open.onupgradeneeded = () => open.result.createObjectStore("keyval");
      open.onerror = () => reject(open.error);
      open.onsuccess = () => {
        const db = open.result, tx = db.transaction("keyval", "readwrite");
        tx.objectStore("keyval").put(value, key);
        tx.oncomplete = () => { db.close(); resolve(); };
        tx.onerror = () => { db.close(); reject(tx.error); };
      };
    });
  }
  /** Скачать сжатые данные языка и распаковать их в браузере. */
  async function gunzipFetch(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + ": " + r.status);
    const raw = new Uint8Array(await r.arrayBuffer());
    if (raw[0] !== 0x1f || raw[1] !== 0x8b) return raw;  // уже распакован
    if (!window.DecompressionStream) throw new Error("браузер не умеет распаковывать gzip");
    return new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer());
  }
  async function recognize(dataUrl) {
    const img = await loadImage(dataUrl);
    // Мелкий текст на скриншотах распознаётся лучше, если картинку увеличить
    const w = img.naturalWidth, scale = w < 1300 ? Math.min(2.5, 1600 / w) : 1;
    const c = document.createElement("canvas");
    c.width = Math.round(w * scale); c.height = Math.round(img.naturalHeight * scale);
    const ctx = c.getContext("2d");
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, 0, 0, c.width, c.height);
    const worker = await getWorker();
    const r = await worker.recognize(c);
    return (r && r.data && r.data.text) || "";
  }
  /** Распознать все прикреплённые картинки и кадры записи. onStep(текст) — для строки «Распознаю…». */
  async function readAll(list, onStep) {
    const images = [];
    for (const it of list) {
      if (it.type === "image") images.push(it.full);
      if (it.type === "video") images.push(...(it.frames || []));
    }
    const seen = new Set(), texts = [];
    for (let i = 0; i < images.length; i++) {
      progressCb = (status, p) => onStep(`Распознаю текст ${images.length > 1 ? `(${i + 1} из ${images.length}) ` : ""}` +
        (status === "recognizing text" ? Math.round(p * 100) + "%" : "— загружаю распознавание…"));
      onStep(`Распознаю текст ${images.length > 1 ? `(${i + 1} из ${images.length})` : ""}…`);
      const text = await recognize(images[i]);
      // в записи экрана соседние кадры повторяются — убираем одинаковые строки
      const fresh = text.split("\n").filter((l) => { const k = l.trim().toLowerCase(); if (!k || seen.has(k)) return false; seen.add(k); return true; });
      if (fresh.length) texts.push(fresh.join("\n"));
    }
    progressCb = null;
    return texts.join("\n").slice(0, 12000);
  }

  // ---------------------------------------------------------------- интерфейс
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  function kb(n) { return n > 1048576 ? (n / 1048576).toFixed(1) + " МБ" : Math.round(n / 1024) + " КБ"; }
  function render() {
    const bar = el.bar;
    bar.hidden = !items.length;
    bar.innerHTML = "";
    items.forEach((it, i) => {
      const chip = document.createElement("div");
      chip.className = "att-chip";
      chip.innerHTML = (it.thumb ? `<img alt="" src="${it.thumb}">` : `<span class="vid">▶</span>`) +
        `<span class="nm">${esc(it.type === "video" ? `Запись ${it.seconds} с · ${kb(it.size)}` : it.name)}</span>` +
        (it.type === "video" ? `<button type="button" class="dl" title="Скачать запись">${H.icon("down")}</button>` : "") +
        `<button type="button" class="x" aria-label="Убрать">×</button>`;
      chip.querySelector(".x").addEventListener("click", () => { if (it.url) URL.revokeObjectURL(it.url); items.splice(i, 1); render(); });
      const dl = chip.querySelector(".dl");
      if (dl) dl.addEventListener("click", () => H.download(it.name, it.blob));
      bar.append(chip);
    });
    if (items.length) {
      const hint = document.createElement("span");
      hint.className = "att-hint";
      hint.textContent = "Rai прочитает текст и ответит на вопросы. Можно дописать задание: «реши», «переведи», «проверь код».";
      bar.append(hint);
    }
    H.onChange && H.onChange(items.length);
  }
  function renderRec() {
    el.rec.hidden = !rec;
    if (!rec) return;
    const s = Math.round((Date.now() - rec.t0) / 1000);
    el.recTime.textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
  }
  function toggleMenu() {
    el.menu.hidden = !el.menu.hidden;
    if (!el.menu.hidden) el.menu.querySelector("button").focus();
  }
  function closeMenu() { el.menu.hidden = true; }

  function init(host) {
    H = host;
    el.bar = document.getElementById("attachBar");
    el.menu = document.getElementById("screenMenu");
    el.rec = document.getElementById("recBar");
    el.recTime = document.getElementById("recTime");
    el.file = document.getElementById("attachFile");
    document.getElementById("attach").addEventListener("click", () => el.file.click());
    el.file.addEventListener("change", () => { addFiles(Array.from(el.file.files || [])); el.file.value = ""; });
    document.getElementById("screenBtn").addEventListener("click", toggleMenu);
    document.getElementById("shotBtn").addEventListener("click", snapshot);
    document.getElementById("recBtn").addEventListener("click", startRecording);
    document.getElementById("recStop").addEventListener("click", stopRecording);
    document.addEventListener("click", (e) => { if (!e.target.closest("#screenMenu, #screenBtn")) closeMenu(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
    // Вставка скриншота из буфера (Ctrl+V) и перетаскивание файлов в окно ввода
    host.input.addEventListener("paste", (e) => {
      const files = Array.from((e.clipboardData && e.clipboardData.files) || []).filter((f) => f.type.startsWith("image/"));
      if (files.length) { e.preventDefault(); addFiles(files); }
    });
    const zone = host.dropZone;
    zone.addEventListener("dragover", (e) => { if (e.dataTransfer && Array.from(e.dataTransfer.types).includes("Files")) { e.preventDefault(); zone.classList.add("drop"); } });
    zone.addEventListener("dragleave", () => zone.classList.remove("drop"));
    zone.addEventListener("drop", (e) => { zone.classList.remove("drop"); if (e.dataTransfer.files.length) { e.preventDefault(); addFiles(Array.from(e.dataTransfer.files)); } });
    if (!canCapture()) document.getElementById("screenBtn").title = "Снимок и запись экрана работают в браузере на компьютере";
  }

  window.RaiScreen = {
    init: init,
    items: () => items.slice(),
    take: () => { const list = items; items = []; render(); return list; },
    readAll: readAll,
    recording: () => !!rec
  };
})();
