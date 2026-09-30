/* Rai PowerPoint — презентация Rai в файл .pptx, который открывается и правится в PowerPoint, Google Slides, Keynote.
   Библиотека PptxGenJS скачивается с CDN только при первом экспорте. Всё управление — через window.RaiPptx. */
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

    deck.slides.forEach((s, i) => {
      const slide = pptx.addSlide();
      slide.background = {color: C.bg};
      const pic = pics[i];
      const text = (value, o) => slide.addText(runs(value), Object.assign({fontFace: BODY, color: C.fg, margin: 0, valign: "top"}, o));
      const kicker = (label) => text(label || String(i + 1).padStart(2, "0"), {x: PAD, y: 0.55, w: 6, h: 0.3, fontFace: MONO, fontSize: 12, color: C.accent, charSpacing: 3});
      const heading = (value, y) => text(plain(value), {x: PAD, y: y || 0.9, w: W - 2 * PAD, h: 0.95, fontFace: HEAD, fontSize: fontFor(value, [[36, 30], [56, 25], [80, 21]]), bold: true, valign: "middle"});
      const card = (x, y, w, h, o) => slide.addShape("roundRect", Object.assign({x: x, y: y, w: w, h: h, rectRadius: 0.12, fill: {color: C.surface}, line: {color: C.line, width: 0.75}}, o));
      const footer = () => {
        slide.addShape("rect", {x: 0, y: H - 0.1, w: W, h: 0.1, fill: {color: C.accent}, line: {type: "none"}});
        text(`${i + 1} / ${total}`, {x: W - 1.6, y: H - 0.5, w: 1.2, h: 0.25, fontFace: MONO, fontSize: 10, color: C.muted, align: "right"});
      };
      const top = 2.05, bottom = H - 0.7, area = bottom - top;

      switch (s.kind) {
        case "title": {
          if (pic) {
            cover(slide, pic, W * 0.46, 0, W * 0.54, H);
            slide.addShape("rect", {x: W * 0.46, y: 0, w: W * 0.54, h: H, fill: {color: C.bg, transparency: 55}, line: {type: "none"}});
          }
          text("ПРЕЗЕНТАЦИЯ", {x: PAD, y: 1.6, w: 6, h: 0.3, fontFace: MONO, fontSize: 12, color: C.accent, charSpacing: 4});
          text(plain(s.title), {x: PAD, y: 2.0, w: W * 0.62, h: 2.6, fontFace: HEAD, fontSize: fontFor(s.title, [[22, 48], [40, 40], [70, 32]]), bold: true, valign: "bottom"});
          slide.addShape("rect", {x: PAD, y: 4.85, w: 1.6, h: 0.12, fill: {color: C.accent}, line: {type: "none"}});
          if (s.subtitle) text(s.subtitle, {x: PAD, y: 5.2, w: W * 0.55, h: 1.2, fontSize: 18, color: C.muted});
          break;
        }
        case "end": {
          if (pic) {
            cover(slide, pic, 0, 0, W, H);
            slide.addShape("rect", {x: 0, y: 0, w: W, h: H, fill: {color: C.bg, transparency: 22}, line: {type: "none"}});
          }
          text(plain(s.title), {x: PAD, y: 2.2, w: W - 2 * PAD, h: 1.6, fontFace: HEAD, fontSize: fontFor(s.title, [[28, 44], [50, 34]]), bold: true, align: "center", valign: "bottom"});
          slide.addShape("rect", {x: W / 2 - 0.7, y: 4.1, w: 1.4, h: 0.1, fill: {color: C.accent}, line: {type: "none"}});
          if (s.subtitle) text(s.subtitle, {x: PAD, y: 4.45, w: W - 2 * PAD, h: 0.8, fontSize: 18, color: C.muted, align: "center"});
          break;
        }
        case "photo": {
          if (pic) {
            cover(slide, pic, 0, 0, W, H);
            slide.addShape("rect", {x: 0, y: H * 0.55, w: W, h: H * 0.45, fill: {color: C.bg, transparency: 15}, line: {type: "none"}});
          }
          text(String(i + 1).padStart(2, "0"), {x: PAD, y: H - 2.85, w: 3, h: 0.3, fontFace: MONO, fontSize: 12, color: C.accent});
          text(plain(s.title), {x: PAD, y: H - 2.5, w: W - 2 * PAD, h: 0.9, fontFace: HEAD, fontSize: fontFor(s.title, [[40, 30], [70, 24]]), bold: true, valign: "middle"});
          if (s.caption) text(s.caption, {x: PAD, y: H - 1.55, w: W - 2 * PAD, h: 0.8, fontSize: 16, color: C.muted});
          break;
        }
        case "agenda": {
          kicker(); heading(s.title || "План");
          const items = (s.items || []).slice(0, 8), rows = Math.ceil(items.length / 2) || 1;
          const cw = (W - 2 * PAD - 0.35) / 2, ch = Math.min(1.05, (area - (rows - 1) * 0.22) / rows);
          items.forEach((it, n) => {
            const x = PAD + (n % 2) * (cw + 0.35), y = top + Math.floor(n / 2) * (ch + 0.22);
            card(x, y, cw, ch, {line: {type: "none"}});
            slide.addShape("rect", {x: x, y: y, w: 0.08, h: ch, fill: {color: C.accent}, line: {type: "none"}});
            text(String(n + 1).padStart(2, "0"), {x: x + 0.3, y: y, w: 0.8, h: ch, fontFace: HEAD, fontSize: 20, bold: true, color: C.accent, valign: "middle"});
            text(it, {x: x + 1.15, y: y, w: cw - 1.35, h: ch, fontSize: fontFor(it, [[40, 18], [70, 15]]), valign: "middle"});
          });
          break;
        }
        case "summary": {
          kicker(); heading(s.title || "Главное");
          const items = (s.items || []).slice(0, 6), rows = Math.ceil(items.length / 2) || 1;
          const cw = (W - 2 * PAD - 0.35) / 2, ch = Math.min(1.9, (area - (rows - 1) * 0.3) / rows);
          items.forEach((it, n) => {
            const x = PAD + (n % 2) * (cw + 0.35), y = top + Math.floor(n / 2) * (ch + 0.3);
            card(x, y, cw, ch);
            slide.addShape("ellipse", {x: x + 0.3, y: y + 0.3, w: 0.55, h: 0.55, fill: {color: C.accent}, line: {type: "none"}});
            text(String(n + 1), {x: x + 0.3, y: y + 0.3, w: 0.55, h: 0.55, fontFace: HEAD, fontSize: 16, bold: true, color: C.on, align: "center", valign: "middle"});
            text(it, {x: x + 1.1, y: y + 0.3, w: cw - 1.4, h: ch - 0.5, fontSize: fontFor(it, [[60, 18], [110, 15]])});
          });
          break;
        }
        case "stats": {
          kicker(); heading(s.title);
          const items = (s.items || []).slice(0, 4), n = items.length || 1, gap = 0.35;
          const cw = (W - 2 * PAD - (n - 1) * gap) / n, ch = Math.min(3.4, area - 0.4), y = top + (area - ch) / 2;
          items.forEach((it, k) => {
            const x = PAD + k * (cw + gap);
            card(x, y, cw, ch, {line: {type: "none"}});
            slide.addShape("rect", {x: x, y: y, w: cw, h: 0.1, fill: {color: C.accent}, line: {type: "none"}});
            text(plain(it.value), {x: x + 0.3, y: y + 0.45, w: cw - 0.6, h: 1.3, fontFace: HEAD, fontSize: fontFor(it.value, n > 3 ? [[5, 36], [8, 28], [11, 22]] : [[6, 44], [9, 34], [12, 26]]), bold: true, color: C.accent, valign: "middle"});
            text(it.label, {x: x + 0.3, y: y + 1.9, w: cw - 0.6, h: ch - 2.2, fontSize: fontFor(it.label, [[50, 16], [90, 13]]), color: C.muted});
          });
          break;
        }
        case "timeline": {
          kicker(); heading(s.title);
          const items = (s.items || []).slice(0, 6), n = items.length || 1, gap = 0.3;
          const cw = (W - 2 * PAD - (n - 1) * gap) / n, y = top + 0.6;
          slide.addShape("rect", {x: PAD, y: y + 0.95, w: W - 2 * PAD, h: 0.06, fill: {color: C.line}, line: {type: "none"}});
          items.forEach((it, k) => {
            const x = PAD + k * (cw + gap);
            text(plain(it.date), {x: x, y: y, w: cw, h: 0.6, fontFace: HEAD, fontSize: n > 4 ? 18 : 22, bold: true, color: C.accent, valign: "bottom"});
            slide.addShape("ellipse", {x: x, y: y + 0.8, w: 0.36, h: 0.36, fill: {color: C.accent}, line: {color: C.bg, width: 4}});
            text(it.text, {x: x, y: y + 1.45, w: cw, h: area - 2.1, fontSize: fontFor(it.text, n > 4 ? [[50, 13], [90, 11]] : [[60, 16], [100, 13]])});
          });
          break;
        }
        case "quote": {
          if (pic) {
            cover(slide, pic, 0, 0, W, H);
            slide.addShape("rect", {x: 0, y: 0, w: W, h: H, fill: {color: C.bg, transparency: 15}, line: {type: "none"}});
          }
          text("«", {x: PAD + 0.6, y: 0.9, w: 2, h: 1.5, fontFace: HEAD, fontSize: 110, bold: true, color: C.accent, valign: "bottom"});
          text(s.text, {x: PAD + 0.6, y: 2.5, w: W - 2 * PAD - 1.2, h: 2.9, fontSize: fontFor(s.text, [[60, 36], [120, 28], [200, 22]]), bold: true, valign: "middle"});
          if (s.author) text("— " + plain(s.author), {x: PAD + 0.6, y: 5.6, w: W - 2 * PAD - 1.2, h: 0.5, fontFace: MONO, fontSize: 16, color: C.muted});
          break;
        }
        case "compare": {
          kicker(); heading(s.title);
          const vs = 0.9, cw = (W - 2 * PAD - vs - 0.5) / 2, ch = area - 0.1;
          [[s.left, PAD, false], [s.right, W - PAD - cw, true]].forEach(([c, x, hot]) => {
            c = c || {};
            card(x, top, cw, ch, hot ? {line: {color: C.accent, width: 1.5}} : {});
            text(plain(c.title), {x: x + 0.35, y: top + 0.3, w: cw - 0.7, h: 0.6, fontFace: HEAD, fontSize: fontFor(c.title, [[18, 20], [40, 16]]), bold: true, color: C.accent});
            const list = (c.items || []).map((it) => ({text: plain(it), options: {bullet: {indent: 18}, paraSpaceAfter: 6}}));
            if (list.length) slide.addText(list, {x: x + 0.35, y: top + 1.05, w: cw - 0.7, h: ch - 1.3, fontFace: BODY, fontSize: fontFor(c.items || [], [[160, 18], [300, 15]]), color: C.fg, valign: "top", margin: 0});
          });
          slide.addShape("ellipse", {x: W / 2 - vs / 2, y: top + ch / 2 - vs / 2, w: vs, h: vs, fill: {color: C.accent}, line: {type: "none"}});
          text("VS", {x: W / 2 - vs / 2, y: top + ch / 2 - vs / 2, w: vs, h: vs, fontFace: HEAD, fontSize: 16, bold: true, color: C.on, align: "center", valign: "middle"});
          break;
        }
        case "fact": {
          kicker(); heading(s.title);
          const w = pic ? W * 0.52 : W - 2 * PAD - 0.4;
          slide.addShape("rect", {x: PAD, y: top + 0.2, w: 0.1, h: area - 0.6, fill: {color: C.accent}, line: {type: "none"}});
          text(s.text, {x: PAD + 0.45, y: top + 0.2, w: w, h: area - 0.6, fontSize: fontFor(s.text, [[120, 28], [200, 24], [300, 20]]), bold: true, valign: "middle"});
          if (pic) cover(slide, pic, W - PAD - W * 0.33, top + 0.3, W * 0.33, W * 0.22, {rounding: false});
          break;
        }
        case "code": {
          kicker(); heading(s.title);
          card(PAD, top, W - 2 * PAD, area);
          text(String(s.code || "").replace(/\s+$/, ""), {x: PAD + 0.3, y: top + 0.25, w: W - 2 * PAD - 0.6, h: area - 0.5, fontFace: MONO, fontSize: Math.max(9, Math.min(16, Math.floor(area * 72 / 1.35 / Math.max(10, String(s.code || "").split("\n").length))))});
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
          if (list.length) slide.addText(list, {x: tx, y: top, w: tw, h: area, fontFace: BODY, fontSize: fontFor(s.bullets || [], pic ? [[180, 22], [320, 18], [480, 15]] : [[240, 24], [420, 20], [600, 17]]), color: C.fg, valign: "middle", margin: 0});
          if (pic) cover(slide, pic, left ? PAD : W - PAD - pw, top + (area - ph) / 2, pw, ph);
        }
      }
      footer();
    });
    return pptx;
  }

  /** Презентация Rai ({title, slides, theme}) → Blob .pptx. */
  async function toBlob(deck) {
    if (!deck || !Array.isArray(deck.slides) || !deck.slides.length) throw new Error("В презентации нет слайдов");
    const P = await load();
    const pics = await Promise.all(deck.slides.map((s) =>
      s.kind === "photo" && /^https:\/\//.test(s.photo || "") ? photoData(s.photo) : s.image ? svgToPng(s.image) : null));
    const pptx = build(P, deck, pics);
    return pptx.write({outputType: "blob", compression: true});
  }

  window.RaiPptx = {toBlob: toBlob, load: load, LIB: LIB};
})();
