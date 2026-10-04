/* Rai Зрение — что на картинке: небо, солнце, закат, облака, море, горы, люди, животные, еда, машины, здания,
   скриншоты, графики… (500 понятий) + основные цвета, тон и яркость. Работает прямо в браузере:
   - модель CLIP (часть, которая «смотрит» на картинку, ≈ 90 МБ, один раз — дальше из кэша браузера) — transformers.js;
   - «отпечатки» понятий заранее посчитал GitHub (tools/build_vision.py → vision_labels.json), поэтому вторая
     половина модели (для текста) не нужна.
   Картинка никуда не отправляется. Модель и библиотека берутся с вашего сайта (ai.php), если он есть. Всё
   управление — window.RaiVision. */
(function () {
  "use strict";

  const TF_VERSION = "4.3.0";
  // Полная сборка: onnxruntime внутри (в «web»-сборке он подключается по имени — так умеет только сборщик кода)
  const TF_FILE = "dist/transformers.min.js";
  const TF_CDN = `https://cdn.jsdelivr.net/npm/@huggingface/transformers@${TF_VERSION}/${TF_FILE}`;
  const TF_ESM = `https://cdn.jsdelivr.net/npm/@huggingface/transformers@${TF_VERSION}/+esm`;  // запасной: jsdelivr сам связывает модули
  const MODEL = "Xenova/clip-vit-base-patch32";

  let lib = null, processor = null, model = null, vocab = null, loading = null;

  async function readVocab() {
    const el = document.getElementById("rai-vision");
    if (el) return JSON.parse(el.textContent);
    const url = window.RAI_VISION_URL || ((window.RAI_CONFIG && window.RAI_CONFIG.pyBase) || "./").replace(/\/?$/, "/") + "vision_labels.json";
    const r = await fetch(url);
    if (!r.ok) throw new Error("словарь понятий не загрузился (" + r.status + ")");
    return r.json();
  }
  function decode(data) {
    const bin = atob(data.emb), n = data.labels.length, d = data.dim, out = new Float32Array(n * d);
    for (let i = 0; i < n * d; i++) { let b = bin.charCodeAt(i); if (b > 127) b -= 256; out[i] = b * data.scale; }
    return out;
  }

  let libLoading = null;
  /** Библиотека transformers.js (одна на зрение и расшифровку речи): с сайта Rai (ai.php) или с jsDelivr. */
  function library() {
    if (libLoading) return libLoading;
    libLoading = (async () => {
      const mirror = window.RAI_AI && window.RAI_AI.pathInfo ? window.RAI_AI.root : null;
      const fromSite = mirror ? `${mirror}/npm/@huggingface/transformers@${TF_VERSION}/${TF_FILE}` : null;
      let found = null;
      for (const url of [fromSite, TF_CDN, TF_ESM].filter(Boolean)) {
        try { found = await import(url); if (found && found.AutoProcessor) break; } catch (e) { found = null; console.warn("Rai:", url, e && e.message); }
      }
      if (!found || !found.AutoProcessor) throw new Error("библиотека нейросетей не загрузилась");
      found.env.allowLocalModels = false;
      if (mirror) found.env.remoteHost = mirror + "/hf/";
      return found;
    })();
    libLoading.catch(() => { libLoading = null; });
    return libLoading;
  }

  /** Загрузить модель (один раз). onStep(текст) — для строки «Загружаю…». */
  function load(onStep) {
    if (loading) return loading;
    loading = (async () => {
      onStep && onStep("Загружаю зрение Rai…");
      const data = await readVocab();
      const mirror = window.RAI_AI && window.RAI_AI.pathInfo ? window.RAI_AI.root : null;
      lib = await library();
      const progress = (p) => {
        if (onStep && p && p.status === "progress" && /vision_model/.test(p.file || "")) onStep(`Загружаю зрение Rai… ${Math.round(p.progress || 0)}%`);
      };
      const open = async () => {
        processor = await lib.AutoProcessor.from_pretrained(MODEL);
        model = await lib.CLIPVisionModelWithProjection.from_pretrained(MODEL, {dtype: "q8", device: "wasm", progress_callback: progress});
      };
      try { await open(); } catch (e) {
        if (!mirror) throw e;
        lib.env.remoteHost = "https://huggingface.co/";  // свой сайт не отдал модель — с исходного сервера
        await open();
      }
      vocab = {data: data, emb: decode(data)};
    })();
    loading.catch(() => { loading = null; });
    return loading;
  }

  // ---------------------------------------------------------------- цвета, тон, яркость
  const COLOR = (h, s, v) => {
    if (v < 0.18) return "чёрный";
    if (s < 0.16) return v > 0.82 ? "белый" : "серый";
    if (h < 15 || h >= 345) return v < 0.45 ? "бордовый" : "красный";
    if (h < 40) return v < 0.6 ? "коричневый" : "оранжевый";
    if (h < 68) return v < 0.5 ? "оливковый" : "жёлтый";
    if (h < 160) return "зелёный";
    if (h < 200) return "голубой";
    if (h < 255) return "синий";
    if (h < 290) return "фиолетовый";
    return "розовый";
  };
  const WARM = new Set(["красный", "бордовый", "оранжевый", "коричневый", "жёлтый", "розовый"]);
  const COOL = new Set(["зелёный", "голубой", "синий", "фиолетовый"]);
  function palette(img) {
    const c = document.createElement("canvas"), n = 48;
    c.width = n; c.height = n;
    const g = c.getContext("2d", {willReadFrequently: true});
    g.drawImage(img, 0, 0, n, n);
    const px = g.getImageData(0, 0, n, n).data, count = {};
    let light = 0;
    for (let i = 0; i < px.length; i += 4) {
      const r = px[i] / 255, gr = px[i + 1] / 255, b = px[i + 2] / 255, max = Math.max(r, gr, b), min = Math.min(r, gr, b), d = max - min;
      let h = 0;
      if (d) h = max === r ? 60 * (((gr - b) / d) % 6) : max === gr ? 60 * ((b - r) / d + 2) : 60 * ((r - gr) / d + 4);
      if (h < 0) h += 360;
      const name = COLOR(h, max ? d / max : 0, max);
      count[name] = (count[name] || 0) + 1;
      light += max;
    }
    const total = n * n;
    const colors = Object.entries(count).map(([name, k]) => ({name: name, share: k / total}))
      .filter((x) => x.share >= 0.07).sort((a, b) => b.share - a.share).slice(0, 4);
    const warm = colors.filter((x) => WARM.has(x.name)).reduce((s, x) => s + x.share, 0);
    const cool = colors.filter((x) => COOL.has(x.name)).reduce((s, x) => s + x.share, 0);
    const avg = light / total;
    return {colors: colors, tone: warm > cool * 1.5 && warm > 0.25 ? "тёплые" : cool > warm * 1.5 && cool > 0.25 ? "холодные" : "",
            light: avg < 0.33 ? "тёмная" : avg > 0.7 ? "светлая" : ""};
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("картинка не открылась"));
      img.src = src;
    });
  }

  /** Что на одной картинке: {labels: [{ru, en, group, p}], colors, tone, light}. */
  async function look(src, onStep) {
    await load(onStep);
    const img = await loadImage(src);
    const look = palette(img);
    const raw = await lib.RawImage.fromURL(src);
    const inputs = await processor(raw);
    const out = await model(inputs);
    const v = (out.image_embeds || out.last_hidden_state).data;
    let norm = 0;
    for (let i = 0; i < v.length; i++) norm += v[i] * v[i];
    norm = Math.sqrt(norm) || 1;
    const {data, emb} = vocab, d = data.dim, n = data.labels.length, logits = new Float32Array(n);
    let best = -Infinity;
    for (let k = 0; k < n; k++) {
      let s = 0;
      for (let i = 0; i < d; i++) s += emb[k * d + i] * v[i];
      logits[k] = (s / norm) * data.logit_scale;
      if (logits[k] > best) best = logits[k];
    }
    let sum = 0;
    const p = Array.from(logits, (x) => { const e = Math.exp(x - best); sum += e; return e; });
    const ranked = p.map((x, k) => ({k: k, p: x / sum})).sort((a, b) => b.p - a.p);
    const labels = ranked.filter((x, i) => i < 3 || x.p >= 0.02).slice(0, 8).map((x) => {
      const [g, ru, en] = data.labels[x.k];
      return {ru: ru, en: en, group: data.groups[g], p: Math.round(x.p * 1000) / 1000};
    });
    return Object.assign({labels: labels}, look);
  }

  /** Все прикреплённые картинки (и по кадру из записи экрана) → список описаний для движка Rai. */
  async function lookAll(list, onStep) {
    const images = [];
    for (const it of list) {
      if (it.type === "image") images.push(it.full);
      if (it.type === "video" && it.frames && it.frames.length) images.push(it.frames[Math.floor(it.frames.length / 2)]);
    }
    const out = [];
    for (let i = 0; i < Math.min(images.length, 4); i++) {
      onStep && onStep(`Смотрю, что на картинке${images.length > 1 ? ` (${i + 1} из ${images.length})` : ""}…`);
      out.push(await look(images[i], onStep));
    }
    return out;
  }

  window.RaiVision = {load: load, look: look, lookAll: lookAll, palette: palette, library: library, MODEL: MODEL, TF_CDN: TF_CDN};
})();
