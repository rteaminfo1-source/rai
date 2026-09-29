# Rai — собственный ИИ-ассистент Rteam на Python

Rai работает **полностью на своём движке**: без OpenAI, Claude и любых других внешних API, без ключей и без интернета.
Этот репозиторий — только Python-часть (сервер). Сайт (HTML/PHP/JS) лежит на другом хостинге и обращается к Rai по ссылке.

## Четыре версии

| Версия | id | Что умеет |
|---|---|---|
| **Rai Pro Fast** | `pro-fast` | Самая быстрая: поиск по ключевым словам, калькулятор, дата и время |
| **Rai Pro** | `pro` | Основная: поиск по смыслу (TF-IDF), калькулятор, время, конвертер единиц, случайные числа |
| **Rai Pro Plus** | `pro-plus` | Всё из Pro, а ещё исправляет опечатки и раскладку (`ghbdtn` → «привет»), даёт все навыки (пароли, работа с текстом), помнит имя, отвечает на «подробнее/ещё» и подсказывает похожие вопросы |
| **Rai Pro Sun** | `pro-sun` | Всё из Plus, а ещё запоминает факты («запомни, что …»), отвечает на несколько вопросов в одном сообщении и сразу даёт подробные ответы |

## Что умеет Rai

- **Отвечает на вопросы**: своя база знаний (`knowledge.json`) + словарь из 100+ понятий (`glossary.json`):
  «что такое фотосинтез», «кто такой хакер», «столица Франции», «сравни Python и PHP».
- **Форматирует ответы**: таблицы, **жирный**, *курсив*, ==выделение==, списки, блоки кода. Любой ответ
  копируется кнопкой «Копировать» с форматированием (вставляется в Word как таблица).
- **Рисует картинки** (`creative.py`, SVG без внешних сервисов): закат, рассвет, ночь, космос, горы, море, лес,
  город, пустыня, зима, сердце, цветок, абстракция, логотипы. Скачать можно в PNG и SVG.
- **Делает презентации**: слайды из базы знаний и словаря, с картинками, анимацией появления текста и
  переходами между слайдами. Смотреть на весь экран, скачать одним `.html` файлом.
- **Голос**: кнопка микрофона — диктовка (Chrome/Edge), кнопка «Озвучить» — чтение ответа вслух.
- **Разные чаты**: список слева, у каждого чата своя история, версия и память. Хранятся в браузере.
- Навыки: калькулятор, дата/время, конвертер, таблица умножения, пароли, работа с текстом, случайности.

Если Rai не знает ответа, он честно говорит об этом и подсказывает похожие темы, а в Pro Sun его можно
научить прямо в чате: «запомни, что квазар — это …». Постоянные знания добавляйте в `knowledge.json` и `glossary.json`.

## Страница чата (`index.html`)

`index.html` — готовый чат с выбором версии. Он сам выбирает, как работать:

- если страницу отдаёт Python-сервер Rai (`python app.py` или хостинг) — запросы идут на сервер;
- если страница лежит на любом статическом хостинге (GitHub Pages, обычный веб-хостинг, raw.githack) —
  **те же `.py` файлы запускаются прямо в браузере** через Pyodide (Python в WebAssembly). Сервер не нужен.
  Первая загрузка ≈ 13 МБ (из папки `pyodide/` рядом со страницей, а если её нет — с CDN jsdelivr/unpkg),
  потом браузер берёт из кэша. Если загрузить не вышло, страница пишет почему и предлагает попробовать снова.

**Один файл `rai.html`** — тот же чат, в который уже встроены все `.py` и `knowledge.json`.
Его можно просто скачать и открыть в браузере или положить на любой хостинг одним файлом
(нужен только интернет для загрузки Pyodide). После правок в `.py` или `knowledge.json`
пересоберите его: `python build_standalone.py`.

**Протестировать сразу из GitHub:** `https://raw.githack.com/rteaminfo1-source/rai/<коммит>/index.html`

**Постоянная ссылка через GitHub Pages:** Settings → Pages → Source: *Deploy from a branch* →
выберите ветку и папку `/ (root)` → Save. Через минуту чат откроется по адресу
`https://rteaminfo1-source.github.io/rai/`.

**Только `index.html` на своём хостинге, а Python — из GitHub:** положите `index.html` на хостинг и
перед ним (в `<head>`, до остальных скриптов) укажите, откуда брать файлы (вместо `main` — ваша ветка):

```html
<script>
  window.RAI_CONFIG = {
    pyBase: "https://raw.githubusercontent.com/rteaminfo1-source/rai/refs/heads/main/"
  };
</script>
```

Если запущен Python-сервер, вместо этого укажите его адрес: `window.RAI_CONFIG = {api: "https://rai-xxxx.onrender.com"}`.
Для быстрой проверки то же самое можно передать в адресе: `index.html?api=...` или `index.html?py=...`.

## Файлы

| Файл | Что это |
|---|---|
| `index.html` | Страница чата: работает и с сервером, и прямо в браузере |
| `rai.html` | Тот же чат одним файлом (Python встроен), собирается `build_standalone.py` |
| `app.py` | Веб-сервер (Flask): отдаёт `index.html` и принимает запросы от сайта |
| `brain.py` | Движок Rai: выбор ответа, память, логика версий |
| `nlp.py` | Своя обработка текста: стемминг, TF-IDF, исправление опечаток |
| `skills.py` | Навыки: калькулятор, дата/время, конвертер, таблицы, столицы, пароли, текст, случайности |
| `creative.py` | Свои картинки (SVG) и презентации |
| `glossary.json` | Словарь понятий для ответов «что такое …» |
| `versions.py` | Настройки четырёх версий |
| `pyodide/` | Python для браузера (Pyodide 314.0.7), чтобы чат не зависел от внешних CDN |
| `knowledge.json` | База знаний: вопросы и ответы. **Дополняйте её сами** |
| `test_app.py` | Тесты: `python -m unittest -v` |
| `requirements.txt`, `Procfile`, `render.yaml` | Для запуска на хостинге |

## Запуск у себя

```bash
pip install -r requirements.txt
python app.py            # откройте http://localhost:8000 — там чат
```

## Запуск на хостинге из GitHub

Нужен хостинг с поддержкой Python. Обычный PHP-хостинг Python не запускает.

**Render.com (бесплатно):** New → Blueprint → выберите этот репозиторий. Render сам прочитает `render.yaml`.
Вручную: New → Web Service → репозиторий `rai`,
Build: `pip install -r requirements.txt`,
Start: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8`.

Так же подойдут Railway, Koyeb (они используют `Procfile`), PythonAnywhere или свой VPS.
Когда сервер запустится, вы получите ссылку вида `https://rai-xxxx.onrender.com`.

Переменные окружения (см. `.env.example`):

- `ALLOWED_ORIGINS`: адрес вашего сайта, например `https://rteam.info`. Тогда запросы к Rai будут приниматься только с него.
- `RAI_DEFAULT_VERSION`: версия по умолчанию (`pro`).
- `RAI_ADMIN_TOKEN`: секрет для обучения через `/api/teach`.
- `RAI_TZ`: часовой пояс (`Europe/Moscow`).

## API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/versions` | Список версий |
| GET | `/health` | Проверка, что сервер жив |
| POST | `/api/chat` | Вопрос → ответ |
| POST | `/api/chat/<версия>` | То же, версия в адресе (`/api/chat/pro-sun`) |
| POST | `/rai.php`, `/rai` | Совместимость со старым `chat.js` |
| POST | `/api/teach` | Научить новому ответу (нужен `RAI_ADMIN_TOKEN`) |

Запрос:

```json
{"message": "что такое python?", "version": "pro-plus", "session_id": "любая-строка-пользователя"}
```

Ответ:

```json
{"answer": "Python — простой и мощный язык…", "version": "pro-plus", "version_name": "Rai Pro Plus", "intent": "python"}
```

`session_id` нужен, чтобы Pro Plus и Pro Sun помнили имя и факты. Это любая строка до 64 символов из букв, цифр и `_.-`.

## Подключение к сайту

В `chat.js` на сайте поменяйте адрес сервера и добавьте версию:

```js
const backendUrl = "https://rai-xxxx.onrender.com/api/chat";   // ваша ссылка

let sessionId = localStorage.getItem("rai_session");
if (!sessionId) {
    sessionId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("rai_session", sessionId);
}

// версия: "pro" | "pro-fast" | "pro-plus" | "pro-sun"
// например из <select id="raiVersion">…</select>
function currentVersion() {
    const el = document.getElementById("raiVersion");
    return el ? el.value : "pro";
}

// внутри sendRequest():
const response = await fetch(backendUrl, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: text, version: currentVersion(), session_id: sessionId})
});
const data = await response.json();
addBlock(data.answer || "Результат не получен.", "rai");
```

Выбор версии в `chat.php`:

```html
<select id="raiVersion">
    <option value="pro">Rai Pro</option>
    <option value="pro-fast">Rai Pro Fast</option>
    <option value="pro-plus">Rai Pro Plus</option>
    <option value="pro-sun">Rai Pro Sun</option>
</select>
```

## Как научить Rai новому

**Способ 1: в `knowledge.json`.** Добавьте блок и сделайте push в GitHub. Хостинг обновится сам.

```json
{
  "id": "schedule",
  "title": "Расписание созвонов",
  "patterns": ["когда созвон", "во сколько собрание", "расписание встреч"],
  "answers": ["Созвон команды — по пятницам в 19:00."],
  "more": "Ссылка на созвон публикуется в чате команды за час до начала."
}
```

- `patterns`: разные формулировки вопроса. Чем их больше, тем лучше Rai понимает.
- `answers`: варианты ответа, Rai выбирает случайный. `{name}` заменяется на «, Имя», если имя известно.
- `more`: подробности. Их показывает Pro Sun сразу, а Pro Plus по команде «подробнее».

**Способ 2: без правки кода, через `/api/teach`** (нужен `RAI_ADMIN_TOKEN`):

```bash
curl -X POST https://rai-xxxx.onrender.com/api/teach \
  -H "Content-Type: application/json" -H "X-Rai-Token: ваш_секрет" \
  -d '{"patterns": ["когда созвон"], "answer": "По пятницам в 19:00."}'
```

Выученное сохраняется в `learned.json` на сервере. На бесплатных хостингах этот файл стирается при перезапуске, поэтому постоянные знания лучше добавлять в `knowledge.json`.

## Важно

- Память сессий (имя, факты) хранится в оперативной памяти сервера и пропадает при перезапуске. Поэтому сервер запускается с одним воркером (`--workers 1`).
- Rai — не генеративная нейросеть. Он отвечает на то, что есть в базе знаний, плюс работает навыками. Чем больше вопросов и ответов в `knowledge.json`, тем он умнее.
