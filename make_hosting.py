"""Собрать файлы для виртуального хостинга: по папке на каждый домен.

    python make_hosting.py dist/hosting                   # папки rai.rteam.info и aistudio.rteam.info
    python make_hosting.py dist/hosting --zip rteam.zip   # и ZIP-архив с ними
    python make_hosting.py dist/hosting --admin путь/к/admin.php   # + rteam.info/admin.php со вкладкой «Rai: подписки»

Секреты в репозитории не хранятся. Если заданы переменные окружения GOOGLE_CLIENT_SECRET и
SSO_SECRET, они вписываются в config.php собранных папок (только в копию, не в репозиторий).
"""

import argparse
import base64
import gzip
import hashlib
import os
import shutil
import zipfile

import build_standalone

BASE = os.path.dirname(os.path.abspath(__file__))

# На хостинге только PHP и HTML: весь Rai — один chat.html (движок, база знаний, вкладки встроены внутрь),
# главная с тарифами — index.php,
# а Python для браузера и распознавание текста страница берёт с CDN (jsdelivr).

DOMAINS = {
    "rai.rteam.info": "hosting/rai",
    "aistudio.rteam.info": "hosting/aistudio",
}

SKIP = {"__pycache__", ".DS_Store"}

PLACEHOLDERS = {
    "ВСТАВЬТЕ_СЮДА_СЕКРЕТ_GOCSPX": "GOOGLE_CLIENT_SECRET",
    "ВСТАВЬТЕ_ОДИНАКОВУЮ_СЛУЧАЙНУЮ_СТРОКУ": "SSO_SECRET",
    "ВСТАВЬТЕ_MERCHANT_ID": "PLATEGA_MERCHANT_ID",
    "ВСТАВЬТЕ_СЕКРЕТНЫЙ_КЛЮЧ_PLATEGA": "PLATEGA_SECRET",
    "ВСТАВЬТЕ_КЛЮЧ_ДЛЯ_АДМИНКИ": "ADMIN_API_KEY",
}

README = """RAI — ФАЙЛЫ ДЛЯ ВИРТУАЛЬНОГО ХОСТИНГА
===================================
Два сайта, каждая папка — содержимое одного сайта (загрузите ВСЁ из папки в корень этого домена):

  rai.rteam.info/        index.php — главная: что умеет Rai, тарифы и оплата (Platega)
                         chat.html — сам Rai: чат, Code, Слайды, скриншоты (всё в одном файле)
                         kb.php — энциклопедия Rai (~10 000 тем из Википедии), чат догружает её в фоне
                         + аккаунты: регистрация, вход, вход через Google, личный кабинет, чаты в аккаунте
  aistudio.rteam.info/   AI Studio: ИИ делает сайты пользователей, API-ключи, хостинг сайтов;
                         вход — аккаунтом Rai. Сайты пишет нейросеть Rai Нейро прямо в браузере
                         (assets/neuro.php — та же нейросеть, что в чате; модели — с rai.rteam.info/ai.php),
                         тариф и лимиты — как в чате Rai (limits.php)

{secrets}

На хостинге нужны только PHP 7.4+ (curl желателен) и HTML — Python не нужен: Rai работает в браузере
посетителя, а Python и распознавание текста браузер скачивает с CDN (jsdelivr) при первом запуске.
Все файлы — .php и .html. Файлы .htaccess и web.config — необязательные настройки для Apache/IIS
(для AI Studio .htaccess передаёт API-ключ в api.php; без него ключ можно слать заголовком X-API-Key).

Интернет для Rai идёт через ваш сайт: rai.rteam.info/net.php — погода, курсы, перевод, Википедия, фото для
презентаций и поиск (DuckDuckGo; Google — если вписать GOOGLE_CSE_KEY и GOOGLE_CSE_CX в начало net.php).
Своя нейросеть Rai Нейро хранится на вашем сайте: rai.rteam.info/ai.php сам скачивает модели и библиотеки
в data/ai/ при первом запуске (нужно 2–6 ГБ места и PHP curl), дальше всё грузится с вашего сайта.
Проверка: https://rai.rteam.info/ai.php/ping — должно быть "path_info":true.

Тарифы и оплата (rai.rteam.info): главная index.php с тарифами, оплата через Platega.
  • В config.php впишите PLATEGA_MERCHANT_ID и PLATEGA_SECRET (кабинет Platega → API) и ADMIN_API_KEY.
  • В кабинете Platega адрес уведомлений: https://rai.rteam.info/pay_callback.php
  • Старый index.html на хостинге УДАЛИТЕ — теперь чат называется chat.html, а главная — index.php.
  • Подписку по логину выдают в админ-панели основного сайта rteam.info/admin.php (вкладка «Rai: подписки»
    встроена в сам файл), тот же ADMIN_API_KEY. Ключи Platega можно вписать и там.

Приложение Rai для компьютера (Windows, macOS, Linux) — раздел «Приложение» на главной, кнопки ведут на download.php.
  • Файлы приложения лежат в rai.rteam.info/app/: Rai-Setup.exe, Rai-mac-arm64.dmg (или .zip), Rai-mac-x64.dmg,
    Rai-linux.AppImage, Rai-linux.deb и latest.yml, latest-mac.yml, latest-linux.yml (по ним приложения
    узнают о новой версии). Их кладёт GitHub Actions (если заданы FTP-секреты) или вы сами по FTP.
  • Если в app/ файла нет — кнопка ведёт на последний релиз на GitHub. Приложения обновляются с GitHub,
    а если он недоступен — отсюда, из app/.

Права на запись для PHP (755 или 775): папки data/ на обоих сайтах и sites/ в AI Studio.
Данные пользователей хранятся в data/*.php — из браузера их прочитать нельзя. HTTPS включите для обоих адресов.

Google Cloud Console → Credentials → клиент 40211315152-…
  Authorized redirect URIs:      https://rai.rteam.info/google_callback.php
  Authorized JavaScript origins: https://rai.rteam.info

Как связаны сайты:
  • Регистрация и вход — на rai.rteam.info (login.php, в чате кнопка «Войти или зарегистрироваться»).
  • AI Studio входит через Rai: кнопка «Войти через аккаунт Rai» — rai.rteam.info выдаёт подписанный
    пропуск на 2 минуты, аккаунт в студии создаётся сам, логин = адрес сайта.
  • Изменили имя, почту или Google в кабинете Rai — это само доходит до AI Studio.
  • Удалили аккаунт — удаляются чаты в Rai и сайт с API-ключами в AI Studio.
  • Всё, что сайты передают друг другу, подписано общим секретом SSO_SECRET (одинаковым в двух config.php).

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


def write_kb(path, name="encyclopedia.json", title="Энциклопедия Rai (~15 000 тем из Википедии, CC BY-SA). Собирает GitHub: tools/build_encyclopedia.py"):
    """JSON для хостинга (энциклопедия → kb.php, зрение → vision.php): отдаётся как JSON с кэшем в браузере.
    На хостинге только PHP и HTML, поэтому данные лежат внутри .php после __halt_compiler(): заранее сжатые (gzip)
    и записанные текстом (base64) — файл в 3 раза меньше, браузер получает сжатое, а загрузка по FTP в любом
    режиме (текстовом или двоичном) его не портит. Браузер без gzip получает обычный JSON."""
    src = os.path.join(BASE, name)
    if not os.path.exists(src):
        return False
    with open(src, "rb") as f:
        data = f.read()
    tag = hashlib.sha1(data).hexdigest()[:16]
    packed = base64.b64encode(gzip.compress(data, 9, mtime=0)).decode("ascii")
    lines = "\n".join(packed[i:i + 76] for i in range(0, len(packed), 76))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<?php\n// {title}\n"
                "header('Content-Type: application/json; charset=utf-8');\n"
                "header('Cache-Control: public, max-age=86400');\n"
                "header('Vary: Accept-Encoding');\n"
                f"header('ETag: \"{tag}\"');\n"
                f"if (trim($_SERVER['HTTP_IF_NONE_MATCH'] ?? '') === '\"{tag}\"') {{ http_response_code(304); exit; }}\n"
                "$gz = base64_decode(file_get_contents(__FILE__, false, null, __COMPILER_HALT_OFFSET__));\n"
                "// сервер сам сжимает ответы (zlib.output_compression) или браузер не понимает gzip — отдаём обычный JSON\n"
                "if (ini_get('zlib.output_compression') || stripos($_SERVER['HTTP_ACCEPT_ENCODING'] ?? '', 'gzip') === false) {\n"
                "    echo gzdecode($gz);\n"
                "} else {\n"
                "    header('Content-Encoding: gzip');\n"
                "    header('Content-Length: ' . strlen($gz));\n"
                "    echo $gz;\n"
                "}\n"
                "__halt_compiler();\n" + lines + "\n")
    return True


def write_js(path, name, title):
    """JS-файл как .php (на хостинге только PHP и HTML): AI Studio берёт нейросеть Rai (neuro.js) отсюда и кэширует её."""
    with open(os.path.join(BASE, name), encoding="utf-8") as f:
        js = f.read()
    if "<?" in js:
        raise SystemExit(f"{name}: в коде есть «<?» — PHP примет это за начало своего кода")
    tag = hashlib.sha1(js.encode("utf-8")).hexdigest()[:16]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<?php\n// {title}\n"
                "header('Content-Type: application/javascript; charset=utf-8');\n"
                "header('Cache-Control: public, max-age=3600');\n"
                f"header('ETag: \"{tag}\"');\n"
                f"if (trim($_SERVER['HTTP_IF_NONE_MATCH'] ?? '') === '\"{tag}\"') {{ http_response_code(304); exit; }}\n"
                "?>\n" + js)


def read_kb(path):
    """Данные из kb.php / vision.php обратно в байты JSON (для проверок)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return gzip.decompress(base64.b64decode(text.split("__halt_compiler();", 1)[1]))


def build_admin(out, admin_path):
    """rteam.info/admin.php: админка основного сайта со встроенной вкладкой «Rai: подписки» (make_admin.py)."""
    import make_admin
    with open(admin_path, encoding="utf-8") as f:
        text = f.read()
    key = os.environ.get("ADMIN_API_KEY", "") or None
    os.makedirs(os.path.join(out, "rteam.info"), exist_ok=True)
    with open(os.path.join(out, "rteam.info", "admin.php"), "w", encoding="utf-8") as f:
        f.write(make_admin.patch(text, key))
    return bool(key)


def build(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    for domain, src in DOMAINS.items():
        copy_tree(os.path.join(BASE, src), os.path.join(out, domain))
    with open(os.path.join(out, "rai.rteam.info", "chat.html"), "w", encoding="utf-8") as f:
        f.write(build_standalone.build(cdn=True))
    write_kb(os.path.join(out, "rai.rteam.info", "kb.php"))
    write_kb(os.path.join(out, "rai.rteam.info", "vision.php"), "vision_labels.json",
             "Зрение Rai: понятия для распознавания картинок (считает GitHub: tools/build_vision.py)")
    write_js(os.path.join(out, "aistudio.rteam.info", "assets", "neuro.php"), "neuro.js",
             "Нейросеть Rai Нейро для AI Studio — копия neuro.js из репозитория (собирает make_hosting.py)")

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
        listing.append(f"\n  {domain}/\n" + "\n".join("    " + n for n in names))
    secrets = ("Секреты УЖЕ вписаны в config.php (" + ", ".join(filled) + ").\n"
               "НЕ выкладывайте эти config.php в GitHub и никому не пересылайте.") if filled else (
               "Впишите секреты в config.php: GOOGLE_CLIENT_SECRET (rai.rteam.info) и одинаковый\n"
               "SSO_SECRET (длинная случайная строка) в оба config.php.")
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
    parser.add_argument("--admin", help="admin.php основного сайта: собрать rteam.info/admin.php со вкладкой «Rai: подписки»")
    args = parser.parse_args()
    filled = build(args.out)
    if args.admin:
        keyed = build_admin(args.out, args.admin)
        with open(os.path.join(args.out, "ПРОЧТИ.txt"), "a", encoding="utf-8") as f:
            f.write("\n  rteam.info/   admin.php — ваша админ-панель со вкладкой «Rai: подписки» (один файл, замените им старый admin.php).\n"
                    + ("                Ключ связи с Rai уже вписан (тот же, что ADMIN_API_KEY в config.php Rai).\n" if keyed else
                       "                Ключ связи впишите во вкладке «Rai: подписки» → «Подключение».\n"))
        filled.append("rteam.info/admin.php" + (": ADMIN_API_KEY" if keyed else ""))
    if args.zip:
        make_zip(args.out, args.zip)
    print("Готово:", args.out, "| секреты вписаны:" if filled else "| секреты не вписаны", ", ".join(filled))


if __name__ == "__main__":
    main()
