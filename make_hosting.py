"""Собрать файлы для виртуального хостинга: по папке на каждый домен.

    python make_hosting.py dist/hosting                   # папки rai.rteam.info и aistudio.rteam.info
    python make_hosting.py dist/hosting --zip rteam.zip   # и ZIP-архив с ними

Секреты в репозитории не хранятся. Если заданы переменные окружения GOOGLE_CLIENT_SECRET и
SSO_SECRET, они вписываются в config.php собранных папок (только в копию, не в репозиторий).
"""

import argparse
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
                         + аккаунты: регистрация, вход, вход через Google, личный кабинет, чаты в аккаунте
  aistudio.rteam.info/   AI Studio: ИИ делает сайты пользователей, API-ключи, хостинг сайтов;
                         вход — аккаунтом Rai

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
  • Подписку по логину выдают в админ-панели основного сайта: admin_rai.php рядом с admin.php,
    вкладка «Rai: подписки», тот же ADMIN_API_KEY.

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


def build(out):
    if os.path.exists(out):
        shutil.rmtree(out)
    for domain, src in DOMAINS.items():
        copy_tree(os.path.join(BASE, src), os.path.join(out, domain))
    with open(os.path.join(out, "rai.rteam.info", "chat.html"), "w", encoding="utf-8") as f:
        f.write(build_standalone.build(cdn=True))

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
    args = parser.parse_args()
    filled = build(args.out)
    if args.zip:
        make_zip(args.out, args.zip)
    print("Готово:", args.out, "| секреты вписаны:" if filled else "| секреты не вписаны", ", ".join(filled))


if __name__ == "__main__":
    main()
