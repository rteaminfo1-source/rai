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
import memes
import online
import proglangs
import skills
import social
import syntax
import talk
import toolbox
import facts  # noqa: F401 — регистрирует справочник в toolbox
import games
import fixer
import encyclopedia
import places
import sight
import webgen
from versions import Version

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.environ.get("RAI_KNOWLEDGE_PATH", os.path.join(BASE_DIR, "knowledge.json"))
LEARNED_PATH = os.environ.get("RAI_LEARNED_PATH", os.path.join(BASE_DIR, "learned.json"))
GLOSSARY_PATH = os.environ.get("RAI_GLOSSARY_PATH", os.path.join(BASE_DIR, "glossary.json"))

MAX_MESSAGE_CHARS = int(os.environ.get("RAI_MAX_MESSAGE_CHARS", "4000"))
MAX_SCREEN_CHARS = 16000
SCREEN_MARK = "[[screen]]"
LINK_MARK = "[[link-data]]"  # данные по ссылке, которые страница уже получила от посредника на хостинге
MAX_LINK_CHARS = 60000
_OPTION_RE = re.compile(r"^\s*(?:[a-dа-гA-DА-Г]|\d{1,2})\s*[).]\s+\S|^\s*[-•○□☐◯]\s+\S")
_QUESTION_START = re.compile(r"^\s*(?:вопрос\s*\d*[.:]?\s*|\d{1,2}\s*[.)]\s*|задани\w*\s*\d*[.:]?\s*)", re.I)
_MATH_LINE = re.compile(r"^[\d\s+\-*/×÷:^().,=?x]{3,}$")
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
# Темы-реплики: отвечают, только когда весь вопрос про них (иначе «что посмотреть вечером» = «добрый вечер»).
_ALL_TOOLS_RE = re.compile(r"(?:все|список|покажи)\s+(?:твои\s+|свои\s+)?(?:функци|возможност|команд)|(?:100|сто)\s+функци|какие\s+(?:у\s+тебя\s+)?(?:есть\s+)?функци", re.I)
_SMALL_TALK = {"greeting", "how_are_you", "thanks", "bye", "ok", "compliment", "insult", "bot_feelings"}
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


_SITE_VERSION = None  # версия для поиска фактов (самая полная), задаётся ниже


class Brain:
    def __init__(self, knowledge_path=KNOWLEDGE_PATH, learned_path=LEARNED_PATH, glossary_path=GLOSSARY_PATH):
        self.knowledge_path = knowledge_path
        self.learned_path = learned_path
        self.glossary_path = glossary_path
        self.sessions = SessionStore()
        self._lock = threading.Lock()
        self.reload()
        webgen.KNOWLEDGE = self._site_facts  # сайты «про X» наполняются фактами из базы знаний

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
            self.small_tokens = set().union(*(intent_tokens.get(k, set()) for k in _SMALL_TALK))
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
        meaningful = set(nlp.tokens(text)) - nlp.GENERIC - nlp.FILLER
        if meaningful:
            other_lang = proglangs.find_language(text)
            other_lang = other_lang and other_lang[0] != "Python"
            kept = []
            for k, s in results:
                matched = meaningful & self.intent_tokens.get(k, set())
                if not matched:
                    continue
                # Совпала меньшая часть смысла: «кто НАПИСАЛ войну и мир» ≠ «куда написать».
                if len(matched) * 2 < len(meaningful):
                    continue
                # Короткие реплики (привет, как дела, спасибо) — только если в вопросе нет другой темы:
                # «что посмотреть вечером» ≠ «добрый вечер».
                if k in _SMALL_TALK and meaningful - matched - self.small_tokens:
                    continue
                # Темы про Python не отвечают на вопрос про другой язык: «цикл в javascript».
                if other_lang and k.startswith("python"):
                    continue
                kept.append((k, s))
            results = kept
        return results[:limit]

    # ------------------------------------------------------------ ответы

    def answer(self, version: Version, message: str, session_id=None, history=None) -> dict:
        message = (message or "").strip()
        if not message:
            raise RaiError("Пустой запрос.")
        screen = SCREEN_MARK in message  # текст со скриншота или записи экрана (распознан в браузере)
        link = LINK_MARK in message
        if len(message) > (MAX_SCREEN_CHARS if screen else MAX_LINK_CHARS if link else MAX_MESSAGE_CHARS):
            raise RaiError(f"Запрос слишком длинный (больше {MAX_MESSAGE_CHARS} символов).", 413)

        session = self.sessions.get(_clean_session_id(session_id)) if version.context else {}
        if version.context and not session.get("name"):
            session["name"] = _name_from_history(history)

        if screen:
            attachments = []
            text = self._screen(version, message, session, attachments)
            return {"answer": text, "version": version.id, "version_name": version.name, "intent": "screen",
                    "attachments": attachments}

        if link:
            question, _, raw = message.partition(LINK_MARK)
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
            attachments = []
            text = self._link(version, question.strip(), attachments, data if isinstance(data, dict) else None)
            return {"answer": text, "version": version.id, "version_name": version.name, "intent": "social",
                    "attachments": attachments}

        # Не та раскладка и опечатки (см. fixer.py) — исправляем и отвечаем на исправленное
        understood = None
        fixed, kind = fixer.fix(message)
        if kind:
            message = understood = fixed

        parts = [message]
        if social.is_link_request(message):
            parts = [message]  # ссылку с вопросом не режем на части
        elif version.multi and not _REMEMBER_RE.match(message) and not codeai.extract_code(message)[0]:
            parts = [p.strip() for p in re.split(r"(?<=\?)\s+|\n+", message) if p.strip()] or [message]

        net.PROBLEMS.clear()
        answers, intents, attachments = [], [], []
        # игры (загадки, викторина, города…) помнят ход в любой версии — отдельное хранилище по чату
        sid = _clean_session_id(session_id)
        play = self.sessions.get("play:" + sid) if sid else {}
        for part in parts[:5]:
            text, intent = self._answer_one(version, part, session, attachments, play)
            answers.append(text)
            intents.append(intent)

        if len(answers) > 1:
            text = "\n\n".join(f"**{q}**\n\n{a}" for q, a in zip(parts, answers))
        else:
            text = answers[0]
        if understood:
            shown = understood if len(understood) <= 160 else understood[:157] + "…"
            text = f"*Понял как: «{shown}»*\n\n" + text
        return {
            "fixed": understood,  # страница отдаёт нейросети уже исправленный вопрос
            "answer": text,
            "version": version.id,
            "version_name": version.name,
            "intent": intents[0] if len(intents) == 1 else intents,
            "attachments": attachments,
            "offline": bool(net.PROBLEMS),  # был сбой сети — страница может отдать вопрос нейросети
        }

    def _answer_one(self, version: Version, text: str, session: dict, attachments: list, play=None):
        # Человеку очень плохо — сначала помощь, всё остальное потом.
        if talk.is_crisis(text):
            return talk.CRISIS, "crisis"
        # Идёт игра (загадка, «угадай число», викторина, города) — сообщение сначала ей
        play = play if play is not None else {}
        if games.active(play):
            reply = games.turn(text, play)
            if reply:
                return reply, "game"
        if _ALL_TOOLS_RE.search(text):
            return toolbox.catalog(), "tools_list"
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

        # ---- ссылка на TikTok, YouTube, Telegram, Instagram, VK, X или сайт — разбор аккаунта, видео, страницы
        if social.is_link_request(text) and not codeai.is_build_request(text):
            return self._link(version, text, attachments), "social"

        if creative.is_slides_request(text):
            if "slides" not in version.skills:
                return "Презентации умеют делать Rai Pro Plus и Rai Pro Sun.", "slides"
            return self._slides(version, text, attachments), "slides"

        # ---- фото: «покажи фото Марса», «как выглядит галактика Андромеды», «фото дня NASA» (а «нарисуй» — рисунок)
        if places.is_apod_request(text):
            if "web" not in version.skills:
                return "Фото дня NASA показывают Rai Pro, Pro Plus, Pro Sun и Pro Quasar.", "photo"
            try:
                reply, found = places.apod()
            except net.NetError as e:
                return net.explain(e, "взять фото дня NASA"), "photo"
            attachments.extend(dict(p, type="photo") for p in found)
            return reply, "photo"
        if places.is_photo_request(text):
            subject = places.photo_subject(text)
            found = places.photos(subject, web="web" in version.skills) if subject else None
            if found:
                attachments.extend(dict(p, type="photo") for p in found[1])
                return found[0], "photo"
            if subject and "web" in version.skills:
                return f"Не нашёл фото «{subject}». Попробуйте назвать иначе — например, полное название.", "photo"

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

        # ---- мемы: своя база, а новых — ищем в интернете
        if memes.is_meme_request(text) and not codeai.is_build_request(text) and not creative.is_slides_request(text):
            known = memes.answer(text)
            if known:
                return known, "meme"
            query = memes.topic(text)
            if query and "web" in version.skills:
                try:
                    found = self._web(query, attachments, raise_errors=True)
                except net.NetError as e:
                    return net.explain(e, "найти этот мем в интернете") + " В моей базе его пока нет.", "meme"
                if found:
                    return found[0], "meme"
            return ("Этого мема пока нет в моей базе. Спросите иначе («что за мем …» с точным названием) "
                    "или включите нейросеть — она поищет и объяснит."), "meme"

        # ---- город, посёлок, деревня: население, достопримечательности, фото, погода, местное время
        place_req = places.kind(text) if not codeai.is_build_request(text) else None
        if place_req:
            focus, phrase = place_req
            topic = encyclopedia.lookup(phrase)
            if topic and not places.is_settlement(topic["desc"]) and focus != "sights":
                # страна, регион, река — отвечает энциклопедия (там и население)
                return self._known(encyclopedia.reply("что такое " + phrase), attachments), "encyclopedia"
            if "web" in version.skills:
                try:
                    found = places.card(phrase, focus)
                except net.NetError as e:
                    found = None
                    offline_note = net.explain(e, "узнать про это место в интернете")
                else:
                    offline_note = None
                if found:
                    attachments.extend(dict(p, type="photo") for p in found[1])
                    return found[0], "place"
                known = encyclopedia.reply("что такое " + phrase)
                if known:
                    return self._known(known, attachments) + (f"\n\n*{offline_note}*" if offline_note else ""), "encyclopedia"
                if offline_note:
                    return offline_note, "place"
                return (f"Не нашёл место «{phrase}». Уточните область или район: «расскажи о посёлке {phrase} Минского района»."), "place"
            known = encyclopedia.reply("что такое " + phrase)
            if known:
                return self._known(known, attachments), "encyclopedia"

        # ---- разговор: стихи, советы фильмов и книг, поддержка
        if talk.is_poem_request(text) and not creative.is_slides_request(text):
            return talk.poem(text), "poem"
        if talk.is_recommend_request(text):
            return talk.recommend(text), "recommend"
        feeling = talk.support(text)
        if feeling:
            return feeling, "support"

        # ---- синтаксис: «как сделать цикл в javascript», «функция на c++», «класс на kotlin»
        if not codeai.extract_code(text)[0] and codelib.find_task(text) in (None, "hello", "class"):
            example = syntax.answer(text)
            if example:
                return example, "proglang"

        # ---- «переведи 100 км в мили», «сколько секунд в часе» — посчитать, а не писать программу
        if "convert" in version.skills:
            converted = skills.converter(text)
            if converted:
                return converted, "skill"

        # ---- 100+ точных функций: математика, деньги, здоровье, время, текст, справочник, игры (toolbox, facts, games)
        if not codeai.is_build_request(text) and not online.explicit_search(text):  # «найди …» — это интернет
            reply, cat = toolbox.find(text, play)
            if reply:
                return reply, "game" if cat == games.CAT else "tool"

        # ---- «сделай сайт / игру / приложение» — это код, даже если в просьбе есть «погода» или «валюты»
        building = codeai.is_build_request(text)
        if building or (session.get("site") and webgen.is_edit(text) and not creative.is_image_request(text)):
            if "code" not in version.skills:
                if building:
                    return "Писать программы и сайты умеют Rai Pro Plus, Pro Sun и Pro Quasar — переключите версию сверху.", "code"
            else:
                result = codeai.chat(text, version, session)
                if result and result.get("code"):
                    self._code_attachment(result, attachments)
                    return result["answer"], "code"
                if building:
                    return codelib.help_text(), "code"

        # ---- навыки с интернетом
        # «переведи 100 км в мили» — это конвертер, а не переводчик
        if "translate" in version.skills and online.is_translate_request(text) and not (
                "convert" in version.skills and skills.converter(text)):
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
        if "code" not in version.skills and (codeai.extract_code(text)[0] or codeai.known_program(text)):
            return "Проверять и писать код умеют Rai Pro Plus, Pro Sun и Pro Quasar — переключите версию сверху.", "code"
        if "code" in version.skills:
            task = codelib.find_task(text)
            if codeai.extract_code(text)[0] or (task and task != "hello") or not code_answer or codeai.known_program(text):
                result = codeai.chat(text, version, session)
                if result:
                    if result.get("code"):
                        self._code_attachment(result, attachments)
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
        # Энциклопедия: ~10 000 тем из Википедии — «кто такой Пушкин», «расскажи о Французской революции»
        known = None if code_answer else encyclopedia.reply(text, explicit_only=True)
        if known:
            return self._known(known, attachments), "encyclopedia"

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
            known = encyclopedia.reply(text)  # просто название темы: «Жираф», «теория относительности»
            if known:
                return self._known(known, attachments), "encyclopedia"

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
                found, note = None, ("\n\n*Поиск в интернете в этом окне недоступен — на сайте [rai.rteam.info](https://rai.rteam.info) он работает.*"
                                     if net.SANDBOX else "\n\n*Поискать в интернете не получилось: нет связи.*")
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
    def _known(found, attachments):
        """Ответ энциклопедии; её картинка (из Википедии) — фото к ответу."""
        if found.get("photo"):
            attachments.append(dict(found["photo"], type="photo"))
        return found["text"]

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
            return net.explain(e, "поискать в интернете"), "web"
        if not found:
            return None
        reply, extra = found
        attachments.extend(extra)
        return reply, "web"

    def _slides(self, version, text, attachments):
        req = creative.parse_deck_request(text)
        topic = req["topic"] or (" и ".join(req["compare"]) if req["compare"] else "")
        theme = creative.deck_theme(text)
        online_ok = "web" in version.skills
        results = self.search(version, topic, limit=4, correct=False) if topic else []
        found = [self.intents[k] for k, score in results if score >= version.threshold * 0.8]
        big = version.detailed
        found = found[:4] if big else found[:2]
        if len(found) < 2 and topic:
            found += self._glossary_for(topic, limit=(6 if big else 3) - len(found))
        photo, photos, notes, page, offline = None, [], [], None, False

        def web(fn, *args):
            nonlocal offline
            if offline or not online_ok:
                return None
            try:
                return fn(*args)
            except net.NetError:
                offline = True
                return None

        if topic and online_ok:
            # Главный материал — статья из интернета целиком, по разделам (а своя база — в дополнение)
            page = web(online.wiki_page, topic)
            if page and not online._relevant(topic, page["title"] + " " + page["lead"][:800]):
                page = None
        web_articles = []
        if page:
            photo = page["image"]
            web_articles.append({"title": page["title"], "answers": [page["lead"]], "web": True,
                                 "blocks": creative.web_blocks(page["title"], page["lead"], first=True)})
            for sec in page["sections"]:
                web_articles.append({"title": sec["title"], "answers": [sec["text"]], "web": True,
                                     "blocks": creative.web_blocks(sec["title"], sec["text"])})
            if set(nlp.tokens(topic)) <= set(nlp.tokens(page["title"])) or len(topic.split()) > 1:
                topic = page["title"]  # «эйфелеву башню» -> «Эйфелева башня», «о солнечной системе» -> «Солнечная система»
        # Разделы, которые попросили: сначала ищем в статье, потом отдельной статьёй
        chosen = []
        for want in req["sections"]:
            words = set(nlp.tokens(want))
            hit = next((a for a in web_articles if words & set(nlp.tokens(a["title"]))), None)
            if not hit:
                extra = None
                for query in (want, f"{want} {topic}".strip()):
                    art = web(online.web_article, query)
                    if art and online._relevant(want, art["title"]):
                        extra = art
                        break
                if extra:
                    hit = {"title": want[:1].upper() + want[1:], "answers": [extra["text"]], "web": True,
                           "blocks": creative.web_blocks(want[:1].upper() + want[1:], extra["text"], first=True)}
                    photos.append(extra["image"]) if extra.get("image") else None
            if hit:
                chosen.append(hit)
            else:
                notes.append(f"про «{want}» материала не нашёл")
        if web_articles or chosen:
            # порядок = приоритет: обзор, заказанные разделы, своя база (там примеры кода), остальные разделы статьи
            # своя база — только то, что точно про эту тему (а не «Операционная система» для «Солнечной системы»)
            want_words = set(nlp.tokens(topic))
            found = [a for a in found if a.get("title") != page["title"] and
                     want_words <= set(nlp.tokens(a.get("title", "") + " " + a["answers"][0][:300]))] if page else found
            overview = [a for a in web_articles[:1] if a not in chosen]
            others = [a for a in web_articles[1:] if a not in chosen]
            mixed = []
            for k in range(max(len(others), len(found))):  # разделы статьи вперемешку со своей базой
                mixed += others[k:k + 1] + found[k:k + 1]
            found = overview + chosen + mixed
        elif topic and online_ok and len(found) < 2:
            art = web(online.web_article, topic)
            if art:
                photo = art["image"]
                found.append({"title": art["title"], "answers": [art["text"]], "web": True})
                if set(nlp.tokens(topic)) <= set(nlp.tokens(art["title"])):
                    topic = art["title"]
        if req["pictures"] != "none" and page:
            photos = [p["url"] for p in (web(online.wiki_images, page["title"], page["lang"]) or [])] + photos
        # Отдельно заказанные слайды: сравнение, цитата, таблица
        compare = None
        if req["compare"]:
            sides = []
            for name in req["compare"]:
                art = web(online.web_article, name)
                if art:
                    side = {"title": art["title"], "text": art["text"]}
                else:  # без интернета — из своего словаря
                    local = next((a for form in _word_forms(name) for a in self._glossary_for(form, 1)), None)
                    side = {"title": local["title"], "text": local["answers"][0]} if local else {"title": name, "text": ""}
                items = [creative._cap(creative._short(x.replace("**", ""), 110)) for x in creative._sentences(side["text"])[:3]]
                sides.append({"title": creative._cap(side["title"]), "items": items})
            if all(x["items"] for x in sides):
                compare = {"kind": "compare", "title": f"{sides[0]['title']} и {sides[1]['title']}", "left": sides[0], "right": sides[1]}
                if not req["topic"]:
                    topic = compare["title"]
                    for name in req["compare"]:
                        found += [a for a in next((g for g in (self._glossary_for(f, 1) for f in _word_forms(name)) if g), [])
                                  if a not in found]
        quote = web(online.wiki_quote, topic) if "quote" in req["want"] and topic else None
        found = [a if a.get("blocks") is not None else dict(a, blocks=creative._article_blocks(a)) for a in found]
        material = [b for a in found for b in a["blocks"]]
        extras, missing = creative.extra_blocks(req["want"], material, quote=quote, compare=compare)
        for kind in ("timeline", "stats"):  # попросили хронологию или цифры — они обязательно попадут в презентацию
            block = next((b for b in material if b["kind"] == kind), None) if kind in req["want"] else None
            if block:
                extras.insert(0, block)
                for a in found:
                    if block in a["blocks"]:
                        a["blocks"] = [b for b in a["blocks"] if b is not block]
        if missing:
            notes.append("не нашёл " + ", ".join(missing))

        title = creative.nominative(topic) if topic else "Rteam"
        if re.fullmatch(r"[a-z0-9+#]{1,5}", title, re.I):
            title = title.upper()  # html -> HTML, php -> PHP
        elif found and found[0].get("key_match") and len(title.split()) == 1:
            title = found[0]["title"]  # «котов» -> «Кошка»
        limit = req["count"] or version.slide_limit
        deck = creative.make_slides(title, found, max_slides=limit, theme=theme,
                                    photo=photo if req["pictures"] != "none" else None, extras=extras,
                                    photos=photos, pictures=req["pictures"]) if found or extras else None
        if not deck:
            hint = "" if online_ok else " Rai Pro, Pro Plus и Pro Sun ещё и ищут материал в интернете."
            if offline:
                hint = " Поискать в интернете не получилось: нет связи."
            return (f"Про «{topic or text}» я пока не нашёл материала, поэтому презентацию не сделал — "
                    f"не хочу показывать пустые слайды.{hint} Попробуйте другую тему, например «презентация про космос».")
        attachments.append(deck)
        n = len(deck["slides"])
        count = f"{n} " + ("слайд" if n % 10 == 1 and n % 100 != 11 else
                          "слайда" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "слайдов")
        colors = " в ваших цветах" if theme["custom"] else ""
        done = []
        if page:
            done.append(f"текст — из Википедии ([{page['title']}]({page['link']}))")
        if any(s.get("pic") for s in deck["slides"]):
            done.append("фото — из интернета")
        kinds = {s["kind"] for s in deck["slides"]}
        names = {"timeline": "хронология", "stats": "цифры", "table": "таблица", "quote": "цитата", "compare": "сравнение"}
        done += [names[k] for k in names if k in kinds]
        if req["count"] and n < req["count"]:
            notes.append(f"материала хватило на {count} из {req['count']}")
        if offline:
            notes.append("интернет был недоступен, собрал из своей базы знаний")
        tail = (" В ней: " + "; ".join(done) + ".") if done else ""
        tail += (" *Заметки: " + "; ".join(notes) + ".*") if notes else ""
        return (f"Готово: презентация **«{deck['title']}»**{colors}, {count}.{tail} "
                "Смотрите на весь экран, скачивайте в PowerPoint, файлом или ZIP-архивом.")

    # ------------------------------------------------------------ анализ по ссылке

    def _link(self, version, text, attachments, data=None):
        """Разбор видео, аккаунта, канала или сайта по ссылке: цифры, вовлечённость, советы."""
        if "web" not in version.skills:
            return ("Разбирать ссылки (TikTok, YouTube, Telegram, Instagram, сайты) умеют версии с интернетом: "
                    "Rai Pro, Pro Plus, Pro Sun и Pro Quasar — переключите версию сверху.")
        url = social.find_link(text)
        if data is None:
            try:
                data = social.fetch(url)
            except net.NetError as e:
                if net.SANDBOX or not (net.PROXY or net.SEARCH_URL or net.SAME_ORIGIN):
                    return (f"Чтобы разобрать {url}, нужен свой сервер Rai: анализ по ссылке работает на сайте "
                            "[rai.rteam.info](https://rai.rteam.info) — там net.php читает TikTok, YouTube, Telegram, Instagram, VK и любые сайты.")
                return net.explain(e, "открыть ссылку") + "\n\nПроверьте, что ссылка открывается без входа в аккаунт."
        if data.get("error"):
            return (f"Не получилось открыть ссылку {url}: {data['error']}.\n\nПроверьте, что ссылка открывается без входа в аккаунт "
                    "(закрытые профили и приватные видео посмотреть нельзя).")
        text, extra = social.report(data)
        attachments.extend(extra)
        return text

    # ------------------------------------------------------------ скриншоты и запись экрана

    def _screen(self, version, message, session, attachments):
        """Разобрать текст со скриншота: показать его и ответить на вопросы, задания, примеры и код."""
        question, _, raw = message.partition(SCREEN_MARK)
        question = question.strip()
        raw, seen_data = sight.split(raw)  # что увидело «зрение» в браузере: небо, солнце, люди, животные…
        seen = sight.describe(seen_data, question) if seen_data else None
        lines = []
        for line in raw.replace("\r", "").split("\n"):
            line = re.sub(r"[ \t]+", " ", line).strip(" |_~")
            letters = sum(ch.isalnum() for ch in line)
            if line and (letters >= 2 and letters / max(1, len(line)) > 0.45 or _MATH_LINE.match(line)):
                lines.append(line)
        text = "\n".join(lines).strip()
        if not text:
            if seen:
                return seen
            return ("На изображении не нашёл текста. Я читаю текст со скриншотов (русский и английский): вопросы, "
                    "задания, примеры, код. Попробуйте скриншот покрупнее или без размытия.")
        out = ([seen, ""] if seen else []) + ["## Текст со скриншота", "", "\n".join("> " + l for l in lines[:40])]
        if len(lines) > 40:
            out.append(f"> … ещё {len(lines) - 40} строк")
        low_q = question.lower()

        # просьбы про весь текст
        if re.search(r"перевед|translate", low_q):
            lang = re.search(r"на\s+([а-я]+(?:ий|ый|кий))", low_q)
            out += ["", "## Перевод", "", online.translate(f"переведи на {lang.group(1) if lang else 'английский'}: {text[:1500]}")]
            return "\n".join(out)

        code = "\n".join(lines)
        code_lines = sum(1 for l in lines if not _OPTION_RE.match(l) and not _MATH_LINE.match(l) and re.search(
            r"[{};]\s*$|^\s*(?:def|class|import|from|for|if|elif|else|while|return|print|function|const|let|var|#include|public|echo)\b"
            r"|^\s*[A-Za-z_]\w*\s*(?:\[.*\])?\s*[-+*/]?=\s*\S|^\s*<\/?[a-z][\w-]*[ >]|\w\(.*\)\s*$", l))
        looks_code = code_lines >= max(2, (len(lines) + 1) // 2)
        if looks_code and "code" in version.skills:
            lang = codeai.detect_lang(code)
            result = codeai.run_action("check", code, lang)
            out += ["", "## Код на скриншоте", "", result["answer"]]
            if not result.get("issues"):
                out += ["", codeai.explain(code, result["lang"])]
            return "\n".join(out)

        # вопросы (с вариантами ответов) и примеры
        tasks, current = [], None
        for line in lines:
            if _MATH_LINE.match(line) and re.search(r"\d\s*[-+*/×÷:^]\s*\d", line):
                tasks.append({"q": re.sub(r"^\s*\d{1,2}\s*[.)]\s+", "", line).rstrip("=? "), "options": [], "math": True})
                current = None
            elif re.search(r"\d\s*[-+*/×÷^]\s*\d", line) and re.search(r"(?:=|\?)\s*$|сколько|вычисл|посчита|реши", line, re.I):
                expr = re.search(r"[\d(][\d\s+\-*/×÷^().,]*\d\)?", line)  # «Сколько будет 12 * 7 =» -> «12 * 7»
                tasks.append({"q": expr.group(0).strip(), "options": [], "math": True, "label": _QUESTION_START.sub("", line).rstrip("=? ")})
                current = None
            elif line.endswith("?") or re.match(r"^\s*(?:вопрос|задани)", line, re.I):
                current = {"q": _QUESTION_START.sub("", line), "options": []}
                tasks.append(current)
            elif current is not None and _OPTION_RE.match(line) and len(current["options"]) < 8:
                current["options"].append(re.sub(r"^\s*(?:[a-dа-гA-DА-Г]|\d{1,2})\s*[).]\s*|^\s*[-•○□☐◯]\s*", "", line))
        answers = []
        for n, t in enumerate(tasks[:12], 1):
            q = t["q"].replace("×", "*").replace("÷", "/") if t.get("math") else t["q"]
            title = (t.get("label") or t["q"]).replace("*", "×")  # «*» ломает жирный заголовок в markdown
            reply, intent = self._answer_one(version, q, dict(session), [])
            reply_text = re.sub(r"\s+", " ", re.sub(r"\*\*|`+|^#+\s*|^>\s*", "", reply, flags=re.M)).strip()
            unknown = intent in (None, "unknown") or reply_text.startswith("Я пока не знаю")
            if t["options"]:
                words = set(nlp.tokens(reply_text))
                scored = sorted(((len(words & set(nlp.tokens(o))), i) for i, o in enumerate(t["options"])), reverse=True)
                if not unknown and scored and scored[0][0] > 0:
                    pick = t["options"][scored[0][1]]
                    answers.append(f"**{n}. {title}**\n\n**Ответ:** {pick}\n\n{reply_text[:300]}")
                else:
                    answers.append(f"**{n}. {title}**\n\nНе уверен в ответе — в моей базе знаний этого нет. Варианты: " + "; ".join(t["options"]))
            elif unknown:
                answers.append(f"**{n}. {title}**\n\nНе знаю ответа на этот вопрос.")
            else:
                answers.append(f"**{n}. {title}**\n\n{reply.strip()}")
        if answers:
            out += ["", f"## Ответы ({len(answers)})", "", "\n\n".join(answers)]
        elif question and not re.search(r"что (здесь|тут) написан|прочитай|распознай|текст", low_q):
            reply, _ = self._answer_one(version, question + " " + text[:600], dict(session), attachments)
            out += ["", "## Ответ", "", reply]
        else:
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", " ".join(lines)) if len(s) > 20]
            if sentences:
                out += ["", "## Коротко", "", "\n".join("- " + s for s in sentences[:3])]
            terms = [d for d in (self.define(version, w, exact_only=True) for w in dict.fromkeys(
                     w for w in re.findall(r"[A-Za-zА-Яа-яЁё+#]{3,}", text) if len(w) > 3)) if d][:3]
            if terms:
                out += ["", "## Термины", "", "\n\n".join(terms)]
        return "\n".join(out)

    @staticmethod
    def _code_attachment(result, attachments):
        attachments.append({"type": "code", "lang": result["lang"], "code": result["code"],
                            "filename": result.get("filename") or "main." + codeai.EXT_OF.get(result["lang"], "txt"),
                            "title": result.get("title") or "Код", "site": bool(result.get("site"))})

    def _site_facts(self, topic):
        """Тексты о теме для сайта «про X»: словарь, база знаний, а если пусто — статья из интернета."""
        texts = [a["answers"][0].replace("{name}", "") for a in self._glossary_for(topic, limit=3)]
        want = set(nlp.tokens(topic)) - nlp.GENERIC
        for key, score in self.search(_SITE_VERSION, topic, limit=3, correct=False):
            intent = self.intents[key]
            if score >= 0.3 and want & set(nlp.tokens(intent.get("title", "") + " " + " ".join(intent["patterns"]))):
                texts.append(intent["answers"][0].replace("{name}", ""))
        if not texts:
            try:
                art = online.web_article(topic, langs=("ru",))
            except net.NetError:
                art = None
            if art:
                texts.append(art["text"])
        return texts

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
        if version.memory and subject:
            lines.append(f"Научите меня: напишите «запомни, что {subject} — это …», и я запомню.")
        lines.append("Включите **Rai Нейро** (кнопка сверху) — нейросеть ответит на любой вопрос. "
                     "Или напишите «найди в интернете …», или «что ты умеешь».")
        return "\n\n".join(lines)


def _word_forms(word):
    """Слово и его вероятная начальная форма: «кошек» -> «кошка», «котов» -> «кот», «собак» -> «собака»."""
    w = word.strip()
    forms = [w]
    for end, repl in (("ек", "ка"), ("ов", ""), ("ев", ""), ("ей", "ь"), ("ы", ""), ("и", "а"), ("ам", "а")):
        if w.endswith(end) and len(w) - len(end) >= 3:
            forms.append(w[:len(w) - len(end)] + repl)
    if re.search(r"[бвгджзклмнпрстфхцчшщ]$", w):
        forms.append(w + "а")
    return forms


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


def _init_site_version():
    global _SITE_VERSION
    from versions import VERSIONS
    _SITE_VERSION = VERSIONS["pro-quasar"]


_init_site_version()
