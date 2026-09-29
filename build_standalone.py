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
FILES = ["versions.py", "nlp.py", "skills.py", "net.py", "online.py", "proglangs.py", "creative.py",
         "codeai.py", "codelib.py", "codeapps.py", "funcgen.py", "webgen.py", "brain.py", "knowledge.json", "glossary.json"]


def build(pyodide=None, fragment=False, stdlib=None):
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        html = f.read()

    # Вкладки Code и Слайды (css и js) встраиваются прямо в страницу — файл остаётся один.
    with open(os.path.join(BASE_DIR, "code.css"), encoding="utf-8") as f:
        html = html.replace('<link rel="stylesheet" href="code.css">', "<style>\n" + f.read() + "</style>", 1)
    with open(os.path.join(BASE_DIR, "slides.css"), encoding="utf-8") as f:
        html = html.replace('<link rel="stylesheet" href="slides.css">', "<style>\n" + f.read() + "</style>", 1)
    for name in ("code.js", "slides.js", "screen.js"):
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
    args = parser.parse_args()
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(build(args.pyodide, args.fragment, args.stdlib))
    print("Готово:", args.output)


if __name__ == "__main__":
    main()
