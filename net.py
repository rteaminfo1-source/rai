"""Запросы в интернет для Rai: одинаково работают на сервере (urllib) и в браузере (Pyodide)."""

import json
import sys
import time
import urllib.parse
import urllib.request

USER_AGENT = "RaiBot/1.0 (+https://github.com/rteaminfo1-source/rai)"
IN_BROWSER = sys.platform == "emscripten"

_cache = {}


class NetError(Exception):
    """Не получилось получить данные из интернета."""


def url(base: str, **params) -> str:
    return base + ("?" + urllib.parse.urlencode(params) if params else "")


def fetch_text(address: str, timeout: float = 10) -> str:
    try:
        if IN_BROWSER:
            # Синхронный запрос браузера: Python в Pyodide не умеет открывать сокеты сам.
            from pyodide.http import open_url
            return open_url(address).getvalue()
        req = urllib.request.Request(address, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:  # сеть, DNS, таймаут, CORS в браузере
        raise NetError(str(e) or e.__class__.__name__) from e


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
