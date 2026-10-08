"""Проверка зрения Rai в настоящем Chrome: что vision.js увидит на фото из Википедии (запускает GitHub).

Берутся фото из английской Википедии — другие снимки, чем в русских статьях, по которым Rai учился узнавать вещи.
"""
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ITEMS = [["Sunset", "en"], ["Cat", "en"], ["Rainbow", "en"], ["Pizza", "en"], ["Andromeda Galaxy", "en"], ["Moscow Kremlin", "en"],
         ["Giraffe", "en"], ["Association football", "en"], ["Eiffel Tower", "en"], ["Mona Lisa", "en"], ["Statue of Liberty", "en"],
         ["Saint Basil's Cathedral", "en"], ["Red fox", "en"], ["Saturn", "en"]]
server = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.on("console", lambda m: print("   [браузер]", m.text) if "%" not in m.text else None)
        page.goto("http://127.0.0.1:8765/tools/vision_check.html")
        results = page.evaluate("(t) => window.check(t)", ITEMS)
        ok = known = 0
        for r in results:
            print(f"{r['title']}: {', '.join(r.get('labels', []))}\n   узнал: {', '.join(r.get('known', [])) or '—'}"
                  f"\n   признаки: {'; '.join(r.get('attrs', []))}\n   части: {'; '.join(r.get('regions', [])) or '—'}"
                  f"\n   цвета: {', '.join(r.get('colors', []))} {r.get('tone', '')} {r.get('light', '')} | {r.get('ms', '?')} мс {r.get('error', '')}")
            ok += bool(r.get("labels"))
            known += bool(r.get("known"))
        print(f"распознано: {ok} из {len(ITEMS)}, узнано конкретных вещей: {known}")
        browser.close()
    if ok < len(ITEMS) // 2:
        sys.exit("Зрение Rai не распознало картинки")
finally:
    server.terminate()
