/*
 * Встроенная копия Rai для работы без интернета: offline/index.html (весь Rai в одном файле, как build_standalone.py)
 * + папки pyodide/ (Python для браузера) и ocr/ (распознавание текста). Запускается перед сборкой приложения.
 */
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.resolve(__dirname, "..", "offline");

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const pythons = process.env.PYTHON ? [process.env.PYTHON] : ["python3", "python", "py"];
let built = false;
for (const py of pythons) {
  try {
    // UTF-8 — иначе на Windows Python не сможет напечатать русский текст и упадёт
    execFileSync(py, [path.join(ROOT, "build_standalone.py"), "-o", path.join(OUT, "index.html")],
      { stdio: "inherit", env: { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" } });
    built = true;
    break;
  } catch (e) { /* пробуем следующий */ }
}
if (!built) throw new Error("Не нашёл Python 3 для build_standalone.py (задайте переменную PYTHON)");

for (const dir of ["pyodide", "ocr"]) {
  const src = path.join(ROOT, dir);
  if (fs.existsSync(src)) fs.cpSync(src, path.join(OUT, dir), { recursive: true });
  else console.warn("нет папки " + dir + " — офлайн-копия будет брать её из интернета");
}
console.log("Офлайн-копия Rai готова:", OUT);
