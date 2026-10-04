"""Сравнение двух вещей: «сравни Python и JavaScript», «чем отличается Java от C++», «что лучше кофе или чай»,
«Марс или Венера», «разница между Пушкиным и Лермонтовым», «iPhone vs Android».

Языки программирования — таблица из справочника языков (год, где применяют, особенности, «привет, мир»).
Любые другие темы — из энциклопедии Rai (что это, коротко, раздел). Что-то не знаю — None (ответит кто-то другой).
"""

import re

import encyclopedia
import proglangs

_PAIR_RE = re.compile(
    r"^\s*(?:а\s+)?(?:"
    r"(?:сравни|сравните|сравнить|сравнение|сопоставь)\s+(?P<a1>.+?)\s+(?:и|с|со|и\s+с|vs\.?|против)\s+(?P<b1>.+?)"
    r"|чем\s+(?:отличается|отличаются|отличие|различаются)\s+(?P<a2>.+?)\s+(?:от|и)\s+(?P<b2>.+?)"
    r"|чем\s+(?P<a3>.+?)\s+отлича\w+\s+от\s+(?P<b3>.+?)"
    r"|(?:в\s+ч[её]м\s+)?разница\s+между\s+(?P<a4>.+?)\s+и\s+(?P<b4>.+?)"
    r"|(?:что|кто|какой|какая|какое)\s+(?:лучше|круче|сильнее|полезнее|быстрее|популярнее|выбрать)[,:]?\s+(?P<a5>.+?)\s+или\s+(?P<b5>.+?)"
    r"|(?P<a6>[^?,]+?)\s+или\s+(?P<b6>[^?,]+?)\s*[,:—-]?\s*(?:что|кто|какой|какая)\s+(?:лучше|круче|сильнее|выбрать)"
    r"|(?P<a7>[\w#+.\- ]{2,40}?)\s+(?:vs\.?|против)\s+(?P<b7>[\w#+.\- ]{2,40}?)"
    r")[\s?!.]*$", re.I)
_TAIL = re.compile(r"\s+(?:подробно|кратко|таблицей|в\s+таблице|пожалуйста|для\s+новичка|по\s+пунктам)$", re.I)


def parse(text):
    """(первое, второе) или None."""
    m = _PAIR_RE.match(text or "")
    if not m:
        return None
    for k in range(1, 8):
        a, b = m.group(f"a{k}"), m.group(f"b{k}")
        if a and b:
            a, b = _TAIL.sub("", a.strip(" «»\"'")), _TAIL.sub("", b.strip(" «»\"'"))
            if a and b and a.lower() != b.lower() and len(a) <= 60 and len(b) <= 60:
                return a, b
    return None


def _lang(name):
    return proglangs.find_language(name, strict_short=False)


def _own(uses, other):
    """Чем язык отличается по применению: первое, чего нет у другого («Python — боты», а не «оба — сайты»)."""
    mine = [u.strip() for u in uses.split(",") if u.strip()]
    theirs = {u.strip().lower() for u in other.split(",")}
    unique = [u for u in mine if u.lower() not in theirs]
    return ", ".join((unique or mine)[:2])


def _languages(a, b):
    la, lb = _lang(a), _lang(b)
    if not la or not lb or la[0] == lb[0]:
        return None
    (na, _, ya, ua, da, ca, ha), (nb, _, yb, ub, db, cb, hb) = la, lb
    rows = [("Появился", f"{ya} г.", f"{yb} г."), ("Где применяют", ua, ub), ("Особенности", da, db)]
    older = na if ya < yb else nb
    table = "\n".join(f"| {r} | {x} | {y} |" for r, x, y in rows)
    return (f"## {na} и {nb}\n\n| | **{na}** | **{nb}** |\n|---|---|---|\n{table}\n\n"
            f"**Привет, мир:**\n\n```{ca}\n{ha}\n```\n\n```{cb}\n{hb}\n```\n\n"
            f"**Итог:** {na} — {_own(ua, ub)}; {nb} — {_own(ub, ua)}. "
            f"{older} старше{f' на {abs(ya - yb)} лет' if ya != yb else ''}. Выбирайте по задаче: что хотите делать — то и учите.")


def _first(text):
    return re.split(r"(?<=[.!?])\s+", text or "")[0]


def _topics(a, b, question):
    ta, tb = encyclopedia.lookup(a), encyclopedia.lookup(b)
    if not ta or not tb or ta["title"] == tb["title"]:
        return None
    name = lambda t: re.sub(r"\s*\([^)]*\)$", "", re.sub(r"^(.+?), (.+)$", r"\2 \1", t["title"]) if encyclopedia._PERSON_RE.match(t["title"]) else t["title"])
    na, nb = name(ta), name(tb)
    cap = lambda s: (s[:1].upper() + s[1:]) if s else "—"
    rows = [("Что это", cap(ta["desc"]), cap(tb["desc"])),
            ("Коротко", _first(ta["text"]), _first(tb["text"])),
            ("Раздел", ta["section"], tb["section"])]
    table = "\n".join(f"| {r} | {x.replace('|', '/')} | {y.replace('|', '/')} |" for r, x, y in rows)
    out = f"## {na} и {nb}\n\n| | **{na}** | **{nb}** |\n|---|---|---|\n{table}"
    if re.search(r"лучше|круче|сильнее|полезнее|выбрать", question, re.I):
        out += ("\n\nОднозначно «лучше» не бывает — зависит от того, что вам важно. Сравните главное в таблице; "
                "если нужен совет с доводами за и против — включите **Rai Нейро**.")
    out += (f"\n\n📚 По материалам Википедии: [{na}]({encyclopedia.page_url(ta['title'])}), "
            f"[{nb}]({encyclopedia.page_url(tb['title'])}) (CC BY-SA)")
    return out


def answer(text):
    """Таблица сравнения или None."""
    pair = parse(text)
    if not pair:
        return None
    a, b = pair
    return _languages(a, b) or _topics(a, b, text)
