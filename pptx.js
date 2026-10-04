/* Rai PowerPoint — презентация Rai в файл .pptx, который открывается и правится в PowerPoint, Google Slides, Keynote.
   Библиотека PptxGenJS скачивается с CDN только при первом экспорте. Всё управление — через window.RaiPptx.
   Переходы между слайдами и появление элементов (как в Rai) PptxGenJS не умеет — дописываем их в XML слайдов сами:
   <p:transition> и <p:timing>. Элементы помечены именем «rai-a-<очередь>-<эффект>». */
(function () {
  "use strict";

  const LIB = "https://cdn.jsdelivr.net/npm/pptxgenjs@3.12.0/dist/pptxgen.bundle.js";
  const W = 13.333, H = 7.5, PAD = 0.75;
  const HEAD = "Arial Black", BODY = "Arial", MONO = "Consolas";

  let loading = null;
  function load() {
    if (window.PptxGenJS) return Promise.resolve(window.PptxGenJS);
    if (loading) return loading;
    loading = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = window.RAI_PPTX_URL || LIB;
      s.onload = () => window.PptxGenJS ? resolve(window.PptxGenJS) : reject(new Error("PowerPoint-библиотека не загрузилась"));
      s.onerror = () => reject(new Error("Нет доступа к cdn.jsdelivr.net — проверьте интернет"));
      document.head.append(s);
    }).catch((e) => { loading = null; throw e; });
    return loading;
  }

  // ---------------------------------------------------------------- помощники
  const hex = (c, d) => (/^#[0-9a-f]{6}$/i.test(c || "") ? c : d).slice(1).toUpperCase();
  const plain = (t) => String(t == null ? "" : t).replace(/\*\*(.+?)\*\*/g, "$1").replace(/`([^`]+)`/g, "$1").replace(/==(.+?)==/g, "$1");
  /** Текст с **жирным** → куски для PptxGenJS. */
  function runs(t, opts) {
    const out = [];
    String(t == null ? "" : t).replace(/`([^`]+)`/g, "$1").split(/(\*\*.+?\*\*)/).forEach((part) => {
      if (!part) return;
      const bold = /^\*\*.+\*\*$/.test(part);
      out.push({text: bold ? part.slice(2, -2) : part, options: Object.assign({}, opts, bold ? {bold: true} : {})});
    });
    return out.length ? out : [{text: "", options: opts || {}}];
  }
  /** Размер шрифта по длине текста: длинный текст — мельче, чтобы влез в рамку. */
  function fontFor(value, steps) {
    const n = plain(Array.isArray(value) ? value.join(" ") : value).length;
    for (const [limit, size] of steps) if (n <= limit) return size;
    return steps[steps.length - 1][1] - 2;
  }
  function svgToPng(svg) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        try {
          const cv = document.createElement("canvas");
          cv.width = img.naturalWidth || 1200; cv.height = img.naturalHeight || 800;
          cv.getContext("2d").drawImage(img, 0, 0, cv.width, cv.height);
          resolve({data: cv.toDataURL("image/png"), w: cv.width, h: cv.height});
        } catch (e) { resolve(null); }
      };
      img.onerror = () => resolve(null);
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    });
  }
  async function photoData(url) {
    const direct = await photoFrom(url);
    if (direct || !window.RAI_NET_PROXY) return direct;
    return photoFrom(window.RAI_NET_PROXY + "?url=" + encodeURIComponent(url));  // через посредник на хостинге
  }
  async function photoFrom(url) {
    try {
      const r = await fetch(url, {mode: "cors", referrerPolicy: "no-referrer"});
      if (!r.ok) return null;
      const blob = await r.blob();
      if (!/^image\/(png|jpe?g|gif|webp)/.test(blob.type)) return null;
      const bmp = await createImageBitmap(blob);
      const cv = document.createElement("canvas");
      const k = Math.min(1, 1920 / bmp.width);
      cv.width = Math.round(bmp.width * k); cv.height = Math.round(bmp.height * k);
      cv.getContext("2d").drawImage(bmp, 0, 0, cv.width, cv.height);
      return {data: cv.toDataURL("image/jpeg", 0.88), w: cv.width, h: cv.height};
    } catch (e) { return null; }
  }
  /** Фон слайда: цвет темы и мягкое свечение акцентных цветов (как на сайте). null — нет canvas. */
  function glow(C) {
    if (typeof document === "undefined") return null;
    try {
      const cv = document.createElement("canvas"), w = 1600, h = 900, g = cv.getContext("2d");
      cv.width = w; cv.height = h;
      const rgb = (x) => [0, 2, 4].map((i) => parseInt(x.slice(i, i + 2), 16)).join(",");
      g.fillStyle = "#" + C.bg; g.fillRect(0, 0, w, h);
      [[w * 0.9, h * 0.04, w * 0.62, C.accent, 0.30], [w * 0.04, h * 1.02, w * 0.55, C.accent2, 0.20], [w * 0.55, h * 0.55, w * 0.5, C.accent, 0.05]]
        .forEach(([x, y, r, c, a]) => {
          const gr = g.createRadialGradient(x, y, 0, x, y, r);
          gr.addColorStop(0, `rgba(${rgb(c)},${a})`); gr.addColorStop(1, `rgba(${rgb(c)},0)`);
          g.fillStyle = gr; g.fillRect(0, 0, w, h);
        });
      g.fillStyle = `rgba(${rgb(C.fg)},0.035)`;  // едва заметная сетка точек
      for (let x = 40; x < w; x += 40) for (let y = 40; y < h; y += 40) g.fillRect(x, y, 2, 2);
      return cv.toDataURL("image/jpeg", 0.9);
    } catch (e) { return null; }
  }
  const SHADOW = {type: "outer", blur: 12, offset: 4, angle: 90, color: "000000", opacity: 0.3};

  /** Картинка «обрезкой по рамке» (как object-fit: cover). */
  function cover(slide, pic, x, y, w, h, extra) {
    slide.addImage(Object.assign({data: pic.data, x: x, y: y, w: w, h: h, sizing: {type: "cover", w: w, h: h}}, extra || {}));
  }

  // ---------------------------------------------------------------- слайды
  function build(P, deck, pics) {
    const t = deck.theme || {};
    const C = {
      bg: hex(t.bg, "#0b0b0c"), fg: hex(t.fg, "#f3f1f1"), accent: hex(t.accent, "#e10600"), accent2: hex(t.accent2, t.accent || "#ff6a5c"),
      muted: hex(t.muted, "#9b9599"), surface: hex(t.surface, "#151517"), line: hex(t.line, "#2a2a2e"), on: hex(t.on_accent, "#ffffff")
    };
    const pptx = new P();
    pptx.layout = "LAYOUT_WIDE";
    pptx.author = "Rai";
    pptx.company = "Rteam";
    pptx.title = plain(deck.title || "Презентация");
    const total = deck.slides.length;
    const bg = glow(C);

    deck.slides.forEach((s, i) => {
      const slide = pptx.addSlide();
      slide.background = bg ? {data: bg} : {color: C.bg};
      const pic = pics[i];
      // a(очередь, эффект) — элемент появится сам по очереди: rise (всплывает), fade, zoom, wipe
      const a = (n, fx) => ({objectName: `rai-a-${n}-${fx || "rise"}`});
      const text = (value, o) => slide.addText(runs(value), Object.assign({fontFace: BODY, color: C.fg, margin: 0, valign: "top"}, o));
      const kicker = (label) => text(label || String(i + 1).padStart(2, "0"), Object.assign({x: PAD, y: 0.55, w: 6, h: 0.3, fontFace: MONO, fontSize: 12, color: C.accent, charSpacing: 3}, a(0, "fade")));
      const heading = (value, y) => text(plain(value), Object.assign({x: PAD, y: y || 0.9, w: W - 2 * PAD, h: 0.95, fontFace: HEAD, fontSize: fontFor(value, [[36, 30], [56, 25], [80, 21]]), bold: true, valign: "middle"}, a(1)));
      const card = (x, y, w, h, o) => slide.addShape("roundRect", Object.assign({x: x, y: y, w: w, h: h, rectRadius: 0.12, fill: {color: C.surface}, line: {color: C.line, width: 0.75}, shadow: SHADOW}, o));
      // декоративные круги-«свечения» на обложке и финале
      const orbs = () => {
        slide.addShape("ellipse", {x: W - 3.6, y: -2.2, w: 6, h: 6, fill: {color: C.accent, transparency: 86}, line: {type: "none"}});
        slide.addShape("ellipse", {x: W - 2.2, y: 3.9, w: 3.2, h: 3.2, fill: {color: C.accent2, transparency: 88}, line: {type: "none"}});
      };
      const footer = () => {
        slide.addShape("rect", {x: 0, y: H - 0.1, w: W, h: 0.1, fill: {color: C.accent}, line: {type: "none"}});
        text(`${i + 1} / ${total}`, {x: W - 1.6, y: H - 0.5, w: 1.2, h: 0.25, fontFace: MONO, fontSize: 10, color: C.muted, align: "right"});
      };
      const top = 2.05, bottom = H - 0.7, area = bottom - top;

      switch (s.kind) {
        case "title": {
          if (pic) {
            cover(slide, pic, W * 0.46, 0, W * 0.54, H, a(0, "fade"));
            slide.addShape("rect", Object.assign({x: W * 0.46, y: 0, w: W * 0.54, h: H, fill: {color: C.bg, transparency: 55}, line: {type: "none"}}, a(0, "fade")));
          } else orbs();
          text("ПРЕЗЕНТАЦИЯ", Object.assign({x: PAD, y: 1.6, w: 6, h: 0.3, fontFace: MONO, fontSize: 12, color: C.accent, charSpacing: 4}, a(1, "fade")));
          text(plain(s.title), Object.assign({x: PAD, y: 2.0, w: W * 0.62, h: 2.6, fontFace: HEAD, fontSize: fontFor(s.title, [[22, 48], [40, 40], [70, 32]]), bold: true, valign: "bottom"}, a(2)));
          slide.addShape("rect", Object.assign({x: PAD, y: 4.85, w: 1.6, h: 0.12, fill: {color: C.accent}, line: {type: "none"}}, a(3, "wipe")));
          if (s.subtitle) text(s.subtitle, Object.assign({x: PAD, y: 5.2, w: W * 0.55, h: 1.2, fontSize: 18, color: C.muted}, a(4, "fade")));
          break;
        }
        case "end": {
          if (pic) {
            cover(slide, pic, 0, 0, W, H);
            slide.addShape("rect", {x: 0, y: 0, w: W, h: H, fill: {color: C.bg, transparency: 22}, line: {type: "none"}});
          } else orbs();
          text(plain(s.title), Object.assign({x: PAD, y: 2.2, w: W - 2 * PAD, h: 1.6, fontFace: HEAD, fontSize: fontFor(s.title, [[28, 44], [50, 34]]), bold: true, align: "center", valign: "bottom"}, a(1, "zoom")));
          slide.addShape("rect", Object.assign({x: W / 2 - 0.7, y: 4.1, w: 1.4, h: 0.1, fill: {color: C.accent}, line: {type: "none"}}, a(2, "wipe")));
          if (s.subtitle) text(s.subtitle, Object.assign({x: PAD, y: 4.45, w: W - 2 * PAD, h: 0.8, fontSize: 18, color: C.muted, align: "center"}, a(3, "fade")));
          break;
        }
        case "photo": {
          if (pic) {
            cover(slide, pic, 0, 0, W, H);
            slide.addShape("rect", {x: 0, y: H * 0.55, w: W, h: H * 0.45, fill: {color: C.bg, transparency: 15}, line: {type: "none"}});
          }
          text(String(i + 1).padStart(2, "0"), Object.assign({x: PAD, y: H - 2.85, w: 3, h: 0.3, fontFace: MONO, fontSize: 12, color: C.accent}, a(1, "fade")));
          text(plain(s.title), Object.assign({x: PAD, y: H - 2.5, w: W - 2 * PAD, h: 0.9, fontFace: HEAD, fontSize: fontFor(s.title, [[40, 30], [70, 24]]), bold: true, valign: "middle"}, a(2)));
          if (s.caption) text(s.caption, Object.assign({x: PAD, y: H - 1.55, w: W - 2 * PAD, h: 0.8, fontSize: 16, color: C.muted}, a(3, "fade")));
          break;
        }
        case "agenda": {
          kicker(); heading(s.title || "План");
          const items = (s.items || []).slice(0, 8), rows = Math.ceil(items.length / 2) || 1;
          const cw = (W - 2 * PAD - 0.35) / 2, ch = Math.min(1.05, (area - (rows - 1) * 0.22) / rows);
          items.forEach((it, n) => {
            const x = PAD + (n % 2) * (cw + 0.35), y = top + Math.floor(n / 2) * (ch + 0.22);
            const an = a(2 + n);
            card(x, y, cw, ch, Object.assign({line: {type: "none"}}, an));
            slide.addShape("rect", Object.assign({x: x, y: y, w: 0.08, h: ch, fill: {color: C.accent}, line: {type: "none"}}, an));
            text(String(n + 1).padStart(2, "0"), Object.assign({x: x + 0.3, y: y, w: 0.8, h: ch, fontFace: HEAD, fontSize: 20, bold: true, color: C.accent, valign: "middle"}, an));
            text(it, Object.assign({x: x + 1.15, y: y, w: cw - 1.35, h: ch, fontSize: fontFor(it, [[40, 18], [70, 15]]), valign: "middle"}, an));
          });
          break;
        }
        case "summary": {
          kicker(); heading(s.title || "Главное");
          const items = (s.items || []).slice(0, 6), rows = Math.ceil(items.length / 2) || 1;
          const cw = (W - 2 * PAD - 0.35) / 2, ch = Math.min(1.9, (area - (rows - 1) * 0.3) / rows);
          items.forEach((it, n) => {
            const x = PAD + (n % 2) * (cw + 0.35), y = top + Math.floor(n / 2) * (ch + 0.3);
            const an = a(2 + n);
            card(x, y, cw, ch, an);
            slide.addShape("ellipse", Object.assign({x: x + 0.3, y: y + 0.3, w: 0.55, h: 0.55, fill: {color: C.accent}, line: {type: "none"}}, an));
            text(String(n + 1), Object.assign({x: x + 0.3, y: y + 0.3, w: 0.55, h: 0.55, fontFace: HEAD, fontSize: 16, bold: true, color: C.on, align: "center", valign: "middle"}, an));
            text(it, Object.assign({x: x + 1.1, y: y + 0.3, w: cw - 1.4, h: ch - 0.5, fontSize: fontFor(it, [[60, 18], [110, 15]])}, an));
          });
          break;
        }
        case "stats": {
          kicker(); heading(s.title);
          const items = (s.items || []).slice(0, 4), n = items.length || 1, gap = 0.35;
          const cw = (W - 2 * PAD - (n - 1) * gap) / n, ch = Math.min(3.4, area - 0.4), y = top + (area - ch) / 2;
          items.forEach((it, k) => {
            const x = PAD + k * (cw + gap);
            const an = a(2 + k, "zoom");
            card(x, y, cw, ch, Object.assign({line: {type: "none"}}, an));
            slide.addShape("rect", Object.assign({x: x, y: y, w: cw, h: 0.1, fill: {color: C.accent}, line: {type: "none"}}, an));
            text(plain(it.value), Object.assign({x: x + 0.3, y: y + 0.45, w: cw - 0.6, h: 1.3, fontFace: HEAD, fontSize: fontFor(it.value, n > 3 ? [[5, 36], [8, 28], [11, 22]] : [[6, 44], [9, 34], [12, 26]]), bold: true, color: C.accent, valign: "middle"}, an));
            text(it.label, Object.assign({x: x + 0.3, y: y + 1.9, w: cw - 0.6, h: ch - 2.2, fontSize: fontFor(it.label, [[50, 16], [90, 13]]), color: C.muted}, an));
          });
          break;
        }
        case "timeline": {
          kicker(); heading(s.title);
          const items = (s.items || []).slice(0, 6), n = items.length || 1, gap = 0.3;
          const cw = (W - 2 * PAD - (n - 1) * gap) / n, y = top + 0.6;
          slide.addShape("rect", Object.assign({x: PAD, y: y + 0.95, w: W - 2 * PAD, h: 0.06, fill: {color: C.line}, line: {type: "none"}}, a(2, "wipe")));
          items.forEach((it, k) => {
            const x = PAD + k * (cw + gap), an = a(3 + k);
            text(plain(it.date), Object.assign({x: x, y: y, w: cw, h: 0.6, fontFace: HEAD, fontSize: n > 4 ? 18 : 22, bold: true, color: C.accent, valign: "bottom"}, an));
            slide.addShape("ellipse", Object.assign({x: x, y: y + 0.8, w: 0.36, h: 0.36, fill: {color: C.accent}, line: {color: C.bg, width: 4}}, a(3 + k, "zoom")));
            text(it.text, Object.assign({x: x, y: y + 1.45, w: cw, h: area - 2.1, fontSize: fontFor(it.text, n > 4 ? [[50, 13], [90, 11]] : [[60, 16], [100, 13]])}, an));
          });
          break;
        }
        case "quote": {
          if (pic) {
            cover(slide, pic, 0, 0, W, H);
            slide.addShape("rect", {x: 0, y: 0, w: W, h: H, fill: {color: C.bg, transparency: 15}, line: {type: "none"}});
          }
          text("«", Object.assign({x: PAD + 0.6, y: 0.9, w: 2, h: 1.5, fontFace: HEAD, fontSize: 110, bold: true, color: C.accent, valign: "bottom"}, a(1, "zoom")));
          text(s.text, Object.assign({x: PAD + 0.6, y: 2.5, w: W - 2 * PAD - 1.2, h: 2.9, fontSize: fontFor(s.text, [[60, 36], [120, 28], [200, 22]]), bold: true, valign: "middle"}, a(2)));
          if (s.author) text("— " + plain(s.author), Object.assign({x: PAD + 0.6, y: 5.6, w: W - 2 * PAD - 1.2, h: 0.5, fontFace: MONO, fontSize: 16, color: C.muted}, a(3, "fade")));
          break;
        }
        case "compare": {
          kicker(); heading(s.title);
          const vs = 0.9, cw = (W - 2 * PAD - vs - 0.5) / 2, ch = area - 0.1;
          [[s.left, PAD, false, 2], [s.right, W - PAD - cw, true, 4]].forEach(([c, x, hot, n]) => {
            c = c || {};
            const an = a(n);
            card(x, top, cw, ch, Object.assign(hot ? {line: {color: C.accent, width: 1.5}} : {}, an));
            text(plain(c.title), Object.assign({x: x + 0.35, y: top + 0.3, w: cw - 0.7, h: 0.6, fontFace: HEAD, fontSize: fontFor(c.title, [[18, 20], [40, 16]]), bold: true, color: C.accent}, an));
            const list = (c.items || []).map((it) => ({text: plain(it), options: {bullet: {indent: 18}, paraSpaceAfter: 6}}));
            if (list.length) slide.addText(list, Object.assign({x: x + 0.35, y: top + 1.05, w: cw - 0.7, h: ch - 1.3, fontFace: BODY, fontSize: fontFor(c.items || [], [[160, 18], [300, 15]]), color: C.fg, valign: "top", margin: 0}, an));
          });
          slide.addShape("ellipse", Object.assign({x: W / 2 - vs / 2, y: top + ch / 2 - vs / 2, w: vs, h: vs, fill: {color: C.accent}, line: {type: "none"}, shadow: SHADOW}, a(3, "zoom")));
          text("VS", Object.assign({x: W / 2 - vs / 2, y: top + ch / 2 - vs / 2, w: vs, h: vs, fontFace: HEAD, fontSize: 16, bold: true, color: C.on, align: "center", valign: "middle"}, a(3, "zoom")));
          break;
        }
        case "fact": {
          kicker(); heading(s.title);
          const w = pic ? W * 0.52 : W - 2 * PAD - 0.4;
          slide.addShape("rect", Object.assign({x: PAD, y: top + 0.2, w: 0.1, h: area - 0.6, fill: {color: C.accent}, line: {type: "none"}}, a(2, "wipe")));
          text(s.text, Object.assign({x: PAD + 0.45, y: top + 0.2, w: w, h: area - 0.6, fontSize: fontFor(s.text, [[120, 28], [200, 24], [300, 20]]), bold: true, valign: "middle"}, a(3, "fade")));
          if (pic) cover(slide, pic, W - PAD - W * 0.33, top + 0.3, W * 0.33, W * 0.22, Object.assign({rounding: false}, a(4, "zoom")));
          break;
        }
        case "code": {
          kicker(); heading(s.title);
          card(PAD, top, W - 2 * PAD, area, a(2, "fade"));
          text(String(s.code || "").replace(/\s+$/, ""), Object.assign({x: PAD + 0.3, y: top + 0.25, w: W - 2 * PAD - 0.6, h: area - 0.5, fontFace: MONO, fontSize: Math.max(9, Math.min(16, Math.floor(area * 72 / 1.35 / Math.max(10, String(s.code || "").split("\n").length))))}, a(2, "fade")));
          break;
        }
        case "table": {
          kicker(); heading(s.title);
          const [head, ...rows] = s.rows && s.rows.length ? s.rows : [[]];
          if (head.length) {
            const cell = (v, h) => ({text: plain(v), options: h ? {bold: true, color: C.accent, fill: {color: C.surface}} : {}});
            slide.addTable([head.map((c) => cell(c, true))].concat(rows.map((r) => head.map((_, k) => cell(r[k] || "", false)))), {
              x: PAD, y: top, w: W - 2 * PAD, fontFace: BODY, fontSize: rows.length > 6 ? 12 : 14, color: C.fg,
              border: {type: "solid", pt: 0.75, color: C.line}, autoPage: false, margin: 0.08
            });
          }
          break;
        }
        default: {
          kicker(); heading(s.title);
          const left = s.side === "left";
          const pw = W * 0.36, ph = pw * 2 / 3;
          const tx = pic && left ? PAD + pw + 0.5 : PAD, tw = pic ? W - 2 * PAD - pw - 0.5 : W - 2 * PAD;
          const list = (s.bullets || []).map((b) => ({text: plain(b), options: {bullet: {indent: 22}, paraSpaceAfter: 10}}));
          if (list.length) slide.addText(list, Object.assign({x: tx, y: top, w: tw, h: area, fontFace: BODY, fontSize: fontFor(s.bullets || [], pic ? [[180, 22], [320, 18], [480, 15]] : [[240, 24], [420, 20], [600, 17]]), color: C.fg, valign: "middle", margin: 0}, a(2)));
          if (pic) cover(slide, pic, left ? PAD : W - PAD - pw, top + (area - ph) / 2, pw, ph, a(3, "zoom"));
        }
      }
      footer();
    });
    return pptx;
  }

  // ---------------------------------------------------------------- переходы и анимации внутри .pptx
  // Переходы Rai → переходы PowerPoint (есть во всех версиях PowerPoint, в Keynote и LibreOffice)
  const PPT_TRANSITIONS = {
    fade: '<p:fade/>', slide: '<p:push dir="l"/>', zoom: '<p:zoom dir="in"/>', wipe: '<p:wipe dir="r"/>', rise: '<p:push dir="u"/>'
  };
  const CRC_TABLE = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(u8) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < u8.length; i++) c = CRC_TABLE[(c ^ u8[i]) & 255] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }
  /** Несжатый ZIP (PptxGenJS с compression: false) → [{name, data}]. Читаем по центральному каталогу. */
  function unzip(u8) {
    const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength), dec = new TextDecoder();
    let end = u8.length - 22;
    while (end >= 0 && dv.getUint32(end, true) !== 0x06054b50) end--;
    if (end < 0) throw new Error("файл .pptx повреждён");
    const out = [];
    let p = dv.getUint32(end + 16, true);
    for (let i = dv.getUint16(end + 10, true); i > 0; i--) {
      if (dv.getUint32(p, true) !== 0x02014b50 || dv.getUint16(p + 10, true) !== 0) throw new Error("неожиданный формат .pptx");
      const size = dv.getUint32(p + 20, true), nameLen = dv.getUint16(p + 28, true), local = dv.getUint32(p + 42, true);
      const start = local + 30 + dv.getUint16(local + 26, true) + dv.getUint16(local + 28, true);
      out.push({name: dec.decode(u8.subarray(p + 46, p + 46 + nameLen)), data: u8.subarray(start, start + size)});
      p += 46 + nameLen + dv.getUint16(p + 30, true) + dv.getUint16(p + 32, true);
    }
    return out;
  }
  /** [{name, data}] → ZIP (без сжатия) как список кусков для Blob. */
  function zip(files) {
    const enc = new TextEncoder(), parts = [], central = [];
    let offset = 0;
    for (const f of files) {
      const name = enc.encode(f.name), crc = crc32(f.data), size = f.data.length;
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true);
      h.setUint16(12, 0x21, true); h.setUint32(14, crc, true); h.setUint32(18, size, true); h.setUint32(22, size, true);
      h.setUint16(26, name.length, true);
      parts.push(new Uint8Array(h.buffer), name, f.data);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
      c.setUint16(14, 0x21, true); c.setUint32(16, crc, true); c.setUint32(20, size, true); c.setUint32(24, size, true);
      c.setUint16(28, name.length, true); c.setUint32(42, offset, true);
      central.push(new Uint8Array(c.buffer), name);
      offset += 30 + name.length + size;
    }
    const cdSize = central.reduce((n, x) => n + x.length, 0), e = new DataView(new ArrayBuffer(22));
    e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true);
    e.setUint32(12, cdSize, true); e.setUint32(16, offset, true);
    return parts.concat(central, [new Uint8Array(e.buffer)]);
  }

  /** Эффект появления одного элемента (PowerPoint: «Вход»). */
  function effect(spid, fx, id) {
    const tgt = `<p:tgtEl><p:spTgt spid="${spid}"/></p:tgtEl>`;
    const show = `<p:set><p:cBhvr><p:cTn id="${id()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>${tgt}` +
      `<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>`;
    const filter = (f, dur) => `<p:animEffect transition="in" filter="${f}"><p:cBhvr><p:cTn id="${id()}" dur="${dur}"/>${tgt}</p:cBhvr></p:animEffect>`;
    const anim = (attr, from, to, dur) => `<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base"><p:cTn id="${id()}" dur="${dur}" fill="hold"/>${tgt}` +
      `<p:attrNameLst><p:attrName>${attr}</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst><p:tav tm="0"><p:val><p:strVal val="${from}"/></p:val></p:tav>` +
      `<p:tav tm="100000"><p:val><p:strVal val="${to}"/></p:val></p:tav></p:tavLst></p:anim>`;
    if (fx === "rise") return {preset: 42, sub: 0, xml: show + filter("fade", 600) + anim("ppt_x", "#ppt_x", "#ppt_x", 600) + anim("ppt_y", "#ppt_y+.08", "#ppt_y", 600)};
    if (fx === "zoom") return {preset: 53, sub: 16, xml: show + anim("ppt_w", "0.7*#ppt_w", "#ppt_w", 500) + anim("ppt_h", "0.7*#ppt_h", "#ppt_h", 500) + filter("fade", 500)};
    if (fx === "wipe") return {preset: 22, sub: 8, xml: show + filter("wipe(left)", 600)};
    return {preset: 10, sub: 0, xml: show + filter("fade", 500)};
  }
  /** <p:timing>: элементы с именем «rai-a-<очередь>-<эффект>» появляются сами, по очереди, после показа слайда. */
  function timing(xml) {
    const found = [];
    const re = /<p:(sp|pic)>\s*<p:nv(?:Sp|Pic)Pr>\s*<p:cNvPr id="(\d+)" name="rai-a-(\d+)-([a-z]+)"/g;
    let m;
    while ((m = re.exec(xml))) found.push({sp: m[1] === "sp", id: m[2], order: +m[3], fx: m[4]});
    if (!found.length) return "";
    found.sort((x, y) => x.order - y.order);
    const ranks = [...new Set(found.map((f) => f.order))];
    let n = 4;
    const id = () => ++n;
    const effects = found.map((f, k) => {
      const rank = ranks.indexOf(f.order), delay = rank === 0 ? 0 : 250 + (rank - 1) * 170;
      const outer = id(), e = effect(f.id, f.fx, id);
      return `<p:par><p:cTn id="${outer}" presetID="${e.preset}" presetClass="entr" presetSubtype="${e.sub}" fill="hold" grpId="0" ` +
        `nodeType="${k === 0 ? "afterEffect" : "withEffect"}"><p:stCondLst><p:cond delay="${delay}"/></p:stCondLst>` +
        `<p:childTnLst>${e.xml}</p:childTnLst></p:cTn></p:par>`;
    }).join("");
    const builds = found.filter((f) => f.sp).map((f) => `<p:bldP spid="${f.id}" grpId="0" animBg="1"/>`).join("");
    return `<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>` +
      `<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>` +
      `<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>` +
      `<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>${effects}</p:childTnLst></p:cTn></p:par>` +
      `</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>` +
      `<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>` +
      `<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>` +
      `</p:childTnLst></p:cTn></p:par></p:tnLst>` + (builds ? `<p:bldLst>${builds}</p:bldLst>` : "") + `</p:timing>`;
  }
  /** Готовый .pptx (байты без сжатия) + переходы и анимации → куски файла. */
  function addMotion(u8, deck) {
    const files = unzip(u8), enc = new TextEncoder(), dec = new TextDecoder();
    for (const f of files) {
      const m = /^ppt\/slides\/slide(\d+)\.xml$/.exec(f.name);
      if (!m) continue;
      const s = deck.slides[+m[1] - 1] || {}, kind = PPT_TRANSITIONS[s.transition] ? s.transition : "fade";
      const extra = `<p:transition spd="${kind === "fade" ? "slow" : "med"}">${PPT_TRANSITIONS[kind]}</p:transition>`;
      let xml = dec.decode(f.data);
      if (xml.includes("<p:transition") || xml.includes("<p:timing")) continue;
      const add = extra + timing(xml);
      xml = xml.includes("</p:clrMapOvr>") ? xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + add) : xml.replace("</p:sld>", add + "</p:sld>");
      f.data = enc.encode(xml);
    }
    return zip(files);
  }

  /** Презентация Rai ({title, slides, theme}) → Blob .pptx с переходами и анимациями. */
  async function toBlob(deck) {
    if (!deck || !Array.isArray(deck.slides) || !deck.slides.length) throw new Error("В презентации нет слайдов");
    const P = await load();
    const pics = await Promise.all(deck.slides.map((s) =>
      s.kind === "photo" && /^https:\/\//.test(s.photo || "") ? photoData(s.photo)
        : /^https:\/\//.test(s.pic || "") ? photoData(s.pic).then((p) => p || (s.image ? svgToPng(s.image) : null))
        : s.image ? svgToPng(s.image) : null));
    const pptx = build(P, deck, pics);
    const type = "application/vnd.openxmlformats-officedocument.presentationml.presentation";
    try {
      const raw = await pptx.write({outputType: "uint8array", compression: false});
      return new Blob(addMotion(raw, deck), {type: type});
    } catch (e) {
      console.warn("Анимации в .pptx не добавились:", e);
      return build(P, deck, pics).write({outputType: "blob", compression: true});  // без анимаций, но файл будет
    }
  }

  window.RaiPptx = {toBlob: toBlob, load: load, LIB: LIB, build: build, addMotion: addMotion};
})();
