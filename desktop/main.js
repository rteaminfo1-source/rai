/*
 * Rai — приложение для Windows, macOS и Linux.
 *
 * Как устроено:
 *  • Окно показывает сам сайт https://rai.rteam.info/chat.html — поэтому чат, функции и нейросеть всегда свежие:
 *    как только обновился сайт (или GitHub выложил его на хостинг), обновилось и приложение. Раз в 20 минут
 *    приложение проверяет, не изменился ли сайт, и предлагает обновить страницу.
 *  • Нет интернета или сайта — открывается встроенная копия Rai (движок, Python и распознавание текста внутри),
 *    чат работает без сети.
 *  • Само приложение обновляется: проверяет новые версии на GitHub (релизы), а если GitHub недоступен —
 *    на хостинге (https://rai.rteam.info/app/). Windows и Linux ставят обновление сами, на macOS — открывается
 *    страница загрузки (без платной подписи Apple обновлять приложение само нельзя).
 */
const { app, BrowserWindow, Menu, Tray, shell, session, protocol, net, dialog, desktopCapturer, ipcMain, nativeImage } = require("electron");
const path = require("path");
const fs = require("fs");

const SITE = process.env.RAI_SITE || "https://rai.rteam.info";
const START = SITE + "/chat.html";
const DOWNLOAD_PAGE = SITE + "/#download";
const RELEASES = "https://github.com/rteaminfo1-source/rai/releases/latest";
const OFFLINE_DIR = app.isPackaged ? path.join(process.resourcesPath, "offline") : path.join(__dirname, "offline");
const ICON = path.join(__dirname, "build", "icon.png");
const STATE_FILE = () => path.join(app.getPath("userData"), "window.json");

let win = null;
let tray = null;
let offline = false;
let siteStamp = null;   // ETag / Last-Modified сайта при загрузке — чтобы заметить обновление
let quitting = false;

// WebGPU — для нейросети Rai Нейро на видеокарте (в Linux по умолчанию выключен)
app.commandLine.appendSwitch("enable-unsafe-webgpu");
app.commandLine.appendSwitch("enable-features", "Vulkan,WebGPU");

// Своя «внутренняя» схема для офлайн-копии: на file:// браузер не даёт загрузить Python (WebAssembly)
protocol.registerSchemesAsPrivileged([
  { scheme: "rai", privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true } },
]);

// Одна копия приложения: второй запуск просто показывает окно уже открытого Rai
const firstCopy = app.requestSingleInstanceLock();
if (!firstCopy) {
  app.quit();
} else {
  app.on("second-instance", () => { if (win) { if (win.isMinimized()) win.restore(); win.show(); win.focus(); } });
}

const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript", ".wasm": "application/wasm",
  ".json": "application/json", ".zip": "application/zip", ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml",
  ".traineddata": "application/octet-stream", ".gz": "application/gzip", ".txt": "text/plain; charset=utf-8",
};

function serveOffline() {
  protocol.handle("rai", async (request) => {
    const url = new URL(request.url);
    let rel = decodeURIComponent(url.pathname).replace(/^\/+/, "") || "index.html";
    const file = path.normalize(path.join(OFFLINE_DIR, rel));
    if (!file.startsWith(OFFLINE_DIR)) return new Response("forbidden", { status: 403 });
    try {
      const data = await fs.promises.readFile(file);
      return new Response(data, {
        headers: {
          "Content-Type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream",
          // изоляция страницы — нейросеть на процессоре работает в несколько потоков
          "Cross-Origin-Opener-Policy": "same-origin",
          "Cross-Origin-Embedder-Policy": "credentialless",
          // Python отсюда берёт и страница сайта (rai.rteam.info) — разрешаем ей читать эти файлы
          "Access-Control-Allow-Origin": "*",
          "Cross-Origin-Resource-Policy": "cross-origin",
        },
      });
    } catch (e) {
      return new Response("not found", { status: 404 }); // me.php, limits.php… в офлайне нет — страница это понимает
    }
  });
}

function loadState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE(), "utf8")); } catch (e) { return { width: 1280, height: 860 }; }
}
function saveState() {
  if (!win) return;
  try {
    const b = win.getNormalBounds();
    fs.writeFileSync(STATE_FILE(), JSON.stringify({ ...b, maximized: win.isMaximized() }));
  } catch (e) { /* не страшно */ }
}

async function siteReachable() {
  try {
    const r = await net.fetch(START, { method: "HEAD", cache: "no-store" });
    if (!r.ok) return false;
    siteStamp = r.headers.get("etag") || r.headers.get("last-modified") || r.headers.get("content-length");
    return true;
  } catch (e) {
    return false;
  }
}

async function openRai() {
  if (await siteReachable()) {
    offline = false;
    try {
      await win.loadURL(START);
    } catch (e) {
      // сайт ответил, но страница не открылась — встроенный Rai (его включает did-fail-load)
    }
  } else {
    offline = true;
    await win.loadURL("rai://app/index.html").catch(() => {});
    banner("Нет связи с rai.rteam.info — работает встроенный Rai без интернета. Когда связь появится, нажмите «Обновить».", "Обновить", "online", 20);
  }
  buildMenu();
}

/** Полоска сверху страницы с кнопкой (страница обновилась, вышла новая версия, нет интернета). */
function banner(text, button, action = "reload", hideAfter = 0) {
  if (!win) return;
  const js = `(() => {
    let b = document.getElementById("rai-app-banner");
    if (!b) { b = document.createElement("div"); b.id = "rai-app-banner"; document.body.appendChild(b); }
    b.style.cssText = "position:fixed;left:50%;top:12px;transform:translateX(-50%);z-index:99999;display:flex;gap:12px;align-items:center;" +
      "padding:10px 14px;border-radius:14px;background:#16161f;color:#fff;font:14px system-ui,sans-serif;border:1px solid #3a2030;" +
      "box-shadow:0 12px 40px -10px rgba(255,45,45,.6);max-width:calc(100vw - 32px)";
    b.innerHTML = "";
    const t = document.createElement("span"); t.textContent = ${JSON.stringify(text)}; b.appendChild(t);
    const go = document.createElement("button"); go.textContent = ${JSON.stringify(button)};
    go.style.cssText = "border:0;border-radius:10px;padding:7px 12px;font-weight:600;color:#fff;cursor:pointer;background:linear-gradient(120deg,#ff2d2d,#ff3d81 55%,#8b5cff)";
    go.onclick = () => { b.remove(); window.RaiApp && window.RaiApp.action(${JSON.stringify(action)}); };
    const x = document.createElement("button"); x.textContent = "✕"; x.title = "Закрыть";
    x.style.cssText = "border:0;background:none;color:#aaa;font-size:16px;cursor:pointer"; x.onclick = () => b.remove();
    b.append(go, x);
    if (${Number(hideAfter) || 0}) setTimeout(() => b.remove(), ${(Number(hideAfter) || 0) * 1000});
  })();`;
  win.webContents.executeJavaScript(js).catch(() => {});
}

// ---------------------------------------------------------------- обновления содержимого (сайт)
async function checkSite() {
  if (!win) return;
  const before = siteStamp;
  const ok = await siteReachable();
  if (offline && ok) {
    banner("Связь с rai.rteam.info есть — можно открыть полную версию Rai.", "Открыть", "online");
    return;
  }
  if (!offline && ok && before && siteStamp && before !== siteStamp) {
    banner("Rai обновился: на сайте новая версия.", "Обновить страницу");
  }
}

// ---------------------------------------------------------------- обновления самого приложения
let updater = null;
function setupUpdater() {
  if (!app.isPackaged) return; // при разработке не обновляемся
  try {
    updater = require("electron-updater").autoUpdater;
  } catch (e) {
    return;
  }
  updater.autoDownload = process.platform !== "darwin";
  updater.autoInstallOnAppQuit = true;
  updater.on("update-downloaded", (info) => {
    banner(`Скачана новая версия Rai ${info.version}. Она установится при выходе — или прямо сейчас.`, "Перезапустить", "install");
  });
  updater.on("update-available", (info) => {
    if (process.platform === "darwin") {
      banner(`Вышла новая версия Rai ${info.version}.`, "Скачать", "download");
    }
  });
}

async function checkApp(manual = false) {
  if (!updater) {
    if (manual) dialog.showMessageBox(win, { message: "Обновления проверяются в установленном приложении.", buttons: ["Хорошо"] });
    return;
  }
  // Сначала GitHub (релизы), если не вышло — свой хостинг
  const feeds = [
    { provider: "github", owner: "rteaminfo1-source", repo: "rai", releaseType: "release" },
    { provider: "generic", url: SITE + "/app/" },
  ];
  for (const feed of feeds) {
    try {
      updater.setFeedURL(feed);
      const r = await updater.checkForUpdates();
      const latest = r && r.updateInfo && r.updateInfo.version;
      if (manual) {
        const newer = latest && latest !== app.getVersion();
        dialog.showMessageBox(win, {
          message: newer ? `Найдена версия ${latest} — ${process.platform === "darwin" ? "откроется страница загрузки" : "скачивается"}.` : `У вас последняя версия Rai (${app.getVersion()}).`,
          buttons: ["Хорошо"],
        });
        if (newer && process.platform === "darwin") shell.openExternal(DOWNLOAD_PAGE);
      }
      return;
    } catch (e) {
      continue;
    }
  }
  if (manual) dialog.showMessageBox(win, { message: "Не удалось проверить обновления: нет связи с GitHub и rai.rteam.info.", buttons: ["Хорошо"] });
}

ipcMain.on("rai-action", (_e, action) => {
  if (action === "reload") { win.webContents.reloadIgnoringCache(); }
  else if (action === "online") { openRai(); }
  else if (action === "install" && updater) { quitting = true; updater.quitAndInstall(); }
  else if (action === "download") { shell.openExternal(DOWNLOAD_PAGE); }
  else if (action === "check-updates") { checkApp(true); }
});
ipcMain.handle("rai-info", () => ({ version: app.getVersion(), platform: process.platform, offline }));

// ---------------------------------------------------------------- окно, меню, трей
function buildMenu() {
  const template = [
    {
      label: "Rai",
      submenu: [
        { label: "Обновить страницу", accelerator: "CmdOrCtrl+R", click: () => win.webContents.reloadIgnoringCache() },
        { label: "Открыть полную версию (сайт)", click: () => openRai() },
        { label: "Проверить обновления приложения…", click: () => checkApp(true) },
        { type: "separator" },
        { label: "Открыть rai.rteam.info в браузере", click: () => shell.openExternal(SITE) },
        { label: "Личный кабинет", click: () => win.loadURL(SITE + "/account.php") },
        { label: "Тарифы", click: () => win.loadURL(SITE + "/#pricing") },
        { type: "separator" },
        { label: `О программе (версия ${app.getVersion()})`, click: () => dialog.showMessageBox(win, {
          title: "Rai", icon: ICON,
          message: `Rai ${app.getVersion()}`,
          detail: "Свой ИИ-помощник команды Rteam.\nСодержимое обновляется с rai.rteam.info, приложение — с GitHub.\n" + (offline ? "Сейчас: встроенная версия без интернета." : "Сейчас: rai.rteam.info"),
          buttons: ["Хорошо"] }) },
        { type: "separator" },
        { label: "Выход", accelerator: "CmdOrCtrl+Q", click: () => { quitting = true; app.quit(); } },
      ],
    },
    { label: "Правка", submenu: [{ role: "undo", label: "Отменить" }, { role: "redo", label: "Повторить" }, { type: "separator" },
      { role: "cut", label: "Вырезать" }, { role: "copy", label: "Копировать" }, { role: "paste", label: "Вставить" }, { role: "selectAll", label: "Выделить всё" }] },
    { label: "Вид", submenu: [{ role: "zoomIn", label: "Крупнее" }, { role: "zoomOut", label: "Мельче" }, { role: "resetZoom", label: "Обычный размер" },
      { type: "separator" }, { role: "togglefullscreen", label: "Во весь экран" }, { role: "toggleDevTools", label: "Инструменты разработчика" }] },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createTray() {
  try {
    const img = nativeImage.createFromPath(ICON).resize({ width: 18, height: 18 });
    tray = new Tray(img);
    tray.setToolTip("Rai");
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: "Открыть Rai", click: () => { win.show(); win.focus(); } },
      { label: "Проверить обновления", click: () => checkApp(true) },
      { type: "separator" },
      { label: "Выход", click: () => { quitting = true; app.quit(); } },
    ]));
    tray.on("click", () => { win.isVisible() ? win.focus() : win.show(); });
  } catch (e) { tray = null; }
}

function isOwn(url) {
  try {
    const u = new URL(url);
    return u.protocol === "rai:" || u.origin === new URL(SITE).origin;
  } catch (e) { return false; }
}

function createWindow() {
  const st = loadState();
  win = new BrowserWindow({
    width: st.width || 1280, height: st.height || 860, x: st.x, y: st.y, minWidth: 380, minHeight: 500,
    title: "Rai", icon: ICON, backgroundColor: "#0b0b0c", show: false, autoHideMenuBar: process.platform !== "darwin",
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true, spellcheck: true },
  });
  if (st.maximized) win.maximize();
  win.once("ready-to-show", () => win.show());
  ["resize", "move", "close"].forEach((ev) => win.on(ev, saveState));

  // Окно закрыли — на macOS и с треем приложение остаётся в фоне
  win.on("close", (e) => {
    if (!quitting && process.platform === "darwin") { e.preventDefault(); win.hide(); }
  });

  // Чужие ссылки — в обычном браузере, Google-вход — в отдельном окне
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/accounts\.google\.com/.test(url)) return { action: "allow" };
    if (!isOwn(url)) { shell.openExternal(url); return { action: "deny" }; }
    return { action: "allow" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (!isOwn(url) && !/accounts\.google\.com|google\.com\/signin/.test(url)) { e.preventDefault(); shell.openExternal(url); }
  });
  // Сайт не открылся (пропала связь) — встроенный Rai
  win.webContents.on("did-fail-load", (_e, code, _desc, url, isMain) => {
    if (isMain && code !== -3 && !String(url).startsWith("rai:")) { offline = true; win.loadURL("rai://app/index.html"); }
  });
}

function setupSession() {
  const ses = session.defaultSession;
  // Google не любит встроенные браузеры: представляемся обычным Chrome
  ses.setUserAgent(ses.getUserAgent().replace(/\s?Electron\/\S+/, "").replace(/\s?rai-desktop\/\S+/i, "").replace(/\s?Rai\/\S+/, ""));
  // Микрофон (голосовой ввод), запись экрана и уведомления — только для Rai
  ses.setPermissionRequestHandler((wc, permission, callback, details) => {
    const allowed = ["media", "display-capture", "notifications", "clipboard-read", "clipboard-sanitized-write", "fullscreen"];
    callback(allowed.includes(permission) && isOwn(details.requestingUrl || wc.getURL()));
  });
  // «Записать экран» и «Снимок экрана» в Rai: отдаём весь основной экран
  ses.setDisplayMediaRequestHandler((request, callback) => {
    desktopCapturer.getSources({ types: ["screen"] }).then((sources) => {
      callback(sources.length ? { video: sources[0], audio: process.platform === "win32" ? "loopback" : undefined } : {});
    }).catch(() => callback({}));
  }, { useSystemPicker: true });
}

app.whenReady().then(async () => {
  if (!firstCopy) return;
  serveOffline();
  setupSession();
  createWindow();
  buildMenu();
  createTray();
  setupUpdater();
  await openRai();
  setTimeout(() => checkApp(false), 15 * 1000);            // обновления приложения: через 15 секунд после запуска
  setInterval(() => checkApp(false), 4 * 60 * 60 * 1000);   // и каждые 4 часа
  setInterval(checkSite, 20 * 60 * 1000);                   // обновления сайта — каждые 20 минут
});

app.on("activate", () => { if (win) { win.show(); win.focus(); } });
app.on("before-quit", () => { quitting = true; saveState(); });
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
