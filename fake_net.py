"""Подмена интернета для тестов: ответы в формате настоящих сервисов."""
import json
import urllib.parse

GEO = {"results": [{"name": "Москва", "latitude": 55.75, "longitude": 37.62, "country": "Россия"}]}
KAZAN = {"results": [{"name": "Казань", "latitude": 55.79, "longitude": 49.12, "country": "Россия"}]}
FORECAST = {
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

calls = []


def fetch_text(address, timeout=10):
    calls.append(address)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(address).query)
    if "geocoding-api" in address:
        name = q.get("name", [""])[0].lower()
        if name.startswith("москв"):
            return json.dumps(GEO)
        if name.startswith("казан"):
            return json.dumps(KAZAN)
        return json.dumps({})
    if "api.open-meteo.com" in address:
        return json.dumps(FORECAST)
    if "er-api" in address:
        return json.dumps(RATES)
    if "mymemory" in address:
        text, pair = q["q"][0], q["langpair"][0]
        return json.dumps({"responseData": {"translatedText": f"[{pair}] {text}"}, "responseStatus": 200})
    if "wikipedia.org/w/api.php" in address:
        return json.dumps(WIKI_SEARCH if "эйфел" in q["srsearch"][0].lower() else {"query": {"search": []}})
    if "rest_v1/page/summary" in address:
        return json.dumps(WIKI_PAGE)
    raise AssertionError("неожиданный адрес " + address)
