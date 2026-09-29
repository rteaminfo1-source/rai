# Rteam: что положить на виртуальный хостинг

Три адреса, Python на хостинге не нужен:

| Адрес | Что это | Где лежит |
|---|---|---|
| **rteam.info** | ваш сайт (PHP), вход, кнопка «Rai» | виртуальный хостинг |
| **rai.rteam.info** | основной ИИ Rai: страница, в которую встроен чат с GitHub | виртуальный хостинг (1 файл) + GitHub Pages |
| **aistudio.rteam.info** | AI Studio: ИИ делает сайты пользователей, API-ключи, хостинг сайтов | виртуальный хостинг (PHP) |

```
rteam.info ──«Rai»──► rai.rteam.info ── встроен чат ──► rteaminfo1-source.github.io/rai/ (Python в браузере)
     │                      │
     └──────────────► aistudio.rteam.info ── ИИ создаёт ──► aistudio.rteam.info/sites/<имя>/
                            └── справа встроен тот же чат Rai с GitHub
```

## 0. Один раз на GitHub: включить Pages

github.com/rteaminfo1-source/rai → **Settings → Pages** → Source: *Deploy from a branch* →
ветка `claude/peaceful-allen-c7nn4t` (или `main`), папка `/ (root)` → **Save**.
Чат появится по адресу `https://rteaminfo1-source.github.io/rai/` и дальше обновляется сам после каждого `git push`.

## 1. Поддомены в панели хостинга

Создайте поддомены **rai.rteam.info** и **aistudio.rteam.info** (каждому своя папка) и включите для них HTTPS
(Let's Encrypt в панели хостинга). Для aistudio нужен PHP 7.4 или новее.

## 2. rai.rteam.info — основной ИИ

В папку поддомена положите **один файл**: `hosting/rai/index.html`.
Это тонкая шапка (AI Studio, Rteam, GitHub) и чат Rai с GitHub Pages на всю страницу.

## 3. aistudio.rteam.info — AI Studio

В папку поддомена положите **всё содержимое** `hosting/aistudio/`:

| Файл / папка | Зачем |
|---|---|
| `index.php` | главная: что такое студия, вход и регистрация |
| `studio.php` | рабочее место: ИИ-конструктор, предпросмотр, публикация, API-ключ, чат Rai |
| `sitegen.php` | ИИ, который создаёт и правит сайты |
| `actions.php` | кнопки студии |
| `api.php` | API по ключу (`Authorization: Bearer rai_…`) |
| `auth.php`, `google_start.php`, `google_callback.php` | вход, регистрация, Google |
| `config.php` | настройки — **вставьте сюда секрет Google** (`GOOGLE_CLIENT_SECRET`) |
| `assets/` | стили и скрипт студии |
| `data/` | пользователи и черновики (закрыта от посетителей). Папке нужны права на запись |
| `sites/` | сайты пользователей: `sites/<имя>/index.html`. Нужны права на запись, PHP здесь отключён |
| `.htaccess` / `web.config` | защита для Apache / IIS |

Права: папкам `data/` и `sites/` дайте запись для PHP (обычно 755 или 775 — как в панели хостинга).

Как это работает:

- регистрация: имя пользователя (латиница) = папка его сайта `sites/<имя>/`;
- пользователь пишет «сайт кофейни «Зерно» с меню и отзывами» → ИИ студии собирает сайт → «Опубликовать»;
- правки словами: «добавь раздел цены», «сделай синим», «переименуй в …», «измени раздел о нас на: …»;
- **файлы сайтов создаёт только ИИ студии**: загрузить свои файлы нельзя, поэтому на хостинг не попадёт
  чужой PHP-код;
- API-ключ выдаётся в студии (показывается один раз, хранится только хеш), им можно создавать и править
  сайт из своих программ: `POST https://aistudio.rteam.info/api.php?a=generate`.

## 4. rteam.info — ваш сайт

| Файл | Что сделать |
|---|---|
| `chat.php` | заменить на `php/chat.php` — ведёт на rai.rteam.info |
| `google_start.php`, `google_callback.php` | положить из `php/` |
| `config.php` | дописать строки из `php/config.google.example.php` и вставить секрет |
| `chat.js`, `rai.php` | больше не нужны |

## 5. Google Cloud Console

console.cloud.google.com → APIs & Services → Credentials → клиент `40211315152-…`:

- **Authorized redirect URIs**: `https://rteam.info/google_callback.php` и `https://aistudio.rteam.info/google_callback.php`
- **Authorized JavaScript origins**: `https://rteam.info` и `https://aistudio.rteam.info`

## Что не выкладывать в GitHub

`config.php` с секретом, папки `data/` и `sites/` с хостинга, `users.json` с паролями.
В репозитории `config.php` лежит без секрета.
