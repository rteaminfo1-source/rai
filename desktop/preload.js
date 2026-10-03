/* Мостик между страницей Rai и приложением: страница узнаёт, что она в приложении, и может нажать кнопки полоски. */
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("RaiApp", {
  isApp: true,
  // Python (Pyodide) из самого приложения: чат на сайте запускается без скачивания и без CDN
  pyodide: "rai://app/pyodide/",
  info: () => ipcRenderer.invoke("rai-info"),
  action: (name) => ipcRenderer.send("rai-action", String(name)),
  checkUpdates: () => ipcRenderer.send("rai-action", "check-updates"),
});
