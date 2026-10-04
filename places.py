"""Города, сёла и посёлки — карточка места из интернета, фото чего угодно и космическое фото дня.

«расскажи о городе Гродно», «посёлок Малиновка», «что посмотреть в Казани», «достопримечательности Минска»,
«сколько жителей в Бресте», «население Новосибирска» — население, область и страна, местное время, погода сейчас,
достопримечательности рядом с центром (статьи Википедии с координатами) и их фото. Работает для любого места,
которое находит геокодер погоды: от столиц до деревень.
«покажи фото Марса», «как выглядит галактика Андромеды», «фото Эйфелевой башни» — фото из энциклопедии и Википедии.
«фото дня NASA» — астрономическая картинка дня (NASA APOD) с переводом.
"""

import datetime
import math
import re
import urllib.parse

import encyclopedia
import net
import nlp
import online

_KINDS = (r"город\w*|посёлк\w*|поселк\w*|посёлок|поселок|сел[оеау]|сёл\w*|деревн\w*|деревеньк\w*|станиц\w*|хутор\w*|"
          r"аул\w*|агрогород\w*|пгт|местечк\w*|слобод\w*")
_CARD_RE = re.compile(
    rf"^\s*(?:расскажи|расскажите|что\s+(?:ты\s+)?знаешь|что\s+известно|информаци[яю]|инфа|вс[её]|справка|карточка)\s+"
    rf"(?:мне\s+)?(?:о|об|про)\s+(?:{_KINDS})\s+(.+?)[\s?!.]*$"
    rf"|^\s*(?:{_KINDS})\s+([а-яёa-z][^?!.]{{1,60}}?)[\s?!.]*$", re.I)
_SIGHTS_RE = re.compile(
    rf"достопримечательност\w*\s+(?:есть\s+)?(?:в|во|на|у)?\s*(?:(?:{_KINDS})\s+)?(.+?)[\s?!.]*$"
    rf"|(?:что\s+(?:можно\s+|стоит\s+)?(?:посмотреть|посетить)|куда\s+(?:можно\s+|стоит\s+)?сходить|"
    rf"интересные\s+места|что\s+интересного)\s+(?:есть\s+)?(?:в|во|на)\s+(?:(?:{_KINDS})\s+)?(.+?)[\s?!.]*$", re.I)
# «что посмотреть в кино / на выходных» — это не место
_NOT_PLACE = re.compile(r"^(?:кино\w*|интернет\w*|ютуб\w*|youtube|netflix|нетфликс\w*|выходн\w*|отпуск\w*|каникул\w*|"
                        r"телевизор\w*|тв|театр\w*|сериал\w*|мире|земле|космосе|игре|фильме|книге|жизни|школе|работе|"
                        r"дом[еау]?|квартир\w*|погоде|новостях|этом\s+году|субботу|воскресенье|вечер\w*|выходные)\b", re.I)
_POP_RE = re.compile(
    rf"(?:сколько\s+(?:жителей|людей|человек|народу|населения)\s+(?:сейчас\s+)?(?:живёт\s+|живет\s+|проживает\s+)?(?:в|во|на)\s+|"
    rf"(?:население|численность\s+населения|число\s+жителей|количество\s+жителей)\s+(?:в\s+|во\s+)?)"
    rf"(?:(?:{_KINDS})\s+)?(.+?)[\s?!.]*$", re.I)
_PHOTO_RE = re.compile(
    r"^\s*(?:покажи|найди|пришли|скинь|дай|отправь|хочу\s+(?:увидеть|посмотреть))\s+(?:мне\s+)?"
    r"(?:фото\w*|фотк\w*|фотограф\w*|картинк\w*|изображени\w*|снимк\w*|снимок)\s+(?:с\s+|со\s+)?(.+?)[\s?!.]*$"
    r"|^\s*как\s+выгляд(?:ит|ят|ел|ела|ело|ели)\s+(.+?)[\s?!.]*$"
    r"|^\s*(?:фото|фотография|фотографии|фотки|снимок|снимки)\s+(.+?)[\s?!.]*$", re.I)
_APOD_RE = re.compile(
    r"(?:фото\w*|картинк\w*|снимок|изображени\w*)\s+дня\s+(?:от\s+)?(?:nasa|наса)|(?:nasa|наса)\s+(?:фото\w*|картинк\w*|снимок)\s+дня|"
    r"(?:астрономическ\w+|космическ\w+)\s+(?:фото\w*|картинк\w*|снимок|изображени\w*)\s+дня|\bapod\b|фото\s+космоса\s+(?:дня|сегодня)", re.I)
_SIGHT = re.compile(
    r"собор|церк|храм|монастыр|музей|памятник|замок|усадьб|дворец|парк\b|парк |сквер|крепост|кремл|театр|\bмост|башн|"
    r"костёл|костел|мечет|синагог|часовн|площадь|набережн|галере|мемориал|фонтан|ботаническ|зоопарк|обелиск|водопад|"
    r"пещер|заповедник|бульвар|ратуш|маяк|руин|курган|городищ|лавр|триумфальн|ворота|планетари|цирк|аквапарк|"
    r"филармони|оперн|кафедральн|базилик|аббатств|святилищ|мавзоле|некропол", re.I)
_SETTLEMENT = re.compile(r"\b(?:город|деревня|посёлок|поселок|село|станица|агрогородок|хутор|столица|населённый пункт)", re.I)


def _norm(s):
    return " ".join(nlp.normalize(s or "").split())


def _clean_subject(s):
    return re.sub(r"\s+(?:пожалуйста|плиз|сейчас|сегодня)$", "", (s or "").strip(" «»\"'"), flags=re.I)


def kind(text):
    """Какая это просьба: ("card"|"sights"|"population", место) или None."""
    for name, rx in (("population", _POP_RE), ("sights", _SIGHTS_RE), ("card", _CARD_RE)):
        m = rx.search(text or "")
        if m:
            subject = _clean_subject(next((g for g in m.groups() if g), ""))
            if 1 < len(subject) <= 60 and not _NOT_PLACE.search(subject):
                return name, subject
    return None


def is_photo_request(text):
    return bool(_PHOTO_RE.search(text or "")) and not re.search(r"\bнарисуй|\bсгенерируй|\bсоздай\b", text or "", re.I)


def is_apod_request(text):
    return bool(_APOD_RE.search(text or ""))


def is_settlement(desc):
    return bool(_SETTLEMENT.search(desc or ""))


# ------------------------------------------------------------------ сведения о месте
def _locate(phrase):
    asked = online.parse_place("погода в " + phrase) or {"place": phrase}
    return online.geocode(asked["place"], asked.get("admin"), asked.get("country"))


def _near(lat, lon, radius=10000):
    """Статьи Википедии рядом с точкой (от ближних к дальним)."""
    data = net.fetch_json(net.url(
        "https://ru.wikipedia.org/w/api.php", action="query", list="geosearch", gscoord=f"{lat}|{lon}",
        gsradius=radius, gslimit=150, format="json", origin="*", utf8=1), ttl=86400)
    return data.get("query", {}).get("geosearch", [])


def _article(place, near):
    """Название статьи о самом месте: среди статей рядом — с тем же названием (до скобок и запятой)."""
    name = _norm(place["name"])
    for g in near:
        if _norm(re.split(r"[(,]", g["title"])[0]) == name:
            return g["title"]
    try:
        art = online.web_article(" ".join(x for x in (place["name"], place.get("admin1") or "") if x), langs=("ru",))
    except net.NetError:
        art = None
    if art and _norm(re.split(r"[(,]", art["title"])[0]) == name:
        return art["title"]
    return None


def _summary(title):
    return net.fetch_json("https://ru.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_")),
                          ttl=86400)


def _population(qid, place, extract):
    """(число жителей, год) — Wikidata, текст статьи или геокодер."""
    if qid:
        try:
            data = net.fetch_json(f"https://www.wikidata.org/w/rest.php/wikibase/v1/entities/items/{qid}/statements?property=P1082",
                                  ttl=86400)
            best = None
            for st in data.get("P1082", []):
                amount = int(float(st["value"]["content"]["amount"]))
                year = ""
                for q in st.get("qualifiers", []):
                    if q.get("property", {}).get("id") == "P585":
                        year = str(q.get("value", {}).get("content", {}).get("time", ""))[1:5]
                key = (st.get("rank") == "preferred", year)
                if best is None or key > best[0]:
                    best = (key, amount, year)
            if best:
                return best[1], best[2] or None
        except (net.NetError, KeyError, ValueError, TypeError, AttributeError):
            pass
    m = re.search(r"[Нн]аселени[ея][^.\d]{0,60}?(\d[\d   ]{2,})\s*(?:чел|жит)", extract or "")
    if m:
        return int(re.sub(r"\D", "", m.group(1))), None
    if place.get("population"):
        return int(place["population"]), None
    return None, None


def _weather_now(lat, lon):
    """(строка «+12°, дождь, ветер 4 м/с», местное время) или (None, None)."""
    try:
        data = net.fetch_json(net.url("https://api.open-meteo.com/v1/forecast", latitude=lat, longitude=lon, timezone="auto",
                                      wind_speed_unit="ms", current="temperature_2m,weather_code,wind_speed_10m"), ttl=600)
    except net.NetError:
        return None, None
    cur = data.get("current") or {}
    local = None
    if "utc_offset_seconds" in data:
        local = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=data["utc_offset_seconds"])
    if cur.get("temperature_2m") is None:
        return None, local
    t = round(cur["temperature_2m"])
    desc = online.WEATHER_CODES.get(cur.get("weather_code"), ("без осадков",))[0]
    wind = cur.get("wind_speed_10m")
    line = f"{'+' if t > 0 else ''}{t}°, {desc}" + (f", ветер {round(wind)} м/с" if wind is not None else "")
    return line, local


def _distance(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _thumbs(titles, size=640):
    """{название статьи: адрес её главной картинки}."""
    if not titles:
        return {}
    data = net.fetch_json(net.url("https://ru.wikipedia.org/w/api.php", action="query", prop="pageimages", titles="|".join(titles),
                                  piprop="thumbnail", pithumbsize=size, pilimit=len(titles), format="json", origin="*", utf8=1), ttl=86400)
    out = {}
    for page in (data.get("query", {}).get("pages") or {}).values():
        src = (page.get("thumbnail") or {}).get("source")
        if src and src.startswith("https://") and not re.search(r"\.svg", src, re.I):
            out[page.get("title")] = src
    return out


def _fmt(n):
    return f"{n:,}".replace(",", " ")


def card(phrase, focus="card"):
    """Карточка места: (текст, фото) или None, если место не нашлось. Ошибки сети — net.NetError."""
    place = _locate(phrase)
    if not place:
        return None
    lat, lon = place["latitude"], place["longitude"]
    near = _near(lat, lon)
    title = _article(place, near)
    summary = {}
    if title:
        try:
            summary = _summary(title)
        except net.NetError:
            summary = {}
    name = place.get("name") or phrase
    link = (summary.get("content_urls") or {}).get("desktop", {}).get("page") or (encyclopedia.page_url(title) if title else "")
    extract = (summary.get("extract") or "").strip()
    region = ", ".join(x for x in (place.get("admin2"), place.get("admin1"), place.get("country")) if x)
    people, year = _population(summary.get("wikibase_item"), place, extract)
    weather, local = _weather_now(lat, lon)

    sights = []
    for g in near:
        if g["title"] != title and _SIGHT.search(g["title"]) and all(g["title"] != s["title"] for s in sights):
            sights.append(g)
        if len(sights) >= 8:
            break
    thumbs = {}
    try:
        thumbs = _thumbs([s["title"] for s in sights[:6]])
    except net.NetError:
        pass
    photos = []
    main = (summary.get("originalimage") or summary.get("thumbnail") or {}).get("source")
    if main and focus != "sights":
        photos.append({"url": main, "title": name, "source": link})
    for s in sights:
        if s["title"] in thumbs and len(photos) < 5:
            photos.append({"url": thumbs[s["title"]], "title": s["title"], "source": encyclopedia.page_url(s["title"])})

    def sight_lines():
        rows = []
        for s in sights:
            km = _distance(lat, lon, s["lat"], s["lon"])
            rows.append(f"- [{s['title']}]({encyclopedia.page_url(s['title'])}) — "
                        + (f"{round(km * 1000)} м" if km < 1 else f"{km:.1f} км".replace(".", ",")) + " от центра")
        return rows

    source = f"📚 [Википедия]({link}) (CC BY-SA)" if link else "📚 Википедия"
    if focus == "population":
        if not people:
            return (f"Не нашёл, сколько людей живёт в месте «{name}»" + (f" ({region})" if region else "") + ". "
                    "Попробуйте уточнить область или район.", photos[:1])
        return (f"## {name}\n\n👥 Население: **{_fmt(people)}** чел." + (f" (данные {year} года)" if year else "") +
                (f"\n📍 {region}" if region else "") + f"\n\n{source}", photos[:1])
    if focus == "sights":
        if not sights:
            return (f"Рядом с центром места «{name}» ({region}) не нашёл статей Википедии о достопримечательностях. "
                    f"Спросите «найди достопримечательности {name}» — поищу в интернете.", [])
        return (f"## Что посмотреть: {name}\n\n" + "\n".join(sight_lines()) +
                (f"\n\n📍 {region}" if region else "") + "\n\n📚 Статьи Википедии с координатами (CC BY-SA)", photos)

    info = [f"📍 {region}" if region else "",
            f"👥 {_fmt(people)} жителей" + (f" ({year})" if year else "") if people else "",
            f"🕐 {local:%H:%M} местного времени" if local else ""]
    lines = [f"## {name}"]
    if summary.get("description"):
        lines.append("*" + summary["description"][:1].upper() + summary["description"][1:] + "*")
    lines.append("")
    lines.append(" · ".join(x for x in info if x))
    if weather:
        lines.append(f"🌤 Сейчас {weather}")
    if extract:
        lines += ["", online._first_sentences(extract, 600)]
    if sights:
        lines += ["", "**Что посмотреть:**"] + sight_lines()[:6]
    lines += ["", source + " · погода — Open-Meteo · «погода " + name + "» — прогноз на несколько дней"]
    return "\n".join(lines), photos


# ------------------------------------------------------------------ фото чего угодно, фото дня NASA
def photo_subject(text):
    m = _PHOTO_RE.search(text or "")
    return _clean_subject(next((g for g in m.groups() if g), "")) if m else ""


def photos(subject, web=True, limit=4):
    """(текст, [фото]) или None: картинка темы из энциклопедии и фото из статьи Википедии."""
    t = encyclopedia.lookup(subject)
    found, title = [], subject
    if t:
        title = t["title"]
        if t.get("image"):
            found.append({"url": t["image"], "title": t["title"], "source": encyclopedia.page_url(t["title"])})
    if web:
        try:
            for url in online.photos_for(re.sub(r"\s*\([^)]*\)$", "", title) if t else subject, limit):
                if all(url != f["url"] for f in found):
                    found.append({"url": url, "title": title, "source": encyclopedia.page_url(title) if t else ""})
        except net.NetError:
            pass
    if not found:
        return None
    shown = re.sub(r"^(.+?), (.+)$", r"\2 \1", title) if t and encyclopedia._PERSON_RE.match(title) else title
    head = f"### {shown}"
    if t and t.get("desc"):
        head += "\n*" + t["desc"][:1].upper() + t["desc"][1:] + "*"
    return head + "\n\n📷 Фото из Википедии (Викисклад, свободные лицензии).", found[:limit]


def _to_russian(text):
    try:
        data = net.fetch_json(net.url("https://api.mymemory.translated.net/get", q=text[:480], langpair="en|ru"), ttl=86400)
        out = (data.get("responseData") or {}).get("translatedText") or ""
        return out if out and int(data.get("responseStatus", 200)) == 200 else text
    except (net.NetError, ValueError, TypeError):
        return text


def apod():
    """Астрономическая картинка дня NASA: (текст, [фото])."""
    data = net.fetch_json("https://api.nasa.gov/planetary/apod?api_key=DEMO_KEY&thumbs=true", ttl=3600)
    image = data.get("url") if data.get("media_type") == "image" else data.get("thumbnail_url")
    title = data.get("title") or "Astronomy Picture of the Day"
    explanation = (data.get("explanation") or "").strip()
    first = " ".join(re.split(r"(?<=[.!?])\s+", explanation)[:3])
    text = (f"## 🔭 Фото дня NASA: {_to_russian(title)}\n*{title} · {data.get('date', '')}*\n\n{_to_russian(first)}"
            + ("\n\n*Сегодня это видео — показываю кадр.*" if data.get("media_type") == "video" else "")
            + f"\n\n🌌 [NASA APOD](https://apod.nasa.gov/apod/astropix.html)"
            + (f" · автор: {data['copyright'].strip()}" if data.get("copyright") else ""))
    photos_ = [{"url": image, "title": title, "source": "https://apod.nasa.gov/apod/astropix.html"}] if image and image.startswith("https://") else []
    return text, photos_
