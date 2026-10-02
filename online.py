"""Навыки Rai, которым нужен интернет: погода, валюты, перевод, поиск.

Используются бесплатные открытые сервисы без ключей:
- погода — Open-Meteo (open-meteo.com);
- курсы валют — open.er-api.com (запасной — cbr-xml-daily.ru, курсы ЦБ РФ);
- перевод — MyMemory (mymemory.translated.net);
- поиск — Википедия, а через посредник на хостинге (net.php) — Google или DuckDuckGo.
"""

import re
from datetime import date

import urllib.parse

import cities
import creative
import net
import nlp

# ================================================================== погода

WEATHER_CODES = {
    0: ("ясно", "clear"), 1: ("преимущественно ясно", "clear"), 2: ("переменная облачность", "partly"),
    3: ("пасмурно", "cloudy"), 45: ("туман", "fog"), 48: ("туман с изморозью", "fog"),
    51: ("слабая морось", "rain"), 53: ("морось", "rain"), 55: ("сильная морось", "rain"),
    56: ("ледяная морось", "rain"), 57: ("ледяная морось", "rain"),
    61: ("небольшой дождь", "rain"), 63: ("дождь", "rain"), 65: ("сильный дождь", "rain"),
    66: ("ледяной дождь", "rain"), 67: ("сильный ледяной дождь", "rain"),
    71: ("небольшой снег", "snow"), 73: ("снег", "snow"), 75: ("сильный снег", "snow"), 77: ("снежная крупа", "snow"),
    80: ("небольшой ливень", "rain"), 81: ("ливень", "rain"), 82: ("сильный ливень", "rain"),
    85: ("снегопад", "snow"), 86: ("сильный снегопад", "snow"),
    95: ("гроза", "storm"), 96: ("гроза с градом", "storm"), 99: ("сильная гроза с градом", "storm"),
}
_WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

_WEATHER_RE = re.compile(
    r"(погод\w*|температур\w*|прогноз\w*|дожд\w*|снег\w*|холодно|жарко|тепло)", re.I
)
_CITY_RE = re.compile(
    r"(?:\bв|\bво|\bна|\bдля|\bпо)\s+(?:городе\s+|город\s+)?([а-яёa-z][а-яёa-z\- ]{1,40}?)"
    r"(?:\s+(?:сегодня|сейчас|завтра|на завтра|на неделю|на выходные|будет|есть))?[\s?!.]*$",
    re.I,
)


def is_weather_request(text: str) -> bool:
    low = text.lower()
    if not _WEATHER_RE.search(low):
        return False
    # «прогноз» без погоды и «снег»/«дождь» как тема «что такое дождь» — не про погоду
    if re.search(r"что такое|кто такой|нарису|презентац", low):
        return False
    return bool(re.search(r"погод|температур|будет ли|идет ли|идёт ли|холодно|жарко|тепло|прогноз погод", low))


# Слова вокруг названия места: «какая погода завтра в …», «будет ли дождь в …»
_PLACE_STOP = set("""
какая какой какое какие каков какова как что сколько ли будет будут есть был была было идет идёт пойдет пойдёт
погода погоду погоды погоде прогноз прогноза прогнозу температура температуру температуры градус градуса градусов
по цельсию дождь дождя дожди снег снега снегопад ветер ветра солнце солнечно холодно жарко тепло прохладно мороз
морозно зонт зонтик одеваться одеться надеть одеть куртку осадки осадков влажность давление
сейчас сегодня завтра послезавтра утром утро днём днем вечером вечер ночью ночь неделю неделе неделя выходные
выходных дня дней день часа часов
в во на для по из с со к о об про у при над под около возле рядом города городе город городу
а и или но же ну там тут здесь у нас меня вас тебя мне нам вам
скажи скажите покажи покажите узнай узнать подскажи подскажите хочу знать нужна нужен нужно пожалуйста плиз спасибо
привет рай rai можешь можно дай дайте глянь посмотри
""".split())
_PLACE_KIND = re.compile(r"^(деревн\w*|дер|д|сел\w*|с|посел\w*|посёл\w*|пос|п|пгт|агрогород\w*|аг|хутор\w*|станиц\w*|ст|"
                         r"аул\w*|кишлак\w*|мкр|микрорайон\w*|городок|городке|курорт\w*)$", re.I)
_ADMIN_WORD = re.compile(r"^(област\w*|обл|район\w*|р-н|рн|край|краю|края|республик\w*|округ\w*)$", re.I)
_COUNTRIES = {"беларус": "BY", "белорусс": "BY", "росси": "RU", "рф": "RU", "украин": "UA", "казахстан": "KZ", "узбекистан": "UZ",
              "кыргызстан": "KG", "киргиз": "KG", "таджикистан": "TJ", "армени": "AM", "грузи": "GE", "азербайджан": "AZ",
              "молдов": "MD", "латви": "LV", "литв": "LT", "эстони": "EE", "польш": "PL", "германи": "DE", "турци": "TR",
              "сша": "US", "франци": "FR", "итали": "IT", "испани": "ES", "китай": "CN", "китае": "CN", "япони": "JP"}


def parse_place(text: str):
    """Место из вопроса о погоде: {"place", "kind", "admin", "country"} или None.

    «погода Минск», «Минск погода», «погода в деревне Малиновка Минского района завтра», «дождь в Ждановичах, Беларусь».
    """
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+(?:-[A-Za-zА-Яа-яЁё0-9]+)*\.?", text or "")
    place, admin, country, kind = [], None, None, None
    for i, raw in enumerate(words):
        w = raw.rstrip(".")
        low = w.lower()
        code = next((c for k, c in _COUNTRIES.items() if low.startswith(k)), None)
        if code:
            country = code
        elif _ADMIN_WORD.match(low):
            if place and not admin:
                admin = place.pop()  # «Минского района» — прилагательное перед словом «район»
        elif _PLACE_KIND.match(low) and (raw.endswith(".") or len(low) > 2 or i + 1 < len(words)):
            kind = kind or low
        elif low in _PLACE_STOP or low.isdigit() or _WEATHER_RE.fullmatch(low):
            if place and admin is None and low not in ("в", "во", "на", "у", "и", "а"):
                continue
        else:
            place.append(w)
    if not place:
        return None
    phrase = " ".join(place[:4])
    # «посёлок Энергетиков Бобруйск»: последнее слово — известный город, это подсказка, где искать
    if len(place) >= 2 and not cities.find(phrase) and cities.find(place[-1]) and not admin:
        admin, phrase = cities.find(place[-1])["name"], " ".join(place[:-1][:3])
    return {"place": phrase, "kind": kind, "admin": admin, "country": country}


def _city_candidates(phrase: str):
    """«Москве» -> «Москве», «Москва», «Москв»… «Ждановичах» -> «Ждановичи». Open-Meteo ищет по началу названия."""
    phrase = phrase.strip(" -")
    words = phrase.split()
    cands = [phrase]
    if len(words) == 1:
        w = words[0]
        for old, new in (("ах", "и"), ("ах", "ы"), ("ях", "и"), ("е", "а"), ("и", "ь"), ("и", "а"), ("е", ""), ("у", "а"),
                         ("и", "я"), ("ом", ""), ("ой", "ая"), ("ом", "о"), ("е", "о")):
            if w.lower().endswith(old) and len(w) > 3:
                cands.append(w[: -len(old)] + new)
        cands.append(nlp.stem(w.lower()))
    else:
        fixed = []
        for w in words:
            lw = w.lower()
            if lw.endswith(("ем", "ом")) and len(lw) > 4:
                fixed.append(w[:-2] + ("ий" if lw.endswith("ем") else "ый"))
            elif lw.endswith("ой") and len(lw) > 4:
                fixed.append(w[:-2] + "ая")
            elif lw.endswith("е") and len(lw) > 3:
                fixed.append(w[:-1])
            else:
                fixed.append(w)
        cands.append(" ".join(fixed))
    out = []
    for c in cands:
        if c and c.lower() not in [o.lower() for o in out]:
            out.append(c)
    return out[:7]


def _norm(s):
    return (s or "").lower().replace("ё", "е").strip()


def _score(result, cand, admin=None, country=None, home=None):
    """Насколько найденное место похоже на то, о чём спросили (home — страна, о которой спрашивали раньше)."""
    score = 0.0
    if home and not country and (result.get("country_code") or "").upper() == home:
        score += 3
    name = _norm(result.get("name"))
    if name == _norm(cand):
        score += 4
    elif name.startswith(_norm(cand)):
        score += 1
    if country and (result.get("country_code") or "").upper() == country:
        score += 6
    if admin:
        stem = nlp.stem(_norm(admin))[:5]
        if any(stem and stem in _norm(result.get(k)) for k in ("admin1", "admin2", "admin3", "admin4")):
            score += 5
    pop = result.get("population") or 0
    score += min(3, len(str(int(pop))) / 2) if pop else 0
    if result.get("feature_code") in ("PPLC", "PPLA"):
        score += 1
    return score


def _nominatim(query: str, country=None):
    """Запасной поиск места по OpenStreetMap — там есть почти все деревни и посёлки."""
    params = {"q": query, "format": "jsonv2", "limit": 5, "accept-language": "ru", "addressdetails": 1}
    if country:
        params["countrycodes"] = country.lower()
    data = net.fetch_json(net.url("https://nominatim.openstreetmap.org/search", **params), ttl=86400)
    for r in data if isinstance(data, list) else []:
        if r.get("lat") and r.get("lon"):
            a = r.get("address") or {}
            name = (r.get("name") or query).strip()
            region = a.get("county") or a.get("state_district") or a.get("state") or ""
            return {"name": name, "latitude": float(r["lat"]), "longitude": float(r["lon"]), "country": a.get("country", ""),
                    "admin1": region, "country_code": (a.get("country_code") or "").upper()}
    return None


def geocode(phrase: str, admin=None, country=None, home=None):
    """Координаты места: свой справочник крупных городов (без запроса), потом Open-Meteo (города, сёла, посёлки
    по всему миру — выбираем лучшее совпадение с учётом района и страны), потом OpenStreetMap."""
    if not admin and not country:
        for cand in [phrase] + _city_candidates(phrase):
            known = cities.find(cand)
            if known:
                return known
    best, best_score, same = None, -1.0, []
    for cand in _city_candidates(phrase):
        params = {"name": cand, "count": 10, "language": "ru", "format": "json"}
        if country:
            params["countryCode"] = country
        data = net.fetch_json(net.url("https://geocoding-api.open-meteo.com/v1/search", **params), ttl=86400)
        results = data.get("results") or []
        for r in results:
            sc = _score(r, cand, admin, country, home)
            if sc > best_score:
                best, best_score = r, sc
        # одноимённые места в разных областях — скажем, какое выбрали
        same = [r for r in results if _norm(r.get("name")) == _norm(cand)]
        if best and best_score >= 4 + (5 if admin else 0):
            break  # точное совпадение (и с районом, если его назвали) — дальше не ищем
    if best and (best_score >= 4 or not admin):
        if not admin and len({(r.get("admin1"), r.get("country_code")) for r in same}) > 1:
            best = dict(best, others=[", ".join(x for x in (r.get("admin1"), r.get("country")) if x)
                                      for r in same if r is not best and r.get("admin1") != best.get("admin1")][:4])
        return best
    try:
        found = _nominatim(" ".join(x for x in (phrase, admin) if x), country)
    except net.NetError:
        found = None
    if not found:
        for cand in _city_candidates(phrase)[1:3]:
            try:
                found = _nominatim(" ".join(x for x in (cand, admin) if x), country)
            except net.NetError:
                found = None
            if found:
                break
    return found or best


_FOLLOW_UP = re.compile(r"^\s*(?:а|и|ну|ещё|еще)?\s*(?:в|во|на|для)\s+[A-Za-zА-Яа-яЁё.-]+(?:\s+[A-Za-zА-Яа-яЁё.-]+){0,3}\s*\??\s*$", re.I)


def weather(text: str, session: dict, default_city: str = "Москва"):
    """Вернуть (ответ, вложения) или None, если это не вопрос о погоде."""
    follow_up = bool(session.get("weather_last") and _FOLLOW_UP.match(text or ""))  # «а в Малиновке?» после погоды
    if not is_weather_request(text) and not follow_up:
        session.pop("weather_last", None)
        return None
    session["weather_last"] = True
    asked = parse_place(text)
    note = ""
    if asked:
        city_phrase = asked["place"]
    elif session.get("city"):
        city_phrase = session["city"]
    else:
        city_phrase = default_city
        note = (f"\n\n*Место не указано, поэтому это погода для города {default_city}. Спросите, например: «погода Минск» "
                "или «погода в деревне Малиновка Минского района».*")
    try:
        place = geocode(city_phrase, asked and asked.get("admin"), asked and asked.get("country"), session.get("country"))
        if not place:
            return (f"Не нашёл место «{city_phrase}». Уточните район или область: «погода {city_phrase} Минский район» "
                    "или напишите название полностью."), []
        data = net.fetch_json(net.url(
            "https://api.open-meteo.com/v1/forecast",
            latitude=place["latitude"], longitude=place["longitude"], timezone="auto", forecast_days=4,
            wind_speed_unit="ms",
            current="temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
            daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        ), ttl=600)
    except net.NetError as e:
        return net.explain(e, "узнать погоду"), []

    session["city"] = place.get("name", city_phrase)
    code_country = (place.get("country_code") or "").upper() or {"Беларусь": "BY", "Россия": "RU", "Украина": "UA", "Казахстан": "KZ"}.get(place.get("country"))
    if code_country:
        session["country"] = code_country  # одноимённые сёла дальше ищем сначала в этой стране
    if place.get("others"):
        note += (f"\n\n*Мест с названием «{place.get('name')}» несколько — показываю: {place.get('admin1') or place.get('country')}. "
                 f"Есть ещё: {'; '.join(place['others'])}. Уточните район или область, например: «погода {place.get('name')} Минский район».*")
    cur = data.get("current", {})
    code = int(cur.get("weather_code", 0))
    desc, kind = WEATHER_CODES.get(code, ("без осадков", "cloudy"))
    temp = cur.get("temperature_2m")
    feels = cur.get("apparent_temperature")
    name = place.get("name", city_phrase)
    region = place.get("admin1") if place.get("admin1") and _norm(place.get("admin1")) != _norm(name) and \
        not cities.find(name) else ""
    where = ", ".join(x for x in (name, region, place.get("country")) if x)

    def t(v):
        return f"{'+' if v is not None and round(v) > 0 else ''}{round(v)}°" if v is not None else "—"

    lines = [
        f"## Погода: {where}",
        f"Сейчас **{t(temp)}**, {desc}. Ощущается как {t(feels)}.",
        f"Ветер {cur.get('wind_speed_10m', '—')} м/с, влажность {cur.get('relative_humidity_2m', '—')}%.",
    ]
    daily = data.get("daily", {})
    days = daily.get("time", [])
    if days:
        lines.append("\n| День | Погода | Мин | Макс | Осадки |\n|---|---|---|---|---|")
        for i, day in enumerate(days[:4]):
            d = date.fromisoformat(day)
            label = "сегодня" if i == 0 else "завтра" if i == 1 else f"{_WEEKDAYS[d.weekday()]}, {d.day:02d}.{d.month:02d}"
            dcode = int(daily.get("weather_code", [0] * 4)[i])
            prob = (daily.get("precipitation_probability_max") or [None] * 4)[i]
            lines.append(
                f"| {label} | {WEATHER_CODES.get(dcode, ('—',))[0]} | {t(daily['temperature_2m_min'][i])} | "
                f"**{t(daily['temperature_2m_max'][i])}** | {'' if prob is None else str(prob) + '%'} |"
            )
    card = creative.weather_card(name, t(temp), desc, kind, bool(cur.get("is_day", 1)), f"ощущается как {t(feels)}")
    return "\n".join(lines) + note, [card]


# ================================================================== валюты

# (код, слова-формы (регулярное выражение для целого слова), название)
CURRENCIES = [
    ("BYN", r"белорусск\w*|byn", "белорусский рубль"),
    ("CAD", r"канадск\w*|cad", "канадский доллар"),
    ("AUD", r"австралийск\w*|aud", "австралийский доллар"),
    ("SEK", r"шведск\w*|sek", "шведская крона"),
    ("CZK", r"чешск\w*|czk", "чешская крона"),
    ("RUB", r"рубл\w*|руб|rub|₽", "рубль"),
    ("USD", r"доллар\w*|бакс\w*|usd|\$", "доллар США"),
    ("EUR", r"евро|eur|€", "евро"),
    ("CNY", r"юан\w*|cny|¥", "юань"),
    ("GBP", r"фунт\w*|стерлинг\w*|gbp|£", "фунт стерлингов"),
    ("JPY", r"[иий]ен\w*|jpy", "иена"),
    ("KZT", r"тенге|kzt|₸", "тенге"),
    ("UAH", r"гривн\w*|uah|₴", "гривна"),
    ("TRY", r"лир[аыу]?|лирах", "турецкая лира"),
    ("CHF", r"франк\w*|chf", "швейцарский франк"),
    ("KRW", r"вон[аыу]|krw", "вона"),
    ("INR", r"рупи\w*|inr", "индийская рупия"),
    ("PLN", r"злот\w*|pln", "злотый"),
    ("KGS", r"сом(?:а|ов|ы)?|kgs", "сом"),
    ("UZS", r"сум(?:ов)?|uzs", "сум"),
    ("GEL", r"лари|gel", "лари"),
    ("AMD", r"драм(?:ов)?|amd", "драм"),
    ("AZN", r"манат\w*|azn", "манат"),
    ("AED", r"дирхам\w*|aed", "дирхам ОАЭ"),
    ("ILS", r"шекел\w*|ils", "шекель"),
    ("THB", r"бат(?:а|ов)?|thb", "бат"),
    ("BRL", r"реал(?:а|ов)|brl", "бразильский реал"),
]
# «белорусских рублей», «канадских долларов» — второе слово не отдельная валюта
_COMPOUND = {"BYN": "RUB", "CAD": "USD", "AUD": "USD", "SEK": "", "CZK": ""}


def _find_currencies(text):
    """Найти валюты в тексте по порядку упоминания: [(позиция, код)]."""
    low = text.lower().replace("ё", "е")
    found = []
    prev_word_code = None  # валюта, найденная в предыдущем слове
    for m in re.finditer(r"[a-zа-я]+|[$€£¥₽₸₴]", low):
        word = m.group(0)
        code = next((c for c, pattern, _ in CURRENCIES if re.fullmatch(pattern, word)), None)
        skip = prev_word_code and code is not None and (
            _COMPOUND.get(prev_word_code) == code or (prev_word_code in ("SEK", "CZK") and word.startswith("крон")))
        if code and not skip:
            found.append((m.start(), code))
        if prev_word_code in ("SEK", "CZK") and word.startswith("крон"):
            code = None
        prev_word_code = None if skip else code
    return found


def is_currency_request(text: str) -> bool:
    low = text.lower()
    if re.search(r"курс\w*\s+валют|валют\w*\s+курс", low):
        return True
    cur = _find_currencies(text)
    if not cur:
        return False
    if re.search(r"\bкурс", low):
        return True
    has_number = bool(re.search(r"\d", low))
    if len(cur) >= 2 and (has_number or re.search(r"\bв\b|\bto\b|сколько", low)):
        return True
    return has_number and bool(re.search(r"сколько|стоит|это|будет", low))


def rates():
    """Курсы к доллару: {"USD": 1, "RUB": 92.1, ...}, дата."""
    try:
        data = net.fetch_json("https://open.er-api.com/v6/latest/USD", ttl=3600)
        if data.get("result") == "success":
            return data["rates"], data.get("time_last_update_utc", "")[:16]
    except net.NetError:
        pass
    data = net.fetch_json("https://www.cbr-xml-daily.ru/daily_json.js", ttl=3600)
    rub = {"RUB": 1.0}
    for code, v in data.get("Valute", {}).items():
        rub[code] = v["Value"] / v["Nominal"]  # рублей за 1 единицу
    usd = rub["USD"]
    return {code: usd / value for code, value in rub.items()}, "ЦБ РФ, " + data.get("Date", "")[:10]


def _money(v):
    if float(v).is_integer() and abs(v) < 1e15:
        return f"{int(v):,}".replace(",", " ")
    if v >= 100:
        s = f"{v:,.2f}"
    elif v >= 1:
        s = f"{v:,.4f}".rstrip("0").rstrip(".")
    else:
        s = f"{v:.6f}".rstrip("0").rstrip(".")
    return s.replace(",", " ").replace(".", ",")


def _name(code):
    return next((n for c, _, n in CURRENCIES if c == code), code)


def currency(text: str):
    if not is_currency_request(text):
        return None
    try:
        table, updated = rates()
    except net.NetError as e:
        return net.explain(e, "получить курсы валют")
    found = [code for _, code in _find_currencies(text)]
    low = text.lower()
    if not found or re.search(r"курс\w*\s+валют", low) and len(found) < 2:
        rows = "\n".join(
            f"| {_name(c)} | {c} | **{_money(table['RUB'] / table[c])} ₽** |"
            for c in ("USD", "EUR", "CNY", "GBP", "JPY", "KZT", "BYN", "TRY") if c in table
        )
        return f"## Курсы валют к рублю\n\n| Валюта | Код | Курс |\n|---|---|---|\n{rows}\n\nОбновлено: {updated}."
    num = re.search(r"(\d[\d\s]*(?:[.,]\d+)?)\s*(тыс\w*|к\b|млн|миллион\w*)?", low)
    amount = 1.0
    if num:
        amount = float(num.group(1).replace(" ", "").replace(",", "."))
        mult = num.group(2) or ""
        amount *= 1000 if mult.startswith(("тыс", "к")) else 1_000_000 if mult.startswith(("млн", "миллион")) else 1
    src = found[0]
    dst = found[1] if len(found) > 1 and found[1] != src else ("RUB" if src != "RUB" else "USD")
    if src not in table or dst not in table:
        return "Для этой валюты у меня нет курса."
    value = amount * table[dst] / table[src]
    one = table[dst] / table[src]
    return (f"**{_money(amount)} {src} = {_money(value)} {dst}**\n\n"
            f"Курс: 1 {_name(src)} = {_money(one)} {dst}. Обновлено: {updated}.")


# ================================================================== перевод

LANGS = {
    "en": ("английск", "английский"), "ru": ("русск", "русский"), "de": ("немецк", "немецкий"),
    "fr": ("французск", "французский"), "es": ("испанск", "испанский"), "it": ("итальянск", "итальянский"),
    "pt": ("португальск", "португальский"), "pl": ("польск", "польский"), "uk": ("украинск", "украинский"),
    "be": ("белорусск", "белорусский"), "kk": ("казахск", "казахский"), "zh": ("китайск", "китайский"),
    "ja": ("японск", "японский"), "ko": ("корейск", "корейский"), "ar": ("арабск", "арабский"),
    "tr": ("турецк", "турецкий"), "el": ("греческ", "греческий"), "he": ("иврит", "иврит"),
    "hi": ("хинди", "хинди"), "cs": ("чешск", "чешский"), "nl": ("нидерландск", "нидерландский"),
    "sv": ("шведск", "шведский"), "no": ("норвежск", "норвежский"), "da": ("датск", "датский"),
    "fi": ("финск", "финский"), "hu": ("венгерск", "венгерский"), "ro": ("румынск", "румынский"),
    "bg": ("болгарск", "болгарский"), "sr": ("сербск", "сербский"), "hr": ("хорватск", "хорватский"),
    "lv": ("латышск", "латышский"), "lt": ("литовск", "литовский"), "et": ("эстонск", "эстонский"),
    "ka": ("грузинск", "грузинский"), "hy": ("армянск", "армянский"), "az": ("азербайджанск", "азербайджанский"),
    "uz": ("узбекск", "узбекский"), "tt": ("татарск", "татарский"), "fa": ("персидск", "персидский"),
    "vi": ("вьетнамск", "вьетнамский"), "th": ("тайск", "тайский"), "id": ("индонезийск", "индонезийский"),
    "la": ("латын", "латынь"), "eo": ("эсперанто", "эсперанто"), "ky": ("киргизск", "киргизский"),
    "tg": ("таджикск", "таджикский"), "mn": ("монгольск", "монгольский"), "sk": ("словацк", "словацкий"),
    "sl": ("словенск", "словенский"), "ga": ("ирландск", "ирландский"), "is": ("исландск", "исландский"),
}
_LANG_ALIAS = {"голландск": "nl", "фарси": "fa", "по-русск": "ru", "англ": "en"}

_STOP = {
    "en": "the and is are you to of in it what hello how this that with for my your i we they be not have".split(),
    "de": "und der die das ist nicht ich du ein eine wie guten danke mit für ist sie wir haben".split(),
    "fr": "le la les et est je vous un une bonjour pas que merci avec pour nous il elle".split(),
    "es": "el la los las y es que de hola como estás por una gracias con para muy yo".split(),
    "it": "il lo la e è che di ciao come sono non una grazie con per io tu".split(),
    "pt": "o a os e é que de olá você não um uma obrigado com para eu muito".split(),
    "pl": "i w nie jest to się na cześć jak dzień dobry dziękuję ja ty".split(),
    "tr": "ve bir bu ne merhaba nasılsın için değil ben sen teşekkür".split(),
    "nl": "de het een en is niet ik hallo hoe dank je wij".split(),
    "sv": "och är jag du det inte hej tack en ett".split(),
    "cs": "a je to se na ne ahoj jak děkuji já ty".split(),
    "id": "dan yang di ini itu apa saya kamu terima kasih".split(),
}
_HINTS = [("es", "ñ¿¡"), ("de", "ßäöü"), ("tr", "ğşı"), ("pl", "łąęśźżćń"), ("pt", "ãõ"),
          ("fr", "àâçèêëîïôœùû"), ("cs", "ěřůčšž"), ("ro", "ăîșț"), ("hu", "őű")]


def detect_language(text: str) -> str:
    """Свой определитель языка: по алфавиту, особым буквам и частым словам."""
    s = text.lower()
    scripts = [
        (r"[぀-ヿ]", "ja"), (r"[가-힯]", "ko"), (r"[一-鿿]", "zh"),
        (r"[؀-ۿ]", "ar"), (r"[֐-׿]", "he"), (r"[Ͱ-Ͽ]", "el"),
        (r"[฀-๿]", "th"), (r"[ऀ-ॿ]", "hi"), (r"[Ⴀ-ჿ]", "ka"),
        (r"[԰-֏]", "hy"),
    ]
    for pattern, code in scripts:
        if re.search(pattern, s):
            if code == "ar" and re.search(r"[پچژگ]", s):
                return "fa"
            return code
    if re.search(r"[а-яёіїєґўәғқңөұүһђћџјљњ]", s):
        if re.search(r"[әғқңөұүһ]", s):
            return "kk"
        if re.search(r"[їєґ]", s) or (re.search(r"і", s) and not re.search(r"ў", s)):
            return "uk"
        if re.search(r"ў", s):
            return "be"
        if re.search(r"[ђћџјљњ]", s):
            return "sr"
        return "ru"
    words = re.findall(r"[a-zà-ÿąęłśźżćńěřůčšžőűăîșțğşı]+", s)
    scores = {lang: sum(2 for w in words if w in stop) for lang, stop in _STOP.items()}
    for lang, letters in _HINTS:
        scores[lang] = scores.get(lang, 0) + sum(3 for ch in s if ch in letters)
    best = max(scores, key=scores.get) if scores else "en"
    return best if scores.get(best) else "en"


_TRANSLATE_RE = re.compile(
    r"^\s*(?:пожалуйста\s+)?(?:переведи(?:те)?|перевод|translate|как (?:будет|сказать|пишется)|как)\b", re.I
)


def _lang_code(word: str):
    w = word.lower().replace("ё", "е")
    for alias, code in _LANG_ALIAS.items():
        if w.startswith(alias):
            return code
    for code, (prefix, _) in LANGS.items():
        if w.startswith(prefix):
            return code
    return None


def is_translate_request(text: str) -> bool:
    low = text.lower()
    if re.match(r"^\s*(?:пожалуйста\s+)?(?:переведи|перевод|translate)\b", low):
        return True
    return bool(re.search(r"\bпо-[а-я]+(?:ски|цки)\b", low) and re.match(r"^\s*как\b", low))


def parse_translate(text: str):
    """Разобрать запрос: (текст, язык-источник или None, язык перевода или None)."""
    src = dst = None
    body = text.strip()
    quoted = re.search(r"[«\"“'](.+?)[»\"”']", body)
    m = re.search(r"\bс\s+([а-я]+(?:ого|ого языка)?)\s+(?:на|в)\s+([а-я-]+)", body, re.I)
    if m:
        src, dst = _lang_code(m.group(1)), _lang_code(m.group(2))
        body = body.replace(m.group(0), " ")
    m = re.search(r"\b(?:на|в)\s+([а-я-]+?)(?:\s+язык)?\b(?=[\s:,.!?]|$)", body, re.I)
    if not dst and m and _lang_code(m.group(1)):
        dst = _lang_code(m.group(1))
        body = body.replace(m.group(0), " ", 1)
    m = re.search(r"\bпо-([а-я]+)", body, re.I)
    if not dst and m and _lang_code(m.group(1)):
        dst = _lang_code(m.group(1))
        body = body.replace(m.group(0), " ", 1)
    m = re.search(r"\b(?:to|into)\s+([a-z]+)\s*$", body, re.I)
    if not dst and m:
        names = {"english": "en", "russian": "ru", "german": "de", "french": "fr", "spanish": "es",
                 "italian": "it", "chinese": "zh", "japanese": "ja", "korean": "ko", "ukrainian": "uk"}
        if m.group(1).lower() in names:
            dst = names[m.group(1).lower()]
            body = body[: m.start()]
    if quoted:
        body = quoted.group(1)
    else:
        body = _TRANSLATE_RE.sub("", body, count=1)
        body = re.sub(r"^\s*(?:текст|слово|фразу|предложение)?\s*[:\-—]?\s*", "", body, flags=re.I)
        body = re.sub(r"^\s*(?:будет|сказать)\s+", "", body, flags=re.I)
    return body.strip(" \t\n:—-?"), src, dst


def _chunks(text, size=450):
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > size:
            parts.append(sentence[:size]); sentence = sentence[size:]
        if len(cur) + len(sentence) + 1 > size:
            parts.append(cur); cur = ""
        cur = (cur + " " + sentence).strip()
    if cur:
        parts.append(cur)
    return parts


def translate(text: str):
    if not is_translate_request(text):
        return None
    body, src, dst = parse_translate(text)
    if not body:
        return "Что перевести? Напишите, например: «переведи на английский: доброе утро»."
    if len(body) > 3000:
        return "Текст слишком длинный для перевода — до 3000 символов за раз."
    src = src or detect_language(body)
    dst = dst or ("en" if src == "ru" else "ru")
    if src == dst:
        dst = "en" if src != "en" else "ru"
    out = []
    try:
        for part in _chunks(body):
            data = net.fetch_json(net.url("https://api.mymemory.translated.net/get", q=part, langpair=f"{src}|{dst}"),
                                  ttl=86400)
            if int(data.get("responseStatus", 200)) != 200:
                return f"Сервис перевода ответил: {data.get('responseDetails', 'ошибка')}."
            out.append(data.get("responseData", {}).get("translatedText", ""))
    except net.NetError as e:
        return net.explain(e, "перевести")
    result = " ".join(x for x in out if x).strip()
    return (f"**{LANGS.get(src, (None, src))[1].capitalize()} → {LANGS.get(dst, (None, dst))[1]}:**\n\n"
            f"> {body}\n\n{result}")


# ================================================================== поиск

_SEARCH_RE = re.compile(
    r"^\s*(?:найди|поищи|загугли|погугли|найти|ищи|поиск)(?:\s+(?:в\s+интернете|в\s+сети|в\s+гугле|информацию))*"
    r"(?:\s+(?:про|о|об|что такое))?\s+(.+?)[\s?!.]*$",
    re.I,
)


def explicit_search(text: str):
    m = _SEARCH_RE.match(text)
    return m.group(1) if m else None


def _first_sentences(text, limit=700):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > 200 else cut.rstrip() + "…"


def web_article(query: str, langs=("ru", "en")):
    """Статья из Википедии: {"title", "text", "image", "link", "lang"} или None."""
    query = query.strip(" ?!.")
    if len(query) < 2:
        return None
    for lang in langs:
        found = net.fetch_json(net.url(
            f"https://{lang}.wikipedia.org/w/api.php", action="query", list="search", srsearch=query,
            srlimit=1, format="json", origin="*", utf8=1), ttl=3600)
        hits = found.get("query", {}).get("search", [])
        if not hits:
            continue
        title = hits[0]["title"]
        page = net.fetch_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
                              + urllib.parse.quote(title.replace(" ", "_")), ttl=3600)
        extract = (page.get("extract") or "").strip()
        if not extract:
            continue
        return {
            "title": page.get("title", title), "text": extract, "lang": lang,
            "link": page.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "image": page.get("thumbnail", {}).get("source") or page.get("originalimage", {}).get("source"),
        }
    return None


_SKIP_SECTIONS = re.compile(r"^(примечани|литератур|ссылки|см\. также|источник|галере|библиограф|notes|references|"
                            r"see also|external links|further reading|bibliography|sources|gallery)", re.I)


def wiki_page(query: str, langs=("ru", "en")):
    """Статья Википедии целиком, по разделам — материал для презентации.

    {"title", "lang", "link", "image", "lead", "sections": [{"title", "text"}]} или None.
    """
    query = query.strip(" ?!.")
    if len(query) < 2:
        return None
    for lang in langs:
        found = net.fetch_json(net.url(
            f"https://{lang}.wikipedia.org/w/api.php", action="query", list="search", srsearch=query,
            srlimit=1, format="json", origin="*", utf8=1), ttl=3600)
        hits = found.get("query", {}).get("search", [])
        if not hits:
            continue
        title = hits[0]["title"]
        data = net.fetch_json(net.url(
            f"https://{lang}.wikipedia.org/w/api.php", action="query", prop="extracts|pageimages", titles=title,
            explaintext=1, exsectionformat="wiki", piprop="original|thumbnail", pithumbsize=1280, redirects=1,
            format="json", origin="*", utf8=1), ttl=3600)
        pages = list((data.get("query", {}).get("pages") or {}).values())
        if not pages or not pages[0].get("extract"):
            continue
        page = pages[0]
        parts = re.split(r"^(={2,4})\s*(.+?)\s*\1\s*$", page["extract"], flags=re.M)
        lead = parts[0].strip()
        sections, skip_level = [], None
        for k in range(1, len(parts) - 2, 3):
            level, head, body = len(parts[k]), parts[k + 1].strip(), parts[k + 2].strip()
            if skip_level and level > skip_level:
                continue
            skip_level = level if _SKIP_SECTIONS.match(head) else None
            if skip_level or len(body) < 80:
                continue
            sections.append({"title": head, "text": body})
        image = (page.get("original") or {}).get("source") or (page.get("thumbnail") or {}).get("source")
        return {"title": page.get("title", title), "lang": lang, "lead": lead, "sections": sections,
                "image": image if image and re.search(r"\.(jpe?g|png|webp)$", image, re.I) else None,
                "link": f"https://{lang}.wikipedia.org/wiki/" + urllib.parse.quote(page.get("title", title).replace(" ", "_"))}
    return None


_BAD_PICTURE = re.compile(r"(flag|logo|icon|symbol|coat|герб|флаг|логотип|значок|map|карта|signature|подпись|"
                          r"commons-|wiki|question_book|edit-clear|ambox|disambig|folder|crystal|nuvola|pictogram|"
                          r"\.svg$|\.gif$|\.tiff?$)", re.I)


def wiki_images(title: str, lang: str = "ru", limit: int = 12):
    """Настоящие фотографии из статьи Википедии: [{"url", "title", "page"}] (без флагов, значков и схем)."""
    data = net.fetch_json(net.url(
        f"https://{lang}.wikipedia.org/w/api.php", action="query", generator="images", titles=title, gimlimit=40,
        prop="imageinfo", iiprop="url|size|mime", iiurlwidth=1280, format="json", origin="*", utf8=1), ttl=86400)
    out = []
    for page in (data.get("query", {}).get("pages") or {}).values():
        name = page.get("title", "")
        info = (page.get("imageinfo") or [{}])[0]
        if _BAD_PICTURE.search(name) or info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        if (info.get("width") or 0) < 500 or (info.get("height") or 0) < 300:
            continue
        url = info.get("thumburl") or info.get("url")
        if url and url.startswith("https://upload.wikimedia.org/"):
            out.append({"url": url, "title": re.sub(r"^(Файл|File):|\.\w+$", "", name).replace("_", " "),
                        "page": info.get("descriptionurl", "")})
    return out[:limit]


def photos_for(query: str, limit: int = 12):
    """Фотографии по теме из Википедии (главное фото статьи + фото из неё): список адресов https."""
    page = wiki_page(query)
    if not page:
        return []
    out = [page["image"]] if page["image"] else []
    out += [p["url"] for p in wiki_images(page["title"], page["lang"], limit)]
    return list(dict.fromkeys(out))[:limit]


def wiki_quote(topic: str):
    """Цитата по теме из Викицитатника: {"text", "author"} или None."""
    found = net.fetch_json(net.url("https://ru.wikiquote.org/w/api.php", action="query", list="search", srsearch=topic,
                                   srlimit=1, format="json", origin="*", utf8=1), ttl=86400)
    hits = found.get("query", {}).get("search", [])
    if not hits:
        return None
    title = hits[0]["title"]
    data = net.fetch_json(net.url("https://ru.wikiquote.org/w/api.php", action="query", prop="extracts", titles=title,
                                  explaintext=1, format="json", origin="*", utf8=1), ttl=86400)
    pages = list((data.get("query", {}).get("pages") or {}).values())
    text = pages[0].get("extract", "") if pages else ""
    lines = [l.strip() for l in text.split("\n")]
    for i, line in enumerate(lines):
        if not 30 <= len(line) <= 220 or line.startswith("=") or re.search(r"\b(ISBN|стр\.|с\.\s*\d|№|изд\.)", line):
            continue
        author = ""
        for nxt in lines[i + 1:i + 3]:
            if re.match(r"^[—–-]\s*\S", nxt):
                author = re.sub(r"^[—–-]\s*", "", nxt).split(",")[0].strip()[:60]
                break
        if re.search(r"[а-яё]", line, re.I):
            return {"text": line.strip("«»\"„“ "), "author": author or title}
    return None


def _relevant(query, text):
    """Есть ли в тексте хотя бы половина значимых слов вопроса."""
    want = {w for w in nlp.tokens(query) if w not in nlp.GENERIC and len(w) > 2}
    if not want:
        return True
    have = set(nlp.tokens(text))
    return len(want & have) * 2 >= len(want)


_FACT_WORDS = re.compile(
    r"(?<![а-яёa-z])(кто|что так|что за|что значит|когда|где|почему|зачем|сколько|какой|какая|какое|какие|каков|"
    r"расскажи|объясни|новост|последн|сегодня|сейчас|курс|цена|стоит|стоимость|факт|истори|биограф|сравни|"
    r"лучше|отличи|what|who|when|where|why|how|which)", re.I)


def needs_facts(text: str) -> bool:
    """Вопрос о фактах (а не просьба написать код, сочинить или поболтать) — стоит поискать в интернете."""
    t = (text or "").strip().lower()
    return len(t) >= 6 and bool(_FACT_WORDS.search(t)) and len(nlp.tokens(t)) >= 1


def context_for(query: str, limit_chars: int = 2600) -> dict:
    """Сведения из интернета для нейросети: {"text", "sources": [{"title", "url"}]}.

    Википедия (связный текст) + результаты поиска Google / DuckDuckGo (через посредник на хостинге).
    """
    parts, sources = [], []
    try:
        art = web_article(query)
    except net.NetError:
        art = None
    if art and _relevant(query, art["title"] + " " + art["text"][:600]):
        parts.append(f"[{art['title']} — Википедия]({art['link']}): {art['text'][:1600]}")
        sources.append({"title": art["title"] + " — Википедия", "url": art["link"]})
    for r in web_results(query, 5):
        if any(r["url"] == x["url"] for x in sources) or not _relevant(query, r["title"] + " " + r.get("snippet", "")):
            continue
        parts.append(f"[{_md(r['title'])}]({_safe_url(r['url'])}): {r.get('snippet', '')}")
        sources.append({"title": _md(r["title"]), "url": _safe_url(r["url"])})
    return {"text": "\n\n".join(parts)[:limit_chars], "sources": sources[:5]}


def web_results(query: str, limit: int = 6):
    """Результаты поиска в интернете или [] (нет посредника или поиск не ответил)."""
    try:
        return net.search(query, limit)
    except net.NetError:
        return []


def web_search(query: str):
    """Найти ответ в интернете: (ответ, вложения) или None.

    Сначала Википедия (готовый связный текст), затем поиск Google / DuckDuckGo через посредник на хостинге.
    """
    error = None
    try:
        art = web_article(query)
    except net.NetError as e:
        art, error = None, e
    if art and not _relevant(query, art["title"] + " " + art["text"][:600]):
        art = None  # Википедия нашла что-то не то
    results = [r for r in web_results(query) if _relevant(query, r["title"] + " " + r.get("snippet", ""))]
    if not art and not results:
        if error:
            raise error
        return None
    attachments = []
    if art:
        answer = f"**{art['title']}**\n\n{_first_sentences(art['text'])}"
        if art["lang"] == "en":
            answer += "\n\n*(нашёл только в английской Википедии)*"
        answer += f"\n\nИсточник: [Википедия]({art['link']})" if art["link"] else ""
        if art["image"]:
            attachments.append({"type": "photo", "url": art["image"], "title": art["title"], "source": art["link"]})
        more = [r for r in results if "wikipedia.org" not in r["url"]][:3]
        if more:
            answer += "\n\n**Ещё в интернете:**\n" + "\n".join(f"- [{_md(r['title'])}]({_safe_url(r['url'])})" for r in more)
        return answer, attachments
    lines = ["Вот что нашёл в интернете:"]
    for r in results[:4]:
        snippet = _first_sentences(r.get("snippet") or "", 300)
        lines.append(f"**[{_md(r['title'])}]({_safe_url(r['url'])})**" + (f"\n{_md(snippet)}" if snippet else ""))
    return "\n\n".join(lines), attachments


def _md(text):
    """Текст из интернета без символов разметки (чтобы не ломал ссылки и жирный шрифт)."""
    return re.sub(r"[*`=~]", "", str(text or "")).replace("[", "(").replace("]", ")").strip()


def _safe_url(u):
    return str(u).replace(" ", "%20").replace(")", "%29").replace("(", "%28")
