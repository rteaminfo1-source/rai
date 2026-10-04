"""Проверка зрения Rai в настоящем Chrome: что vision.js увидит на фото из Википедии (запускает GitHub)."""
import json
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

TITLES = ["Закат", "Кошка", "Радуга", "Пицца", "Галактика Андромеды", "Московский Кремль", "Жираф", "Футбол"]
server = subprocess.Popen([sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.on("console", lambda m: print("   [браузер]", m.text) if "%" not in m.text else None)
        page.goto("http://127.0.0.1:8765/tools/vision_check.html")
        results = page.evaluate("(t) => window.check(t)", TITLES)
        ok = 0
        for r in results:
            print(f"{r['title']}: {', '.join(r.get('labels', []))} | цвета: {', '.join(r.get('colors', []))} {r.get('tone', '')} {r.get('light', '')} "
                  f"| {r.get('ms', '?')} мс {r.get('error', '')}")
            ok += bool(r.get("labels"))
        browser.close()
    if ok < len(TITLES) // 2:
        sys.exit("Зрение Rai не распознало картинки")
finally:
    server.terminate()
