"""Собрать файлы для виртуального хостинга: по папке на каждый домен.

    python make_hosting.py dist/hosting                   # папки rteam.info, rai.rteam.info, aistudio.rteam.info
    python make_hosting.py dist/hosting --zip rteam.zip   # и ZIP-архив с ними

Секреты в репозитории не хранятся. Если заданы переменные окружения GOOGLE_CLIENT_SECRET и
RTEAM_SSO_SECRET, они вписываются в config.php собранных папок (только в копию, не в репозиторий).
"""

import argparse
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))

# Файлы самого Rai: страница, вкладки, Python-движок, база знаний, Python для браузера, распознавание текста
RAI_APP = ["index.html", "code.js", "code.css", "slides.js", "slides.css", "screen.js",
           "versions.py", "nlp.py", "skills.py", "net.py", "online.py", "proglangs.py", "creative.py", "codeai.py",
           "codelib.py", "codeapps.py", "funcgen.py", "webgen.py", "brain.py", "knowledge.json", "glossary.json"]
RAI_DIRS = ["pyodide", "ocr"]

DOMAINS = {
    "rteam.info": "hosting/rteam.info",
    "aistudio.rteam.info": "hosting/aistudio",
    "rai.rteam.info": "hosting/rai",
}

SKIP = {"__pycache__", ".DS_Store"}

PLACEHOLDERS = {
    "ВСТАВЬТЕ_СЮДА_СЕКРЕТ_GOCSPX": "GOOGLE_CLIENT_SECRET",
    "ВСТАВЬТЕ_ОДИНАКОВУЮ_СЛУЧАЙНУЮ_СТРОКУ": "RTEAM_SSO_SECRET",
}

README = """RTEAM — ФАЙЛЫ ДЛЯ ВИРТУАЛЬНОГО ХОСТИНГА
======================================
Каждая папка — содержимое одного сайта (загрузите ВСЁ из папки в корень этого домена):

  rteam.info/            главный сайт: регистрация, вход (и через Google), личный кабинет, единый вход
  rai.rteam.info/        Rai целиком: чат, Code, Слайды, скриншоты; вход через аккаунт Rteam, чаты в аккаунте
  aistudio.rteam.info/   AI Studio: ИИ делает сайты пользователей, API-ключи, хостинг сайтов

{secrets}

Права на запись для PHP (755 или 775): папки data/ на всех трёх сайтах и sites/ в AI Studio.
Нужен PHP 7.4+ (curl желателен). HTTPS включите для всех трёх адресов.

Google Cloud Console → Credentials → клиент 40211315152-…
  Authorized redirect URIs:      https://rteam.info/google_callback.php
  Authorized JavaScript origins: https://rteam.info

Как связаны сайты:
  • Вход и регистрация — только на rteam.info. Rai и AI Studio входят через него (кнопка «Войти через
    аккаунт Rteam»): rteam.info выдаёт подписанный пропуск на 2 минуты.
  • Изменили имя, почту или Google в кабинете — rteam.info сам сообщает об этом Rai и AI Studio.
  • Удалили аккаунт — удаляются и чаты в Rai, и сайт с API-ключами в AI Studio.
  • Все сообщения между сайтами подписаны общим секретом SSO_SECRET (одинаковым в трёх config.php).

Список файлов:
{files}
"""


def copy_tree(src, dst):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP]
        rel = os.path.relpath(root, src)
        # данные пользователей и опубликованные сайты не копируем — только защитные файлы папок
        parts = rel.split(os.sep)
        for name in files:
            if name in SKIP or name.endswith((".pyc", ".lock", ".tmp")):
                continue
            if parts[0] in ("data", "sites") and name not in (".htaccess", "index.html"):
                continue
            if parts[0] == "data" and name == "index.html":
                continue
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            shutil.copy2(os.path.join(root, name), os.path.join(dst, rel, name))


def build(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    for domain, src in DOMAINS.items():
        copy_tree(os.path.join(BASE, src), os.path.join(out, domain))
    rai = os.path.join(out, "rai.rteam.info")
    for name in RAI_APP:
        shutil.copy2(os.path.join(BASE, name), os.path.join(rai, name))
    for d in RAI_DIRS:
        copy_tree(os.path.join(BASE, d), os.path.join(rai, d))

    filled = []
    for domain in DOMAINS:
        path = os.path.join(out, domain, "config.php")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for placeholder, env in PLACEHOLDERS.items():
            value = os.environ.get(env, "")
            if value and placeholder in text:
                text = text.replace(placeholder, value)
                filled.append(f"{domain}: {env}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    listing = []
    for domain in DOMAINS:
        root = os.path.join(out, domain)
        names = []
        for r, _, files in os.walk(root):
            for name in files:
                names.append(os.path.relpath(os.path.join(r, name), root))
        names.sort()
        big = [n for n in names if n.startswith(("pyodide", "ocr"))]
        shown = [n for n in names if n not in big]
        listing.append(f"\n  {domain}/\n" + "\n".join("    " + n for n in shown) +
                       (f"\n    pyodide/ и ocr/ — {len(big)} файлов Python и распознавания текста (загрузите папки целиком)" if big else ""))
    secrets = ("Секреты УЖЕ вписаны в config.php (" + ", ".join(filled) + ").\n"
               "НЕ выкладывайте эти config.php в GitHub и никому не пересылайте.") if filled else (
               "Впишите секреты в config.php: GOOGLE_CLIENT_SECRET (только rteam.info) и одинаковый\n"
               "SSO_SECRET (длинная случайная строка) во все три config.php.")
    with open(os.path.join(out, "ПРОЧТИ.txt"), "w", encoding="utf-8") as f:
        f.write(README.format(secrets=secrets, files="".join(listing)))
    return filled


def make_zip(out, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out):
            for name in files:
                full = os.path.join(root, name)
                z.write(full, os.path.relpath(full, out))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out", nargs="?", default=os.path.join(BASE, "dist", "hosting"))
    parser.add_argument("--zip", help="ещё и ZIP-архив")
    args = parser.parse_args()
    filled = build(args.out)
    if args.zip:
        make_zip(args.out, args.zip)
    print("Готово:", args.out, "| секреты вписаны:" if filled else "| секреты не вписаны", ", ".join(filled))


if __name__ == "__main__":
    main()
