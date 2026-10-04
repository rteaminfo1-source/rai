"""Подмена интернета для тестов: ответы в формате настоящих сервисов."""
import json
import urllib.parse

GEO = {"results": [{"name": "Москва", "latitude": 55.75, "longitude": 37.62, "country": "Россия"}]}
KAZAN = {"results": [{"name": "Казань", "latitude": 55.79, "longitude": 49.12, "country": "Россия"}]}
FORECAST = {
    "utc_offset_seconds": 10800,
    "current": {"temperature_2m": 12.4, "apparent_temperature": 10.1, "relative_humidity_2m": 71,
                "weather_code": 61, "wind_speed_10m": 4.2, "is_day": 1},
    "daily": {"time": ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"],
              "weather_code": [61, 3, 0, 71], "temperature_2m_max": [14.1, 11.0, 9.5, 2.0],
              "temperature_2m_min": [8.0, 6.2, 3.1, -1.5], "precipitation_probability_max": [80, 20, 0, 60]},
}
RATES = {"result": "success", "base_code": "USD", "time_last_update_utc": "Tue, 29 Sep 2026 00:02:31 +0000",
         "rates": {"USD": 1, "RUB": 92.5, "EUR": 0.92, "CNY": 7.1, "GBP": 0.78, "JPY": 148.0, "KZT": 480.0,
                   "BYN": 3.27, "TRY": 34.0, "UAH": 41.0, "CAD": 1.36}}
WIKI_SEARCH = {"query": {"search": [{"title": "Эйфелева башня", "snippet": "..."}]}}
WIKI_PAGE = {"title": "Эйфелева башня", "extract": "Эйфелева башня — металлическая башня в центре Парижа. "
             "Самая узнаваемая архитектурная достопримечательность Парижа.",
             "thumbnail": {"source": "https://upload.wikimedia.org/eiffel.jpg"},
             "content_urls": {"desktop": {"page": "https://ru.wikipedia.org/wiki/Эйфелева_башня"}}}

SOLAR_EXTRACT = (
    "Солнечная система — планетная система, включающая Солнце и все объекты, которые вращаются вокруг него. "
    "Она сформировалась около 4,6 млрд лет назад из гравитационного сжатия газопылевого облака.\n\n"
    "== Планеты ==\nВ Солнечной системе восемь планет: четыре земные и четыре газовых гиганта. "
    "Меркурий ближе всего к Солнцу. Юпитер — самая большая планета системы. "
    "Сатурн знаменит своими кольцами из льда и камня.\n\n"
    "== Исследования ==\nВ 1957 году был запущен первый искусственный спутник Земли. "
    "В 1961 году Юрий Гагарин впервые полетел в космос. "
    "В 1969 году люди впервые высадились на Луну. "
    "В 1977 году запущены аппараты «Вояджер».\n\n"
    "== В цифрах ==\nМасса Солнца составляет около 99,86% массы всей системы. "
    "Расстояние от Земли до Солнца — около 150 млн км. "
    "Свет от Солнца идёт до Земли около 8 мин и 20 секунд. "
    "Диаметр Юпитера — около 140 тыс. км.\n\n"
    "== Примечания ==\nСсылка на источник, ещё ссылка на источник, и ещё одна ссылка на источник для проверки.\n")
PLANET_PAGES = {
    "Солнечная система": {"extract": SOLAR_EXTRACT, "original": {"source": "https://upload.wikimedia.org/solar.jpg"}},
    "Марс": {"extract": "Марс — четвёртая по удалённости от Солнца планета. Его называют красной планетой из-за оксида железа.",
             "original": {"source": "https://upload.wikimedia.org/mars.jpg"}},
}
IMAGES = {"query": {"pages": {
    "1": {"title": "Файл:Planets2013.jpg", "imageinfo": [{"mime": "image/jpeg", "width": 2000, "height": 1000,
          "thumburl": "https://upload.wikimedia.org/planets.jpg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:Planets2013.jpg"}]},
    "2": {"title": "Файл:Flag of Russia.svg", "imageinfo": [{"mime": "image/svg+xml", "width": 900, "height": 600,
          "thumburl": "https://upload.wikimedia.org/flag.png"}]},
    "3": {"title": "Файл:Jupiter.jpg", "imageinfo": [{"mime": "image/jpeg", "width": 1600, "height": 1600,
          "thumburl": "https://upload.wikimedia.org/jupiter.jpg"}]},
    "4": {"title": "Файл:Tiny.png", "imageinfo": [{"mime": "image/png", "width": 40, "height": 40, "thumburl": "https://upload.wikimedia.org/tiny.png"}]},
}}}
QUOTE_EXTRACT = ("== Цитаты ==\nЗемля — колыбель разума, но нельзя вечно жить в колыбели.\n"
                 "— Константин Циолковский, письмо, 1911\n")

VILLAGES = {
    "малиновк": [
        {"name": "Малиновка", "latitude": 51.31, "longitude": 45.12, "country": "Россия", "country_code": "RU",
         "admin1": "Саратовская область", "population": 1200, "feature_code": "PPL"},
        {"name": "Малиновка", "latitude": 53.85, "longitude": 27.47, "country": "Беларусь", "country_code": "BY",
         "admin1": "Минская область", "admin2": "Минский район", "feature_code": "PPL"}],
    "жданович": [
        {"name": "Ждановичи", "latitude": 53.95, "longitude": 27.42, "country": "Беларусь", "country_code": "BY",
         "admin1": "Минская область", "feature_code": "PPL"}],
}
NOMINATIM = {"энергетиков": [{"lat": "53.13", "lon": "29.21", "name": "Энергетиков",
                               "address": {"country": "Беларусь", "state": "Могилёвская область", "country_code": "by"}}]}

# Казань: статьи рядом, сводка, население (Wikidata), фото достопримечательностей; фото дня NASA
NEAR_KAZAN = {"query": {"geosearch": [
    {"title": "Казань", "lat": 55.796, "lon": 49.108, "dist": 40},
    {"title": "Казанский кремль", "lat": 55.7989, "lon": 49.1061, "dist": 350},
    {"title": "Улица Баумана", "lat": 55.789, "lon": 49.118, "dist": 900},
    {"title": "Мечеть Кул-Шариф", "lat": 55.7983, "lon": 49.1050, "dist": 400},
    {"title": "Храм всех религий", "lat": 55.8000, "lon": 48.9700, "dist": 9000}]}}
KAZAN_SUMMARY = {"title": "Казань", "description": "город в России, столица Республики Татарстан",
                 "extract": "Казань — город в России, столица Республики Татарстан. Крупный порт на левом берегу Волги.",
                 "originalimage": {"source": "https://upload.wikimedia.org/kazan.jpg"}, "wikibase_item": "Q900",
                 "content_urls": {"desktop": {"page": "https://ru.wikipedia.org/wiki/Казань"}}}
KAZAN_POPULATION = {"P1082": [
    {"rank": "normal", "value": {"content": {"amount": "+1257391"}},
     "qualifiers": [{"property": {"id": "P585"}, "value": {"content": {"time": "+2021-01-01T00:00:00Z"}}}]},
    {"rank": "normal", "value": {"content": {"amount": "+1318604"}},
     "qualifiers": [{"property": {"id": "P585"}, "value": {"content": {"time": "+2024-01-01T00:00:00Z"}}}]}]}
APOD = {"title": "The Andromeda Galaxy", "date": "2026-10-04", "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/andromeda.jpg",
        "explanation": "The Andromeda Galaxy is the nearest large galaxy. It is 2.5 million light-years away. Look up."}

calls = []


def fetch_text(address, timeout=10):
    calls.append(address)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(address).query)
    if "geocoding-api" in address:
        name = q.get("name", [""])[0].lower()
        country = q.get("countryCode", [""])[0]
        for prefix, places in VILLAGES.items():
            if name.startswith(prefix):
                return json.dumps({"results": [p for p in places if not country or p["country_code"] == country]})
        if name.startswith("москв"):
            return json.dumps(GEO)
        if name.startswith("казан"):
            return json.dumps(KAZAN)
        return json.dumps({})
    if "nominatim.openstreetmap.org" in address:
        term = q.get("q", [""])[0].lower()
        return json.dumps(next((v for k, v in NOMINATIM.items() if term.startswith(k)), []))
    if "api.open-meteo.com" in address:
        return json.dumps(FORECAST)
    if "er-api" in address:
        return json.dumps(RATES)
    if "mymemory" in address:
        text, pair = q["q"][0], q["langpair"][0]
        return json.dumps({"responseData": {"translatedText": f"[{pair}] {text}"}, "responseStatus": 200})
    if "wikiquote.org/w/api.php" in address:
        if "srsearch" in q:
            hit = "солнечн" in q["srsearch"][0].lower() or "космос" in q["srsearch"][0].lower()
            return json.dumps({"query": {"search": [{"title": "Космос"}] if hit else []}})
        return json.dumps({"query": {"pages": {"1": {"title": "Космос", "extract": QUOTE_EXTRACT}}}})
    if "api.nasa.gov/planetary/apod" in address:
        return json.dumps(APOD)
    if "wikidata.org/w/rest.php" in address and "/Q900/" in address:
        return json.dumps(KAZAN_POPULATION)
    if "wikipedia.org/w/api.php" in address:
        if q.get("list") == ["geosearch"]:
            lat = float(q["gscoord"][0].split("|")[0])
            return json.dumps(NEAR_KAZAN if abs(lat - 55.79) < 0.1 else {"query": {"geosearch": []}})
        if q.get("prop") == ["pageimages"]:
            pages = {str(i): {"title": t, "thumbnail": {"source": "https://upload.wikimedia.org/" + str(i) + ".jpg"}}
                     for i, t in enumerate(q["titles"][0].split("|"))}
            return json.dumps({"query": {"pages": pages}})
        if q.get("generator") == ["images"]:
            return json.dumps(IMAGES)
        if q.get("prop", [""])[0].startswith("extracts"):
            title = q["titles"][0]
            page = dict(PLANET_PAGES.get(title, {}), title=title)
            return json.dumps({"query": {"pages": {"1": page}}})
        term = q["srsearch"][0].lower()
        if "эйфел" in term:
            return json.dumps(WIKI_SEARCH)
        if "солнечн" in term:
            return json.dumps({"query": {"search": [{"title": "Солнечная система"}]}})
        if term.startswith("марс"):
            return json.dumps({"query": {"search": [{"title": "Марс"}]}})
        return json.dumps({"query": {"search": []}})
    if "net.php" in address and "search" in q:
        term = q["search"][0].lower()
        if "радио" in term:
            return json.dumps({"engine": "duckduckgo", "results": [
                {"title": "Кто изобрёл радио", "url": "https://example.ru/radio", "snippet": "Радио изобрели Попов и Маркони в 1895 году."},
                {"title": "Радио — Википедия", "url": "https://ru.wikipedia.org/wiki/Радио", "snippet": "Радио — связь."}]})
        return json.dumps({"engine": "", "results": []})
    if "rest_v1/page/summary" in address:
        title = urllib.parse.unquote(address.rsplit("/", 1)[1]).replace("_", " ")
        if title == "Казань":
            return json.dumps(KAZAN_SUMMARY)
        if title in PLANET_PAGES:
            p = PLANET_PAGES[title]
            return json.dumps({"title": title, "extract": p["extract"], "originalimage": p["original"],
                               "content_urls": {"desktop": {"page": "https://ru.wikipedia.org/wiki/" + title}}})
        return json.dumps(WIKI_PAGE)
    raise AssertionError("неожиданный адрес " + address)
