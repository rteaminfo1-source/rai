"""Счётчик токенов Rai и лимиты по тарифам.

Токен — маленький кусочек текста (примерно короткое слово или часть длинного слова). Точного
токенизатора нейросети у нас нет, поэтому токены оцениваем по буквам: кириллица в токенизаторах
плотнее латиницы. Главное — считать ОДИНАКОВО везде (здесь, в Python, и в браузере — tokens.js),
чтобы пользователю было видно, сколько стоит каждый ответ, и работал лимит по тарифу.

Что видит пользователь:
  • сколько токенов стоил ответ (запрос + ответ + размышление движка),
  • сколько потрачено за день и сколько осталось по его тарифу,
  • система одна и та же в чате, слайдах и коде.
"""

import math
import re

# слово латиницей, слово кириллицей, число или одиночный символ (знак препинания — тоже токен)
_PIECE = re.compile(r"[A-Za-z]+|[А-Яа-яЁё]+|[0-9]+|\S", re.UNICODE)


def count(text):
    """Приблизительное число токенов в тексте (как в tokens.js — одинаково)."""
    n = 0
    for m in _PIECE.finditer(text or ""):
        w = m.group(0)
        c = w[0]
        if ("а" <= c <= "я") or ("А" <= c <= "Я") or c in "ёЁ":
            n += max(1, math.ceil(len(w) / 3))      # кириллица — ~3 буквы на токен
        elif ("a" <= c <= "z") or ("A" <= c <= "Z"):
            n += max(1, math.ceil(len(w) / 4))       # латиница — ~4 буквы на токен
        elif "0" <= c <= "9":
            n += max(1, math.ceil(len(w) / 3))
        else:
            n += 1                                    # один символ (знак) — один токен
    return n


# Во сколько раз уровень размышления «дороже»: чем выше, тем больше Rai читает и перепроверяет.
LEVEL_COST = {"low": 1.0, "medium": 2.0, "high": 3.5, "code": 4.0, "extra": 6.0, "ultra": 10.0}
DEFAULT_COST = 2.0

# Дневной лимит токенов по версии (тарифу). Выше тариф — больше лимит. У Pro Sun — почти без границ.
# Дневной лимит токенов по тарифу. 0 = без ограничений (бесконечно). Выше тариф — больше токенов,
# у топового (Quasar / «Ультра») — безлимит.
PLAN_LIMIT = {
    "pro-fast": 100_000,
    "pro": 300_000,
    "pro-plus": 1_000_000,     # Плюс — больше
    "pro-sun": 3_000_000,      # Премиум — ещё больше
    "pro-quasar": 0,           # Ультра — бесконечно
}
DEFAULT_LIMIT = 300_000
UNLIMITED = 0


def limit_for(version_id):
    """Дневной лимит токенов для версии (0 — безлимит)."""
    return PLAN_LIMIT.get(version_id, DEFAULT_LIMIT)


def reasoning_cost(prompt_tokens, answer_tokens, level):
    """Сколько токенов ушло на размышление движка (зависит от выбранного уровня)."""
    cost = LEVEL_COST.get((level or "").lower(), DEFAULT_COST)
    return int(round((prompt_tokens + answer_tokens) * (cost - 1) * 0.5))


def usage(prompt="", answer="", extra_text="", level=None, version_id=None, reasoning=None):
    """Стоимость ответа в токенах: {prompt, answer, reasoning, total, level, limit}."""
    p = count(prompt)
    a = count(answer) + count(extra_text)
    if reasoning is None:
        reasoning = reasoning_cost(p, a, level)
    reasoning = max(0, int(reasoning))
    return {"prompt": p, "answer": a, "reasoning": reasoning, "total": p + a + reasoning,
            "level": (level or ""), "limit": limit_for(version_id)}


def human(n):
    """123456 -> «123 456»."""
    try:
        return f"{int(n):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(n)
