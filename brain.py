"""Движок Rai: собственный ИИ без внешних API.

Как отвечает Rai:
1. команды памяти («запомни, что …», «как меня зовут») — Pro Plus / Pro Sun;
2. встроенные навыки (калькулятор, время, конвертер, …);
3. поиск по базе знаний knowledge.json (+ learned.json);
4. поиск по запомненным фактам (Pro Sun);
5. если ничего не подошло — честно говорит и предлагает похожие темы.
"""

import json
import os
import random
import re
import threading
import time
from collections import OrderedDict

import codeai
import codelib
import creative
import net
import nlp
import online
import proglangs
import skills
from versions import Version

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.environ.get("RAI_KNOWLEDGE_PATH", os.path.join(BASE_DIR, "knowledge.json"))
LEARNED_PATH = os.environ.get("RAI_LEARNED_PATH", os.path.join(BASE_DIR, "learned.json"))
GLOSSARY_PATH = os.environ.get("RAI_GLOSSARY_PATH", os.path.join(BASE_DIR, "glossary.json"))

MAX_MESSAGE_CHARS = int(os.environ.get("RAI_MAX_MESSAGE_CHARS", "4000"))
MAX_FACTS = 50
DEFAULT_CITY = os.environ.get("RAI_DEFAULT_CITY", "Москва")

_NAME_RE = re.compile(
    r"(?:меня зовут|мое имя|моё имя|зови меня|называй меня|my name is)\s+([A-Za-zА-Яа-яЁё-]{2,30})",
    re.I,
)
_ASK_NAME_RE = re.compile(r"как меня зовут|ты помнишь как меня|мое имя\??$|моё имя\??$|who am i", re.I)
_MORE_RE = re.compile(r"^(а\s+)?(подробнее|ещ[её]|расскажи подробнее|расскажи ещ[её]|продолжай|дальше|и\?)[\s?!.]*$", re.I)
_REMEMBER_RE = re.compile(r"^\s*запомни(?:,)?\s*(?:что|:)?\s*(.+)$", re.I | re.S)
_RECALL_RE = re.compile(r"что ты (?:помнишь|запомнил|знаешь обо мне)|что я тебе говорил", re.I)
_FORGET_RE = re.compile(r"^\s*забудь (?:вс[её]|об? мне)", re.I)
_ARCHIVE_RE = re.compile(r"(сделай|собери|скачай|создай|упакуй|сохрани)\w*\s+(?:мне\s+)?(?:весь\s+)?(?:чат\s+)?(?:в\s+)?(архив|zip)|"
                         r"^\s*(архив|zip)(?:\s+чата)?\s*[.!?]*$", re.I)
_DEFINE_RE = re.compile(
    r"^\s*(?:а\s+)?(?:что такое|что это(?: такое)?|кто такой|кто такая|кто такие|что значит|что означает|"
    r"что такое это|расскажи (?:про|о|об)|что ты знаешь (?:про|о|об)|что знаешь (?:про|о|об)|объясни(?: что такое)?)"
    r"\s+(.+?)[\s?!.]*$|^\s*(.+?)\s*(?:[-—]\s*)?это что[\s?!.]*$",
    re.I,
)


class RaiError(Exception):
    """Ошибка, текст которой можно показать пользователю."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class SessionStore:
    """Память разговоров в оперативной памяти сервера (с лимитом и сроком жизни)."""

    def __init__(self, limit: int = 5000, ttl: int = 6 * 3600):
        self.limit, self.ttl = limit, ttl
        self._data = OrderedDict()
        self._lock = threading.Lock()

    def get(self, session_id):
        if not session_id:
            return {}
        now = time.time()
        with self._lock:
            session = self._data.pop(session_id, None)
            if session is None or now - session["_seen"] > self.ttl:
                session = {"facts": []}
            session["_seen"] = now
            self._data[session_id] = session
            while len(self._data) > self.limit:
                self._data.popitem(last=False)
            return session


def _clean_session_id(value):
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value):
        return value
    return None


class Brain:
    def __init__(self, knowledge_path=KNOWLEDGE_PATH, learned_path=LEARNED_PATH, glossary_path=GLOSSARY_PATH):
        self.knowledge_path = knowledge_path
        self.learned_path = learned_path
        self.glossary_path = glossary_path
        self.sessions = SessionStore()
        self._lock = threading.Lock()
        self.reload()

    # ------------------------------------------------------------ база знаний

    def _read(self, path):
        if not path or not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("intents", [])

    def reload(self):
        intents = self._read(self.knowledge_path) + self._read(self.learned_path)
        by_id = {}
        for intent in intents:
            if intent.get("id") and intent.get("patterns") and intent.get("answers"):
                by_id[intent["id"]] = intent
        docs = [(i["id"], p) for i in by_id.values() for p in i["patterns"] + [i.get("title", "")] if p]
        indexes = {
            "keywords": nlp.KeywordIndex(docs),
            "tfidf": nlp.TfidfIndex(docs, fuzzy=False),
            "tfidf+fuzzy": nlp.TfidfIndex(docs, fuzzy=True),
        }
        intent_tokens = {}
        for key, text in docs:
            intent_tokens.setdefault(key, set()).update(nlp.tokens(text))
        glossary = []
        if self.glossary_path and os.path.exists(self.glossary_path):
            with open(self.glossary_path, encoding="utf-8") as f:
                for entry in json.load(f).get("terms", []):
                    keys = [tuple(nlp.tokens(t, keep_stopwords=True)) for t in entry["terms"]]
                    glossary.append(([k for k in keys if k], entry["text"]))
        # Слова из статей словаря тоже «известные», чтобы корректор их не «исправлял».
        vocab = [text for _, text in docs] + [text for _, text in glossary] + [
            " ".join(k) for keys, _ in glossary for k in keys]
        speller = nlp.SpellChecker(vocab)
        with self._lock:
            self.intents, self.indexes = by_id, indexes
            self.intent_tokens, self.speller = intent_tokens, speller
            self.glossary = glossary

    def teach(self, patterns, answer, title=None):
        """Добавить знание в learned.json (админ-функция)."""
        patterns = [p.strip() for p in patterns if isinstance(p, str) and p.strip()]
        if not patterns or not isinstance(answer, str) or not answer.strip():
            raise RaiError("Нужны patterns (список фраз) и answer (ответ).")
        with self._lock:
            learned = self._read(self.learned_path)
            intent_id = f"learned_{len(learned) + 1}_{int(time.time())}"
            learned.append({
                "id": intent_id,
                "title": (title or patterns[0]).strip(),
                "patterns": patterns,
                "answers": [answer.strip()],
            })
            with open(self.learned_path, "w", encoding="utf-8") as f:
                json.dump({"intents": learned}, f, ensure_ascii=False, indent=2)
        self.reload()
        return intent_id

    def define(self, version: Version, text: str, exact_only: bool = False):
        """Найти понятие в словаре: «что такое атом», «кто такой хакер», просто «фотосинтез»."""
        m = _DEFINE_RE.match(text)
        subject = (m.group(1) or m.group(2)) if m else None
        if exact_only and not subject:
            return None
        target = subject if subject else text
        if version.fuzzy:
            target = self.speller.correct(target)
        words = tuple(nlp.tokens(target, keep_stopwords=True))
        if not words:
            return None
        best, best_len = None, 0
        for keys, definition in self.glossary:
            for key in keys:
                exact = words == key
                # «что такое X» — X может быть частью фразы («что такое оперативная память в компьютере»)
                inside = subject and not exact_only and any(words[i:i + len(key)] == key for i in range(len(words)))
                if (exact or inside) and len(key) > best_len:
                    best, best_len = definition, len(key)
        return best

    def search(self, version: Version, text: str, limit: int = 5, correct: bool = True):
        """Найти подходящие темы: [(id, сходство)], только уверенные совпадения."""
        if version.fuzzy and correct:
            text = self.speller.correct(text)
        key = "keywords" if version.search == "keywords" else ("tfidf+fuzzy" if version.fuzzy else "tfidf")
        results = self.indexes[key].search(text)
        # Совпадение только по общим словам («что», «такое», «как»…) при наличии
        # в вопросе значимых слов — не совпадение: «что такое рхп» ≠ «что такое python».
        meaningful = set(nlp.tokens(text)) - nlp.GENERIC
        if meaningful:
            results = [(k, s) for k, s in results if meaningful & self.intent_tokens.get(k, set())]
        return results[:limit]

    # ------------------------------------------------------------ ответы

    def answer(self, version: Version, message: str, session_id=None, history=None) -> dict:
        message = (message or "").strip()
        if not message:
            raise RaiError("Пустой запрос.")
        if len(message) > MAX_MESSAGE_CHARS:
            raise RaiError(f"Запрос слишком длинный (больше {MAX_MESSAGE_CHARS} символов).", 413)

        session = self.sessions.get(_clean_session_id(session_id)) if version.context else {}
        if version.context and not session.get("name"):
            session["name"] = _name_from_history(history)

        parts = [message]
        if version.multi and not _REMEMBER_RE.match(message) and not codeai.extract_code(message)[0]:
            parts = [p.strip() for p in re.split(r"(?<=\?)\s+|\n+", message) if p.strip()] or [message]

        answers, intents, attachments = [], [], []
        for part in parts[:5]:
            text, intent = self._answer_one(version, part, session, attachments)
            answers.append(text)
            intents.append(intent)

        if len(answers) > 1:
            text = "\n\n".join(f"**{q}**\n\n{a}" for q, a in zip(parts, answers))
        else:
            text = answers[0]
        return {
            "answer": text,
            "version": version.id,
            "version_name": version.name,
            "intent": intents[0] if len(intents) == 1 else intents,
            "attachments": attachments,
        }

    def _answer_one(self, version: Version, text: str, session: dict, attachments: list):
        name_match = _NAME_RE.search(text)
        if name_match:
            name = name_match.group(1).capitalize()
            if version.context:
                session["name"] = name
                return f"Приятно познакомиться, {name}! Запомнил.", "set_name"
            return f"Приятно познакомиться, {name}! (Запоминать имя умеют Pro Plus и Pro Sun.)", "set_name"

        if _ASK_NAME_RE.search(text):
            if not version.context:
                return "Запоминать имя умеют Rai Pro Plus и Rai Pro Sun.", "get_name"
            if session.get("name"):
                return f"Вас зовут {session['name']}.", "get_name"
            return "Вы ещё не говорили, как вас зовут. Напишите: «меня зовут …».", "get_name"

        if _MORE_RE.match(text):
            if not version.context:
                return "Продолжать тему умеют Rai Pro Plus и Rai Pro Sun. Задайте вопрос целиком.", "more"
            if session.get("last_intent") in self.intents:
                return self._more(session), "more"
            return "О чём рассказать подробнее? Задайте вопрос.", "more"

        if _REMEMBER_RE.match(text) or _RECALL_RE.search(text) or _FORGET_RE.match(text):
            if not version.memory:
                return "Запоминать факты умеет только Rai Pro Sun.", "memory"
            return self._memory(text, session), "memory"

        if creative.is_slides_request(text):
            if "slides" not in version.skills:
                return "Презентации умеют делать Rai Pro Plus и Rai Pro Sun.", "slides"
            return self._slides(version, text, attachments), "slides"

        if creative.is_image_request(text):
            if "image" not in version.skills:
                return "Картинки умеют рисовать Rai Pro, Pro Plus и Pro Sun.", "image"
            image = creative.make_image(text)
            attachments.append(image)
            if image.get("unknown"):
                return ("Такой сюжет я пока рисовать не умею, поэтому нарисовал **абстракцию**. "
                        "Умею: закат, рассвет, ночь, космос, горы, море, лес, город, пустыню, зиму, "
                        "сердце, цветок и логотипы."), "image"
            return f"Готово: **{image['title']}**. Картинку можно скачать в PNG или SVG.", "image"

        # ---- навыки с интернетом
        if "translate" in version.skills and online.is_translate_request(text):
            return online.translate(text), "translate"
        if "weather" in version.skills:
            found = online.weather(text, session, DEFAULT_CITY)
            if found:
                reply, extra = found
                attachments.extend(extra)
                return reply, "weather"
        if "currency" in version.skills:
            reply = online.currency(text)
            if reply:
                return reply, "currency"
        query = online.explicit_search(text)
        if query:
            if "web" not in version.skills:
                return "Искать в интернете умеют Rai Pro, Pro Plus и Pro Sun.", "web"
            return self._web(query, attachments) or (f"В интернете ничего не нашёл про «{query}».", "web")

        # ---- архив: собрать чат (картинки, презентации, код) в ZIP
        if _ARCHIVE_RE.search(text):
            attachments.append({"type": "archive", "scope": "chat", "title": "Архив чата"})
            return ("Собрал архив: все ответы этого чата, картинки (SVG), презентации (HTML) и код — одним ZIP-файлом. "
                    "Нажмите «Скачать архив»."), "archive"

        # ---- код: проверка, объяснение, исправление, генерация программ
        code_answer = proglangs.answer(text)
        if "code" not in version.skills and (codeai.extract_code(text)[0] or
                                             (codelib.find_task(text) not in (None, "hello") and codeai.chat(text))):
            return "Проверять и писать код умеют Rai Pro Plus, Pro Sun и Pro Quasar — переключите версию сверху.", "code"
        if "code" in version.skills:
            task = codelib.find_task(text)
            if codeai.extract_code(text)[0] or (task and task != "hello") or not code_answer:
                result = codeai.chat(text, version)
                if result:
                    if result.get("code"):
                        attachments.append({"type": "code", "lang": result["lang"], "code": result["code"],
                                            "filename": result.get("filename") or "main." + codeai.EXT_OF.get(result["lang"], "txt"),
                                            "title": result.get("title") or "Код"})
                    return result["answer"], "code"
        if code_answer and (proglangs._LIST_RE.search(text) or proglangs._CODE_RE.search(text)):
            return code_answer, "proglang"

        reply = skills.run(text, version.skills)
        if reply:
            return reply, "skill"

        # «Что такое X», где X точно есть в словаре, — отвечаем определением.
        # Языки программирования отвечает справочник proglangs, а не словарь.
        definition = None if code_answer else self.define(version, text, exact_only=True)
        if definition:
            return self._enrich(version, text, definition, attachments), "glossary"

        results = self.search(version, text)
        best = results[0][1] if results else 0.0

        if version.memory:
            fact, score = self._find_fact(text, session)
            if fact and score >= best:
                return f"Вы мне говорили: {fact}.", "memory"

        if best < version.threshold:
            if code_answer:
                return code_answer, "proglang"
            definition = self.define(version, text)
            if definition:
                return self._enrich(version, text, definition, attachments), "glossary"

        if best >= version.threshold:
            intent = self.intents[results[0][0]]
            if version.context:
                # «подробнее»/«ещё» имеют смысл только для тем с продолжением.
                if intent.get("more") or intent.get("repeatable"):
                    session["last_intent"] = intent["id"]
                    session["more_used"] = False
                else:
                    session.pop("last_intent", None)
            return self._render(intent, version, session), intent["id"]

        note = ""
        if "web" in version.skills and self._worth_searching(text):
            try:
                found = self._web(self._subject(text) or text, attachments, raise_errors=True)
            except net.NetError:
                found, note = None, "\n\n*Поискать в интернете не получилось: нет связи.*"
            if found:
                return found
        return self._fallback(version, results, text) + note, None

    def _enrich(self, version, text, answer, attachments):
        """Quasar: дополнить короткое определение фактами из Википедии (если статья про то же самое)."""
        subject = self._subject(text) or text
        if not version.enrich or "web" not in version.skills:
            return answer
        try:
            art = online.web_article(subject, langs=("ru",))
        except net.NetError:
            return answer
        if not art or not set(nlp.tokens(subject)) & set(nlp.tokens(art["title"])):
            return answer
        extra = [s for s in creative._sentences(art["text"]) if s not in answer][:3]
        if not extra:
            return answer
        if art["image"]:
            attachments.append({"type": "photo", "url": art["image"], "title": art["title"], "source": art["link"]})
        return answer + "\n\n**Из интернета:** " + " ".join(extra) + (f"\n\nИсточник: [Википедия]({art['link']})" if art["link"] else "")

    @staticmethod
    def _subject(text):
        m = _DEFINE_RE.match(text)
        return ((m.group(1) or m.group(2)) if m else "").strip()

    @staticmethod
    def _worth_searching(text):
        """Искать в интернете только осмысленные вопросы, а не «ок» или «ыыы»."""
        meaningful = [w for w in nlp.tokens(text) if w not in nlp.GENERIC and len(w) > 2]
        return bool(meaningful) and bool(re.search(r"[а-яa-z]{3,}", text.lower()))

    def _web(self, query, attachments, raise_errors=False):
        try:
            found = online.web_search(query)
        except net.NetError as e:
            if raise_errors:
                raise
            return f"Поискать в интернете не получилось: нет связи ({e}).", "web"
        if not found:
            return None
        reply, extra = found
        attachments.extend(extra)
        return reply, "web"

    def _slides(self, version, text, attachments):
        topic = creative.slides_topic(text)
        theme = creative.deck_theme(text)
        results = self.search(version, topic, limit=4, correct=False) if topic else []
        found = [self.intents[k] for k, score in results if score >= version.threshold * 0.8]
        big = version.detailed
        found = found[:4] if big else found[:2]
        if len(found) < 2 and topic:
            found += self._glossary_for(topic, limit=(6 if big else 3) - len(found))
        photo = None
        if topic and "web" in version.skills and (len(found) < 2 or version.enrich):
            # Материала мало — дополняем статьёй из интернета (и берём оттуда настоящую фотографию)
            try:
                art = online.web_article(topic, langs=("ru",))
            except net.NetError:
                art = None
            if art:
                photo = art["image"]
                found.append({"title": art["title"], "answers": [art["text"]], "web": True})
        web = next((a for a in found if a.get("web")), None)
        if web and set(nlp.tokens(topic)) <= set(nlp.tokens(web["title"])):
            topic = web["title"]  # «эйфелеву башню» -> «Эйфелева башня»
        title = topic or "Rteam"
        if re.fullmatch(r"[a-z0-9+#]{1,5}", title, re.I):
            title = title.upper()  # html -> HTML, php -> PHP
        elif found and found[0].get("key_match") and len(title.split()) == 1:
            title = found[0]["title"]  # «котов» -> «Кошка»
        limit = version.slide_limit
        deck = creative.make_slides(title, found, max_slides=limit, theme=theme, photo=photo)
        if not deck:
            hint = "" if "web" in version.skills else " Rai Pro, Pro Plus и Pro Sun ещё и ищут материал в интернете."
            return (f"Про «{topic or text}» я пока не нашёл материала, поэтому презентацию не сделал — "
                    f"не хочу показывать пустые слайды.{hint} Попробуйте другую тему, например «презентация про космос».")
        attachments.append(deck)
        n = len(deck["slides"])
        count = f"{n} " + ("слайд" if n % 10 == 1 and n % 100 != 11 else
                          "слайда" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "слайдов")
        colors = " в ваших цветах" if theme["custom"] else ""
        return (f"Готово: презентация **«{deck['title']}»**{colors}, {count}. "
                "Смотрите на весь экран, скачивайте файлом или ZIP-архивом.")

    def _glossary_for(self, topic, limit=3):
        """Понятия из словаря, связанные с темой, в виде статей для слайдов."""
        want = set(nlp.tokens(topic)) - nlp.GENERIC
        if not want or limit <= 0:
            return []
        by_key, by_text = [], []
        for keys, text in self.glossary:
            key_words = {w for k in keys for w in k}
            if want & key_words:
                by_key.append((len(want & key_words), keys, text))
            elif want & set(nlp.tokens(text)):
                by_text.append((len(want & set(nlp.tokens(text))), keys, text))
        # Сначала понятия, в названии которых есть тема, потом те, где она упоминается.
        scored = [(True,) + x for x in sorted(by_key, key=lambda x: -x[0])] + \
                 [(False,) + x for x in sorted(by_text, key=lambda x: -x[0])]
        out = []
        for key_match, _, keys, text in scored[:limit]:
            m = re.match(r"\*\*(.+?)\*\*", text)
            title = m.group(1) if m else " ".join(keys[0]).capitalize()
            out.append({"title": title, "key_match": key_match,
                        "answers": [re.sub(r"^\*\*.+?\*\*\s*(\([^)]*\)\s*)?[—-]\s*", "", text)]})
        return out

    def _pick(self, intent, session):
        """Случайный вариант ответа, по возможности не тот же, что в прошлый раз."""
        options = [a for a in intent["answers"] if a != session.get("last_answer")] or intent["answers"]
        choice = random.choice(options)
        session["last_answer"] = choice
        name = session.get("name")
        return choice.replace("{name}", f", {name}" if name else "")

    def _render(self, intent, version, session):
        answer = self._pick(intent, session)
        if version.detailed and intent.get("more"):
            answer += "\n\n" + intent["more"]
            session["more_used"] = True
        return answer

    def _more(self, session):
        intent = self.intents[session["last_intent"]]
        if intent.get("more") and not session.get("more_used"):
            session["more_used"] = True
            return intent["more"]
        if len(intent["answers"]) > 1:
            return self._pick(intent, session)
        return "Больше по этой теме мне добавить нечего. Спросите что-нибудь ещё!"

    def _memory(self, text, session):
        facts = session.setdefault("facts", [])
        m = _REMEMBER_RE.match(text)
        if m:
            fact = m.group(1).strip().rstrip(".!")
            if len(facts) >= MAX_FACTS:
                facts.pop(0)
            facts.append(fact)
            return f"Запомнил: {fact}."
        if _FORGET_RE.match(text):
            facts.clear()
            session.pop("name", None)
            return "Хорошо, всё забыл."
        if not facts and not session.get("name"):
            return "Пока ничего не запомнил. Скажите: «запомни, что …»."
        lines = [f"• вас зовут {session['name']}"] if session.get("name") else []
        lines += [f"• {f}" for f in facts]
        return "Я помню:\n" + "\n".join(lines)

    def _find_fact(self, text, session):
        """Найти запомненный факт, похожий на вопрос: (факт, сходство)."""
        facts = session.get("facts") or []
        if not facts:
            return None, 0.0
        index = nlp.TfidfIndex(list(enumerate(facts)), fuzzy=True)
        results = index.search(text, 1)
        meaningful = set(nlp.tokens(text)) - nlp.GENERIC
        if results and results[0][1] >= 0.3:
            fact = facts[results[0][0]]
            if not meaningful or meaningful & set(nlp.tokens(fact)):
                return fact, results[0][1]
        return None, 0.0

    def _fallback(self, version, results, text=""):
        m = _DEFINE_RE.match(text)
        subject = ((m.group(1) or m.group(2)) if m else "").strip()
        base = f"Про «{subject}» я пока не знаю." if subject else "Я пока не знаю ответа на это."
        lines = [base]
        if version.suggestions:
            titles = [self.intents[k].get("title", k) for k, s in results[:3] if s >= 0.1]
            if titles:
                lines.append("Возможно, вы имели в виду:\n" + "\n".join(f"- {t}" for t in titles))
        if version.memory:
            example = subject or "Rai"
            lines.append(f"Научите меня: напишите «запомни, что {example} — это …», и я запомню.")
        else:
            lines.append("Попробуйте спросить иначе или напишите «что ты умеешь».")
        return "\n\n".join(lines)


def _name_from_history(history):
    if not isinstance(history, list):
        return None
    for item in reversed(history[-50:]):
        if isinstance(item, dict) and item.get("role") == "user":
            text = item.get("content", item.get("text"))
            m = _NAME_RE.search(text) if isinstance(text, str) else None
            if m:
                return m.group(1).capitalize()
    return None
