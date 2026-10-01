"""ИИ поддержки rteam.info (Rai). Отвечает клиентам в тикетах и подсказывает ответы сотрудникам.

Откуда берёт ответы (по порядку):
1. База знаний о сайте — support_kb.json (как подать заявку, привязать бота, золотой билет…);
2. Страницы сайта rteam.info — скачивает публичные страницы и ищет в них нужный абзац
   (SUPPORT_SITE_URL, SUPPORT_SITE_PAGES; обновляет раз в 6 часов в фоне);
3. Интернет — Википедия и поиск Google / DuckDuckGo через посредник net.php (online.web_search).

Чего ИИ не делает:
- Не знает паролей, токенов и других секретов: ему их не передают, и он отказывается их обсуждать.
  Всё, что попало бы в ИИ, можно выманить хитрым вопросом, поэтому секретов у него просто нет.
- Не решает вопросы оплаты, банов и апелляций — сразу передаёт тикет администратору (handoff).

Используется в app.py: POST /api/support (ключ SUPPORT_AI_KEY в заголовке X-Support-Key).
"""

import html
import json
import os
import re
import threading
import time

import net
import nlp
import online

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "support_kb.json")
NAME = "Rai"

SITE_URL = os.environ.get("SUPPORT_SITE_URL", "https://rteam.info").rstrip("/")
SITE_PAGES = [p.strip() for p in os.environ.get("SUPPORT_SITE_PAGES", "/,/team.php,/projects.php").split(",") if p.strip()]
SITE_TTL = 6 * 3600


def _load_kb():
    with open(KB_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for item in data.get("items", []):
        phrases = list(dict.fromkeys(nlp.normalize(k) for k in item.get("keys", [])))  # «стажёр» = «стажер»
        item["_phrases"] = phrases
        item["_stems"] = [set(nlp.tokens(k)) for k in phrases]
    return data


KB = _load_kb()

# ============================================================ безопасность

# Просьбы выдать пароль, токен или чужие данные
_SECRET_WORD = r"(парол\w*|password\w*|passwd|токен\w*|token\w*|секрет\w*|secret\w*|api[\s-]?ключ\w*|ключ\w*\s+api|cookie\w*|куки|сесси\w+|cvv|данные\s+карты)"
_ASK = r"(скажи|скажите|дай|дайте|покажи|покажите|назови|скинь|пришли|напиши|узна\w*|выдай|слей|раскрой|подскажи|какой|какие|tell|give|show|send)"
_WHOSE = r"(админ\w*|руководител\w*|друг\w*|чуж\w*|друго\w*|бот\w*|сайт\w*|баз\w*|users|пользовател\w*|сотрудник\w*|директор\w*|школ\w*)"
SECRET_ASK_RE = re.compile(rf"{_ASK}.{{0,40}}{_SECRET_WORD}|{_SECRET_WORD}.{{0,40}}{_WHOSE}|{_WHOSE}.{{0,20}}{_SECRET_WORD}", re.I | re.S)

SECRET_REPLY = (
    "Я не знаю паролей, токенов и других секретов — у меня нет к ним доступа, и сотрудники RTeam "
    "никогда их не спрашивают. Свой пароль можно сменить в личном кабинете: rteam.info/cabinet.php → "
    "«Безопасность». Если вы его не помните, нажмите «Позвать администратора» — он поможет восстановить доступ."
)

# Что вырезаем из любого найденного текста, прежде чем показать: вдруг на странице оказался секрет
_REDACT = [
    (re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"), "[скрыто]"),                       # токен Telegram-бота
    (re.compile(r"\b[A-Fa-f0-9]{32,}\b"), "[скрыто]"),                                  # длинные ключи
    (re.compile(r"(?i)\b(pass(word)?|пароль|token|secret|key)\s*[:=]\s*\S+"), r"\1: [скрыто]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[скрыто]"),                                # номера карт
]


def redact(text: str) -> str:
    for rx, repl in _REDACT:
        text = rx.sub(repl, text)
    return text


# ============================================================ страницы сайта

class SiteIndex:
    """Тексты публичных страниц сайта, разбитые на абзацы — «знания о сайте» для ответов."""

    def __init__(self, base=SITE_URL, pages=SITE_PAGES, ttl=SITE_TTL):
        self.base, self.pages, self.ttl = base, pages, ttl
        self.chunks = []          # [{"url", "text", "stems"}]
        self.loaded_at = 0.0
        self._lock = threading.Lock()
        self._loading = False

    @staticmethod
    def html_to_text(page: str) -> str:
        page = re.sub(r"(?is)<(script|style|svg|noscript|template)\b.*?</\1>", " ", page)
        page = re.sub(r"(?is)<!--.*?-->", " ", page)
        page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|section|article|tr|summary|details)>", "\n", page)
        page = re.sub(r"<[^>]+>", " ", page)
        page = html.unescape(page)
        page = re.sub(r"<\?php.*?\?>", " ", page, flags=re.S)
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in page.split("\n")]
        return "\n".join(ln for ln in lines if len(ln) > 2)

    @staticmethod
    def split(text: str, size: int = 420):
        out, cur = [], ""
        for line in text.split("\n"):
            if len(cur) + len(line) > size and cur:
                out.append(cur.strip())
                cur = ""
            cur += " " + line
        if cur.strip():
            out.append(cur.strip())
        return [c for c in out if len(c) > 40]

    def refresh(self):
        chunks = []
        try:
            for path in self.pages:
                address = self.base + (path if path.startswith("/") else "/" + path)
                try:
                    text = self.html_to_text(net.fetch_text(address, timeout=8))
                except Exception:  # сайт недоступен или страница сломана — берём остальные
                    continue
                for c in self.split(redact(text)):
                    chunks.append({"url": address, "text": c, "stems": set(nlp.tokens(c))})
        finally:
            with self._lock:
                if chunks:
                    self.chunks = chunks
                self.loaded_at = time.time()
                self._loading = False

    def ensure_fresh(self, wait: bool = False):
        """Обновляет страницы в фоне, если устарели. wait=True — дождаться (для тестов и первого запуска)."""
        if not self.base or time.time() - self.loaded_at < self.ttl:
            return
        with self._lock:
            if self._loading:
                return
            self._loading = True
        if wait:
            self.refresh()
        else:
            threading.Thread(target=self.refresh, daemon=True).start()

    def search(self, query: str):
        want = {w for w in nlp.tokens(query) if w not in nlp.GENERIC and len(w) > 2}
        if len(want) < 1:
            return None
        best, best_score = None, 0.0
        for ch in self.chunks:
            hit = len(want & ch["stems"])
            score = hit / len(want)
            if hit >= 2 and score > best_score:
                best, best_score = ch, score
        return (best, best_score) if best and best_score >= 0.5 else None


site = SiteIndex()

# ============================================================ разбор вопроса

_GREETING_RE = re.compile(r"^\s*(привет\w*|здравству\w*|здрасьте|добрый\s+(день|вечер|утро)|доброе\s+утро|хай|hello|hi|салам)[\s!.,)]*$", re.I)
_THANKS_RE = re.compile(r"^\s*(спасибо|благодарю|спс|thanks|thank you|понял|понятно|ок|окей|ясно)[\s!.,)]*$", re.I)
_HUMAN_RE = re.compile(r"(позов\w*|позвать|нужен|нужна|хочу|дайте|соедин\w*|переключ\w*).{0,25}(админ\w*|человек\w*|оператор\w*|сотрудник\w*|модератор\w*|живо\w*)", re.I)
_SEARCH_RE = re.compile(r"^(найди|поищи|загугли|погугли|что такое|кто такой|кто такая|search)\b|в интернете", re.I)


def kb_match(text: str):
    """Лучшая запись базы знаний для вопроса: (запись, очки) или (None, 0)."""
    norm = " " + nlp.normalize(text) + " "
    stems = set(nlp.tokens(text))
    best, best_score = None, 0.0
    for item in KB.get("items", []):
        score = 0.0
        for phrase, kst in zip(item["_phrases"], item["_stems"]):
            if phrase and " " + phrase + " " in norm:
                score += 3 + len(phrase.split())
            elif kst and kst <= stems:
                score += 2 + len(kst)
            elif kst:
                score += 0.5 * len(kst & stems)
        if score > best_score:
            best, best_score = item, score
    return (best, best_score) if best_score >= 3 else (None, 0.0)


def _plain(md: str) -> str:
    """Markdown из поиска → обычный текст для чата поддержки (там без разметки)."""
    md = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", md)
    md = re.sub(r"[*_`]{1,3}", "", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def _history_text(history, limit=6):
    """Последние сообщения клиента — чтобы понять вопрос по контексту («а как это сделать?»)."""
    if not isinstance(history, list):
        return ""
    msgs = [str(h.get("text", "")) for h in history[-limit:] if isinstance(h, dict) and h.get("from") == "client"]
    return " ".join(msgs)[-600:]


def reply(message: str, history=None, topic: str = "", mode: str = "client") -> dict:
    """Ответ на сообщение клиента.

    mode="client" — ответ от имени Rai прямо в тикет;
    mode="draft"  — черновик ответа для сотрудника (он отредактирует и отправит сам).
    Возвращает {"reply", "handoff", "source", "confidence", "links"}.
    handoff=True — вопрос должен решать человек: тикет передаётся администратору.
    """
    text = (message or "").strip()[:2000]
    draft = mode == "draft"
    site.ensure_fresh()

    def out(reply_text, source, confidence, handoff=False, links=None):
        reply_text = redact(reply_text)
        if draft and not reply_text.startswith("Здравствуйте"):
            reply_text = "Здравствуйте! " + reply_text
        return {"reply": reply_text, "handoff": bool(handoff and not draft), "source": source,
                "confidence": round(confidence, 2), "links": links or []}

    if not text:
        return out("Напишите, пожалуйста, ваш вопрос — я постараюсь помочь.", "empty", 0.2)

    # 1. Пароли и прочие секреты — никогда
    if SECRET_ASK_RE.search(text) and not re.search(r"\b(забыл\w*|не помню|сменить|поменять|восстанов\w*|сброс\w*)\b", text, re.I):
        return out(SECRET_REPLY, "secret", 1.0)

    # 2. Просьба позвать человека
    if _HUMAN_RE.search(text) and not draft:
        return out("Хорошо, зову администратора — я отключаюсь. Опишите, пожалуйста, вопрос подробнее, "
                   "чтобы сотруднику было проще помочь.", "human", 1.0, handoff=True)

    if _GREETING_RE.match(text) and not draft:
        return out(f"Здравствуйте! Я {NAME}, ИИ-помощник поддержки RTeam. Опишите, пожалуйста, ваш вопрос — "
                   "отвечу сразу. Если нужен живой сотрудник, нажмите «Позвать администратора».", "greeting", 0.9)
    if _THANKS_RE.match(text) and not draft:
        return out("Рад помочь! Если появятся ещё вопросы — пишите сюда. Если вопрос решён, тикет можно не закрывать: "
                   "администрация закроет его сама.", "thanks", 0.9)

    # 3. База знаний о сайте (с учётом темы тикета и прошлых сообщений)
    query = " ".join(x for x in (topic, _history_text(history), text) if x)
    item, score = kb_match(text)
    if not item:
        item, score = kb_match(query)
    found = site.search(text) or site.search(query)
    if item and score < 5 and not item.get("handoff") and found and found[1] >= 0.66:
        item = None  # совпало одно слово базы («стажёр»), а на сайте есть абзац почти обо всём вопросе
    if item:
        handoff = bool(item.get("handoff"))
        if not handoff and item.get("handoff_if"):
            handoff = any(w in nlp.normalize(text) for w in item["handoff_if"])
        answer = item.get("draft") if draft and item.get("draft") else item["answer"]
        return out(answer, "kb:" + item["id"], min(1.0, score / 8), handoff=handoff)

    # 4. Страницы сайта
    if found:
        ch, sc = found
        snippet = ch["text"][:500].rsplit(" ", 1)[0]
        tail = "" if draft else "\n\nЕсли это не то, что нужно, уточните вопрос или нажмите «Позвать администратора»."
        return out(f"Вот что сказано об этом на сайте:\n\n«{snippet}…»\n\nПодробнее: {ch['url']}{tail}",
                   "site", sc * 0.8, links=[ch["url"]])

    # 5. Интернет — для общих вопросов («что такое…», «как обновить драйвер»)
    if _SEARCH_RE.search(text) or online.needs_facts(text) or len(nlp.tokens(text)) >= 3:
        try:
            res = online.web_search(re.sub(_SEARCH_RE, "", text).strip() or text)
        except net.NetError:
            res = None
        if res:
            body = _plain(res[0])[:1400]
            tail = "" if draft else ("\n\nЭто ответ из интернета. Если вопрос про сайт RTeam и ответ не подошёл — "
                                     "нажмите «Позвать администратора».")
            return out(body + tail, "web", 0.5)

    # 6. Не нашёл — честно говорим и предлагаем человека
    if draft:
        return out("Спасибо за обращение! Уточните, пожалуйста, подробности: что именно происходит, на какой "
                   "странице и с какого аккаунта — так мы быстрее поможем.", "fallback", 0.1)
    return out("Я не нашёл точного ответа на этот вопрос. Попробуйте описать подробнее — или нажмите "
               "«Позвать администратора», и вам ответит сотрудник RTeam.", "fallback", 0.1)


def status() -> dict:
    return {"ok": True, "kb": len(KB.get("items", [])), "site_url": SITE_URL, "site_chunks": len(site.chunks),
            "site_loaded_at": int(site.loaded_at)}
