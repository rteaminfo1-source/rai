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

import nlp
import skills
from versions import Version

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_PATH = os.environ.get("RAI_KNOWLEDGE_PATH", os.path.join(BASE_DIR, "knowledge.json"))
LEARNED_PATH = os.environ.get("RAI_LEARNED_PATH", os.path.join(BASE_DIR, "learned.json"))

MAX_MESSAGE_CHARS = int(os.environ.get("RAI_MAX_MESSAGE_CHARS", "4000"))
MAX_FACTS = 50

_NAME_RE = re.compile(
    r"(?:меня зовут|мое имя|моё имя|зови меня|называй меня|my name is)\s+([A-Za-zА-Яа-яЁё-]{2,30})",
    re.I,
)
_ASK_NAME_RE = re.compile(r"как меня зовут|ты помнишь как меня|мое имя\??$|моё имя\??$|who am i", re.I)
_MORE_RE = re.compile(r"^(а\s+)?(подробнее|ещ[её]|расскажи подробнее|расскажи ещ[её]|продолжай|дальше|и\?)[\s?!.]*$", re.I)
_REMEMBER_RE = re.compile(r"^\s*запомни(?:,)?\s*(?:что|:)?\s*(.+)$", re.I | re.S)
_RECALL_RE = re.compile(r"что ты (?:помнишь|запомнил|знаешь обо мне)|что я тебе говорил", re.I)
_FORGET_RE = re.compile(r"^\s*забудь (?:вс[её]|об? мне)", re.I)


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
    def __init__(self, knowledge_path=KNOWLEDGE_PATH, learned_path=LEARNED_PATH):
        self.knowledge_path = knowledge_path
        self.learned_path = learned_path
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
        speller = nlp.SpellChecker(text for _, text in docs)
        with self._lock:
            self.intents, self.indexes = by_id, indexes
            self.intent_tokens, self.speller = intent_tokens, speller

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

    def search(self, version: Version, text: str, limit: int = 5):
        """Найти подходящие темы: [(id, сходство)], только уверенные совпадения."""
        if version.fuzzy:
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
        if version.multi and not _REMEMBER_RE.match(message):
            parts = [p.strip() for p in re.split(r"(?<=\?)\s+|\n+", message) if p.strip()] or [message]

        answers, intents = [], []
        for part in parts[:5]:
            text, intent = self._answer_one(version, part, session)
            answers.append(text)
            intents.append(intent)

        if len(answers) > 1:
            text = "\n\n".join(f"— {q}\n{a}" for q, a in zip(parts, answers))
        else:
            text = answers[0]
        return {
            "answer": text,
            "version": version.id,
            "version_name": version.name,
            "intent": intents[0] if len(intents) == 1 else intents,
        }

    def _answer_one(self, version: Version, text: str, session: dict):
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

        reply = skills.run(text, version.skills)
        if reply:
            return reply, "skill"

        results = self.search(version, text)
        best = results[0][1] if results else 0.0

        if version.memory:
            fact, score = self._find_fact(text, session)
            if fact and score >= best:
                return f"Вы мне говорили: {fact}.", "memory"

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

        return self._fallback(version, results), None

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

    def _fallback(self, version, results):
        base = "Я пока не знаю ответа на это."
        if version.suggestions:
            titles = [self.intents[k].get("title", k) for k, s in results[:3] if s >= 0.1]
            if titles:
                return base + " Возможно, вы имели в виду:\n" + "\n".join(f"• {t}" for t in titles)
        return base + " Попробуйте спросить иначе или напишите «помощь»."


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
