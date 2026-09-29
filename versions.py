"""Четыре версии Rai: Pro, Pro Fast, Pro Plus, Pro Sun.

Все версии работают на собственном движке, без внешних API.
Отличаются набором возможностей.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Version:
    id: str
    name: str
    description: str
    search: str                 # "keywords" (быстро) или "tfidf" (по смыслу)
    fuzzy: bool                 # понимать опечатки (буквенные триграммы)
    skills: frozenset           # встроенные навыки
    context: bool = False       # помнит имя и тему разговора, «подробнее»
    memory: bool = False        # «запомни, что …» — память фактов
    multi: bool = False         # несколько вопросов в одном сообщении
    detailed: bool = False      # сразу даёт подробный ответ
    suggestions: bool = False   # предлагает похожие вопросы, если не понял
    threshold: float = 0.35     # минимальное сходство для ответа
    code: bool = False          # режим для кода: лучше понимает код, объясняет, проверяет, пишет
    enrich: bool = False        # дополняет короткие ответы фактами из интернета
    slide_limit: int = 8        # сколько слайдов может быть в презентации
    features: list = field(default_factory=list)

    def public(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "features": self.features,
        }


ONLINE = {"weather", "currency", "translate"}
ALL_SKILLS = frozenset({"calc", "time", "convert", "random", "password", "text", "table", "capital", "image", "slides",
                        "web", "code"} | ONLINE)

VERSIONS = {
    "pro": Version(
        id="pro",
        name="Rai Pro",
        description="Основная версия: понимает смысл вопроса, основные навыки.",
        search="tfidf",
        fuzzy=False,
        skills=frozenset({"calc", "time", "convert", "random", "table", "capital", "image", "web"} | ONLINE),
        slide_limit=8,
        threshold=0.35,
        features=["поиск по смыслу", "погода", "валюты", "перевод", "поиск в интернете", "таблицы", "картинки"],
    ),
    "pro-fast": Version(
        id="pro-fast",
        name="Rai Pro Fast",
        description="Самая быстрая версия: поиск по ключевым словам.",
        search="keywords",
        fuzzy=False,
        skills=frozenset({"calc", "time", "capital"} | ONLINE),
        threshold=0.3,
        features=["поиск по ключевым словам", "калькулятор", "погода", "валюты", "перевод"],
    ),
    "pro-plus": Version(
        id="pro-plus",
        name="Rai Pro Plus",
        description="Понимает опечатки, все навыки, картинки и презентации, помнит имя.",
        search="tfidf",
        fuzzy=True,
        skills=ALL_SKILLS,
        context=True,
        suggestions=True,
        threshold=0.3,
        features=["понимает опечатки", "все навыки", "картинки", "презентации", "помнит имя",
                  "«подробнее» по теме", "подсказки"],
    ),
    "pro-sun": Version(
        id="pro-sun",
        name="Rai Pro Sun",
        description="Максимальная версия: память фактов, несколько вопросов сразу, подробные ответы.",
        search="tfidf",
        fuzzy=True,
        skills=ALL_SKILLS,
        context=True,
        memory=True,
        multi=True,
        detailed=True,
        suggestions=True,
        threshold=0.27,
        slide_limit=12,
        features=["всё из Pro Plus", "память фактов («запомни, что …»)",
                  "несколько вопросов сразу", "подробные ответы", "большие презентации"],
    ),
    "pro-quasar": Version(
        id="pro-quasar",
        name="Rai Pro Quasar",
        description="Самая сильная версия: всё из Pro Sun, режим Code, ответы с фактами из интернета, "
                    "презентации до 16 слайдов.",
        search="tfidf",
        fuzzy=True,
        skills=ALL_SKILLS,
        context=True,
        memory=True,
        multi=True,
        detailed=True,
        suggestions=True,
        threshold=0.25,
        code=True,
        enrich=True,
        slide_limit=16,
        features=["всё из Pro Sun", "вкладка Code: запуск, проверка, объяснение и исправление кода",
                  "ответы дополняются фактами из интернета", "презентации до 16 слайдов с фото",
                  "архивы ZIP"],
    ),
}

DEFAULT_VERSION = os.environ.get("RAI_DEFAULT_VERSION", "pro").strip() or "pro"

# Разные написания, которые может прислать сайт: "Pro Fast", "pro_fast", "profast"…
_ALIASES = {key.replace("-", ""): key for key in VERSIONS}


def resolve(version: Optional[str]) -> Optional[Version]:
    """Вернуть версию по id/названию или None, если такой нет."""
    if not version:
        return VERSIONS.get(DEFAULT_VERSION, VERSIONS["pro"])
    key = str(version).strip().lower()
    if key.startswith("rai"):
        key = key[3:]
    key = key.replace(" ", "").replace("_", "").replace("-", "")
    return VERSIONS.get(_ALIASES.get(key, "")) or VERSIONS.get(_ALIASES.get("pro" + key, ""))
