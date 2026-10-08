/* Rai Зрение — что на картинке: небо, солнце, закат, облака, море, горы, люди, животные, еда, машины, здания,
   скриншоты, графики… (500 понятий) + основные цвета, тон и яркость. Ещё:
   - признаки: фото это или рисунок, скриншот, документ; улица или помещение; день, ночь, закат; погода, время года;
     сколько людей; ракурс;
   - ~6000 конкретных вещей из энциклопедии Rai (Эйфелева башня, жираф, «Мона Лиза», Сатурн…) — по названию и по
     сходству с фотографией из статьи (vision_topics, догружается при первой картинке). Людей по лицу Rai не узнаёт;
   - на компьютере и уровне High и выше — разбор по частям картинки (что слева, справа, в центре).
   Работает прямо в браузере:
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

  let lib = null, processor = null, model = null, vocab = null, loading = null, topics = null, topicsLoading = null;

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
  function int8(b64) {
    const bin = atob(b64), out = new Int8Array(bin.length);
    for (let i = 0; i < bin.length; i++) { const b = bin.charCodeAt(i); out[i] = b > 127 ? b - 256 : b; }
    return out;
  }

  /** Конкретные вещи из энциклопедии (vision2.php на сайте или vision_topics.json.gz рядом). Нет файла — без них. */
  function loadTopics() {
    if (topicsLoading) return topicsLoading;
    topicsLoading = (async () => {
      let data = null;
      const url = window.RAI_VISION_TOPICS_URL || ((window.RAI_CONFIG && window.RAI_CONFIG.pyBase) || "./").replace(/\/?$/, "/") + "vision_topics.json.gz";
      const r = await fetch(url);
      if (!r.ok) return null;
      const buf = new Uint8Array(await r.arrayBuffer());
      if (buf[0] === 0x1f && buf[1] === 0x8b) {          // файл .gz рядом со страницей — распаковываем сами
        if (typeof DecompressionStream !== "function") return null;
        data = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"))).json();
      } else {
        data = JSON.parse(new TextDecoder().decode(buf));   // сайт (vision2.php) отдаёт уже распакованный JSON
      }
      topics = {data: data, text: int8(data.text), image: int8(data.image)};
      return topics;
    })().catch((e) => { console.warn("Rai: вещи для зрения не загрузились", e); return null; });
    return topicsLoading;
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
      vocab = {data: data, emb: decode(data),
               attr: data.attr_emb ? Array.from(int8(data.attr_emb), (b) => b * data.attr_scale) : null};
      loadTopics();
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

  /** Вектор картинки (длина 1) от модели CLIP. */
  async function embed(raw) {
    const inputs = await processor(raw);
    const out = await model(inputs);
    const v = Float32Array.from((out.image_embeds || out.last_hidden_state).data);
    let norm = 0;
    for (let i = 0; i < v.length; i++) norm += v[i] * v[i];
    norm = Math.sqrt(norm) || 1;
    for (let i = 0; i < v.length; i++) v[i] /= norm;
    return v;
  }

  /** Общие понятия: [{ru, en, group, p}] — лучшие по вероятности. */
  function concepts(v, limit) {
    const {data, emb} = vocab, d = data.dim, n = data.labels.length, logits = new Float32Array(n);
    let best = -Infinity;
    for (let k = 0; k < n; k++) {
      let s = 0;
      for (let i = 0; i < d; i++) s += emb[k * d + i] * v[i];
      logits[k] = s * data.logit_scale;
      if (logits[k] > best) best = logits[k];
    }
    let sum = 0;
    const p = Array.from(logits, (x) => { const e = Math.exp(x - best); sum += e; return e; });
    const ranked = p.map((x, k) => ({k: k, p: x / sum})).sort((a, b) => b.p - a.p);
    return ranked.filter((x, i) => i < 3 || x.p >= 0.02).slice(0, limit || 8).map((x) => {
      const [g, ru, en] = data.labels[x.k];
      return {ru: ru, en: en, group: data.groups[g], p: Math.round(x.p * 1000) / 1000};
    });
  }

  /** Признаки: что это (фото, рисунок, скриншот…), где, когда, погода, время года, люди, ракурс. */
  function attributes(v) {
    const {data, attr} = vocab;
    if (!attr || !data.attrs) return [];
    const d = data.dim, out = [];
    let row = 0;
    for (const a of data.attrs) {
      const logits = a.options.map((_, j) => {
        let s = 0;
        for (let i = 0; i < d; i++) s += attr[(row + j) * d + i] * v[i];
        return s * data.logit_scale;
      });
      row += a.options.length;
      const best = Math.max(...logits);
      const ex = logits.map((x) => Math.exp(x - best)), sum = ex.reduce((x, y) => x + y, 0);
      const k = ex.indexOf(Math.max(...ex));
      out.push({key: a.key, ru: a.ru, value: a.options[k], p: Math.round(ex[k] / sum * 1000) / 1000});
    }
    return out;
  }

  // Порог сходства с фотографией из статьи: чем «похожее» выглядят разные вещи этого вида, тем он выше
  const PHOTO_MIN = {landmark: 0.8, art: 0.82, animal: 0.8, plant: 0.8, food: 0.82, place: 0.86, thing: 0.84, space: 0.9};
  /** Конкретные вещи: по сходству с фото из статьи и по названию. [{title, en, kind, by, score}] */
  function known(v) {
    if (!topics) return [];
    const {data, text, image} = topics, d = data.dim, n = data.topics.length;
    let bestPhoto = -1, photo = -1, nameRank = [];
    for (let k = 0; k < n; k++) {
      const has = data.topics[k][4], off = k * d;
      if (has & 2) {
        let s = 0;
        for (let i = 0; i < d; i++) s += image[off + i] * v[i];
        s *= data.image_scale;
        if (s > bestPhoto) { bestPhoto = s; photo = k; }
      }
      if (has & 1) {
        let s = 0;
        for (let i = 0; i < d; i++) s += text[off + i] * v[i];
        nameRank.push([s * data.text_scale, k]);
      }
    }
    const out = [];
    const item = (k) => ({title: data.topics[k][0], en: data.topics[k][1], kind: data.kinds[data.topics[k][3]], section: data.sections[data.topics[k][2]]});
    if (photo >= 0 && bestPhoto >= (PHOTO_MIN[data.kinds[data.topics[photo][3]]] || 0.85)) {
      out.push(Object.assign(item(photo), {by: "photo", score: Math.round(bestPhoto * 1000) / 1000}));
    }
    nameRank.sort((a, b) => b[0] - a[0]);
    if (nameRank.length) {
      // насколько лучший вариант по названию выделяется среди 20 следующих (как уверенность)
      const top = nameRank.slice(0, 20), best = top[0][0];
      const ex = top.map(([s]) => Math.exp((s - best) * 100)), sum = ex.reduce((x, y) => x + y, 0);
      const p = ex[0] / sum, k = top[0][1];
      if (best >= 0.27 && p >= 0.45 && !out.some((x) => x.title === data.topics[k][0])) {
        out.push(Object.assign(item(k), {by: "name", score: Math.round(best * 1000) / 1000, p: Math.round(p * 1000) / 1000}));
      }
    }
    return out;
  }

  /** Что в разных частях картинки (4 четверти и центр) — для подробного разбора. */
  async function regions(raw, main) {
    const W = raw.width, H = raw.height, out = [];
    const parts = [["слева вверху", 0, 0, 0.55, 0.55], ["справа вверху", 0.45, 0, 1, 0.55], ["слева внизу", 0, 0.45, 0.55, 1],
                   ["справа внизу", 0.45, 0.45, 1, 1], ["в центре", 0.25, 0.25, 0.75, 0.75]];
    for (const [where, x0, y0, x1, y1] of parts) {
      try {
        const crop = await raw.crop([Math.round(x0 * W), Math.round(y0 * H), Math.round(x1 * W) - 1, Math.round(y1 * H) - 1]);
        const top = concepts(await embed(crop), 1)[0];
        if (top && top.p >= 0.3 && top.ru !== main) out.push({where: where, ru: top.ru, group: top.group, p: top.p});
      } catch (e) { /* часть не разобралась — пропускаем */ }
    }
    return out;
  }

  /** Что на одной картинке: {labels, attrs, known, regions, colors, tone, light}. opts.detail — разбор по частям. */
  async function look(src, onStep, opts) {
    await load(onStep);
    const t0 = performance.now();
    const img = await loadImage(src);
    const view = palette(img);
    const raw = await lib.RawImage.fromURL(src);
    const v = await embed(raw);
    const labels = concepts(v);
    await Promise.race([loadTopics(), new Promise((r) => setTimeout(r, 8000))]);   // не ждём вечно
    const out = Object.assign({labels: labels, attrs: attributes(v), known: known(v)}, view);
    if (opts && opts.detail && raw.width >= 200 && raw.height >= 200) {
      onStep && onStep("Рассматриваю части картинки…");
      out.regions = await regions(raw, labels[0] && labels[0].ru);
    }
    out.ms = Math.round(performance.now() - t0);
    return out;
  }

  /** Все прикреплённые картинки (и по кадру из записи экрана) → список описаний для движка Rai. */
  async function lookAll(list, onStep, opts) {
    const images = [];
    for (const it of list) {
      if (it.type === "image") images.push(it.full);
      if (it.type === "video" && it.frames && it.frames.length) images.push(it.frames[Math.floor(it.frames.length / 2)]);
    }
    const out = [];
    for (let i = 0; i < Math.min(images.length, 4); i++) {
      onStep && onStep(`Смотрю, что на картинке${images.length > 1 ? ` (${i + 1} из ${images.length})` : ""}…`);
      out.push(await look(images[i], onStep, opts));
    }
    return out;
  }

  window.RaiVision = {load: load, look: look, lookAll: lookAll, palette: palette, library: library, loadTopics: loadTopics,
                      MODEL: MODEL, TF_CDN: TF_CDN};
})();
