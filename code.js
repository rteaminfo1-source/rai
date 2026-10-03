/* Rai Code — вкладка для программирования: редактор с подсветкой, запуск Python / JavaScript / HTML
   прямо в браузере, ИИ-помощник (проверить, исправить, объяснить, прокомментировать, написать).
   Страница подключает этот файл и вызывает RaiCode.init(host) — см. index.html. */
(function () {
  "use strict";

  const STORE = "rai_code_v1";
  const EXT = {
    py: "python", js: "javascript", mjs: "javascript", cjs: "javascript", ts: "typescript", html: "html", htm: "html",
    css: "css", php: "php", json: "json", cpp: "cpp", cc: "cpp", hpp: "cpp", c: "c", h: "c", java: "java", cs: "csharp",
    go: "go", rs: "rust", sql: "sql", sh: "bash", kt: "kotlin", md: "text", txt: "text", csv: "text"
  };
  const NAMES = {
    python: "Python", javascript: "JavaScript", typescript: "TypeScript", html: "HTML", css: "CSS", php: "PHP", json: "JSON",
    cpp: "C++", c: "C", java: "Java", csharp: "C#", go: "Go", rust: "Rust", sql: "SQL", bash: "Bash", kotlin: "Kotlin", text: "Текст"
  };
  const FAMILY = {
    python: "python", javascript: "js", typescript: "js", json: "json", css: "css", php: "php", sql: "sql", bash: "bash",
    c: "c", cpp: "c", java: "c", csharp: "c", go: "c", rust: "c", kotlin: "c"
  };
  const langOf = (name) => EXT[((String(name).match(/\.([a-z0-9]+)$/i) || [])[1] || "").toLowerCase()] || "text";
  const unitOf = (lang) => (["html", "css", "javascript", "typescript", "json"].includes(lang) ? 2 : 4);

  // ================================================================ подсветка
  const WORDS = (s) => new Set(s.split(" "));
  const KW = {
    python: WORDS("False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case"),
    js: WORDS("break case catch class const continue debugger default delete do else export extends false finally for from function if import in instanceof let new null of return static super switch this throw true try typeof undefined var void while with yield async await get set interface type enum implements public private protected readonly as"),
    c: WORDS("auto break case catch char class const constexpr continue default delete do double else enum explicit extern false float for friend goto if inline int long namespace new nullptr operator private protected public register return short signed sizeof static struct switch template this throw true try typedef typename union unsigned using virtual void volatile while bool abstract boolean byte extends final finally implements import instanceof interface package super synchronized throws null var string object decimal foreach in out ref override readonly sealed base is as let mut fn impl pub use mod match trait crate self Self where loop move dyn func go defer chan select type range map fallthrough val fun when"),
    php: WORDS("abstract and array as break callable case catch class clone const continue declare default do echo else elseif empty endfor endforeach endif endswitch endwhile extends final finally fn for foreach function global if implements include include_once instanceof interface isset list match namespace new or print private protected public readonly require require_once return static switch throw trait try unset use var while xor yield true false null"),
    sql: WORDS("select from where insert into values update set delete create table drop alter add primary key foreign references not null unique default index join left right inner outer full on as and or in is like between order by group having limit offset distinct union all exists case when then else end integer int varchar text real boolean date autoincrement"),
    bash: WORDS("if then else elif fi for while do done case esac in function return exit local export source"),
    css: WORDS("important"), json: WORDS("true false null")
  };
  const BUILTIN = {
    python: WORDS("print input len range int str float list dict set tuple bool type open abs min max sum sorted reversed enumerate zip map filter round isinstance super self object Exception ValueError TypeError KeyError IndexError any all chr ord divmod pow hex bin format repr id iter next"),
    js: WORDS("console document window Math JSON Array Object String Number Boolean Promise Date Map Set RegExp Error parseInt parseFloat setTimeout setInterval clearInterval clearTimeout fetch alert prompt localStorage require module exports process"),
    c: WORDS("printf scanf puts cout cin endl std vector string System out println main String Console WriteLine fmt Println Printf len make append"),
    php: WORDS("strlen count explode implode str_replace substr strpos json_encode json_decode array_map array_filter in_array htmlspecialchars date time rand file_get_contents file_put_contents"),
    sql: WORDS("count sum avg min max"), bash: WORDS("echo read cd ls mkdir rm cp mv cat grep sudo pwd"), css: WORDS(""), json: WORDS("")
  };
  const END = "(?![\\s\\S])";
  const STR = String.raw`"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?`;
  const TPL = String.raw`\`(?:\\[\s\S]|[^\`\\])*\`?`;
  const NUM = String.raw`\b(?:0[xXbBoO][\da-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?)[a-zA-Z%]*`;
  const IDENT = String.raw`[A-Za-z_][\w]*`;
  const BLOCK = String.raw`\/\*[\s\S]*?(?:\*\/|${END})`;
  const RULES = {
    python: [["#.*", "c"], [`[rRbBfFuU]{0,2}(?:"""[\\s\\S]*?(?:"""|${END})|'''[\\s\\S]*?(?:'''|${END}))`, "s"],
             ["[rRbBfFuU]{0,2}(?:" + STR + ")", "s"], [String.raw`@[\w.]+`, "d"], [NUM, "n"], [IDENT, "w"]],
    js: [[String.raw`\/\/.*|` + BLOCK, "c"], [STR + "|" + TPL, "s"], [NUM, "n"], [String.raw`[A-Za-z_$][\w$]*`, "w"]],
    c: [[String.raw`\/\/.*|` + BLOCK, "c"], [String.raw`#\s*(?:include|define|ifndef|ifdef|endif|pragma|undef|if|else)\b.*`, "d"],
        [STR + "|" + TPL, "s"], [NUM, "n"], [IDENT, "w"]],
    php: [[String.raw`\/\/.*|#(?!\[).*|` + BLOCK, "c"], [String.raw`<\?php|<\?=|\?>`, "t"], [String.raw`\$[A-Za-z_]\w*`, "d"],
          [STR, "s"], [NUM, "n"], [IDENT, "w"]],
    sql: [[String.raw`--.*|` + BLOCK, "c"], [STR, "s"], [NUM, "n"], [IDENT, "w"]],
    bash: [["#.*", "c"], [STR, "s"], [String.raw`\$\{?[\w@#?]+\}?`, "d"], [NUM, "n"], [String.raw`[A-Za-z_][\w-]*`, "w"]],
    css: [[BLOCK, "c"], [STR, "s"], [String.raw`@[\w-]+`, "d"], [String.raw`#[\da-fA-F]{3,8}\b`, "n"],
          [String.raw`--[\w-]+|[a-zA-Z-]+(?=\s*:[^;{}]*[;}])`, "p"], [NUM, "n"], ["!important", "k"]],
    json: [[String.raw`"(?:\\.|[^"\\\n])*"(?=\s*:)`, "p"], [STR, "s"], [String.raw`-?` + NUM, "n"], [IDENT, "w"]],
    tag: [[String.raw`<\/?[\w:-]+|\/?>`, "t"], [STR, "s"], [String.raw`[^\s=<>"'\/]+(?=\s*=)`, "a"]]
  };
  const RE = {};
  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  }
  function tokens(src, fam) {
    const rules = RULES[fam];
    const re = RE[fam] || (RE[fam] = new RegExp(rules.map((r) => "(" + r[0] + ")").join("|"), "g"));
    const kw = KW[fam] || KW.js, bi = BUILTIN[fam] || BUILTIN.js;
    re.lastIndex = 0;
    let out = "", last = 0, m;
    while ((m = re.exec(src))) {
      if (!m[0]) { re.lastIndex++; continue; }
      out += esc(src.slice(last, m.index));
      let g = 1;
      while (m[g] === undefined) g++;
      let cls = rules[g - 1][1];
      if (cls === "w") {
        const w = fam === "sql" ? m[0].toLowerCase() : m[0];
        cls = kw.has(w) ? "k" : bi.has(w) ? "b" : /^\s*\(/.test(src.slice(re.lastIndex, re.lastIndex + 8)) ? "f" : "";
      }
      out += cls ? `<span class="hl-${cls}">${esc(m[0])}</span>` : esc(m[0]);
      last = re.lastIndex;
    }
    return out + esc(src.slice(last));
  }
  function hlHTML(src) {
    const re = /<!-{2}[\s\S]*?(?:-->|(?![\s\S]))|(<(script|style)\b[^>]*>)([\s\S]*?)(?=<\/\2\s*>|(?![\s\S]))|<!doctype[^>]*>?|<\/?[A-Za-z][^>]*>?/gi;
    let out = "", last = 0, m;
    while ((m = re.exec(src))) {
      out += esc(src.slice(last, m.index));
      if (m[0].startsWith("<!-" + "-")) out += `<span class="hl-c">${esc(m[0])}</span>`;
      else if (m[1]) out += tokens(m[1], "tag") + tokens(m[3], m[2].toLowerCase() === "script" ? "js" : "css");
      else if (/^<!doctype/i.test(m[0])) out += `<span class="hl-c">${esc(m[0])}</span>`;
      else out += tokens(m[0], "tag");
      last = re.lastIndex;
    }
    return out + esc(src.slice(last));
  }
  function highlight(src, lang) {
    if (src.length > 300000) return esc(src);
    if (lang === "html") return hlHTML(src);
    if (lang === "php" && !/^\s*<\?php/.test(src) && /<[a-z!]/i.test(src)) {
      // PHP внутри HTML: подсвечиваем PHP-вставки, остальное — как HTML
      return src.split(/(<\?(?:php|=)[\s\S]*?(?:\?>|(?![\s\S])))/).map((part, i) => i % 2 ? tokens(part, "php") : hlHTML(part)).join("");
    }
    const fam = FAMILY[lang];
    return fam ? tokens(src, fam) : esc(src);
  }

  // ================================================================ состояние
  let H = null;            // помощники страницы (api, md, toast, download, zip, pyodideSources…)
  let project = null;      // {files: [{name, text}], active, stdin}
  let el = {};
  let marks = new Map();   // строка -> {sev, msgs}
  let saveTimer = null, checkTimer = null, hlQueued = false;
  let lineCount = 0;

  const SAMPLE = [
    "# Rai Code: пишите код и нажимайте «Запустить» (Ctrl+Enter).",
    "# Справа — вывод программы и ИИ-помощник: проверит, исправит и объяснит код.",
    "",
    "name = input(\"Как вас зовут? \")",
    "print(f\"Привет, {name}!\")",
    "",
    "for i in range(1, 6):",
    "    print(i, \"в квадрате =\", i * i)",
    ""
  ].join("\n");

  function load() {
    try {
      const d = JSON.parse(localStorage.getItem(STORE) || "null");
      if (d && Array.isArray(d.files) && d.files.length) project = d;
    } catch (e) { /* пустой проект */ }
    if (!project) project = {files: [{name: "main.py", text: SAMPLE}], active: "main.py", stdin: "Мир"};
    if (!project.files.some((f) => f.name === project.active)) project.active = project.files[0].name;
  }
  function save(now) {
    clearTimeout(saveTimer);
    const write = () => {
      try { localStorage.setItem(STORE, JSON.stringify(project)); }
      catch (e) { H.toast("В браузере не хватает места для проекта — скачайте его ZIP-архивом"); }
    };
    if (now) write(); else saveTimer = setTimeout(write, 400);
  }
  const active = () => project.files.find((f) => f.name === project.active);
  const lang = () => langOf(project.active);

  // ================================================================ разметка
  const ICON = (n) => `<svg class="i"><use href="#i-${n}"/></svg>`;
  function build(root) {
    root.innerHTML = `
<div class="code-top">
  <button class="tb run" type="button" id="cRun" title="Запустить (Ctrl+Enter)">${ICON("play")}<span class="lbl">Запустить</span></button>
  <button class="tb stop" type="button" id="cStop" hidden>${ICON("stop")}<span class="lbl">Стоп</span></button>
  <span class="lang-pill" id="cLang"></span>
  <button class="tb diag" type="button" id="cDiag" hidden></button>
  <span class="spacer"></span>
  <button class="tb" type="button" id="cOpen" title="Открыть файлы с компьютера">${ICON("folder")}<span class="lbl">Открыть</span></button>
  <button class="tb" type="button" id="cDl" title="Скачать текущий файл">${ICON("down")}<span class="lbl">Файл</span></button>
  <button class="tb" type="button" id="cZip" title="Скачать весь проект ZIP-архивом">${ICON("zip")}<span class="lbl">Проект ZIP</span></button>
  <input type="file" id="cFile" multiple hidden>
</div>
<div class="code-main">
  <div class="editor-col">
    <div class="files" id="cFiles" role="tablist" aria-label="Файлы проекта"></div>
    <div class="editor">
      <div class="gutter" id="cGutter" aria-hidden="true"></div>
      <div class="code-wrap"><pre aria-hidden="true"><code id="cHl"></code></pre>
        <textarea id="cText" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off" wrap="off" aria-label="Код"></textarea></div>
    </div>
  </div>
  <div class="side-col">
    <div class="side-tabs" role="tablist">
      <button type="button" role="tab" data-pane="out" aria-selected="true">Вывод</button>
      <button type="button" role="tab" data-pane="preview" aria-selected="false">Просмотр</button>
      <button type="button" role="tab" data-pane="ai" aria-selected="false">ИИ-помощник</button>
    </div>
    <div class="pane" id="outPane">
      <div class="stdin"><label for="cStdin">Ввод для программы (input / prompt): каждое значение с новой строки</label>
        <textarea id="cStdin" spellcheck="false"></textarea></div>
      <pre class="console" id="cConsole" aria-live="polite"></pre>
    </div>
    <div class="pane" id="previewPane" hidden>
      <div class="preview-empty" id="cPrevEmpty">Здесь появится страница, когда вы запустите HTML-файл.</div>
    </div>
    <div class="pane" id="aiPane" hidden>
      <div class="ai-quick">
        <button class="tb" type="button" data-act="check">${ICON("check")}Проверить</button>
        <button class="tb" type="button" data-act="fix">${ICON("wand")}Исправить</button>
        <button class="tb" type="button" data-act="explain">${ICON("book")}Объяснить</button>
        <button class="tb" type="button" data-act="comment">${ICON("edit")}Комментарии</button>
      </div>
      <div class="ai-log" id="cAiLog"></div>
      <form class="ai-form" id="cAiForm">
        <textarea id="cAiInput" rows="1" placeholder="Что написать? Сайт кофейни в тёмных тонах, игра тетрис, погода, функция среднего… Для сайта: «добавь раздел цены»"></textarea>
        <button class="round" type="submit" aria-label="Отправить">${ICON("send")}</button>
      </form>
    </div>
  </div>
</div>`;
    for (const id of ["cRun", "cStop", "cLang", "cDiag", "cOpen", "cDl", "cZip", "cFile", "cFiles", "cGutter", "cHl", "cText",
                      "cStdin", "cConsole", "outPane", "previewPane", "cPrevEmpty", "aiPane", "cAiLog", "cAiForm", "cAiInput"]) {
      el[id] = root.querySelector("#" + id);
    }
    el.root = root;
    el.ta = el.cText;
  }

  // ================================================================ файлы
  function renderFiles() {
    const box = el.cFiles;
    box.textContent = "";
    for (const f of project.files) {
      const tab = document.createElement("div");
      tab.className = "file-tab" + (f.name === project.active ? " on" : "");
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(f.name === project.active));
      tab.tabIndex = 0;
      tab.title = "Двойной щелчок — переименовать";
      tab.innerHTML = `<span class="n">${esc(f.name)}</span>` +
        (project.files.length > 1 ? `<span class="x" role="button" aria-label="Удалить файл ${esc(f.name)}" title="Удалить">×</span>` : "");
      tab.addEventListener("click", (e) => {
        if (e.target.closest(".x")) { askDelete(tab, f); return; }
        if (f.name !== project.active) openTab(f.name);
      });
      tab.addEventListener("keydown", (e) => { if (e.key === "Enter") openTab(f.name); if (e.key === "F2") rename(tab, f); });
      tab.addEventListener("dblclick", () => rename(tab, f));
      box.append(tab);
    }
    const add = document.createElement("button");
    add.type = "button";
    add.className = "file-add";
    add.title = "Новый файл";
    add.setAttribute("aria-label", "Новый файл");
    add.textContent = "+";
    add.addEventListener("click", () => newFile(add));
    box.append(add);
    el.cLang.textContent = NAMES[lang()] || lang();
  }
  function askDelete(tab, f) {
    const x = tab.querySelector(".x");
    if (x.dataset.sure) {
      project.files = project.files.filter((g) => g !== f);
      if (project.active === f.name) project.active = project.files[0].name;
      save(true); loadEditor(); renderFiles();
      return;
    }
    x.dataset.sure = "1";
    x.textContent = "удалить?";
    setTimeout(() => { if (x.isConnected) { delete x.dataset.sure; x.textContent = "×"; } }, 2500);
  }
  function validName(name, except) {
    if (!/^[\w\-. ]{1,60}$/u.test(name) || /^\.+$/.test(name)) return "Имя файла: латинские буквы, цифры, точка, дефис";
    if (project.files.some((f) => f.name.toLowerCase() === name.toLowerCase() && f.name !== except)) return "Такой файл уже есть";
    return null;
  }
  function nameField(initial, done) {
    const field = document.createElement("input");
    field.value = initial;
    field.setAttribute("aria-label", "Имя файла");
    let finished = false;
    const finish = (ok) => { if (!finished) { finished = true; done(ok ? field.value.trim() : null); } };
    field.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); finish(true); }
      if (e.key === "Escape") finish(false);
    });
    field.addEventListener("blur", () => finish(true));
    return field;
  }
  function rename(tab, f) {
    const field = nameField(f.name, (name) => {
      if (name && name !== f.name) {
        const err = validName(name, f.name);
        if (err) H.toast(err);
        else { if (project.active === f.name) project.active = name; f.name = name; save(true); }
      }
      renderFiles(); refresh();
    });
    tab.replaceChildren(field);
    field.focus(); field.select();
  }
  function uniqueName(name) {
    if (!project.files.some((f) => f.name === name)) return name;
    const m = name.match(/^(.*?)(\.[^.]+)?$/);
    for (let k = 2; ; k++) {
      const n = m[1] + k + (m[2] || "");
      if (!project.files.some((f) => f.name === n)) return n;
    }
  }
  function newFile(btn) {
    const ext = (project.active.match(/\.[^.]+$/) || [".py"])[0];
    const field = nameField(uniqueName("file" + ext), (name) => {
      if (name) {
        const err = validName(name);
        if (err) H.toast(err);
        else { project.files.push({name: name, text: ""}); project.active = name; save(true); loadEditor(); }
      }
      renderFiles();
      el.ta.focus();
    });
    btn.replaceWith(field);
    field.focus(); field.select();
  }
  function openTab(name) {
    project.active = name;
    save(true);
    renderFiles();
    loadEditor();
    el.ta.focus();
  }
  /** Добавить файл в проект (из чата или с компьютера) и открыть его. */
  function addFile(name, text) {
    name = (name || "main.py").replace(/[^\w\-. ]+/gu, "_").slice(0, 60) || "main.py";
    const same = project.files.find((f) => f.name === name);
    if (same && (same.text === text || !same.text.trim() || same.text === SAMPLE)) same.text = text;
    else { name = uniqueName(name); project.files.push({name: name, text: text}); }
    project.active = name;
    save(true); renderFiles(); loadEditor();
    return name;
  }

  // ================================================================ редактор
  function loadEditor() {
    const f = active();
    el.ta.value = f.text;
    el.ta.scrollTop = 0; el.ta.scrollLeft = 0;
    marks = new Map();
    el.cDiag.hidden = true;
    lineCount = 0;
    refresh();
    scheduleCheck();
  }
  function refresh() {
    hlQueued = false;
    el.cHl.innerHTML = highlight(el.ta.value, lang()) + "\n";
    renderGutter();
    syncScroll();
  }
  function queueRefresh() {
    if (hlQueued) return;
    hlQueued = true;
    requestAnimationFrame(refresh);
  }
  function renderGutter(force) {
    const n = el.ta.value.split("\n").length;
    if (n === lineCount && !force) return;
    lineCount = n;
    let html = "";
    for (let k = 1; k <= n; k++) {
      const m = marks.get(k);
      html += m ? `<div><span class="${m.sev === "error" ? "bad" : "warn"}" title="${esc(m.msgs.join("\n"))}">${k}</span></div>` : `<div>${k}</div>`;
    }
    el.cGutter.innerHTML = html + "<div></div><div></div>";
  }
  function syncScroll() {
    const pre = el.cHl.parentElement;
    pre.scrollTop = el.ta.scrollTop;
    pre.scrollLeft = el.ta.scrollLeft;
    el.cGutter.scrollTop = el.ta.scrollTop;
  }
  function onInput() {
    active().text = el.ta.value;
    save();
    queueRefresh();
    scheduleCheck();
  }

  function insert(text) {
    el.ta.focus();
    let ok = false;
    try { ok = document.execCommand("insertText", false, text); } catch (e) { ok = false; }
    if (!ok) {
      el.ta.setRangeText(text, el.ta.selectionStart, el.ta.selectionEnd, "end");
      onInput();
    }
  }
  function lineStart(v, pos) { return v.lastIndexOf("\n", pos - 1) + 1; }
  function selectLines() {
    const v = el.ta.value, s = el.ta.selectionStart, e = el.ta.selectionEnd;
    const a = lineStart(v, s);
    let b = v.indexOf("\n", e > s && v[e - 1] === "\n" ? e - 1 : e);
    if (b < 0) b = v.length;
    return [a, b];
  }
  function replaceLines(fn) {
    const [a, b] = selectLines();
    const v = el.ta.value;
    const next = v.slice(a, b).split("\n").map(fn).join("\n");
    el.ta.setSelectionRange(a, b);
    insert(next);
    el.ta.setSelectionRange(a, a + next.length);
  }
  const PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'", "`": "`"};
  const COMMENT = {python: "#", bash: "#", sql: "--", php: "//", javascript: "//", typescript: "//", c: "//", cpp: "//",
                   java: "//", csharp: "//", go: "//", rust: "//", kotlin: "//"};

  function onKey(e) {
    const ta = el.ta, v = ta.value, s = ta.selectionStart, en = ta.selectionEnd;
    const unit = " ".repeat(unitOf(lang()));
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key === "Enter") { e.preventDefault(); run(); return; }
    if (mod && (e.key === "s" || e.key === "S")) { e.preventDefault(); save(true); H.toast("Сохранено в браузере"); return; }
    if (mod && e.key === "/") {
      e.preventDefault();
      const mark = COMMENT[lang()];
      if (!mark) return;
      const [a, b] = selectLines();
      const lines = v.slice(a, b).split("\n");
      const all = lines.filter((l) => l.trim()).every((l) => l.trim().startsWith(mark));
      replaceLines((l) => !l.trim() ? l : all ? l.replace(new RegExp("^(\\s*)" + mark.replace(/[/]/g, "\\/") + " ?"), "$1") : l.replace(/^(\s*)/, "$1" + mark + " "));
      return;
    }
    if (e.key === "Tab" && !mod && !e.altKey) {
      e.preventDefault();
      if (e.shiftKey) replaceLines((l) => l.replace(new RegExp("^ {1," + unit.length + "}|^\\t"), ""));
      else if (v.slice(s, en).includes("\n")) replaceLines((l) => (l ? unit + l : l));
      else insert(unit.slice((s - lineStart(v, s)) % unit.length));
      return;
    }
    if (e.key === "Enter" && !mod && !e.shiftKey && !e.altKey && !e.isComposing) {
      e.preventDefault();
      const ls = lineStart(v, s);
      const before = v.slice(ls, s);
      const indent = before.match(/^[ \t]*/)[0];
      const trimmed = before.replace(/\s+$/, "");
      const opens = lang() === "python" ? /[:([{]$/.test(trimmed) : /[{([]$/.test(trimmed) || (lang() === "html" && /<(?!\/)(?!(?:br|img|input|meta|link|hr)\b)[\w-]+[^>]*>$/.test(trimmed));
      const closer = v[s];
      if (opens && s === en && /^[)\]}<]/.test(closer || "") && !(lang() === "python" && trimmed.endsWith(":"))) {
        insert("\n" + indent + unit + "\n" + indent);
        const pos = s + 1 + indent.length + unit.length;
        ta.setSelectionRange(pos, pos);
      } else {
        const dedent = lang() === "python" && /^\s*(return|pass|break|continue|raise)\b/.test(before);
        insert("\n" + (opens ? indent + unit : dedent ? indent.slice(unit.length) : indent));
      }
      return;
    }
    if (e.key === "Backspace" && s === en && s > 0 && !mod) {
      const before = v.slice(lineStart(v, s), s);
      if (before.length && /^ +$/.test(before)) {
        e.preventDefault();
        const drop = before.length % unit.length || unit.length;
        ta.setSelectionRange(s - drop, s);
        insert("");
        return;
      }
      if (PAIRS[v[s - 1]] && PAIRS[v[s - 1]] === v[s]) {
        e.preventDefault();
        ta.setSelectionRange(s - 1, s + 1);
        insert("");
        return;
      }
    }
    if (!mod && !e.altKey && e.key.length === 1) {
      const ch = e.key;
      if (")]}\"'`".includes(ch) && s === en && v[s] === ch) {
        const quote = ch === '"' || ch === "'" || ch === "`";
        if (!quote || v[s - 1] !== "\\") { e.preventDefault(); ta.setSelectionRange(s + 1, s + 1); return; }
      }
      if (PAIRS[ch]) {
        const quote = ch === '"' || ch === "'" || ch === "`";
        if (s !== en) {
          e.preventDefault();
          const inner = v.slice(s, en);
          insert(ch + inner + PAIRS[ch]);
          ta.setSelectionRange(s + 1, s + 1 + inner.length);
          return;
        }
        const next = v[s] || "";
        const prev = v[s - 1] || "";
        if (/^[\s)\]},;:]?$/.test(next) && !(quote && /[\w\\]/.test(prev)) && !(ch === "`" && lang() !== "javascript")) {
          e.preventDefault();
          insert(ch + PAIRS[ch]);
          ta.setSelectionRange(s + 1, s + 1);
        }
      }
    }
  }

  function jumpTo(line) {
    const v = el.ta.value;
    let pos = 0;
    for (let k = 1; k < line && pos >= 0; k++) pos = v.indexOf("\n", pos) + 1 || v.length;
    const end = v.indexOf("\n", pos);
    el.ta.focus();
    el.ta.setSelectionRange(pos, end < 0 ? v.length : end);
    const lh = parseFloat(getComputedStyle(el.ta).lineHeight) || 20;
    el.ta.scrollTop = Math.max(0, (line - 1) * lh - el.ta.clientHeight / 3);
    syncScroll();
  }

  // ================================================================ пометки ошибок
  function setMarks(issues) {
    marks = new Map();
    let errors = 0, warns = 0;
    for (const it of issues || []) {
      if (!it.line || it.severity === "info") continue;
      const m = marks.get(it.line) || {sev: "warning", msgs: []};
      if (it.severity === "error") { m.sev = "error"; errors++; } else warns++;
      m.msgs.push(it.message + (it.hint ? " — " + it.hint : ""));
      marks.set(it.line, m);
    }
    renderGutter(true);
    const d = el.cDiag;
    d.hidden = !(errors || warns);
    d.className = "tb diag " + (errors ? "bad" : "warn");
    d.textContent = errors ? `Ошибок: ${errors}` + (warns ? ` · замечаний: ${warns}` : "") : `Замечаний: ${warns}`;
  }
  function scheduleCheck() {
    clearTimeout(checkTimer);
    const f = active();
    if (!H.ready() || !f.text.trim() || f.text.length > 60000 || lang() === "text") { setMarks([]); return; }
    checkTimer = setTimeout(async () => {
      const snapshot = f.text, name = f.name;
      try {
        const r = await H.api("check", snapshot, lang(), "");
        if (project.active === name && active().text === snapshot) setMarks(r.issues || []);
      } catch (e) { /* проверка «на лету» необязательна */ }
    }, 900);
  }

  // ================================================================ вывод
  let outBuf = [], outQueued = false, outSize = 0;
  const OUT_LIMIT = 200000;
  function out(text, cls) {
    outBuf.push([text, cls || ""]);
    if (!outQueued) { outQueued = true; requestAnimationFrame(flushOut); }
  }
  function flushOut() {
    outQueued = false;
    const c = el.cConsole;
    const stick = c.scrollTop + c.clientHeight >= c.scrollHeight - 30;
    const frag = document.createDocumentFragment();
    for (const [text, cls] of outBuf) {
      const s = document.createElement("span");
      if (cls) s.className = cls;
      s.textContent = text;
      frag.append(s);
      outSize += text.length;
    }
    outBuf = [];
    c.append(frag);
    while (outSize > OUT_LIMIT && c.firstChild) {
      outSize -= c.firstChild.textContent.length;
      c.firstChild.remove();
      if (!c.querySelector(".cut")) {
        const cut = document.createElement("span");
        cut.className = "sys cut";
        cut.textContent = "… начало вывода обрезано …\n";
        c.prepend(cut);
      }
    }
    if (stick) c.scrollTop = c.scrollHeight;
  }
  function clearOut() { el.cConsole.textContent = ""; outBuf = []; outSize = 0; }
  function outImage(b64) {
    flushOut();
    const img = document.createElement("img");
    img.alt = "График";
    img.className = "plot";
    img.src = "data:image/png;base64," + b64;
    el.cConsole.append(img, document.createTextNode("\n"));
  }
  function showPane(name) {
    for (const b of el.root.querySelectorAll(".side-tabs button")) b.setAttribute("aria-selected", String(b.dataset.pane === name));
    el.outPane.hidden = name !== "out";
    el.previewPane.hidden = name !== "preview";
    el.aiPane.hidden = name !== "ai";
  }

  const PY_HINTS = {
    NameError: "Такого имени нет: переменная или функция не создана до этой строки, либо опечатка в названии.",
    TypeError: "Неподходящий тип данных — например, строка плюс число. input() всегда возвращает строку: оберните в int() или float().",
    ValueError: "Неподходящее значение — например, int(\"abc\"). Проверьте, что во «Ввод» вписано число.",
    ZeroDivisionError: "Деление на ноль. Проверьте делитель перед делением.",
    IndexError: "Индекс за пределами списка: элементы нумеруются с 0, последний — len(список) - 1.",
    KeyError: "Такого ключа нет в словаре. Используйте словарь.get(ключ) или проверьте «ключ in словарь».",
    AttributeError: "У объекта нет такого метода или поля — проверьте название и тип объекта.",
    SyntaxError: "Синтаксическая ошибка: проверьте двоеточия, скобки и кавычки. Во вкладке «ИИ-помощник» есть кнопка «Исправить».",
    IndentationError: "Ошибка отступов: строки внутри блока должны иметь одинаковый отступ (4 пробела).",
    TabError: "Смешаны табы и пробелы. Кнопка «Исправить» заменит табы на пробелы.",
    ModuleNotFoundError: "Модуль не найден. В браузере есть вся стандартная библиотека и популярные пакеты (numpy, pandas, matplotlib), если Python загружен с CDN. Своим модулем может быть файл проекта.",
    ImportError: "Не получилось импортировать — проверьте название модуля и того, что из него берётся.",
    RecursionError: "Слишком глубокая рекурсия: у функции нет условия выхода или оно не срабатывает.",
    EOFError: "Программа ждёт ввод: впишите данные в поле «Ввод» над консолью (каждое значение — с новой строки).",
    FileNotFoundError: "Файл не найден. Файлы проекта лежат рядом с программой — проверьте имя.",
    UnboundLocalError: "Переменная используется в функции до присваивания. Если она общая — добавьте global имя.",
    OverflowError: "Число слишком большое для этой операции.",
    MemoryError: "Не хватает памяти — вероятно, бесконечно растущий список.",
    AssertionError: "Проверка assert не прошла.",
    UnicodeDecodeError: "Не та кодировка файла: откройте его с encoding=\"utf-8\"."
  };
  const JS_HINTS = {
    ReferenceError: "Такого имени нет: переменная не объявлена (let/const) или опечатка. document и window есть только на странице — запустите HTML-файл.",
    TypeError: "Действие с неподходящим значением: например, вызов не функции или обращение к полю у undefined/null.",
    SyntaxError: "Синтаксическая ошибка: проверьте скобки, кавычки и запятые.",
    RangeError: "Значение вне допустимого диапазона — часто это бесконечная рекурсия."
  };

  // ================================================================ запуск
  let running = null;  // {kind, worker, t0}
  let pyWorker = null, pyBooted = false, jsWorker = null;

  function setRunning(on) {
    el.cRun.hidden = on;
    el.cStop.hidden = !on;
  }
  function finish(info, hints) {
    const ms = running ? Math.round(performance.now() - running.t0) : 0;
    running = null;
    setRunning(false);
    let r = {};
    try { r = typeof info === "string" ? JSON.parse(info) : info || {}; } catch (e) { r = {}; }
    for (const b64 of r.images || []) outImage(b64);
    if (r.ok === false && r.etype) {
      const hint = hints[r.etype];
      if (hint) out("\nПодсказка: " + hint + "\n", "hint");
      if (r.line && (!r.file || r.file === project.active)) {
        flushOut();
        setMarks([{line: r.line, severity: "error", message: r.etype + ": " + (r.msg || ""), hint: hint}]);
        const b = document.createElement("button");
        b.type = "button"; b.className = "jump";
        b.textContent = "Перейти к строке " + r.line;
        b.addEventListener("click", () => jumpTo(r.line));
        el.cConsole.append(b, document.createTextNode("\n"));
      }
      out(`\n— программа завершилась с ошибкой (${ms} мс)\n`, "sys");
    } else if (r.ok === false && r.exit) {
      out(`\n— выход с кодом ${r.exit} (${ms} мс)\n`, "sys");
    } else {
      out(`\n— готово за ${ms} мс\n`, "sys");
    }
  }

  const PY_RUNNER = String.raw`
def _rai_run(main, stdin_text):
    import os, sys, runpy, traceback, json, builtins, js
    d = "/home/pyodide/project"
    lines = stdin_text.split("\n") if stdin_text else []
    if lines and lines[-1] == "":
        lines.pop()

    class _W:
        def __init__(self, kind):
            self.kind = kind
        def write(self, t):
            if t:
                js.raiWrite(self.kind, str(t))
            return len(t)
        def flush(self):
            pass
        def isatty(self):
            return False

    class _R:
        def readline(self, *a):
            if not lines:
                return ""
            line = lines.pop(0)
            js.raiWrite("in", line + "\n")
            return line + "\n"
        def read(self, *a):
            rest = "".join(l + "\n" for l in lines)
            del lines[:]
            return rest
        def __iter__(self):
            while lines:
                yield self.readline()
        def isatty(self):
            return False

    def _input(prompt=""):
        if prompt:
            sys.stdout.write(str(prompt))
        if not lines:
            raise EOFError("нет входных данных для input()")
        line = lines.pop(0)
        js.raiWrite("in", line + "\n")
        return line

    saved = sys.stdout, sys.stderr, sys.stdin, builtins.input, list(sys.argv), os.getcwd()
    sys.stdout, sys.stderr, sys.stdin, builtins.input = _W("out"), _W("err"), _R(), _input
    os.environ.setdefault("MPLBACKEND", "Agg")
    info = {"ok": True}
    try:
        os.chdir(d)
        if d not in sys.path:
            sys.path.insert(0, d)
        for name, mod in list(sys.modules.items()):
            if (getattr(mod, "__file__", None) or "").startswith(d):
                del sys.modules[name]
        sys.argv = [main]
        try:
            runpy.run_path(os.path.join(d, main), run_name="__main__")
        except SystemExit as e:
            if e.code not in (None, 0):
                info = {"ok": False, "exit": str(e.code)}
        except BaseException as e:
            frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename.startswith(d)]
            text = traceback.format_exception_only(type(e), e)
            if frames:
                text = ["Traceback (most recent call last):\n"] + traceback.format_list(frames) + text
            sys.stderr.write("".join(text).replace(d + "/", ""))
            if isinstance(e, SyntaxError):
                line, fname = e.lineno, os.path.basename(e.filename or main)
            elif frames:
                line, fname = frames[-1].lineno, os.path.basename(frames[-1].filename)
            else:
                line, fname = None, main
            info = {"ok": False, "etype": type(e).__name__, "msg": str(e), "line": line, "file": fname}
        plt = sys.modules.get("matplotlib.pyplot")
        if plt is not None:
            import io, base64
            images = []
            for num in plt.get_fignums():
                buf = io.BytesIO()
                plt.figure(num).savefig(buf, format="png", dpi=100, bbox_inches="tight")
                images.append(base64.b64encode(buf.getvalue()).decode())
            plt.close("all")
            info["images"] = images
    finally:
        sys.stdout, sys.stderr, sys.stdin, builtins.input, sys.argv, cwd = saved
        try:
            os.chdir(cwd)
        except OSError:
            pass
    return json.dumps(info)
`;

  // Модульный воркер: новые версии Pyodide не запускаются в классических воркерах
  const PY_WORKER = `
let py = null, booting = null;
self.raiWrite = (kind, text) => postMessage({type: kind, text: text});
async function boot(sources) {
  const problems = [];
  for (const src of sources) {
    try {
      const mod = await import(src.url + "pyodide.mjs");
      const opts = {indexURL: src.url};
      if (src.stdlib) opts.stdLibURL = src.stdlib;
      py = await mod.loadPyodide(opts);
      py.runPython(${JSON.stringify(PY_RUNNER)});
      return;
    } catch (e) {
      problems.push(src.url + ": " + (e && e.message || e));
    }
  }
  throw new Error(problems.join("\\n"));
}
self.onmessage = async (e) => {
  const m = e.data;
  try {
    if (!py) { postMessage({type: "sys", text: "Загружаю Python (первый запуск — несколько секунд)…\\n"}); await (booting || (booting = boot(m.sources))); postMessage({type: "booted"}); }
  } catch (err) { booting = null; postMessage({type: "fatal", text: String(err && err.message || err)}); return; }
  const d = "/home/pyodide/project";
  try { py.FS.mkdirTree(d); } catch (_) {}
  for (const f of py.FS.readdir(d)) {
    if (f === "." || f === "..") continue;
    try { py.FS.unlink(d + "/" + f); } catch (_) {}
  }
  for (const f of m.files) py.FS.writeFile(d + "/" + f.name, f.text);
  try {
    await py.loadPackagesFromImports(m.files.filter((f) => f.name.endsWith(".py")).map((f) => f.text).join("\\n"),
      {messageCallback: (t) => { if (/^Loaded|^Loading/.test(t)) postMessage({type: "sys", text: t.replace(/^Loaded/, "Загружено:").replace(/^Loading/, "Загружаю:") + "\\n"}); },
       errorCallback: (t) => postMessage({type: "sys", text: t + "\\n"})});
  } catch (err) { postMessage({type: "sys", text: "Не удалось загрузить библиотеку: " + (err && err.message || err) + "\\n"}); }
  let info;
  try { info = py.globals.get("_rai_run")(m.main, m.stdin); }
  catch (err) { info = JSON.stringify({ok: false, etype: "Error", msg: String(err && err.message || err)}); postMessage({type: "err", text: String(err && err.message || err) + "\\n"}); }
  postMessage({type: "done", info: info});
};`;

  const JS_WORKER = `
"use strict";
let lines = [];
function fmt(v, depth) {
  if (typeof v === "string") return depth ? JSON.stringify(v) : v;
  if (v === undefined) return "undefined";
  if (typeof v === "function") return "[Function " + (v.name || "anonymous") + "]";
  if (v instanceof Error) return v.name + ": " + v.message;
  if (typeof v === "bigint") return v + "n";
  if (typeof v === "symbol") return v.toString();
  if (v && typeof v === "object") {
    if ((depth || 0) > 2) return Array.isArray(v) ? "[Array]" : "[Object]";
    try {
      if (Array.isArray(v)) return "[ " + v.map((x) => fmt(x, (depth || 0) + 1)).join(", ") + " ]";
      if (v instanceof Map) return "Map(" + v.size + ") { " + [...v].map(([k, x]) => fmt(k, 1) + " => " + fmt(x, 1)).join(", ") + " }";
      if (v instanceof Set) return "Set(" + v.size + ") { " + [...v].map((x) => fmt(x, 1)).join(", ") + " }";
      return "{ " + Object.keys(v).map((k) => k + ": " + fmt(v[k], (depth || 0) + 1)).join(", ") + " }";
    } catch (e) { return String(v); }
  }
  return String(v);
}
const send = (type, args) => postMessage({type: type, text: args.map((a) => fmt(a)).join(" ") + "\\n"});
console.log = console.info = console.debug = (...a) => send("out", a);
console.warn = (...a) => send("hint", a);
console.error = (...a) => send("err", a);
console.table = (d) => send("out", [d]);
self.prompt = (q) => { if (q) postMessage({type: "out", text: String(q)}); const l = lines.shift(); if (l === undefined) { postMessage({type: "out", text: "\\n"}); return null; } postMessage({type: "in", text: l + "\\n"}); return l; };
self.alert = (q) => send("out", [String(q)]);
function lineOf(err) { const m = String(err && err.stack || "").match(/<anonymous>:(\\d+):\\d+/); return m ? +m[1] : null; }
function report(err) {
  send("err", [(err && err.name ? err.name + ": " + err.message : String(err))]);
  return JSON.stringify({ok: false, etype: err && err.name, msg: err && err.message, line: lineOf(err)});
}
self.addEventListener("error", (e) => { send("err", [e.message]); });
self.addEventListener("unhandledrejection", (e) => { send("err", ["Необработанная ошибка в Promise: " + fmt(e.reason)]); });
onmessage = async (e) => {
  lines = e.data.stdin ? e.data.stdin.replace(/\\n$/, "").split("\\n") : [];
  let code = e.data.code, info = JSON.stringify({ok: true});
  try {
    let r;
    try { r = (0, eval)(code); }
    catch (err) {
      if (err instanceof SyntaxError && /\\bawait\\b/.test(code)) r = (0, eval)("(async () => {" + code + "\\n})()");
      else throw err;
    }
    if (r && typeof r.then === "function") await r;
  } catch (err) { info = report(err); }
  postMessage({type: "done", info: info});
};`;

  function workerFrom(source, module) {
    return new Worker(URL.createObjectURL(new Blob([source], {type: "text/javascript"})), module ? {type: "module"} : undefined);
  }
  function wire(worker, hints) {
    worker.onmessage = (e) => {
      const m = e.data || {};
      if (m.type === "out") out(m.text);
      else if (m.type === "err") out(m.text, "err");
      else if (m.type === "in") out(m.text, "in");
      else if (m.type === "hint") out(m.text, "hint");
      else if (m.type === "sys") out(m.text, "sys");
      else if (m.type === "booted") pyBooted = true;
      else if (m.type === "fatal") {
        out("Не удалось загрузить Python для запуска:\n" + m.text + "\nПроверьте интернет и попробуйте ещё раз.\n", "err");
        stop(true);
      } else if (m.type === "done" && running && running.worker === worker) finish(m.info, hints);
    };
    worker.onerror = (e) => {
      e.preventDefault && e.preventDefault();
      out("Ошибка запуска: " + (e.message || "неизвестная") + "\n", "err");
      if (running && running.worker === worker) stop(true);
    };
  }

  /**
   * Запуск кода без вкладки Code — для нейросети в чате (посчитать, проверить, получить данные).
   * Возвращает {ok, output, error, images}; зависшую программу останавливает по времени.
   */
  let snippetWorker = null;
  function runSnippet(language, code, sources, timeoutMs) {
    return new Promise((resolve) => {
      const isPy = language !== "javascript";
      let worker;
      try {
        worker = isPy ? (snippetWorker || (snippetWorker = workerFrom(PY_WORKER, true))) : workerFrom(JS_WORKER);
      } catch (e) { resolve({ok: false, output: "", error: "Браузер не умеет запускать код в фоне"}); return; }
      let output = "", done = false;
      const finish = (res) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        worker.onmessage = null;
        if (!isPy) worker.terminate();
        resolve(Object.assign({images: []}, res, {output: (res.output || "").slice(0, 6000)}));
      };
      const timer = setTimeout(() => {
        worker.terminate();
        if (isPy) snippetWorker = null;
        finish({ok: false, output: output, error: "Программа работала слишком долго и была остановлена"});
      }, timeoutMs || 60000);
      worker.onmessage = (e) => {
        const m = e.data || {};
        if (m.type === "out" || m.type === "err" || m.type === "hint") output += m.text;
        else if (m.type === "fatal") { snippetWorker = null; finish({ok: false, output: output, error: "Python не загрузился: " + m.text}); }
        else if (m.type === "done") {
          let info = {};
          try { info = JSON.parse(m.info); } catch (_) { /* пустой ответ */ }
          finish({ok: info.ok !== false, output: output, images: info.images || [],
                  error: info.ok === false ? (info.etype ? info.etype + ": " + (info.msg || "") : info.msg || "ошибка") : ""});
        }
      };
      worker.onerror = (e) => { e.preventDefault && e.preventDefault(); finish({ok: false, output: output, error: e.message || "ошибка запуска"}); };
      if (isPy) worker.postMessage({files: [{name: "main.py", text: code}], main: "main.py", stdin: "", sources: sources});
      else worker.postMessage({code: code, stdin: ""});
    });
  }

  function projectFiles() { return project.files.map((f) => ({name: f.name, text: f.text})); }

  function runPython() {
    if (!pyWorker) {
      try { pyWorker = workerFrom(PY_WORKER, true); } catch (e) { out("Этот браузер не умеет запускать код в фоне (Web Worker).\n", "err"); return; }
      wire(pyWorker, PY_HINTS);
      pyBooted = false;
    }
    running = {kind: "python", worker: pyWorker, t0: performance.now()};
    setRunning(true);
    out(`▶ python ${project.active}\n`, "sys");
    pyWorker.postMessage({files: projectFiles(), main: project.active, stdin: el.cStdin.value, sources: H.pyodideSources()});
  }
  function runJS() {
    if (jsWorker) jsWorker.terminate();
    jsWorker = workerFrom(JS_WORKER);
    wire(jsWorker, JS_HINTS);
    running = {kind: "js", worker: jsWorker, t0: performance.now()};
    setRunning(true);
    out(`▶ node ${project.active}\n`, "sys");
    if (/\bdocument\.|\bwindow\.|addEventListener\(|querySelector/.test(active().text) && project.files.some((f) => langOf(f.name) === "html")) {
      out("Код работает со страницей — для него откройте HTML-файл проекта и нажмите «Запустить».\n", "hint");
    }
    jsWorker.postMessage({code: active().text, stdin: el.cStdin.value});
  }

  // Предпросмотр: HTML-файл + подключённые из проекта style.css / script.js
  // В песочнице нет localStorage — подставляем хранилище в памяти, чтобы игры с рекордами не падали
  const CONSOLE_SHIM = `<script>(function(){function mem(){var d={};return{getItem:function(k){return k in d?d[k]:null},setItem:function(k,v){d[k]=String(v)},
removeItem:function(k){delete d[k]},clear:function(){d={}},key:function(i){return Object.keys(d)[i]||null},get length(){return Object.keys(d).length}}}
["localStorage","sessionStorage"].forEach(function(n){try{window[n].length}catch(e){try{Object.defineProperty(window,n,{value:mem(),configurable:true})}catch(_){}}});function f(v){try{return typeof v==="string"?v:v instanceof Error?v.name+": "+v.message:JSON.stringify(v)}catch(e){return String(v)}}
function s(k,a){try{parent.postMessage({raiConsole:1,kind:k,text:Array.prototype.map.call(a,f).join(" ")+"\\n"},"*")}catch(e){}}
console.log=console.info=function(){s("out",arguments)};console.warn=function(){s("hint",arguments)};console.error=function(){s("err",arguments)};
addEventListener("error",function(e){s("err",[e.message+(e.lineno?" (строка "+e.lineno+")":"")])});})();<\/script>`;
  let previewFrame = null;
  function buildPage(file) {
    const files = new Map(project.files.map((f) => [f.name, f.text]));
    let html = file.text;
    html = html.replace(/<link\b[^>]*href=["']([^"']+\.css)["'][^>]*>/gi, (tag, href) =>
      files.has(href.replace(/^\.\//, "")) ? `<style>\n${files.get(href.replace(/^\.\//, "")).replace(/<\/style/gi, "<\\/style")}\n</style>` : tag);
    html = html.replace(/<script\b([^>]*)src=["']([^"']+\.js)["']([^>]*)><\/script>/gi, (tag, a, src, b) =>
      files.has(src.replace(/^\.\//, "")) ? `<script${a}${b}>\n${files.get(src.replace(/^\.\//, "")).replace(/<\/script/gi, "<\\/script")}\n</script>` : tag);
    return /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, (h) => h + CONSOLE_SHIM) : CONSOLE_SHIM + html;
  }
  function runHTML(file) {
    stop(true);
    clearOut();
    el.cPrevEmpty.hidden = true;
    if (previewFrame) previewFrame.remove();
    previewFrame = document.createElement("iframe");
    previewFrame.className = "preview-frame";
    previewFrame.title = "Просмотр страницы";
    previewFrame.setAttribute("sandbox", "allow-scripts allow-modals allow-forms allow-popups");
    previewFrame.srcdoc = buildPage(file);
    el.previewPane.append(previewFrame);
    out(`▶ ${file.name} открыт во вкладке «Просмотр». Сообщения console.log появятся здесь.\n`, "sys");
    showPane("preview");
  }
  window.addEventListener("message", (e) => {
    if (!previewFrame || e.source !== previewFrame.contentWindow || !e.data || !e.data.raiConsole) return;
    out(String(e.data.text), {out: "", err: "err", hint: "hint"}[e.data.kind] || "");
  });

  function run() {
    if (running) return;
    const f = active(), l = lang();
    save(true);
    if (l === "python") { clearOut(); showPane("out"); setMarks([]); runPython(); return; }
    if (l === "javascript") { clearOut(); showPane("out"); setMarks([]); runJS(); return; }
    if (l === "html") { runHTML(f); return; }
    if (l === "css" || l === "json" || l === "text") {
      const page = project.files.find((g) => langOf(g.name) === "html");
      if (page && l === "css") { runHTML(page); return; }
    }
    clearOut();
    showPane("out");
    out(`Запуск прямо в браузере есть для Python, JavaScript и HTML/CSS.\n` +
        `${NAMES[l] || l} здесь можно писать, проверять и объяснять (вкладка «ИИ-помощник»), а запускать — у себя на компьютере: ` +
        `скачайте файл кнопкой «Файл».\n`, "hint");
  }
  function stop(silent) {
    if (!running) { setRunning(false); return; }
    const r = running;
    running = null;
    setRunning(false);
    if (r.kind === "python") {
      r.worker.terminate();
      pyWorker = null;
      if (!silent) out("\n■ Остановлено.\n", "sys");
    } else if (r.kind === "js") {
      r.worker.terminate();
      jsWorker = null;
      if (!silent) out("\n■ Остановлено.\n", "sys");
    }
  }

  // ================================================================ ИИ-помощник
  const ACT_LABEL = {check: "Проверь код", fix: "Исправь ошибки", explain: "Объясни код", comment: "Добавь комментарии", edit: "Правка сайта"};
  function aiMsg(cls, html) {
    const m = document.createElement("div");
    m.className = "ai-msg " + cls;
    if (html !== undefined) m.innerHTML = html;
    el.cAiLog.append(m);
    el.cAiLog.scrollTop = el.cAiLog.scrollHeight;
    return m;
  }
  function actionOf(text) {
    const low = text.toLowerCase();
    if (/исправ|почин|пофикс|\bfix\b/.test(low)) return "fix";
    if (/коммент/.test(low)) return "comment";
    if (/объясн|что делает|как работает|разбери|поясни/.test(low)) return "explain";
    if (/провер|найди ошиб|есть ли ошиб|почему не работает|\bбаг/.test(low)) return "check";
    // Открыт сайт, собранный Rai: «добавь раздел цены», «сделай синим» правят его
    if (lang() === "html" && active().text.includes('id="rai-site"') && SITE_EDIT.test(low) && !/сделай (?:новый )?сайт|создай сайт/.test(low)) return "edit";
    return "generate";
  }
  const SITE_EDIT = /^\s*(?:а\s+)?(?:теперь\s+)?(?:добавь|убери|удали|скрой|переименуй|назови|измени|поменяй|замени|сделай|цвет|другие картинки|новые картинки|слоган|почт|телефон)/;
  function applyCode(target, code) {
    const file = project.files.find((x) => x.name === target);
    if (!file) return false;
    if (project.active !== target) openTab(target);
    el.ta.focus();
    el.ta.setSelectionRange(0, el.ta.value.length);
    insert(code);  // одним действием: Ctrl+Z вернёт как было
    el.ta.setSelectionRange(0, 0);
    el.ta.scrollTop = 0;
    scheduleCheck();
    return true;
  }
  // ---------------------------------------------------------------- нейросеть в Code
  const NEURO_TASK = {
    fix: "Найди и исправь все ошибки в этом коде. Верни весь исправленный файл.",
    explain: "Объясни по-русски, что делает этот код, по шагам и простыми словами. Код целиком не повторяй.",
    comment: "Добавь понятные комментарии на русском к этому коду. Верни весь файл с комментариями.",
    edit: "Внеси изменение в этот файл. Верни весь файл целиком."
  };
  const LANG_EXT = {python: "py", py: "py", javascript: "js", js: "js", typescript: "ts", ts: "ts", html: "html", css: "css", php: "php",
    json: "json", cpp: "cpp", "c++": "cpp", c: "c", java: "java", csharp: "cs", cs: "cs", go: "go", rust: "rs", rs: "rs", sql: "sql",
    bash: "sh", sh: "sh", kotlin: "kt", kt: "kt", swift: "swift", ruby: "rb", lua: "lua", dart: "dart"};
  const CHANGE_WORDS = /измени|добав|исправ|переделай|убери|удали|поменяй|допиши|улучши|сделай(?! новую| новый)|перепиши|замени|ускорь|оптимизируй/;
  function neuroFileName(block) {
    const l = (block.lang || "").toLowerCase();
    if (l === "html" || /<(?:!doctype|html|body)\b/i.test(block.code)) return "index.html";
    if (l === "java") return "Main.java";
    return "main." + (LANG_EXT[l] || (/^\s*(def |import |print\()/m.test(block.code) ? "py" : "txt"));
  }
  async function neuroAi(action, prompt) {
    if (H.takeNeuro && !(await H.takeNeuro())) return;  // лимит нейросети на сегодня исчерпан — окно с тарифами уже показано
    const f = active();
    showPane("ai");
    const me = aiMsg("me");
    me.textContent = prompt || ACT_LABEL[action] + " · " + f.name;
    const pend = aiMsg("rai", `<span class="typing" aria-label="Нейросеть думает"><span></span><span></span><span></span></span>`);
    const stopBtn = document.createElement("button");
    stopBtn.type = "button"; stopBtn.className = "tb"; stopBtn.textContent = "Остановить";
    stopBtn.addEventListener("click", () => H.neuro.stop());
    // Работаем с открытым файлом, если просят изменить его (или это кнопки «Исправить», «Объяснить», «Комментарии»)
    const withFile = !!f.text.trim() && (action !== "generate" || CHANGE_WORDS.test((prompt || "").toLowerCase()));
    const task = action === "generate" ? (withFile ? NEURO_TASK.edit + " Задание: " + prompt : prompt) : NEURO_TASK[action];
    const content = (withFile ? `Файл ${f.name}:\n\`\`\`${lang()}\n${f.text.slice(0, 14000)}\n\`\`\`\n\n` : "") + task;
    const target = f.name;
    let text = "", queued = false, done = false;
    const paint = () => { queued = false; if (done) return; pend.innerHTML = `<div class="md">${H.md(text)}</div>`; pend.append(stopBtn); el.cAiLog.scrollTop = el.cAiLog.scrollHeight; };
    try {
      text = await H.neuro.chat([{role: "user", content: content}], (full) => { text = full; if (!queued) { queued = true; requestAnimationFrame(paint); } },
                                {system: H.neuro.CODE_SYSTEM, temperature: 0.2, maxTokens: 3500});
    } catch (e) {
      done = true;
      pend.innerHTML = H.md("Нейросеть не ответила: " + ((e && e.message) || e));
      return;
    }
    done = true;  // последняя отрисовка по кадру не должна затереть кнопки ниже
    const biggest = (t) => H.neuro.codeBlocks(t).sort((a, b) => b.code.length - a.code.length)[0];
    let main = biggest(text), tested = "";
    // Нейросеть сама проверяет программу запуском и, если упала, исправляет ошибку (один раз)
    const runLang = main ? (FAMILY[main.lang] ? main.lang : langOf(neuroFileName(main))) : "";
    const interactive = /\binput\s*\(|\bprompt\s*\(|turtle|tkinter|pygame|readline|while\s+True|setInterval|requestAnimationFrame|document\.|window\./;
    if (main && action !== "explain" && ["python", "javascript"].includes(runLang) && !interactive.test(main.code) && H.pyodideSources) {
      for (let attempt = 0; attempt < 2; attempt++) {
        pend.innerHTML = `<div class="md">${H.md(attempt ? "🔧 *Исправляю ошибку и проверяю снова…*" : "▶ *Проверяю программу запуском…*")}</div>`;
        const r = await runSnippet(runLang, main.code, H.pyodideSources(), 45000);
        if (r.ok) {
          tested = (attempt ? "🔧 Нашла ошибку при запуске, исправила и проверила — **работает** ✓" : "▶ Проверила запуском — **работает** ✓") +
            (r.output.trim() ? "\n\n```text\n" + r.output.trim().slice(0, 600) + "\n```" : "");
          break;
        }
        if (attempt === 1) { tested = "⚠ При запуске всё ещё ошибка: `" + r.error.slice(0, 200) + "`"; break; }
        let fixed = "";
        try {
          fixed = await H.neuro.chat([{role: "user", content: content}, {role: "assistant", content: text},
            {role: "user", content: "Я запустил этот код, и он упал:\n" + r.error + "\nВывод:\n" + r.output.slice(-1500) +
              "\nИсправь ошибку и верни ВЕСЬ файл целиком в одном блоке кода."}], null,
            {system: H.neuro.CODE_SYSTEM, temperature: 0.2, maxTokens: 3500});
        } catch (e) { break; }
        const again = biggest(fixed);
        if (!again) break;
        main = again; text = fixed;
      }
    }
    pend.innerHTML = `<div class="md">${H.md(main && action !== "explain" ? text.replace(/```[\s\S]*?(?:```|$)/, "*(код — ниже)*") + (tested ? "\n\n" + tested : "") : text)}</div>`;
    if (!main || action === "explain") return;
    const box = document.createElement("div");
    const l = FAMILY[main.lang] ? main.lang : langOf(neuroFileName(main));
    box.innerHTML = `<div class="codeblock ai-code"><div class="codehead"><span>${esc(withFile ? target : neuroFileName(main))}</span></div>` +
      `<pre><code>${highlight(main.code, l)}</code></pre></div>`;
    const row = document.createElement("div");
    row.className = "row";
    const btn = (label, fn, red) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "tb" + (red ? " run" : ""); b.textContent = label;
      b.addEventListener("click", fn);
      row.append(b);
    };
    if (withFile) {
      btn("Применить к " + target, (e) => {
        if (!applyCode(target, main.code)) return;
        e.currentTarget.textContent = "Применено"; e.currentTarget.disabled = true;
        if (langOf(target) === "html") run();
      }, true);
    }
    btn((withFile ? "Новым файлом " : "Создать файл ") + neuroFileName(main), (e) => {
      const name = addFile(neuroFileName(main), main.code);
      e.currentTarget.textContent = "Создан: " + name; e.currentTarget.disabled = true;
      if (langOf(name) === "html") run();
      else if (["python", "javascript"].includes(langOf(name))) H.toast("Готово — нажмите «Запустить»");
    }, !withFile);
    btn("Копировать", () => H.copy(main.code));
    pend.append(box, row);
    el.cAiLog.scrollTop = el.cAiLog.scrollHeight;
  }

  async function ai(action, prompt) {
    const f = active();
    if (action !== "generate" && !f.text.trim()) { H.toast("Файл пустой — сначала напишите код"); return; }
    // Нейросеть включена — пишет и правит код сама; «Проверить» остаётся за быстрым анализатором
    if (H.neuro && H.neuro.ready() && action !== "check") return neuroAi(action === "edit" ? "generate" : action, prompt);
    showPane("ai");
    const me = aiMsg("me");
    me.textContent = prompt || ACT_LABEL[action] + " · " + f.name;
    const sitePane = action === "edit";
    const pend = aiMsg("rai", `<span class="typing" aria-label="Rai думает"><span></span><span></span><span></span></span>`);
    const target = f.name, source = f.text;
    let r;
    try {
      r = await H.api(action, action === "generate" ? "" : source, action === "generate" ? (lang() === "text" ? null : lang()) : lang(), prompt || "");
    } catch (e) {
      pend.innerHTML = H.md("Не удалось получить ответ: " + (e && e.message || e));
      return;
    }
    pend.innerHTML = `<div class="md">${H.md(r.answer || r.error || "Нет ответа.")}</div>`;
    if (r.issues && project.active === target) setMarks(r.issues);
    const lines = [...new Set((r.issues || []).map((i) => i.line).filter(Boolean))].slice(0, 12);
    if (lines.length) {
      const row = document.createElement("div");
      row.className = "row";
      row.append("Перейти к строке: ");
      for (const n of lines) {
        const b = document.createElement("button");
        b.type = "button"; b.className = "jump"; b.textContent = n;
        b.addEventListener("click", () => { if (project.active !== target) openTab(target); jumpTo(n); });
        row.append(b);
      }
      pend.append(row);
    }
    if (r.code) {
      const box = document.createElement("div");
      box.innerHTML = `<div class="codeblock ai-code"><div class="codehead"><span>${esc(r.filename || NAMES[r.lang] || r.lang || "код")}</span></div>` +
        `<pre><code>${highlight(r.code, r.lang)}</code></pre></div>`;
      const row = document.createElement("div");
      row.className = "row";
      const btn = (label, fn, red) => {
        const b = document.createElement("button");
        b.type = "button"; b.className = "tb" + (red ? " run" : ""); b.textContent = label;
        b.addEventListener("click", fn);
        row.append(b);
        return b;
      };
      if (sitePane) {
        // Правка сайта применяется сразу и видна в «Просмотре»; Ctrl+Z в редакторе вернёт как было
        if (applyCode(target, r.code)) { run(); showPane("ai"); }
        btn("Показать сайт", () => run(), true);
      } else if (action === "generate") {
        btn("Создать файл " + (r.filename || "main." + (r.lang || "txt")), (e) => {
          const name = addFile(r.filename || "main.py", r.code);
          e.currentTarget.textContent = "Создан: " + name;
          e.currentTarget.disabled = true;
          if (langOf(name) === "html") run();  // сайт или игру сразу видно в «Просмотре»
          else if (["python", "javascript"].includes(langOf(name))) H.toast("Готово — нажмите «Запустить»");
        }, true);
      } else if (r.changed !== false) {
        btn("Применить к " + target, (e) => {
          if (!applyCode(target, r.code)) return;
          e.currentTarget.textContent = "Применено";
          e.currentTarget.disabled = true;
        }, true);
      }
      btn("Копировать", () => H.copy(r.code));
      pend.append(box, row);
    }
    el.cAiLog.scrollTop = el.cAiLog.scrollHeight;
  }

  // ================================================================ файлы с компьютера
  async function openLocal(list) {
    let n = 0;
    for (const file of list) {
      if (file.size > 1024 * 1024) { H.toast(file.name + ": файл больше 1 МБ"); continue; }
      const text = await file.text();
      if (/\u0000/.test(text.slice(0, 2000))) { H.toast(file.name + ": это не текстовый файл"); continue; }
      addFile(file.name, text.replace(/\r\n/g, "\n"));
      n++;
    }
    if (n) H.toast("Открыто файлов: " + n);
  }

  // ================================================================ инициализация
  function init(host) {
    H = host;
    const root = document.getElementById("codeView");
    build(root);
    load();
    el.cStdin.value = project.stdin || "";
    renderFiles();
    loadEditor();

    el.ta.addEventListener("input", onInput);
    el.ta.addEventListener("keydown", onKey);
    el.ta.addEventListener("scroll", syncScroll);
    el.cStdin.addEventListener("input", () => { project.stdin = el.cStdin.value; save(); });
    el.cRun.addEventListener("click", run);
    el.cStop.addEventListener("click", () => stop(false));
    el.cDiag.addEventListener("click", () => ai("check"));
    el.cDl.addEventListener("click", () => {
      const f = active();
      H.download(f.name, new Blob([f.text], {type: "text/plain;charset=utf-8"}));
    });
    el.cZip.addEventListener("click", () => {
      H.download("rai-code.zip", H.zip(project.files.map((f) => ({name: f.name, data: f.text}))));
    });
    el.cOpen.addEventListener("click", () => el.cFile.click());
    el.cFile.addEventListener("change", () => { openLocal(Array.from(el.cFile.files || [])); el.cFile.value = ""; });
    for (const b of root.querySelectorAll(".side-tabs button")) b.addEventListener("click", () => showPane(b.dataset.pane));
    for (const b of root.querySelectorAll(".ai-quick button")) b.addEventListener("click", () => ai(b.dataset.act));
    const aiInput = el.cAiInput;
    const send = () => {
      const text = aiInput.value.trim();
      if (!text) return;
      aiInput.value = "";
      ai(actionOf(text), text);
    };
    el.cAiForm.addEventListener("submit", (e) => { e.preventDefault(); send(); });
    aiInput.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    if (window.RaiCode && window.RaiCode.neuroChanged) setTimeout(window.RaiCode.neuroChanged, 0);
    aiMsg("rai", H.md("Я — ИИ-помощник Rai для кода. **Проверю** и найду ошибки, **исправлю**, **объясню** по строкам, " +
      "**добавлю комментарии** или **напишу программу** по описанию. Горячие клавиши: `Ctrl+Enter` — запуск, " +
      "`Ctrl+/` — закомментировать, `Tab` / `Shift+Tab` — отступ."));
  }

  window.RaiCode = {
    init: init,
    addFile: addFile,
    engineReady: () => { if (el.ta) scheduleCheck(); },
    neuroChanged: () => {
      if (!el.cAiInput) return;
      el.cAiInput.placeholder = H.neuro && H.neuro.ready()
        ? "Нейросеть напишет что угодно: «игра гонки на canvas», «бот для Telegram на Python», «добавь в этот код счёт очков»…"
        : "Что написать? Сайт кофейни в тёмных тонах, игра тетрис, погода, функция среднего… Для сайта: «добавь раздел цены»";
    },
    focus: () => { if (el.ta) { refresh(); el.ta.focus(); } },
    highlight: highlight,
    langOf: langOf,
    runSnippet: runSnippet
  };
})();
