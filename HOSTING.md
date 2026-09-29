# Как разложить Rai: виртуальный хостинг + GitHub

```
Пользователь ──► ваш сайт (виртуальный хостинг, PHP)
                   │  вход: логин/пароль или Google (google_start.php → google_callback.php)
                   │  кнопка «Rai» / chat.php
                   ▼
                 чат Rai на GitHub Pages: https://rteaminfo1-source.github.io/rai/
                   (Python работает прямо в браузере, сервер не нужен)
                   │  кнопка «← На сайт Rteam»
                   ▼
                 обратно на ваш сайт
```

Python на обычном (PHP) виртуальном хостинге не запускается, поэтому **весь Rai живёт на GitHub**,
а на хостинге остаются сайт, вход и переход в чат.

## Шаг 1. Включить GitHub Pages (один раз)

1. Откройте https://github.com/rteaminfo1-source/rai → **Settings** → **Pages**.
2. **Build and deployment → Source:** *Deploy from a branch*.
3. **Branch:** `claude/peaceful-allen-c7nn4t` (или `main`, если код туда перенесён), папка **`/ (root)`** → **Save**.
4. Через 1–2 минуты чат откроется по адресу **https://rteaminfo1-source.github.io/rai/**.

Ничего копировать не нужно: GitHub сам раздаёт `index.html`, все `.py`, `knowledge.json`, `glossary.json`
и папку `pyodide/`. После каждого `git push` чат обновляется сам.

## Шаг 2. Что положить на виртуальный хостинг

Файлы берите из папки `php/` этого репозитория.

| Файл на хостинге | Что сделать |
|---|---|
| `chat.php` | **Заменить** старый на `php/chat.php` — он переводит в чат Rai на GitHub |
| `google_start.php` | Положить `php/google_start.php` (кнопка «Войти через Google») |
| `google_callback.php` | Положить `php/google_callback.php` (сюда Google возвращает после входа) |
| `config.php` | **Дописать** строки из `php/config.google.example.php` и вставить туда секрет `GOCSPX-…` |
| `chat.js`, `rai.php` | Больше не нужны, можно удалить |
| остальные файлы сайта | Оставить как есть |

Кнопка «Войти через Google» на `login.php` должна вести на `google_start.php`,
а ссылка «Rai» в меню сайта — на `chat.php`.

**Не кладите** на хостинг и в GitHub: `.py` файлы (они на GitHub), папку `pyodide/`,
а в GitHub — `config.php` с секретом и `users.json` с паролями.

## Шаг 3. Google Cloud Console

https://console.cloud.google.com/apis/credentials → ваш OAuth-клиент (`40211315152-…`):

- **Authorized redirect URIs:** `https://ВАШ-САЙТ/google_callback.php` — ровно так же, как `GOOGLE_REDIRECT_URI` в `config.php`.
- **Authorized JavaScript origins:** `https://ВАШ-САЙТ`.

## Шаг 4. Проверка

1. Откройте `https://ВАШ-САЙТ/login.php` → «Войти через Google» → выберите аккаунт → вы на сайте.
2. Нажмите «Rai» (или откройте `https://ВАШ-САЙТ/chat.php`) → открывается чат на `rteaminfo1-source.github.io/rai/`.
3. В чате слева внизу кнопка **«← На сайт Rteam»** возвращает на сайт.
4. Первое открытие чата — 5–15 секунд (браузер скачивает Python ≈ 13 МБ), дальше — из кэша.

## Где хранятся чаты

На GitHub Pages чаты Rai хранятся в браузере пользователя (у каждого свои). Если нужно, чтобы чаты
сохранялись в аккаунте и открывались на любом устройстве, запустите Python-сервер Rai (Render, см. README) —
там свои вход, регистрация и синхронизация чатов. Тогда в `config.php` укажите
`RAI_CHAT_URL` = адрес сервера Rai.
