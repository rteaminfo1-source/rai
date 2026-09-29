# Rteam: что положить на виртуальный хостинг

Три адреса, Python на хостинге не нужен (нужен только PHP 7.4+).

**Быстрее всего:** `python make_hosting.py dist/hosting --zip rteam.zip` соберёт три готовые папки с названиями
доменов (и ZIP). Если перед этим задать переменные `GOOGLE_CLIENT_SECRET` и `RTEAM_SSO_SECRET`, секреты
впишутся в копии `config.php` (в репозиторий они не попадают).

| Адрес | Что это | Откуда файлы |
|---|---|---|
| **rteam.info** | главный сайт: регистрация, вход (и через Google), личный кабинет, единый вход | `hosting/rteam.info/` |
| **rai.rteam.info** | Rai целиком: чат, Code, Слайды, скриншоты; вход через аккаунт Rteam, чаты в аккаунте | страница Rai из корня репозитория + `pyodide/`, `ocr/` + `hosting/rai/` |
| **aistudio.rteam.info** | AI Studio: ИИ делает сайты пользователей, API-ключи, хостинг сайтов | `hosting/aistudio/` |

```
                    аккаунт, пароль, Google, кабинет
                              rteam.info
          sso.php (пропуск) ↙            ↘ sso.php (пропуск)
   rai.rteam.info                          aistudio.rteam.info
   чат · Code · Слайды · скриншоты         сайты пользователей · API-ключи
   чаты хранятся в аккаунте                sites/<логин>/
          ↖ sync.php: имя, почта, удаление аккаунта ↗   (подписано SSO_SECRET)
```

- **Регистрация и вход — только на rteam.info.** В Rai и AI Studio нет своих паролей: кнопка
  «Войти через аккаунт Rteam» → rteam.info (войти или зарегистрироваться) → обратно уже с входом.
- **Пользователи передаются:** пропуск несёт логин, имя, почту и аватар; действует 2 минуты и один раз.
- **Изменения синхронизируются:** сменили имя, почту или Google в кабинете — rteam.info сам сообщает
  Rai и AI Studio. Удалили аккаунт — удаляются чаты в Rai и сайт с API-ключами в AI Studio.
- **Чаты сохраняются в аккаунте**: после входа в Rai они доступны на любом устройстве.
  Без входа Rai тоже работает, чаты тогда хранятся в браузере.

## 0. Один раз на GitHub: включить Pages

github.com/rteaminfo1-source/rai → **Settings → Pages** → Source: *Deploy from a branch* →
ветка `claude/peaceful-allen-c7nn4t` (или `main`), папка `/ (root)` → **Save**.
Чат появится по адресу `https://rteaminfo1-source.github.io/rai/` и дальше обновляется сам после каждого `git push`.

## 1. Поддомены в панели хостинга

Создайте поддомены **rai.rteam.info** и **aistudio.rteam.info** (каждому своя папка) и включите HTTPS
для всех трёх адресов (Let's Encrypt в панели хостинга).

## 2. Общий секрет единого входа

Придумайте длинную случайную строку (от 32 символов, например 64 символа 0-9a-f) и впишите её
**одинаковой** в `SSO_SECRET` трёх файлов: `config.php` сайтов rteam.info, rai.rteam.info и aistudio.rteam.info.
По этому секрету Rai и студия проверяют, что пропуск и изменения профиля пришли именно от rteam.info.

## 3. rteam.info — главный сайт

В корень сайта положите **всё содержимое** `hosting/rteam.info/`:

| Файл / папка | Зачем |
|---|---|
| `index.php` | главная: Rai, Rai Code, AI Studio, модели Rai |
| `login.php` | вход и регистрация (логин + пароль или Google) |
| `auth.php` | обработка форм: вход, регистрация, выход, профиль, пароль, удаление аккаунта |
| `account.php` | личный кабинет: профиль, пароль, привязка Google, ссылки на сервисы |
| `logout.php` | выход по ссылке (с подтверждением) |
| `google_start.php`, `google_callback.php` | вход через Google |
| `sso.php` | единый вход: выдаёт Rai и AI Studio подписанный пропуск (действует 2 минуты, один раз) |
| `chat.php` | старые ссылки на чат ведут на rai.rteam.info |
| `config.php` | настройки — **впишите секрет Google и SSO_SECRET** |
| `assets/site.css` | стиль (чёрно-красный) |
| `data/` | аккаунты (пароли — только хеши). Закрыта от посетителей, нужны права на запись |
| `.htaccess` / `web.config` | защита для Apache / IIS |

Логин — латиница в нижнем регистре, цифры и дефис (3–20 символов); он же адрес сайта в студии.
Старые аккаунты прежнего сайта сами не переносятся.

## 4. rai.rteam.info — основной ИИ

Загрузите **всю папку `rai.rteam.info/`** из сборки (`make_hosting.py`):

| Файл / папка | Зачем |
|---|---|
| `index.html`, `code.js`, `code.css`, `slides.js`, `slides.css`, `screen.js` | страница Rai: чат, Code, Слайды, скриншоты и запись экрана |
| `*.py`, `knowledge.json`, `glossary.json` | движок Rai (Python выполняется в браузере) |
| `pyodide/` | Python для браузера (≈ 13 МБ) |
| `ocr/` | распознавание текста на скриншотах, русский и английский (≈ 14 МБ) |
| `config.php` | настройки — **впишите SSO_SECRET** |
| `sso_start.php`, `sso_callback.php` | вход через аккаунт Rteam |
| `me.php`, `chats.php`, `logout.php` | кто вошёл, чаты в аккаунте, выход |
| `sync.php` | принимает изменения профиля и удаление аккаунта от rteam.info |
| `data/` | пользователи и чаты (закрыта от посетителей, нужны права на запись) |
| `.htaccess` / `web.config` | типы файлов (.wasm, .mjs) и защита для Apache / IIS |

Ссылки: `https://rai.rteam.info/#code` — сразу Code, `#slides` — сразу Слайды.
Копия на GitHub Pages (`rteaminfo1-source.github.io/rai/`) тоже работает, но без входа — чаты в браузере.

## 5. aistudio.rteam.info — AI Studio

В папку поддомена положите **всё содержимое** `hosting/aistudio/`:

| Файл / папка | Зачем |
|---|---|
| `index.php` | главная студии и кнопка «Войти через аккаунт Rteam» |
| `sso_start.php`, `sso_callback.php` | единый вход через rteam.info |
| `sync.php` | принимает изменения профиля и удаление аккаунта от rteam.info |
| `studio.php` | рабочее место: ИИ-конструктор, предпросмотр, публикация, ZIP сайта, API-ключ, чат Rai |
| `sitegen.php` | ИИ, который создаёт и правит сайты |
| `actions.php` | кнопки студии |
| `api.php` | API по ключу (`Authorization: Bearer rai_…`) |
| `auth.php` | выход |
| `config.php` | настройки — **впишите SSO_SECRET** |
| `assets/` | стили и скрипт студии |
| `data/` | пользователи студии и черновики (закрыта от посетителей). Нужны права на запись |
| `sites/` | сайты пользователей: `sites/<логин>/index.html`. Нужны права на запись, PHP здесь отключён |
| `.htaccess` / `web.config` | защита для Apache / IIS |

Если раньше на студии были файлы `google_start.php` и `google_callback.php` — удалите их, вход теперь через rteam.info.

Как это работает:

- «Войти через аккаунт Rteam» → rteam.info (если нужно — вход или регистрация) → обратно в студию, уже войдя;
- логин Rteam = папка сайта `sites/<логин>/`;
- «сайт кофейни «Зерно» с меню и отзывами» → ИИ студии собирает сайт → «Опубликовать» (или «Скачать ZIP»);
- правки словами: «добавь раздел цены», «сделай синим», «переименуй в …»;
- **файлы сайтов создаёт только ИИ студии**: чужой PHP-код на хостинг не попадёт;
- API-ключ показывается один раз, хранится только его хеш: `POST https://aistudio.rteam.info/api.php?a=generate`.

## 6. Google Cloud Console

console.cloud.google.com → APIs & Services → Credentials → клиент `40211315152-…`:

- **Authorized redirect URIs**: `https://rteam.info/google_callback.php`
- **Authorized JavaScript origins**: `https://rteam.info`

Старые адреса `…/aistudio.rteam.info/google_callback.php` можно удалить.

## Что не выкладывать в GitHub

`config.php` с секретами, папки `data/` и `sites/` с хостинга.
В репозитории оба `config.php` лежат без секретов.
