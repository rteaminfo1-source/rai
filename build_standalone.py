"""Собрать rai.html — один файл, в который встроены все .py и knowledge.json.

Такой файл можно открыть откуда угодно (скачать, переслать, положить на любой
хостинг): Python запускается прямо в браузере через Pyodide.

    python build_standalone.py                       # -> rai.html
    python build_standalone.py --pyodide pyodide/    # Pyodide лежит рядом, а не на CDN
    python build_standalone.py --fragment -o out.html  # без <html>/<head>/<body>
"""

import argparse
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = ["meds.py", "mind.py", "deep.py", "sense.py", "codemind.py", "versions.py", "nlp.py", "skills.py", "net.py", "cities.py", "online.py", "proglangs.py", "syntax.py", "talk.py", "tokens.py", "toolbox.py", "facts.py", "games.py", "lexicon.py", "fixer.py", "creative.py",
         "codeai.py", "codelib.py", "codeapps.py", "funcgen.py", "webgen.py", "social.py", "memes.py", "encyclopedia.py", "places.py", "sight.py", "compare.py", "moderation.py", "files.py", "learning.py", "brain.py", "knowledge.json", "glossary.json"]


def build(pyodide=None, fragment=False, stdlib=None, cdn=False):
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        html = f.read()

    # Вкладки Code и Слайды (css и js) встраиваются прямо в страницу — файл остаётся один.
    with open(os.path.join(BASE_DIR, "code.css"), encoding="utf-8") as f:
        html = html.replace('<link rel="stylesheet" href="code.css">', "<style>\n" + f.read() + "</style>", 1)
    with open(os.path.join(BASE_DIR, "slides.css"), encoding="utf-8") as f:
        html = html.replace('<link rel="stylesheet" href="slides.css">', "<style>\n" + f.read() + "</style>", 1)
    for name in ("tokens.js", "festive.js", "code.js", "slides.js", "screen.js", "vision.js", "files.js", "neuro.js", "pptx.js"):
        with open(os.path.join(BASE_DIR, name), encoding="utf-8") as f:
            js = f.read()
        # «<!--» внутри <script> переводит HTML-парсер в особый режим, и тег может не закрыться
        assert "<!--" not in js, name + " не должен содержать <!--"
        html = html.replace(f'<script src="{name}"></script>', "<script>\n" + js.replace("</script", "<\\/script") + "</script>", 1)

    files = {}
    for name in FILES:
        with open(os.path.join(BASE_DIR, name), encoding="utf-8") as f:
            files[name] = f.read()
    # "</" и "<!--" экранируются, чтобы код не мог закрыть тег <script> раньше времени.
    payload = json.dumps(files, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\u0021--")
    embedded = f'<script type="application/json" id="rai-files">{payload}</script>\n'
    html = html.replace("<script>\n(function () {", embedded + "<script>\n(function () {", 1)

    # Энциклопедия (~10 000 тем) — в самом конце страницы: чат запускается, пока она ещё догружается.
    # На хостинге (cdn) она лежит отдельным файлом kb.php: браузер кэширует его, а chat.html меняется чаще.
    kb_path = os.path.join(BASE_DIR, "encyclopedia.json")
    vision_path = os.path.join(BASE_DIR, "vision_labels.json")
    if cdn:
        html = html.replace("window.RAI_PYODIDE_SOURCES = [", 'window.RAI_KB_URL = "kb.php";\n  window.RAI_VISION_URL = "vision.php";\n  window.RAI_PYODIDE_SOURCES = [', 1)
        if os.path.exists(os.path.join(BASE_DIR, "vision_topics.json.gz")):   # зрение: тысячи конкретных вещей — vision2.php
            html = html.replace("window.RAI_PYODIDE_SOURCES = [", 'window.RAI_VISION_TOPICS_URL = "vision2.php";\n  window.RAI_PYODIDE_SOURCES = [', 1)
        if os.path.exists(os.path.join(BASE_DIR, "deep", "manifest.json")):   # глубокие знания — папка deep/ (части до 30 МБ)
            html = html.replace("window.RAI_PYODIDE_SOURCES = [", 'window.RAI_DEEP_URL = "deep/";\n  window.RAI_PYODIDE_SOURCES = [', 1)
        if os.path.exists(os.path.join(BASE_DIR, "medicines.json")):   # большая база лекарств — отдельным файлом meds.php
            html = html.replace("window.RAI_PYODIDE_SOURCES = [", 'window.RAI_MEDS_URL = "meds.php";\n  window.RAI_PYODIDE_SOURCES = [', 1)
    elif os.path.exists(vision_path):  # словарь зрения (~0,3 МБ) — внутрь офлайн-версии
        with open(vision_path, encoding="utf-8") as f:
            vis = f.read().replace("</", "<\\/")
        tag = f'<script type="application/json" id="rai-vision">{vis}</script>\n'
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
    if not cdn and os.path.exists(kb_path):
        with open(kb_path, encoding="utf-8") as f:
            kb = f.read().replace("</", "<\\/").replace("<!--", "<\\u0021--")
        tag = f'<script type="application/json" id="rai-kb">{kb}</script>\n'
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag

    if cdn:
        # Хостинг только с PHP и HTML: рядом нет папок pyodide/ и ocr/ — Python и распознавание текста берём с CDN
        html = html.replace('    "pyodide/",\n', "", 1)
        html = html.replace("window.RAI_PYODIDE_SOURCES = [", "window.RAI_OCR_LOCAL = false;\n  window.RAI_PYODIDE_SOURCES = [", 1)
    if pyodide:
        html = re.sub(r'pyodide: (null|"[^"]*")', f'pyodide: "{pyodide}"', html, count=1)
    if stdlib:
        html = re.sub(r'(pyodide: (?:null|"[^"]*"))', rf'\1,\n    stdlib: "{stdlib}"', html, count=1)

    if fragment:
        html = re.sub(r"<!DOCTYPE html>\s*", "", html, flags=re.I)
        html = re.sub(r"</?(html|head|body)\b[^>]*>\s*", "", html, flags=re.I)
        html = re.sub(r'<meta (charset|name="viewport")[^>]*>\s*', "", html)
    return html


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=os.path.join(BASE_DIR, "rai.html"))
    parser.add_argument("--pyodide", help="адрес Pyodide (по умолчанию — CDN jsdelivr)")
    parser.add_argument("--stdlib", help="свой адрес python_stdlib.zip")
    parser.add_argument("--fragment", action="store_true", help="без <html>/<head>/<body>")
    parser.add_argument("--cdn", action="store_true", help="Python и распознавание текста только с CDN (для хостинга без папок pyodide/ и ocr/)")
    args = parser.parse_args()
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(build(args.pyodide, args.fragment, args.stdlib, args.cdn))
    print("Готово:", args.output)


if __name__ == "__main__":
    main()
