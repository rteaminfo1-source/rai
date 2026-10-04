"""Запросы в интернет для Rai: одинаково работают на сервере (urllib) и в браузере (Pyodide)."""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "RaiBot/1.0 (+https://github.com/rteaminfo1-source/rai)"
IN_BROWSER = sys.platform == "emscripten"

_cache = {}
# Посредник на хостинге (rai.rteam.info/net.php). Страница задаёт его сама, если он доступен:
# тогда браузер ходит в интернет через свой сайт, и чужие сервисы не блокируются (CORS, фильтры).
PROXY = ""
# net.php рядом со страницей — запасная попытка, если посредник ещё не нашёлся (медленный хостинг)
SAME_ORIGIN = ""
# Страница открыта там, где интернет закрыт (окно просмотра Claude): не ждём сбоев, сразу объясняем
SANDBOX = False
# Сбои сети за текущий ответ: страница по ним решает, может ли помочь нейросеть (перевод, знания)
PROBLEMS = []
HOME = "https://rai.rteam.info"


class NetError(Exception):
    """Не получилось получить данные из интернета. offline — связи нет совсем (а не сервис ответил ошибкой)."""

    def __init__(self, message="", offline=False):
        super().__init__(message)
        self.offline = offline
        PROBLEMS.append(message)


def explain(error, what: str) -> str:
    """Понятное сообщение о сбое сети для человека — без технических подробностей."""
    if SANDBOX:
        return (f"Не получилось {what}: в этом окне просмотра интернет закрыт. Откройте Rai на сайте "
                f"[rai.rteam.info]({HOME}) — там погода, курсы, перевод, поиск и анализ ссылок работают через свой сервер.")
    if getattr(error, "offline", False):
        tip = "" if PROXY else (" Если Rai открыт на вашем сайте, проверьте, что на хостинге есть файл **net.php** "
                                "(через него Rai ходит в интернет).")
        return f"Не получилось {what}: нет связи с интернетом или сервис сейчас недоступен. Попробуйте ещё раз через минуту.{tip}"
    return f"Не получилось {what}: сервис ответил ошибкой ({error}). Попробуйте ещё раз чуть позже."


def url(base: str, **params) -> str:
    return base + ("?" + urllib.parse.urlencode(params) if params else "")


def fetch_text(address: str, timeout: float = 10) -> str:
    if IN_BROWSER:
        return _browser_get(address)
    try:
        req = urllib.request.Request(address, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:  # сервис ответил, но с ошибкой
        raise NetError(f"ответ {e.code}") from e
    except Exception as e:  # сеть, DNS, таймаут
        raise NetError(str(e) or e.__class__.__name__, offline=True) from e


class _Status(Exception):
    """Сервер ответил, но не 200."""


def _xhr(address: str) -> str:
    """Синхронный запрос браузера: Python в Pyodide не умеет открывать сокеты сам."""
    if SANDBOX:
        raise NetError("интернет закрыт", offline=True)
    from js import XMLHttpRequest
    req = XMLHttpRequest.new()
    req.open("GET", address, False)
    try:
        req.send(None)
    except Exception as e:  # noqa: BLE001 — нет связи, CORS, политика безопасности страницы
        raise NetError("нет связи", offline=True) from e
    if req.status != 200:
        message = f"ответ {req.status}"
        try:
            message = json.loads(str(req.responseText)).get("error") or message
        except (ValueError, AttributeError):
            pass
        raise NetError(message)
    return str(req.responseText)


def _via(proxy: str, address: str) -> str:
    return proxy + ("&" if "?" in proxy else "?") + "url=" + urllib.parse.quote(address, safe="")


def _browser_get(address: str) -> str:
    """Сначала через посредник на хостинге, потом напрямую, потом — через net.php рядом со страницей."""
    tries = ([_via(PROXY, address)] if PROXY else []) + [address]
    if not PROXY and SAME_ORIGIN:
        tries.append(_via(SAME_ORIGIN, address))
    errors, offline = [], True
    for target in tries:
        try:
            return _xhr(target)
        except NetError as e:
            errors.append(str(e))
            offline = offline and e.offline
            PROBLEMS.pop() if PROBLEMS else None  # копим одну итоговую ошибку, а не каждую попытку
    raise NetError("; ".join(errors), offline=offline)


# На сервере (app.py) поиск идёт через net.php хостинга, если задано RAI_SEARCH_URL=https://rai.rteam.info/net.php
SEARCH_URL = os.environ.get("RAI_SEARCH_URL", "")


def search(query: str, limit: int = 6):
    """Поиск в интернете (Google / DuckDuckGo через посредник net.php): [{"title", "url", "snippet"}].

    Без посредника возвращает [] — тогда Rai ищет только в Википедии.
    """
    base = PROXY or SEARCH_URL or SAME_ORIGIN
    if not base:
        return []
    address = base + ("&" if "?" in base else "?") + urllib.parse.urlencode({"search": query[:300], "n": limit})
    now = time.time()
    if address in _cache and now - _cache[address][0] < 3600:
        return _cache[address][1]
    text = _xhr(address) if IN_BROWSER else fetch_text(address)
    try:
        data = json.loads(text)
    except ValueError as e:
        raise NetError("поиск вернул не JSON") from e
    found = [r for r in (data.get("results") or []) if isinstance(r, dict) and r.get("title") and
             str(r.get("url", "")).startswith(("https://", "http://"))][:limit]
    _cache[address] = (now, found)
    return found


def read(page_url: str) -> dict:
    """Текст страницы из интернета через посредник net.php (?read=): {"url", "title", "text"} — без меню и скриптов."""
    base = PROXY or SEARCH_URL or SAME_ORIGIN
    if not base:
        raise NetError("нет посредника net.php", offline=True)
    address = base + ("&" if "?" in base else "?") + urllib.parse.urlencode({"read": page_url[:2000]})
    now = time.time()
    if address in _cache and now - _cache[address][0] < 3600:
        return _cache[address][1]
    text = _xhr(address) if IN_BROWSER else fetch_text(address, timeout=20)
    try:
        data = json.loads(text)
    except ValueError as e:
        raise NetError("посредник вернул не JSON") from e
    if not isinstance(data, dict) or data.get("error") or not data.get("text"):
        raise NetError(str((data or {}).get("error") or "пустая страница"))
    _cache[address] = (now, data)
    return data


def social(url: str) -> dict:
    """Данные для анализа по ссылке (TikTok, YouTube, Telegram, Instagram, VK, X, сайты) — через посредник на хостинге."""
    base = PROXY or SEARCH_URL or SAME_ORIGIN
    if not base:
        raise NetError("нет посредника net.php", offline=True)
    address = base + ("&" if "?" in base else "?") + urllib.parse.urlencode({"social": url[:2000]})
    text = _xhr(address) if IN_BROWSER else fetch_text(address, timeout=40)
    try:
        data = json.loads(text)
    except ValueError as e:
        raise NetError("посредник вернул не JSON") from e
    if not isinstance(data, dict) or data.get("error"):
        raise NetError(str((data or {}).get("error") or "нет данных"))
    return data


def fetch_json(address: str, ttl: float = 0):
    """Скачать JSON. ttl > 0 — хранить ответ в памяти столько секунд."""
    now = time.time()
    if ttl and address in _cache and now - _cache[address][0] < ttl:
        return _cache[address][1]
    text = fetch_text(address)
    try:
        data = json.loads(text)
    except ValueError as e:
        raise NetError("сервис вернул не JSON") from e
    if ttl:
        _cache[address] = (now, data)
    return data
