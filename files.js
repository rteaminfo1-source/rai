/* Rai Файлы — читает любые файлы прямо в браузере, ничего не отправляя на сервер:
   документы (PDF, Word, Excel, PowerPoint, OpenOffice, EPUB, RTF, старые doc/xls/ppt), код и данные (70+ форматов),
   архивы (ZIP — список и текстовые файлы внутри, GZIP), субтитры, звук и видео (длительность, кадры для зрения Rai,
   расшифровка речи нейросетью Whisper), шрифты, программы и всё остальное — что это за файл по его «подписи» (первым байтам).
   PDF читает pdf.js, речь — transformers.js (обе библиотеки берутся с сайта Rai через ai.php или с jsDelivr).
   RaiFiles.read(file, onStep) → {name, size, ext, mime, kind, label, lang?, text, meta, frames?, images?} */
(function () {
  "use strict";

  const MAX_TEXT = 60000, MAX_ZIP_TEXT = 40;
  const PDF_V = "4.10.38";
  const PDF_CDN = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${PDF_V}/build/`;
  const WHISPER = "Xenova/whisper-tiny";

  const CODE = {
    py: "Python", pyw: "Python", js: "JavaScript", mjs: "JavaScript", cjs: "JavaScript", jsx: "JavaScript (React)", ts: "TypeScript",
    tsx: "TypeScript (React)", java: "Java", kt: "Kotlin", kts: "Kotlin", swift: "Swift", c: "C", h: "C (заголовок)", cpp: "C++",
    cc: "C++", cxx: "C++", hpp: "C++ (заголовок)", cs: "C#", go: "Go", rs: "Rust", rb: "Ruby", php: "PHP", pl: "Perl", lua: "Lua",
    r: "R", dart: "Dart", scala: "Scala", sh: "Shell", bash: "Bash", zsh: "Shell", fish: "Fish", ps1: "PowerShell", bat: "Batch",
    cmd: "Batch", sql: "SQL", html: "HTML", htm: "HTML", css: "CSS", scss: "SCSS", sass: "Sass", less: "Less", vue: "Vue",
    svelte: "Svelte", asm: "Ассемблер", s: "Ассемблер", m: "Objective-C", mm: "Objective-C++", hs: "Haskell", ex: "Elixir",
    exs: "Elixir", erl: "Erlang", clj: "Clojure", fs: "F#", vb: "Visual Basic", vbs: "VBScript", pas: "Pascal", dpr: "Delphi",
    f90: "Fortran", f: "Fortran", jl: "Julia", nim: "Nim", zig: "Zig", groovy: "Groovy", gradle: "Gradle", tf: "Terraform",
    sol: "Solidity", glsl: "GLSL", hlsl: "HLSL", gd: "GDScript", ino: "Arduino", v: "Verilog", vhd: "VHDL", lisp: "Lisp",
    scm: "Scheme", ml: "OCaml", elm: "Elm", cr: "Crystal", d: "D", ada: "Ada", cob: "COBOL", prolog: "Prolog", sb3: "Scratch",
    mcfunction: "Minecraft function", sk: "Skript (Minecraft)", lua5: "Lua", ahk: "AutoHotkey", nsi: "NSIS", cmake: "CMake",
    makefile: "Makefile", dockerfile: "Dockerfile", graphql: "GraphQL", proto: "Protocol Buffers", wgsl: "WGSL",
  };
  const DATA = {
    json: "JSON", jsonl: "JSON Lines", ndjson: "JSON Lines", xml: "XML", yaml: "YAML", yml: "YAML", toml: "TOML", ini: "INI",
    cfg: "настройки", conf: "настройки", env: "переменные окружения", properties: "настройки", csv: "таблица CSV",
    tsv: "таблица TSV", md: "Markdown", markdown: "Markdown", txt: "текст", text: "текст", log: "журнал (лог)", srt: "субтитры",
    vtt: "субтитры", ass: "субтитры", ssa: "субтитры", sub: "субтитры", lrc: "текст песни", tex: "LaTeX", bib: "BibTeX",
    rst: "reStructuredText", adoc: "AsciiDoc", org: "Org", svg: "векторная картинка SVG", ics: "календарь", vcf: "контакты (vCard)",
    gpx: "GPS-трек", kml: "карта KML", geojson: "GeoJSON", eml: "письмо", mbox: "почта", lock: "зависимости (lock)",
    gitignore: "правила Git", editorconfig: "настройки редактора", htaccess: "настройки Apache", nfo: "описание",
    ipynb: "блокнот Jupyter", m3u: "плейлист", m3u8: "плейлист", pls: "плейлист", cue: "разметка диска", reg: "реестр Windows",
    desktop: "ярлык Linux", plist: "настройки macOS", strings: "строки перевода", po: "перевод (gettext)", resx: "ресурсы .NET",
    mcmeta: "ресурспак Minecraft", lang: "перевод", rtf: "документ RTF", url: "ссылка", webloc: "ссылка",
  };
  const ZIP_KIND = {
    docx: ["docx", "документ Word"], docm: ["docx", "документ Word"], dotx: ["docx", "шаблон Word"],
    xlsx: ["xlsx", "таблица Excel"], xlsm: ["xlsx", "таблица Excel"], pptx: ["pptx", "презентация PowerPoint"],
    ppsx: ["pptx", "показ PowerPoint"], potx: ["pptx", "шаблон PowerPoint"], odt: ["odf", "документ OpenOffice"],
    ods: ["odf", "таблица OpenOffice"], odp: ["odf", "презентация OpenOffice"], epub: ["epub", "электронная книга EPUB"],
    jar: ["zip", "программа Java (JAR)"], apk: ["zip", "приложение Android (APK)"], ipa: ["zip", "приложение iPhone (IPA)"],
    xpi: ["zip", "дополнение Firefox"], vsix: ["zip", "расширение VS Code"], mcpack: ["zip", "набор Minecraft"],
    mcworld: ["zip", "мир Minecraft"], mcaddon: ["zip", "аддон Minecraft"], kmz: ["zip", "карта KMZ"], "3mf": ["zip", "3D-модель 3MF"],
    whl: ["zip", "пакет Python (wheel)"], nupkg: ["zip", "пакет NuGet"], cbz: ["zip", "комикс CBZ"], sketch: ["zip", "макет Sketch"],
  };
  // «подписи» форматов: первые байты файла
  const MAGIC = [
    [[0x25, 0x50, 0x44, 0x46], 0, "документ PDF", "pdf"],
    [[0x50, 0x4B, 0x03, 0x04], 0, "ZIP-архив", "zip"], [[0x50, 0x4B, 0x05, 0x06], 0, "пустой ZIP-архив", "zip"],
    [[0x52, 0x61, 0x72, 0x21], 0, "архив RAR", "bin"], [[0x37, 0x7A, 0xBC, 0xAF], 0, "архив 7-Zip", "bin"],
    [[0x1F, 0x8B], 0, "архив GZIP", "gzip"], [[0x42, 0x5A, 0x68], 0, "архив BZIP2", "bin"],
    [[0xFD, 0x37, 0x7A, 0x58, 0x5A], 0, "архив XZ", "bin"], [[0x28, 0xB5, 0x2F, 0xFD], 0, "архив Zstandard", "bin"],
    [[0x75, 0x73, 0x74, 0x61, 0x72], 257, "архив TAR", "tar"],
    [[0xD0, 0xCF, 0x11, 0xE0], 0, "документ старого Microsoft Office (doc, xls, ppt) или msi", "ole"],
    [[0x4D, 0x5A], 0, "программа Windows (exe, dll)", "bin"], [[0x7F, 0x45, 0x4C, 0x46], 0, "программа Linux (ELF)", "bin"],
    [[0xCF, 0xFA, 0xED, 0xFE], 0, "программа macOS (Mach-O)", "bin"], [[0xFE, 0xED, 0xFA, 0xCF], 0, "программа macOS (Mach-O)", "bin"],
    [[0xCA, 0xFE, 0xBA, 0xBE], 0, "Java class или программа macOS", "bin"], [[0x64, 0x65, 0x78, 0x0A], 0, "код Android (DEX)", "bin"],
    [[0x00, 0x61, 0x73, 0x6D], 0, "модуль WebAssembly", "bin"], [[0x53, 0x51, 0x4C, 0x69, 0x74, 0x65], 0, "база данных SQLite", "sqlite"],
    [[0x89, 0x50, 0x4E, 0x47], 0, "картинка PNG", "image"], [[0xFF, 0xD8, 0xFF], 0, "картинка JPEG", "image"],
    [[0x47, 0x49, 0x46, 0x38], 0, "картинка GIF", "image"], [[0x42, 0x4D], 0, "картинка BMP", "image"],
    [[0x49, 0x49, 0x2A, 0x00], 0, "картинка TIFF", "bin"], [[0x4D, 0x4D, 0x00, 0x2A], 0, "картинка TIFF", "bin"],
    [[0x38, 0x42, 0x50, 0x53], 0, "макет Photoshop (PSD)", "bin"], [[0x00, 0x00, 0x01, 0x00], 0, "значок ICO", "image"],
    [[0x52, 0x49, 0x46, 0x46], 0, "файл RIFF (WAV, AVI или WebP)", "riff"], [[0x49, 0x44, 0x33], 0, "звук MP3", "audio"],
    [[0xFF, 0xFB], 0, "звук MP3", "audio"], [[0xFF, 0xF3], 0, "звук MP3", "audio"], [[0x66, 0x4C, 0x61, 0x43], 0, "звук FLAC", "audio"],
    [[0x4F, 0x67, 0x67, 0x53], 0, "звук или видео OGG", "audio"], [[0x4D, 0x54, 0x68, 0x64], 0, "мелодия MIDI", "bin"],
    [[0x1A, 0x45, 0xDF, 0xA3], 0, "видео MKV / WebM", "video"], [[0x66, 0x74, 0x79, 0x70], 4, "видео или звук MP4", "video"],
    [[0x00, 0x01, 0x00, 0x00, 0x00], 0, "шрифт TrueType", "font"], [[0x4F, 0x54, 0x54, 0x4F], 0, "шрифт OpenType", "font"],
    [[0x77, 0x4F, 0x46, 0x46], 0, "шрифт WOFF", "font"], [[0x77, 0x4F, 0x46, 0x32], 0, "шрифт WOFF2", "font"],
    [[0x7B, 0x5C, 0x72, 0x74, 0x66], 0, "документ RTF", "rtf"], [[0x25, 0x21, 0x50, 0x53], 0, "PostScript", "text"],
    [[0x4C, 0x00, 0x00, 0x00, 0x01, 0x14, 0x02, 0x00], 0, "ярлык Windows", "bin"], [[0x43, 0x44, 0x30, 0x30, 0x31], 0x8001, "образ диска ISO", "bin"],
    [[0x67, 0x6C, 0x54, 0x46], 0, "3D-модель glTF (GLB)", "bin"], [[0x4E, 0x45, 0x53, 0x1A], 0, "игра NES", "bin"],
    [[0x0A, 0x0D, 0x0D, 0x0A], 0, "запись сетевого трафика (pcapng)", "bin"], [[0x41, 0x43, 0x31, 0x30], 0, "чертёж AutoCAD (DWG)", "bin"],
  ];

  // ---------------------------------------------------------------- помощники
  const ext = (name) => { const m = /\.([^./\\]+)$/.exec(name || ""); return m ? m[1].toLowerCase() : (/^(makefile|dockerfile)$/i.test(name) ? name.toLowerCase() : ""); };
  const has = (b, sig, off) => sig.every((x, i) => b[off + i] === x);
  function magic(b) {
    for (const [sig, off, label, kind] of MAGIC) if (b.length >= off + sig.length && has(b, sig, off)) return {label, kind};
    return null;
  }
  function looksText(b) {
    const n = Math.min(b.length, 8192);
    if (!n) return true;
    let bad = 0;
    for (let i = 0; i < n; i++) { const c = b[i]; if (c === 0 || (c < 9) || (c > 13 && c < 32 && c !== 27)) bad++; }
    return bad / n < 0.01;
  }
  function decode(b) {
    if (b[0] === 0xFF && b[1] === 0xFE) return new TextDecoder("utf-16le").decode(b.subarray(2));
    if (b[0] === 0xFE && b[1] === 0xFF) return new TextDecoder("utf-16be").decode(b.subarray(2));
    try { return new TextDecoder("utf-8", {fatal: true}).decode(b); }
    catch (e) { return new TextDecoder("windows-1251").decode(b); }  // старые русские тексты
  }
  const ENT = {lt: "<", gt: ">", amp: "&", quot: '"', apos: "'", nbsp: " "};
  const entities = (s) => s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) =>
    e[0] === "#" ? String.fromCodePoint(e[1].toLowerCase() === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10)) : (ENT[e.toLowerCase()] ?? m));
  function xmlText(xml, paraTag, cellTag) {
    let s = xml.replace(/<(?:w:tab|text:tab)\b[^>]*\/>/g, "\t").replace(/<(?:w:br|a:br|text:line-break)\b[^>]*\/>/g, "\n");
    if (cellTag) s = s.replace(new RegExp(`</${cellTag}>`, "g"), " | ");
    s = s.replace(new RegExp(`</${paraTag}>`, "g"), "\n").replace(/<[^>]+>/g, "");
    return entities(s).replace(/[ \t]*\|\s*\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  }
  function htmlText(html) {
    return entities(html.replace(/<(script|style|head)[\s\S]*?<\/\1>/gi, " ").replace(/<\/(p|div|h[1-6]|li|tr|br|section|article)>|<br\s*\/?>/gi, "\n")
      .replace(/<[^>]+>/g, " ")).replace(/[ \t]+/g, " ").replace(/\n\s*\n\s*/g, "\n\n").trim();
  }
  async function sha256(b) {
    try { return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", b))).map((x) => x.toString(16).padStart(2, "0")).join(""); }
    catch (e) { return ""; }
  }
  const clip = (s) => s.length > MAX_TEXT ? s.slice(0, MAX_TEXT) + "\n…(текст длиннее — дальше обрезано)" : s;

  // ---------------------------------------------------------------- ZIP (docx, xlsx, pptx, odt, epub, jar, apk…)
  async function inflate(raw, format) {
    const ds = new DecompressionStream(format || "deflate-raw");
    return new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(ds)).arrayBuffer());
  }
  function zipList(b) {
    const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
    let end = -1;
    for (let i = b.length - 22; i >= Math.max(0, b.length - 65557); i--) if (v.getUint32(i, true) === 0x06054b50) { end = i; break; }
    if (end < 0) throw new Error("архив повреждён или не до конца загружен");
    const count = v.getUint16(end + 10, true), list = [];
    let p = v.getUint32(end + 16, true);
    for (let n = 0; n < count && p + 46 <= b.length && v.getUint32(p, true) === 0x02014b50; n++) {
      const flags = v.getUint16(p + 8, true), nl = v.getUint16(p + 28, true), el = v.getUint16(p + 30, true), cl = v.getUint16(p + 32, true);
      const raw = b.subarray(p + 46, p + 46 + nl);
      let name;
      try { name = new TextDecoder("utf-8", {fatal: !(flags & 0x800)}).decode(raw); } catch (e) { name = new TextDecoder("ibm866").decode(raw); }
      list.push({name: name, method: v.getUint16(p + 10, true), csize: v.getUint32(p + 20, true), size: v.getUint32(p + 24, true),
                 off: v.getUint32(p + 42, true), dir: name.endsWith("/")});
      p += 46 + nl + el + cl;
    }
    return list;
  }
  async function zipGet(b, list, name) {
    const e = typeof name === "string" ? list.find((x) => x.name === name) : name;
    if (!e) return null;
    const v = new DataView(b.buffer, b.byteOffset, b.byteLength);
    const start = e.off + 30 + v.getUint16(e.off + 26, true) + v.getUint16(e.off + 28, true);
    const raw = b.subarray(start, start + e.csize);
    if (e.method === 0) return raw;
    if (e.method === 8) return inflate(raw);
    throw new Error("способ сжатия " + e.method + " не поддерживается");
  }
  const zipText = async (b, list, name) => { const x = await zipGet(b, list, name); return x ? decode(x) : ""; };
  const byNumber = (re) => (a, b) => (+(a.name.match(re) || [0, 0])[1]) - (+(b.name.match(re) || [0, 0])[1]);

  async function readDocx(b, list) {
    let text = xmlText(await zipText(b, list, "word/document.xml"), "w:p", "w:tc");
    for (const e of list.filter((x) => /^word\/(footnotes|endnotes)\.xml$/.test(x.name))) text += "\n\n" + xmlText(await zipText(b, list, e), "w:p");
    const core = await zipText(b, list, "docProps/core.xml");
    const title = entities((core.match(/<dc:title>([^<]*)</) || [])[1] || "");
    return {text: text, meta: {"слов": (text.match(/[\p{L}\d]+/gu) || []).length, "абзацев": text.split(/\n+/).filter(Boolean).length,
                               ...(title ? {"название": title} : {})}};
  }
  async function readPptx(b, list) {
    const slides = list.filter((x) => /^ppt\/slides\/slide\d+\.xml$/.test(x.name)).sort(byNumber(/slide(\d+)/));
    const parts = [];
    for (let i = 0; i < slides.length; i++) parts.push(`Слайд ${i + 1}:\n` + xmlText(await zipText(b, list, slides[i]), "a:p"));
    const notes = list.filter((x) => /^ppt\/notesSlides\/notesSlide\d+\.xml$/.test(x.name)).length;
    return {text: parts.join("\n\n"), meta: {"слайдов": slides.length, ...(notes ? {"заметок докладчика": notes} : {})}};
  }
  function colIndex(ref) { let n = 0; for (const ch of ref.replace(/\d+/g, "")) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; }
  async function readXlsx(b, list) {
    const shared = [];
    for (const si of (await zipText(b, list, "xl/sharedStrings.xml")).match(/<si>[\s\S]*?<\/si>/g) || []) {
      shared.push(entities((si.match(/<t[^>]*>([\s\S]*?)<\/t>/g) || []).map((t) => t.replace(/<[^>]+>/g, "")).join("")));
    }
    const names = ((await zipText(b, list, "xl/workbook.xml")).match(/<sheet [^>]*name="([^"]+)"/g) || []).map((x) => entities(x.match(/name="([^"]+)"/)[1]));
    const sheets = list.filter((x) => /^xl\/worksheets\/sheet\d+\.xml$/.test(x.name)).sort(byNumber(/sheet(\d+)/));
    const out = [], tables = [];
    for (let s = 0; s < sheets.length; s++) {
      const xml = await zipText(b, list, sheets[s]);
      const rows = [];
      for (const row of (xml.match(/<row\b[\s\S]*?<\/row>/g) || []).slice(0, 400)) {
        const cells = [];
        for (const c of row.match(/<c\b[^>]*?(?:\/>|>[\s\S]*?<\/c>)/g) || []) {
          const ref = (c.match(/\br="([A-Z]+\d+)"/) || [])[1];
          const type = (c.match(/\bt="(\w+)"/) || [])[1];
          let val = (c.match(/<v>([\s\S]*?)<\/v>/) || [])[1];
          if (type === "s" && val != null) val = shared[+val];
          else if (type === "inlineStr") val = (c.match(/<t[^>]*>([\s\S]*?)<\/t>/) || [])[1];
          else if (type === "b") val = val === "1" ? "ИСТИНА" : "ЛОЖЬ";
          if (val != null) cells[ref ? colIndex(ref) : cells.length] = entities(String(val));
        }
        if (cells.some((x) => x != null && x !== "")) rows.push(Array.from(cells, (x) => x ?? ""));
      }
      const name = names[s] || `Лист ${s + 1}`;
      tables.push({name: name, rows: rows.slice(0, 60)});
      out.push(`Лист «${name}» (${rows.length} строк):\n` + rows.slice(0, 200).map((r) => r.join(" ; ")).join("\n"));
    }
    return {text: out.join("\n\n"), tables: tables, meta: {"листов": sheets.length, "листы": names.join(", ")}};
  }
  async function readOdf(b, list) {
    const xml = await zipText(b, list, "content.xml");
    const text = xmlText(xml.replace(/<table:table-row\b/g, "\n<table:table-row"), "text:p", "table:table-cell");
    const pages = (xml.match(/<draw:page\b/g) || []).length;
    return {text: text, meta: pages ? {"слайдов": pages} : {"слов": (text.match(/[\p{L}\d]+/gu) || []).length}};
  }
  async function readEpub(b, list) {
    const container = await zipText(b, list, "META-INF/container.xml");
    const opfPath = (container.match(/full-path="([^"]+)"/) || [])[1];
    const opf = opfPath ? await zipText(b, list, opfPath) : "";
    const base = opfPath ? opfPath.replace(/[^/]*$/, "") : "";
    const items = {};
    for (const m of opf.matchAll(/<item\b[^>]*\bid="([^"]+)"[^>]*\bhref="([^"]+)"/g)) items[m[1]] = m[2];
    const order = [...opf.matchAll(/<itemref\b[^>]*\bidref="([^"]+)"/g)].map((m) => items[m[1]]).filter(Boolean);
    const title = entities((opf.match(/<dc:title[^>]*>([^<]*)</) || [])[1] || "");
    const author = entities((opf.match(/<dc:creator[^>]*>([^<]*)</) || [])[1] || "");
    let text = "";
    for (const href of order) {
      if (text.length > MAX_TEXT) break;
      text += "\n\n" + htmlText(await zipText(b, list, decodeURIComponent(base + href)));
    }
    return {text: text.trim(), meta: {...(title ? {"название": title} : {}), ...(author ? {"автор": author} : {}), "глав": order.length}};
  }
  async function readZip(b, list) {
    const files = list.filter((x) => !x.dir);
    const total = files.reduce((s, x) => s + x.size, 0);
    const lines = files.slice(0, 300).map((x) => `${x.name} — ${size(x.size)}`);
    let inside = "", n = 0;
    for (const e of files) {
      if (n >= MAX_ZIP_TEXT || inside.length > MAX_TEXT / 2) break;
      const k = ext(e.name);
      if (e.size < 400000 && (CODE[k] || DATA[k] || /readme|license|changelog/i.test(e.name))) {
        try { const t = decode(await zipGet(b, list, e)); if (t.trim()) { inside += `\n\n=== ${e.name} ===\n` + t.slice(0, 6000); n++; } } catch (err) { /* пропускаем */ }
      }
    }
    const kinds = {};
    for (const x of files) { const k = ext(x.name) || "без расширения"; kinds[k] = (kinds[k] || 0) + 1; }
    const top = Object.entries(kinds).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([k, v]) => `${k}: ${v}`).join(", ");
    return {text: "Файлы в архиве:\n" + lines.join("\n") + (files.length > 300 ? `\n… и ещё ${files.length - 300}` : "") + inside,
            meta: {"файлов": files.length, "распакованный размер": size(total), "типы": top}};
  }

  // ---------------------------------------------------------------- PDF (pdf.js) и сканы
  let pdfLib = null;
  async function pdfjs() {
    if (pdfLib) return pdfLib;
    const mirror = window.RAI_AI && window.RAI_AI.pathInfo ? window.RAI_AI.root : null;
    const roots = [mirror ? `${mirror}/npm/pdfjs-dist@${PDF_V}/build/` : null, PDF_CDN].filter(Boolean);
    let err;
    for (const root of roots) {
      try {
        const lib = await import(root + "pdf.min.mjs");
        // рабочий поток — с того же адреса страницы (через blob), иначе браузер его не запустит
        const src = await (await fetch(root + "pdf.worker.min.mjs")).text();
        lib.GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([src], {type: "text/javascript"}));
        pdfLib = lib;
        return lib;
      } catch (e) { err = e; }
    }
    throw new Error("не загрузилась библиотека PDF" + (err ? ": " + err.message : ""));
  }
  async function readPdf(b, onStep) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({data: b.slice()}).promise;
    let text = "";
    const pages = doc.numPages;
    for (let i = 1; i <= Math.min(pages, 300) && text.length < MAX_TEXT; i++) {
      onStep && onStep(`Читаю PDF: страница ${i} из ${pages}…`);
      const content = await (await doc.getPage(i)).getTextContent();
      const t = content.items.map((it) => it.str + (it.hasEOL ? "\n" : " ")).join("").replace(/[ \t]+/g, " ").trim();
      if (t) text += (pages > 1 ? `\n\n— Страница ${i} —\n` : "") + t;
    }
    const meta = {"страниц": pages};
    try { const info = (await doc.getMetadata()).info || {}; if (info.Title) meta["название"] = info.Title; if (info.Author) meta["автор"] = info.Author; } catch (e) { /* нет сведений */ }
    // Скан без текстового слоя — первые страницы картинками на распознавание текста (OCR)
    const images = [];
    const letters = (text.replace(/— Страница \d+ —/g, "").match(/[\p{L}]/gu) || []).length;
    if (letters < 15 * Math.min(pages, 3)) {   // текстового слоя нет — это скан
      for (let i = 1; i <= Math.min(pages, 3); i++) {
        onStep && onStep(`Это скан — готовлю страницу ${i} для распознавания…`);
        const page = await doc.getPage(i);
        const vp = page.getViewport({scale: 2});
        const c = document.createElement("canvas");
        c.width = vp.width; c.height = vp.height;
        await page.render({canvasContext: c.getContext("2d"), viewport: vp}).promise;
        images.push(c.toDataURL("image/png"));
      }
      meta["скан"] = "да — текст распознаётся с картинок";
    }
    return {text: text.trim(), meta: meta, images: images};
  }

  // ---------------------------------------------------------------- RTF и старые doc/xls/ppt
  function readRtf(s) {
    let t = s.replace(/\\'([0-9a-f]{2})/gi, (m, h) => new TextDecoder("windows-1251").decode(new Uint8Array([parseInt(h, 16)])))
      .replace(/\\u(-?\d+)\??/g, (m, n) => String.fromCharCode(n < 0 ? +n + 65536 : +n))
      .replace(/\{\\\*[^{}]*\}|\{\\(fonttbl|colortbl|stylesheet|info)[\s\S]*?\}\}?/g, "")
      .replace(/\\par[d]?\b/g, "\n").replace(/\\tab\b/g, "\t").replace(/\\[a-z]+-?\d* ?/gi, "").replace(/[{}]/g, "");
    return t.replace(/\n{3,}/g, "\n\n").trim();
  }
  function binaryStrings(b) {
    // текст внутри старых документов Office: строки в UTF-16 и в однобайтовой кодировке
    const out = [];
    let cur = "";
    for (let i = 0; i + 1 < b.length; i += 2) {
      const c = b[i] | (b[i + 1] << 8);
      if ((c >= 0x20 && c < 0x7F) || (c >= 0x400 && c <= 0x4FF) || c === 10 || c === 13 || c === 9) cur += String.fromCharCode(c);
      else { if (cur.trim().length >= 6) out.push(cur.trim()); cur = ""; }
    }
    if (cur.trim().length >= 6) out.push(cur.trim());
    const text = out.filter((x) => /[\p{L}]{3,}/u.test(x)).join("\n");
    return text.length > 200 ? text : decode(b).replace(/[^\p{L}\p{N}\p{P}\s]+/gu, " ").replace(/\s{3,}/g, "\n").trim();
  }

  // ---------------------------------------------------------------- звук и видео
  function media(file, video) {
    return new Promise((resolve) => {
      const el = document.createElement(video ? "video" : "audio");
      el.preload = "metadata"; el.muted = true;
      const url = URL.createObjectURL(file);
      const done = (info) => { resolve(Object.assign(info, {el: el, url: url})); };
      el.onloadedmetadata = () => done({duration: el.duration, width: el.videoWidth || 0, height: el.videoHeight || 0});
      el.onerror = () => done({duration: NaN});
      el.src = url;
      setTimeout(() => done({duration: NaN}), 8000);
    });
  }
  async function frames(info, n) {
    const out = [], el = info.el;
    if (!(info.duration > 0) || !info.width) return out;
    for (let i = 0; i < n; i++) {
      el.currentTime = info.duration * (i + 0.5) / n;
      await new Promise((r) => { el.onseeked = r; setTimeout(r, 3000); });
      const c = document.createElement("canvas"), k = Math.min(1, 1280 / Math.max(info.width, info.height));
      c.width = Math.round(info.width * k); c.height = Math.round(info.height * k);
      c.getContext("2d").drawImage(el, 0, 0, c.width, c.height);
      out.push(c.toDataURL("image/jpeg", 0.85));
    }
    return out;
  }
  let whisper = null;
  /** Расшифровка речи нейросетью Whisper (≈40 МБ, один раз — дальше из кэша браузера), первые 10 минут. */
  async function transcribe(file, onStep) {
    const lib = window.RaiVision && window.RaiVision.library ? await window.RaiVision.library() : null;
    if (!lib || !lib.pipeline) throw new Error("нет библиотеки распознавания речи");
    if (!whisper) {
      onStep && onStep("Загружаю распознавание речи…");
      whisper = await lib.pipeline("automatic-speech-recognition", WHISPER, {dtype: "q8", device: "wasm",
        progress_callback: (p) => { if (onStep && p && p.status === "progress" && p.progress) onStep(`Загружаю распознавание речи… ${Math.round(p.progress)}%`); }});
    }
    onStep && onStep("Слушаю запись…");
    const ctx = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 16000});
    const audio = await ctx.decodeAudioData(await file.arrayBuffer());
    ctx.close && ctx.close();
    const pcm = audio.getChannelData(0).slice(0, 16000 * 600);
    onStep && onStep("Расшифровываю речь…");
    const r = await whisper(pcm, {language: "russian", task: "transcribe", chunk_length_s: 30, stride_length_s: 5});
    return ((r && r.text) || "").trim();
  }

  // ---------------------------------------------------------------- главное
  function size(n) { return n >= 1048576 ? (n / 1048576).toFixed(1).replace(".", ",") + " МБ" : n >= 1024 ? Math.round(n / 1024) + " КБ" : n + " байт"; }
  function kindOf(file) {
    const k = ext(file.name), t = file.type || "";
    if (t.startsWith("image/") && k !== "svg" && k !== "psd" && k !== "tif" && k !== "tiff") return "image";
    if (t.startsWith("video/") || /^(mp4|m4v|mov|webm|mkv|avi|wmv|flv|3gp|mpeg|mpg|ts)$/.test(k)) return "video";
    if (t.startsWith("audio/") || /^(mp3|wav|ogg|oga|opus|m4a|aac|flac|wma|amr|aiff)$/.test(k)) return "audio";
    return "file";
  }
  async function read(file, onStep) {
    const k = ext(file.name), kind = kindOf(file);
    const info = {name: file.name, size: file.size, ext: k, mime: file.type || "", kind: "binary", label: "", text: "", meta: {"размер": size(file.size)}};
    if (kind === "audio" || kind === "video") {
      const m = await media(file, kind === "video");
      info.kind = kind;
      info.label = kind === "video" ? "видео" : "звукозапись";
      if (m.duration > 0) info.meta["длительность"] = Math.floor(m.duration / 60) + " мин " + Math.round(m.duration % 60) + " с";
      if (m.width) info.meta["размер кадра"] = m.width + "×" + m.height;
      if (kind === "video") { onStep && onStep("Смотрю кадры видео…"); info.frames = await frames(m, 3).catch(() => []); }
      URL.revokeObjectURL(m.url);
      if (!(m.duration > 600 * 3)) {
        try { info.text = await transcribe(file, onStep); if (info.text) info.meta["речь"] = "расшифрована"; }
        catch (e) { info.meta["речь"] = "не расшифрована (" + (e.message || "ошибка").slice(0, 80) + ")"; }
      }
      return info;
    }
    const b = new Uint8Array(await file.arrayBuffer());
    const sig = magic(b);
    info.meta["SHA-256"] = await sha256(b);
    try {
      if (sig && sig.kind === "pdf" || k === "pdf") {
        Object.assign(info, {kind: "pdf", label: "документ PDF"}, await readPdf(b, onStep).then((r) => ({text: r.text, images: r.images, meta: Object.assign(info.meta, r.meta)})));
      } else if (sig && sig.kind === "zip" || ZIP_KIND[k]) {
        const list = zipList(b);
        const mime = list.some((x) => x.name === "mimetype") ? decode(await zipGet(b, list, "mimetype")) : "";
        let z = ZIP_KIND[k] || [list.some((x) => x.name === "word/document.xml") ? "docx" : list.some((x) => x.name === "xl/workbook.xml") ? "xlsx" :
          list.some((x) => /^ppt\//.test(x.name)) ? "pptx" : /opendocument/.test(mime) ? "odf" : /epub/.test(mime) ? "epub" : "zip", "ZIP-архив"];
        onStep && onStep(`Читаю «${file.name}»…`);
        const r = z[0] === "docx" ? await readDocx(b, list) : z[0] === "xlsx" ? await readXlsx(b, list) : z[0] === "pptx" ? await readPptx(b, list) :
          z[0] === "odf" ? await readOdf(b, list) : z[0] === "epub" ? await readEpub(b, list) : await readZip(b, list);
        Object.assign(info, {kind: z[0] === "zip" ? "archive" : "document", label: z[1], text: r.text, tables: r.tables}, {meta: Object.assign(info.meta, r.meta)});
      } else if (sig && sig.kind === "gzip") {
        const t = await inflate(b, "gzip");
        Object.assign(info, {kind: "archive", label: "архив GZIP", text: looksText(t) ? decode(t) : "(внутри двоичный файл, " + size(t.length) + ")"});
      } else if (sig && sig.kind === "rtf" || k === "rtf") {
        Object.assign(info, {kind: "document", label: "документ RTF", text: readRtf(decode(b))});
      } else if (sig && sig.kind === "ole" || /^(doc|xls|ppt|msg|pub|vsd)$/.test(k)) {
        Object.assign(info, {kind: "document", label: {doc: "документ Word (старый)", xls: "таблица Excel (старая)", ppt: "презентация PowerPoint (старая)",
          msg: "письмо Outlook"}[k] || (sig ? sig.label : "документ Office"), text: binaryStrings(b), meta: Object.assign(info.meta, {"чтение": "только текст (старый формат)"})});
      } else if (sig && sig.kind === "image") {
        Object.assign(info, {kind: "image", label: sig.label});
      } else if (looksText(b) && !(sig && sig.kind !== "text")) {
        const text = decode(b);
        const lang = CODE[k] || null, data = DATA[k] || null;
        Object.assign(info, {kind: lang ? "code" : "text", label: lang ? "код " + lang : data || "текстовый файл", lang: lang || undefined,
          text: /^(html?|xhtml)$/.test(k) ? text : k === "rtf" ? readRtf(text) : text});
        info.meta["строк"] = text.split("\n").length;
        if (!lang) info.meta["слов"] = (text.match(/[\p{L}\d]+/gu) || []).length;
      } else {
        Object.assign(info, {kind: sig && sig.kind === "font" ? "font" : "binary", label: sig ? sig.label : "двоичный файл" + (k ? " ." + k : "")});
        const strings = binaryStrings(b.subarray(0, 2 * 1048576));
        if (strings.length > 40) info.text = "Строки текста внутри файла:\n" + strings.slice(0, 4000);
      }
    } catch (e) {
      info.label = info.label || (sig ? sig.label : "файл ." + k);
      info.meta["ошибка чтения"] = (e && e.message) || String(e);
    }
    info.text = clip(info.text || "");
    if (!info.label) info.label = sig ? sig.label : "файл";
    return info;
  }

  window.RaiFiles = {read: read, kindOf: kindOf, size: size, ext: ext, CODE: CODE};
})();
