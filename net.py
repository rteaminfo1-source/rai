"""Запросы в интернет для Rai: одинаково работают на сервере (urllib) и в браузере (Pyodide)."""

import json
import os
import sys
import time
import urllib.parse
import urllib.request

USER_AGENT = "RaiBot/1.0 (+https://github.com/rteaminfo1-source/rai)"
IN_BROWSER = sys.platform == "emscripten"

_cache = {}
# Посредник на хостинге (rai.rteam.info/net.php). Страница задаёт его сама, если он доступен:
# тогда браузер ходит в интернет через свой сайт, и чужие сервисы не блокируются (CORS, фильтры).
PROXY = ""


class NetError(Exception):
    """Не получилось получить данные из интернета."""


def url(base: str, **params) -> str:
    return base + ("?" + urllib.parse.urlencode(params) if params else "")


def fetch_text(address: str, timeout: float = 10) -> str:
    try:
        if IN_BROWSER:
            return _browser_get(address)
        req = urllib.request.Request(address, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:  # сеть, DNS, таймаут, CORS в браузере
        raise NetError(str(e) or e.__class__.__name__) from e


def _xhr(address: str) -> str:
    """Синхронный запрос браузера: Python в Pyodide не умеет открывать сокеты сам."""
    from js import XMLHttpRequest
    req = XMLHttpRequest.new()
    req.open("GET", address, False)
    req.send(None)
    if req.status != 200:
        raise NetError(f"ответ {req.status}")
    return str(req.responseText)


def _browser_get(address: str) -> str:
    """Сначала через посредник на хостинге, если он есть, потом напрямую."""
    tries = ([PROXY + ("&" if "?" in PROXY else "?") + "url=" + urllib.parse.quote(address, safe="")] if PROXY else []) + [address]
    errors = []
    for target in tries:
        try:
            return _xhr(target)
        except Exception as e:  # noqa: BLE001 — пробуем следующий путь
            errors.append(str(e) or e.__class__.__name__)
    raise NetError("; ".join(errors))


# На сервере (app.py) поиск идёт через net.php хостинга, если задано RAI_SEARCH_URL=https://rai.rteam.info/net.php
SEARCH_URL = os.environ.get("RAI_SEARCH_URL", "")


def search(query: str, limit: int = 6):
    """Поиск в интернете (Google / DuckDuckGo через посредник net.php): [{"title", "url", "snippet"}].

    Без посредника возвращает [] — тогда Rai ищет только в Википедии.
    """
    base = PROXY or SEARCH_URL
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
