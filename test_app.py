"""Тесты Rai: python -m unittest -v"""

import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock

import app as rai_app
import nlp
import skills
from brain import Brain, RaiError
from versions import VERSIONS, resolve

PRO, FAST, PLUS, SUN = (VERSIONS[k] for k in ("pro", "pro-fast", "pro-plus", "pro-sun"))

import fake_net
import net

_real_fetch = net.fetch_text


def setUpModule():
    # Тесты не ходят в интернет: сервисы отвечают из fake_net.
    net.fetch_text = fake_net.fetch_text
    net._cache.clear()


def tearDownModule():
    net.fetch_text = _real_fetch


class VersionsTest(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(list(VERSIONS), ["pro", "pro-fast", "pro-plus", "pro-sun", "pro-quasar"])
        quasar = VERSIONS["pro-quasar"]
        self.assertTrue(quasar.code and quasar.enrich and quasar.memory and quasar.multi)
        self.assertGreater(quasar.slide_limit, VERSIONS["pro-sun"].slide_limit)
        self.assertEqual(resolve("Quasar").id, "pro-quasar")
        self.assertEqual(resolve("sun").id, "pro-sun")

    def test_aliases(self):
        for raw, expected in [
            (None, "pro"), ("Pro", "pro"), ("Pro Fast", "pro-fast"),
            ("pro_plus", "pro-plus"), ("Rai Pro Sun", "pro-sun"), ("prosun", "pro-sun"),
        ]:
            self.assertEqual(resolve(raw).id, expected, raw)
        self.assertIsNone(resolve("ultra"))


class NlpTest(unittest.TestCase):
    def test_stem_merges_word_forms(self):
        self.assertEqual(nlp.stem("питоне"), nlp.stem("питон"))
        self.assertEqual(nlp.stem("циклы"), nlp.stem("цикл"))

    def test_spellchecker(self):
        sp = nlp.SpellChecker(["привет", "что такое python", "цикл"])
        self.assertEqual(sp.correct("ghbdtn"), "привет")
        self.assertEqual(sp.correct("что такое pyton"), "что такое python")
        self.assertEqual(sp.correct("цыкл"), "цикл")


class SkillsTest(unittest.TestCase):
    def test_calculator(self):
        self.assertEqual(skills.calculator("сколько будет 15*4+2"), "15*4+2 = 62")
        self.assertEqual(skills.calculator("2 плюс 2 умножить на 3"), "2 + 2 * 3 = 8")
        self.assertEqual(skills.calculator("корень из 144"), "√144 = 12")
        self.assertEqual(skills.calculator("20% от 350"), "20% от 350 = 70")
        self.assertEqual(skills.calculator("10/0"), "На ноль делить нельзя.")
        self.assertIsNone(skills.calculator("привет"))
        self.assertIsNone(skills.calculator("__import__('os')"))
        self.assertIsNone(skills.calculator("9**9**9"))

    def test_converter(self):
        self.assertEqual(skills.converter("1 км в м"), "1 км = **1 000** м")
        self.assertEqual(skills.converter("100 c в f"), "100 °C = **212** °F")
        self.assertEqual(skills.converter("1 кг в км"), "Эти единицы нельзя перевести друг в друга.")
        # время, данные, скорость, площадь; «сколько X в Y» в любом порядке слов; склонение и запятая
        self.assertEqual(skills.converter("сколько в часе секунд"), "1 ч = **3 600** с")
        self.assertEqual(skills.converter("сколько секунд в часе"), "1 ч = **3 600** с")
        self.assertEqual(skills.converter("сколько байт в килобайте"), "1 КБ = **1 024** байта")
        self.assertEqual(skills.converter("100 км/ч в м/с"), "100 км/ч = **27,7778** м/с")
        self.assertEqual(skills.converter("сколько соток в гектаре"), "1 га = **100** соток")
        self.assertEqual(skills.converter("переведи 100 км в мили"), "100 км = **62,1371** мили")
        self.assertEqual(skills.converter("2.5 мили в км"), "2,5 мили = **4,0234** км")

    def test_password(self):
        answer = skills.password("сгенерируй пароль 20")
        self.assertEqual(len(answer.rsplit(" ", 1)[1]), 20)

    def test_text_tools(self):
        self.assertEqual(skills.text_tools("переверни: абв"), "вба")
        self.assertTrue(skills.text_tools("сколько слов в: раз два три").startswith("Слов: 3"))

    def test_skill_sets_differ_by_version(self):
        self.assertIsNone(skills.run("сгенерируй пароль", FAST.skills))
        self.assertIsNotNone(skills.run("сгенерируй пароль", PLUS.skills))


class BrainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, version, text, sid="t"):
        return self.brain.answer(version, text, session_id=sid)

    def test_no_false_topic_matches(self):
        # совпадение одного слова — ещё не ответ: «написал» ≠ «куда написать», «вечером» ≠ «добрый вечер»
        q = VERSIONS["pro-quasar"]
        for text, wrong in [("кто написал войну и мир", "contact"), ("что посмотреть вечером", "greeting"),
                            ("сколько дней до нового года", "how_are_you"), ("когда началась вторая мировая война", "debug"),
                            ("как сделать цикл в javascript", "python_loops")]:
            self.assertNotEqual(self.ask(q, text)["intent"], wrong, text)
        for text, right in [("доброе утро всем", "greeting"), ("спасибо большое", "thanks"), ("как дела сегодня", "how_are_you"),
                            ("ок понятно спасибо", "ok"), ("как попасть в команду", "join_team")]:
            self.assertEqual(self.ask(q, text)["intent"], right, text)
        # исправление опечаток не трогает обычные слова и всегда одинаково
        self.assertEqual(self.brain.speller.correct("доброе утро всем"), "доброе утро всем")
        self.assertEqual(self.brain.speller.correct("превет"), "привет")

    def test_syntax_examples(self):
        import syntax
        q = VERSIONS["pro-quasar"]
        for text, head in [("как сделать цикл в javascript", "Циклы на JavaScript"), ("как написать функцию на c++", "Функции на C++"),
                           ("словарь в go", "Словари (ключ → значение) на Go"), ("как сделать класс в php", "Классы и объекты на PHP"),
                           ("ввод с клавиатуры на java", "Ввод с клавиатуры на Java")]:
            r = self.ask(q, text)
            self.assertEqual(r["intent"], "proglang", text)
            self.assertIn(head, r["answer"])
        # конкретная задача — это уже программа, а не справка о синтаксисе
        self.assertEqual(self.ask(q, "напиши функцию на python которая считает факториал")["intent"], "code")
        self.assertEqual(len([1 for t in syntax.S.values() for _ in t]), 114)

    def test_poems_recommendations_support(self):
        q = VERSIONS["pro-quasar"]
        r = self.ask(q, "придумай стих про осень")
        self.assertEqual(r["intent"], "poem")
        self.assertIn("Сочинил Rai", r["answer"])
        self.assertIn("Пушкин", self.ask(q, "прочитай стих пушкина")["answer"])
        self.assertIn("Rai Нейро", self.ask(q, "стих про трактор")["answer"])
        for text in ("посоветуй фильм", "что посмотреть вечером", "посоветуй комедию", "посоветуй книгу фантастика",
                     "во что поиграть", "посоветуй сериал"):
            self.assertEqual(self.ask(q, text)["intent"], "recommend", text)
        self.assertIn("Фильмы: комедия", self.ask(q, "посоветуй комедию")["answer"])
        for text in ("мне грустно", "я устал", "мне скучно", "не могу уснуть", "завтра экзамен, волнуюсь"):
            self.assertEqual(self.ask(q, text)["intent"], "support", text)
        crisis = self.ask(q, "я не хочу жить")
        self.assertEqual(crisis["intent"], "crisis")
        self.assertIn("8-800-2000-122", crisis["answer"])
        # игру по-прежнему делает генератор кода
        self.assertEqual(self.ask(q, "сделай игру змейка")["intent"], "code")

    def test_dates_and_units(self):
        q = VERSIONS["pro-quasar"]
        with mock.patch("skills._now", return_value=__import__("datetime").datetime(2026, 10, 3, 12, 0)):
            self.assertIn("**90 дней**", self.ask(q, "сколько дней до нового года")["answer"])
            self.assertIn("**156 дней**", self.ask(q, "сколько дней до 8 марта")["answer"])
            self.assertIn("**81 год**", self.ask(q, "сколько лет прошло с 1945 года")["answer"])
            self.assertIn("**пятница**", self.ask(q, "какой день недели будет 1 января 2027")["answer"])
            self.assertIn("была **среда**", self.ask(q, "какой день недели был 9 мая 1945")["answer"])
            self.assertIn("13 октября 2026", self.ask(q, "какое число будет через 10 дней")["answer"])
            self.assertIn("високосный", self.ask(q, "високосный ли 2028 год")["answer"])
        r = self.ask(q, "переведи 100 км в мили")
        self.assertEqual((r["intent"], r["answer"]), ("skill", "100 км = **62,1371** мили"))

    def test_knowledge_in_all_versions(self):
        for v in VERSIONS.values():
            self.assertEqual(self.ask(v, "привет")["intent"], "greeting", v.id)
            self.assertEqual(self.ask(v, "что такое питон?")["intent"], "python", v.id)
            self.assertEqual(self.ask(v, "что такое джаваскрипт")["intent"], "javascript", v.id)

    def test_generic_words_do_not_match(self):
        for v in VERSIONS.values():
            self.assertIsNone(self.ask(v, "что такое рхп")["intent"], v.id)

    def test_typos_only_in_plus_and_sun(self):
        self.assertIsNone(self.ask(PRO, "ghbdtn")["intent"])
        self.assertEqual(self.ask(PLUS, "ghbdtn")["intent"], "greeting")
        self.assertEqual(self.ask(SUN, "что такое pyton")["intent"], "python")

    def test_name_memory(self):
        self.ask(PLUS, "меня зовут артём", "a")
        self.assertEqual(self.ask(PLUS, "как меня зовут", "a")["answer"], "Вас зовут Артём.")
        self.assertIn("Артём", self.ask(PLUS, "спасибо", "a")["answer"])
        # Другая сессия имя не знает.
        self.assertNotIn("Артём", self.ask(PLUS, "как меня зовут", "b")["answer"])
        # Pro имя не запоминает.
        self.assertIn("Pro Plus", self.ask(PRO, "как меня зовут", "a")["answer"])

    def test_name_from_history_without_session(self):
        history = [{"role": "user", "content": "Меня зовут Ира"}, {"role": "assistant", "content": "Ок"}]
        r = self.brain.answer(PLUS, "как меня зовут", history=history)
        self.assertEqual(r["answer"], "Вас зовут Ира.")

    def test_more(self):
        self.ask(PLUS, "кто ты", "m")
        self.assertEqual(self.ask(PLUS, "подробнее", "m")["answer"], self.brain.intents["who_are_you"]["more"])
        first = self.ask(PLUS, "расскажи шутку", "m")["answer"]
        self.assertNotEqual(self.ask(PLUS, "ещё", "m")["answer"], first)

    def test_sun_memory_and_multi(self):
        self.assertIn("только Rai Pro Sun", self.ask(PLUS, "запомни, что я люблю чай")["answer"])
        self.ask(SUN, "запомни, что мой любимый цвет красный", "s")
        self.assertIn("красный", self.ask(SUN, "какой мой любимый цвет", "s")["answer"])
        self.assertIn("красный", self.ask(SUN, "что ты помнишь", "s")["answer"])
        self.ask(SUN, "забудь всё", "s")
        self.assertIn("ничего", self.ask(SUN, "что ты помнишь", "s")["answer"])
        self.assertEqual(self.ask(SUN, "что такое html? а css?")["intent"], ["html", "css"])

    def test_sun_is_detailed(self):
        more = self.brain.intents["python"]["more"]
        self.assertIn(more, self.ask(SUN, "что такое python")["answer"])
        self.assertNotIn(more, self.ask(PRO, "что такое python")["answer"])

    def test_suggestions(self):
        r = self.ask(PLUS, "расскажи про php сервер")
        self.assertTrue(r["intent"] or "Возможно" in r["answer"])

    def test_teach(self):
        self.brain.teach(["когда созвон команды"], "Созвон по пятницам в 19:00.")
        self.assertEqual(self.ask(PRO, "когда созвон?")["answer"], "Созвон по пятницам в 19:00.")
        with open(self.brain.learned_path, encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)["intents"]), 1)
        with self.assertRaises(RaiError):
            self.brain.teach([], "x")

    def test_validation(self):
        with self.assertRaises(RaiError):
            self.ask(PRO, "   ")
        with self.assertRaises(RaiError):
            self.ask(PRO, "а" * 10000)


class CreativeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_image(self):
        r = self.brain.answer(PRO, "нарисуй закат над морем")
        image = r["attachments"][0]
        self.assertEqual(image["type"], "image")
        self.assertTrue(image["svg"].startswith("<svg"))
        self.assertIn("Закат", image["title"])
        self.assertIn("не умею", self.brain.answer(PRO, "нарисуй кота")["answer"])
        self.assertEqual(self.brain.answer(FAST, "нарисуй закат")["attachments"], [])

    def test_logo_text_is_escaped(self):
        import creative
        svg = creative.make_image('логотип <script>alert(1)</script>')["svg"]
        self.assertNotIn("<script", svg)

    def test_slides(self):
        self.assertEqual(self.brain.answer(PRO, "сделай презентацию про python")["attachments"], [])
        deck = self.brain.answer(SUN, "сделай презентацию про python")["attachments"][0]
        kinds = [s["kind"] for s in deck["slides"]]
        self.assertEqual((kinds[0], kinds[-1]), ("title", "end"))
        self.assertIn("code", kinds)
        self.assertTrue(deck["slides"][0].get("image"))
        self.assertTrue(all(s.get("transition") for s in deck["slides"]))
        glossary_deck = self.brain.answer(PLUS, "презентация про космос")["attachments"][0]
        self.assertGreaterEqual(len(glossary_deck["slides"]), 4)
        # никаких «замените этот текст» — только настоящий материал
        all_text = json.dumps(glossary_deck, ensure_ascii=False)
        self.assertNotIn("Замените", all_text)
        self.assertNotIn("ваш текст", all_text)
        # нет материала — нет пустой презентации
        r = self.brain.answer(PLUS, "презентация про абвгдейка")
        self.assertEqual(r["attachments"], [])
        self.assertIn("не нашёл материала", r["answer"])

    def test_slide_colors(self):
        import creative
        deck = self.brain.answer(SUN, "сделай презентацию про python в фиолетовых тонах")["attachments"][0]
        self.assertEqual(deck["title"], "Python")
        self.assertEqual(deck["theme"]["accent"], "#7c3aed")
        th = creative.deck_theme("презентация про море, фон белый, акцент зелёный")
        self.assertEqual((th["bg"], th["accent"]), ("#ffffff", "#16a34a"))
        th = creative.deck_theme("чёрно-золотая презентация")
        self.assertEqual((th["bg"], th["accent"]), ("#0b0b0c", "#d4af37"))
        th = creative.deck_theme("в тёмно-синих и оранжевых цветах")
        self.assertEqual((th["bg"], th["accent"]), ("#0b1f4d", "#f97316"))
        self.assertEqual(creative.deck_theme("презентация про #ff00aa кошек")["accent"], "#ff00aa")
        self.assertEqual(creative.slides_topic("презентация про космос в синих тонах"), "космос")
        # картинки рисуются в цветах темы
        self.assertIn("#7c3aed", deck["slides"][0]["image"])

    def test_slide_kinds(self):
        import creative
        # годы -> хронология, крупные числа -> «цифры»
        tl = creative._as_timeline(["В 1991 году вышел Python 0.9", "2000 — Python 2.0", "**2008** — вышел Python 3"])
        self.assertEqual([x["date"] for x in tl], ["1991", "2000", "2008"])
        self.assertEqual(tl[0]["text"], "Вышел Python 0.9")
        st = creative._as_stats(["Население — около 146 млн человек", "Более 190 народов", "85% жителей — горожане"])
        self.assertEqual([x["value"] for x in st], ["≈ 146 млн", "190+", "85%"])
        self.assertIsNone(creative._as_stats(["Python прост", "Много библиотек", "Популярен"]))
        self.assertIsNone(creative._as_timeline(["Первый пункт", "Второй", "Третий"]))
        article = {"title": "Космонавтика", "answers": ["История полётов в космос.\n\n- 1957 — первый спутник\n"
                                                         "- 1961 — полёт Гагарина\n- 1969 — высадка на Луну"]}
        deck = creative.make_slides("космонавтика", [article, {"title": "Ракета", "answers": ["Ракета летит за счёт реактивной тяги двигателя."]}])
        self.assertIn("timeline", [s["kind"] for s in deck["slides"]])
        # один пункт не превращается в список из одного пункта
        self.assertNotIn(1, [len(s["bullets"]) for s in deck["slides"] if s["kind"] == "bullets"])
        # название — в именительном падеже
        self.assertEqual(creative.nominative("историю древнего рима"), "история древнего рима")
        self.assertEqual(creative.nominative("солнечную систему"), "солнечная система")
        self.assertEqual(creative.nominative("кенгуру"), "кенгуру")
        self.assertEqual(self.brain.answer(SUN, "сделай презентацию про историю python")["attachments"][0]["title"][:7], "История")

    def test_archive(self):
        r = self.brain.answer(PRO, "сделай архив")
        self.assertEqual(r["attachments"][0]["type"], "archive")
        # «Как сделать презентацию?» — вопрос, а не просьба.
        self.assertEqual(self.brain.answer(PLUS, "как сделать презентацию")["attachments"], [])

    def test_glossary_capitals_tables(self):
        self.assertEqual(self.brain.answer(PRO, "что такое фотосинтез")["intent"], "glossary")
        self.assertEqual(self.brain.answer(PLUS, "что такое фатосинтез")["intent"], "glossary")
        self.assertEqual(self.brain.answer(PRO, "что такое сервер")["intent"], "glossary")
        self.assertIn("Париж", self.brain.answer(PRO, "столица франции")["answer"])
        self.assertIn("Сеул", self.brain.answer(PRO, "какая столица южной кореи?")["answer"])
        self.assertIn("| 7 × 3 | **21** |", self.brain.answer(PRO, "таблица умножения на 7")["answer"])
        unknown = self.brain.answer(SUN, "что такое квазар")["answer"]
        self.assertIn("запомни, что квазар", unknown)


class OnlineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))
        net._cache.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, text, version=None, sid="o"):
        return self.brain.answer(version or PLUS, text, session_id=sid)

    def test_weather_with_picture_and_city_memory(self):
        r = self.ask("какая погода в Казани?")
        self.assertEqual(r["intent"], "weather")
        self.assertIn("Казань", r["answer"])
        self.assertIn("| завтра |", r["answer"])
        self.assertEqual(r["attachments"][0]["type"], "image")
        self.assertIn("+12°", r["attachments"][0]["svg"])
        self.assertIn("Казань", self.ask("а погода?")["answer"])      # город запомнился
        self.assertIn("Москва", self.ask("погода в москве")["answer"])  # «москве» -> Москва

    def test_web_presentation(self):
        import creative
        req = creative.parse_deck_request("презентация про историю России на 10 слайдов, разделы: Древняя Русь, империя и СССР, с таблицей")
        self.assertEqual((req["topic"], req["count"], req["sections"]), ("историю России", 10, ["Древняя Русь", "империя", "СССР"]))
        self.assertEqual(req["want"], {"table"})
        self.assertEqual(creative.parse_deck_request("про python без картинок")["pictures"], "none")
        self.assertEqual(creative.parse_deck_request("презентация сравни кошек и собак")["compare"], ["кошек", "собак"])

        r = self.ask("подготовь презентацию о Солнечной системе на 12 слайдов с таблицей и цитатой, обязательно про Марс", SUN)
        deck = r["attachments"][0]
        kinds = [s["kind"] for s in deck["slides"]]
        self.assertEqual(deck["title"], "Солнечная система")
        self.assertEqual(len(kinds), 12)
        for kind in ("table", "quote", "agenda"):
            self.assertIn(kind, kinds)
        self.assertIn("Марс", [s["title"] for s in deck["slides"]])                        # заказанный раздел
        self.assertEqual(deck["slides"][0]["pic"], "https://upload.wikimedia.org/solar.jpg")  # фото из интернета
        self.assertNotIn("https://upload.wikimedia.org/flag.png", json.dumps(deck))          # флаги и значки не берём
        quote = next(s for s in deck["slides"] if s["kind"] == "quote")
        self.assertEqual(quote["author"], "Константин Циолковский")
        self.assertIn("Википедии", r["answer"])
        # в плане — только то, что есть на слайдах
        agenda = next(s for s in deck["slides"] if s["kind"] == "agenda")
        titles = {s.get("title") for s in deck["slides"]}
        self.assertTrue(all(t in titles for t in agenda["items"]))
        # просили цифры и хронологию — они есть; без картинок — ни фото, ни рисунков
        deck = self.ask("презентация про солнечную систему без картинок на 7 слайдов с цифрами и хронологией", SUN)["attachments"][0]
        kinds = [s["kind"] for s in deck["slides"]]
        self.assertIn("stats", kinds)
        self.assertIn("timeline", kinds)
        self.assertFalse(any(s.get("pic") or s.get("image") for s in deck["slides"]))
        # сравнение
        deck = self.ask("презентация сравни кошек и собак", SUN)["attachments"][0]
        cmp = next(s for s in deck["slides"] if s["kind"] == "compare")
        self.assertEqual((cmp["left"]["title"], cmp["right"]["title"]), ("Кошка", "Собака"))

    def test_web_search_through_hosting(self):
        # без посредника на хостинге — только Википедия; с ним — ищет в интернете (Google / DuckDuckGo)
        self.assertNotIn("example.ru", self.ask("кто изобрёл радио", SUN)["answer"])
        net.PROXY = "https://rai.test/net.php"
        try:
            r = self.ask("кто изобрёл радио", SUN)
        finally:
            net.PROXY = ""
        self.assertEqual(r["intent"], "web")
        self.assertIn("Попов", r["answer"])
        self.assertIn("(https://example.ru/radio)", r["answer"])
        self.assertTrue(any("net.php?search=" in c for c in fake_net.calls))

    def test_currency(self):
        self.assertIn("**100 USD = 9 250 RUB**", self.ask("100 долларов в рублях")["answer"])
        self.assertIn("1 USD = 92,5 RUB", self.ask("курс доллара")["answer"])
        self.assertIn("50 BYN", self.ask("50 белорусских рублей в рублях")["answer"])
        self.assertIn("| евро | EUR |", self.ask("курсы валют")["answer"])
        # «сумма», «Лариса», «1 фунт в кг» — не валюты
        self.assertNotEqual(self.ask("какая сумма у Ларисы")["intent"], "currency")
        self.assertEqual(self.ask("1 фунт в кг")["intent"], "skill")

    def test_translate(self):
        import online
        self.assertEqual(online.detect_language("Guten Morgen, wie geht es dir?"), "de")
        self.assertEqual(online.detect_language("¿Cómo estás?"), "es")
        self.assertEqual(online.detect_language("Привіт, як справи?"), "uk")
        self.assertEqual(online.detect_language("こんにちは"), "ja")
        self.assertEqual(online.parse_translate("переведи на английский: доброе утро"), ("доброе утро", None, "en"))
        self.assertEqual(online.parse_translate("как по-немецки кошка"), ("кошка", None, "de"))
        r = self.ask("переведи с английского на французский: good morning")
        self.assertIn("[en|fr] good morning", r["answer"])
        self.assertIn("[de|ru]", self.ask("переведи Guten Morgen")["answer"])

    def test_web_search(self):
        r = self.ask("найди в интернете эйфелева башня")
        self.assertEqual(r["intent"], "web")
        self.assertIn("Парижа", r["answer"])
        self.assertEqual(r["attachments"][0]["type"], "photo")
        # неизвестное — Rai сам идёт искать
        self.assertEqual(self.ask("что такое эйфелева башня")["intent"], "web")
        self.assertIn("умеют Rai Pro", self.ask("найди в интернете эйфелева башня", FAST)["answer"])

    def test_no_internet(self):
        def down(*a, **k):
            raise net.NetError("NetworkError: Failed to execute 'send' on 'XMLHttpRequest'", offline=True)
        with mock.patch.object(net, "fetch_text", down):
            r = self.ask("погода в Казани")
            self.assertIn("нет связи", r["answer"])
            self.assertNotIn("XMLHttpRequest", r["answer"])  # без технических подробностей
            self.assertTrue(r["offline"])                     # страница может отдать вопрос нейросети
            self.assertIn("net.php", r["answer"])             # подсказка: посредник на хостинге
            self.assertIn("нет связи", self.ask("курс доллара")["answer"])
            self.assertIn("не получилось перевести", self.ask("переведи на английский: доброе утро")["answer"].lower())
            answer = self.ask("что такое квазар", SUN)["answer"]
            self.assertIn("запомни, что квазар", answer)
            self.assertIn("не получилось", answer)
            # окно просмотра, где интернет закрыт: сразу объясняем, куда идти
            with mock.patch.object(net, "SANDBOX", True):
                self.assertIn("rai.rteam.info", self.ask("погода в Минске")["answer"])
                self.assertIn("rai.rteam.info", self.ask("https://www.tiktok.com/@user/video/1", SUN)["answer"])
        self.assertFalse(self.ask("привет")["offline"])

    def test_weather_any_place(self):
        # город без предлога, в любом порядке, с деревнями и районами
        for q, where in (("погода минск", "Минск, Беларусь"), ("Минск погода", "Минск, Беларусь"),
                         ("температура гомель завтра", "Гомель, Беларусь"),
                         ("погода в деревне Малиновка Минского района", "Малиновка, Минская область, Беларусь"),
                         ("погода в Ждановичах", "Ждановичи, Минская область, Беларусь"),
                         ("погода в посёлке Энергетиков Бобруйск", "Энергетиков, Могилёвская область, Беларусь")):
            self.assertIn("## Погода: " + where, self.ask(q, sid="p" + q)["answer"], q)
        # одноимённые сёла: говорим, какое показали, и как уточнить
        answer = self.ask("погода Малиновка", sid="amb")["answer"]
        self.assertIn("несколько", answer)
        self.assertIn("Минская область", answer)
        # после «погода минск» — сначала Беларусь; «а в …?» — продолжение
        self.ask("погода минск", sid="home")
        self.assertIn("Малиновка, Минская область", self.ask("а в Малиновке?", sid="home")["answer"])
        # место не указано — честно говорим, для какого города погода
        self.assertIn("Место не указано", self.ask("какая погода сегодня", sid="none")["answer"])

    def test_memes(self):
        import memes
        self.assertIn("Маргрит ван Бревоорт", self.ask("что за мем ждун", SUN)["answer"])
        self.assertEqual(self.ask("откуда мем шлепа", SUN)["intent"], "meme")
        self.assertIn("Скуф", self.ask("что значит скуф", SUN)["answer"])
        self.assertIn("Мемы 2025 года", self.ask("мемы 2025", SUN)["answer"])
        self.assertNotEqual(self.ask("что такое сигма", SUN)["intent"], "meme")   # без слова «мем» — не мем
        self.assertEqual(self.ask("что за мем сигма", SUN)["intent"], "meme")
        self.assertEqual(memes.topic("что за мем бобр курва"), "бобр курва мем")    # нет в базе — ищем в интернете
        self.assertGreaterEqual(len(memes.MEMES), 50)

    def test_cities_offline(self):
        import cities
        for phrase, name in (("Минске", "Минск"), ("Нижнем Новгороде", "Нижний Новгород"), ("Ростове-на-Дону", "Ростов-на-Дону"),
                             ("Питере", "Санкт-Петербург"), ("Уфе", "Уфа"), ("Перми", "Пермь"), ("Орле", "Орёл"), ("Бресте", "Брест")):
            self.assertEqual(cities.find(phrase)["name"], name, phrase)
        self.assertIsNone(cities.find("Березино"))
        fake_net.calls.clear()
        r = self.ask("какая погода в минске?")
        self.assertIn("Минск, Беларусь", r["answer"])
        self.assertFalse(any("geocoding" in c for c in fake_net.calls))  # город из справочника — без лишнего запроса

    def test_programming_languages(self):
        self.assertIn("```go", self.ask("hello world на go")["answer"])
        self.assertIn("**Rust**", self.ask("что такое rust")["answer"])
        self.assertIn("**C#**", self.ask("что такое c#")["answer"])
        self.assertIn("Языки программирования", self.ask("какие языки программирования ты знаешь")["answer"])
        import proglangs
        self.assertGreaterEqual(len(proglangs.LANGUAGES), 45)
        # короткие названия («c», «r») только в явном контексте
        self.assertIsNone(proglangs.find_language("у меня есть r и c"))


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        rai_app.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))
        self.client = rai_app.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_index_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"<title>Rai", resp.data)
        # Формы входа в самой странице нет (они на login.php хостинга); есть вкладка Code
        self.assertNotIn(b"authDialog", resp.data)
        self.assertIn(b'src="code.js"', resp.data)
        resp.close()

    def test_standalone_build(self):
        import re
        import build_standalone
        html = build_standalone.build()
        self.assertNotIn('src="code.js"', html)
        self.assertIn("window.RaiCode", html)
        self.assertIn("window.RaiNeuro", html)  # нейросеть в браузере встроена в страницу
        self.assertIn("window.RaiPptx", html)  # экспорт в PowerPoint тоже
        scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S)
        # «<!--» внутри <script> ломает разбор страницы
        self.assertFalse(any("<!--" in s for s in scripts))
        payload = re.search(r'<script type="application/json" id="rai-files">(.*?)</script>', html, re.S).group(1)
        files = json.loads(payload)
        self.assertIn("codeai.py", files)
        self.assertIn("codelib.py", files)
        # сборка для хостинга только с PHP и HTML: Python и распознавание — с CDN
        cdn = build_standalone.build(cdn=True)
        self.assertNotIn('"pyodide/",', cdn)
        self.assertIn("window.RAI_OCR_LOCAL = false", cdn)
        self.assertIn("webgen.py", cdn)

    def test_versions_endpoint(self):
        data = self.client.get("/api/versions").get_json()
        self.assertEqual([v["id"] for v in data["versions"]], list(VERSIONS))

    def test_chat_js_compatible(self):
        resp = self.client.post("/rai.php", json={"message": "Привет"})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["answer"])
        self.assertEqual(data["version"], "pro")

    def test_version_in_path_body_and_form(self):
        self.assertEqual(self.client.post("/api/chat/pro-sun", json={"message": "x"}).get_json()["version"], "pro-sun")
        body = {"message": "x", "version": "Pro Fast"}
        self.assertEqual(self.client.post("/api/chat", json=body).get_json()["version"], "pro-fast")
        self.assertEqual(self.client.post("/rai", data=body).get_json()["version"], "pro-fast")

    def test_errors(self):
        r = self.client.post("/api/chat", json={"message": "x", "version": "ultra"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("answer", r.get_json())
        self.assertEqual(self.client.post("/api/chat", json={"message": " "}).status_code, 400)

    def test_teach_requires_token(self):
        body = {"patterns": ["пароль от wifi"], "answer": "Спросите у админа."}
        with mock.patch.dict(os.environ, {"RAI_ADMIN_TOKEN": ""}):
            self.assertEqual(self.client.post("/api/teach", json=body).status_code, 403)
        with mock.patch.dict(os.environ, {"RAI_ADMIN_TOKEN": "secret"}):
            self.assertEqual(self.client.post("/api/teach", json=body).status_code, 403)
            ok = self.client.post("/api/teach", json=body, headers={"X-Rai-Token": "secret"})
            self.assertEqual(ok.status_code, 200)
        answer = self.client.post("/api/chat", json={"message": "пароль от wifi"}).get_json()["answer"]
        self.assertEqual(answer, "Спросите у админа.")



class CodeAITest(unittest.TestCase):
    BUGGY = ('import os\nage = input("Возраст? ")\nif age > 18\n    print "взрослый"\n'
             'for i in range(len(items)):\n    print(nme)\n')

    def test_syntax_error_in_russian(self):
        import codeai
        issues = codeai.check_python(self.BUGGY)
        self.assertEqual(issues[0]["severity"], "error")
        self.assertIn("двоеточия", issues[0]["message"])
        self.assertEqual(issues[0]["line"], 3)

    def test_fix_then_deep_check(self):
        import codeai
        fixed, changes = codeai.fix_python(self.BUGGY)
        self.assertIn("if age > 18:", fixed)
        self.assertIn('print("взрослый")', fixed)
        self.assertEqual(len(changes), 2)
        messages = " ".join(i["message"] for i in codeai.check_python(fixed))
        self.assertIn("input() возвращает строку", messages)
        self.assertIn("«items» нигде не определено", messages)
        self.assertIn("«os» импортировано, но не используется", messages)
        hint = next(i["hint"] for i in codeai.check_python("name = 1\nprint(nme)") if "nme" in i["message"])
        self.assertIn("«name»", hint)

    def test_explain_and_comment(self):
        import codeai
        code = "def square(x):\n    return x * x\n\nfor i in range(3):\n    print(square(i))\n"
        text = codeai.explain(code)
        self.assertIn("объявляет функцию square(x)", text)
        self.assertIn("перебирает числа от 0 до 3", text)
        commented = codeai.comment_python(code)
        self.assertIn("# Объявляет функцию square(x)", commented)
        compile(commented, "x.py", "exec")  # комментарии не ломают код

    def test_other_languages(self):
        import codeai
        lang, issues = codeai.check_code("function f() {\n  if (a == 1) {\n    return 1;\n}\n", None)
        self.assertEqual(lang, "javascript")
        self.assertTrue(any("не закрыта" in i["message"] for i in issues))
        lang, issues = codeai.check_code("<!DOCTYPE html><html><body><div><p>x</body></html>", None)
        self.assertTrue(any("<div> не закрыт" in i["message"] for i in issues))
        lang, issues = codeai.check_code('{"a": 1,}', "json")
        self.assertEqual(issues[0]["severity"], "error")

    def test_generate(self):
        import codeai
        import codelib
        r = codeai.chat("напиши игру змейка")
        self.assertEqual((r["lang"], r["filename"]), ("html", "index.html"))
        self.assertIn("<canvas", r["code"])
        self.assertEqual(codeai.chat("калькулятор на c++")["lang"], "cpp")
        self.assertEqual(codeai.chat("напиши сортировку")["filename"], "main.py")
        self.assertIsNone(codeai.chat("что такое html?"))
        self.assertIsNone(codeai.chat("как дела"))
        for key, t in codelib.T.items():  # весь Python в библиотеке синтаксически верный
            if "python" in t["codes"]:
                compile(t["codes"]["python"], key, "exec")

    def test_code_in_chat_and_api(self):
        tmp = tempfile.TemporaryDirectory()
        brain = Brain(learned_path=os.path.join(tmp.name, "l.json"))
        quasar = VERSIONS["pro-quasar"]
        r = brain.answer(quasar, "найди ошибку:\n```python\nfor i in range(3)\n    print(i)\n```")
        self.assertEqual(r["intent"], "code")
        self.assertIn("двоеточия", r["answer"])
        r = brain.answer(quasar, "напиши игру крестики нолики")
        self.assertEqual(r["attachments"][0]["type"], "code")
        self.assertIn("Pro Quasar", brain.answer(PRO, "напиши игру змейка")["answer"])
        client = rai_app.app.test_client()
        data = client.post("/api/code", json={"action": "fix", "code": "if x == None\n    pass\n"}).get_json()
        self.assertIn("if x is None:", data["code"])
        tmp.cleanup()



class BuildersTest(unittest.TestCase):
    """Сайты по описанию, новые программы и функции."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "l.json"))
        self.q = VERSIONS["pro-quasar"]

    def tearDown(self):
        self.tmp.cleanup()

    def code_of(self, text, session="b1"):
        r = self.brain.answer(self.q, text, session)
        att = [a for a in r["attachments"] if a["type"] == "code"]
        return r, (att[0] if att else None)

    def test_site_spec(self):
        import webgen
        spec = webgen.new_spec("сайт кофейни зерно в тёмных тонах, меню: капучино 190, латте 220. почта z@z.ru")
        self.assertEqual((spec["type"], spec["title"], spec["theme"]), ("cafe", "Зерно", "dark"))
        menu = next(s for s in spec["sections"] if s["kind"] == "menu")
        self.assertEqual(menu["items"][1], {"title": "Латте", "price": "220 ₽", "text": ""})
        self.assertEqual(spec["contacts"]["email"], "z@z.ru")
        # «сервис» — не серый цвет, «работы» — не бот
        self.assertEqual(webgen.new_spec("сайт автосервиса «Мотор»")["accent"], "#e10600")
        self.assertEqual(webgen.new_spec("сайт с разделами: о нас, наши работы")["type"], "business")
        html = webgen.render(spec)
        self.assertEqual(webgen.spec_from_html(html)["title"], "Зерно")
        spec2, done = webgen.edit_spec(spec, "добавь раздел цены")
        self.assertIn("Цены", [s["title"] for s in spec2["sections"]])
        self.assertIsNone(webgen.edit_spec(spec, "непонятная просьба")[1])

    def test_site_in_chat_and_edits(self):
        r, att = self.code_of("сделай сайт кофейни зерно")
        self.assertTrue(att and att["site"] and att["filename"] == "index.html")
        r, att = self.code_of("добавь раздел цены")
        self.assertIn("Сделано", r["answer"])
        self.assertIn("Цены", att["code"])
        r, att = self.code_of("сделай синим")
        self.assertIn("#1e5bff", att["code"])

    def test_site_about_topic_uses_knowledge(self):
        r, att = self.code_of("сделай сайт про python", "b2")
        self.assertIn("Python", att["code"])
        self.assertNotIn("Оставьте заявку", att["code"])

    def test_programs(self):
        for text, title in [("напиши игру тетрис", "Тетрис"), ("сделай приложение погоды", "Приложение погоды"),
                            ("сделай конвертер валют", "Конвертер валют"), ("калькулятор ИМТ", "Калькулятор ИМТ"),
                            ("напиши функцию которая считает среднее списка", "Среднее арифметическое"),
                            ("шифр цезаря на javascript", "Шифр Цезаря"), ("напиши бота для дискорда", "Discord-бот")]:
            r, att = self.code_of(text, "p-" + text)
            self.assertTrue(att, text)
            self.assertEqual(att["title"], title)
        # вопросы остаются вопросами
        self.assertEqual(self.brain.answer(self.q, "таблица умножения на 7", "x")["intent"], "skill")
        self.assertNotEqual(self.brain.answer(self.q, "прогноз погоды", "x")["intent"], "code")

    def test_generated_functions_run(self):
        import contextlib
        import io
        import funcgen
        for _, title, python, _ in funcgen.F:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(python, title, "exec"), {"__name__": "__main__"})

    def test_code_api_edit(self):
        import webgen
        html = webgen.render(webgen.new_spec("сайт пекарни"))
        data = rai_app.app.test_client().post("/api/code", json={"action": "edit", "code": html, "prompt": "убери отзывы"}).get_json()
        self.assertIn("убрал раздел", data["answer"])
        self.assertNotIn(">Отзывы<", data["code"])


class ScreenTest(unittest.TestCase):
    """Текст со скриншота или записи экрана: вопросы, варианты ответов, примеры, код."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "l.json"))
        self.q = VERSIONS["pro-quasar"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_questions_options_and_math(self):
        text = "Реши [[screen]]\n1. Столица Франции?\nа) Берлин\n6) Париж\n2. Сколько будет 12 * 7 =\nВычисли 2^10"
        r = self.brain.answer(self.q, text, "s")
        self.assertEqual(r["intent"], "screen")
        self.assertIn("**Ответ:** Париж", r["answer"])
        self.assertIn("= 84", r["answer"])
        self.assertIn("= 1024", r["answer"])

    def test_code_and_empty(self):
        r = self.brain.answer(self.q, "[[screen]]\ndef f(x)\n    return x*2", "s")
        self.assertIn("Код на скриншоте", r["answer"])
        self.assertIn("двоеточия", r["answer"])
        self.assertIn("не нашёл текста", self.brain.answer(self.q, "[[screen]]\n@# ~", "s")["answer"])

    def test_long_screen_text_allowed(self):
        long = "[[screen]]\n" + "Это длинный текст с экрана. " * 400
        self.assertEqual(self.brain.answer(self.q, long, "s")["intent"], "screen")


class HostingTest(unittest.TestCase):
    """Пакет для хостинга и PHP: свой сервер нейросети (ai.php) и посредник для интернета (net.php)."""

    def test_package(self):
        import make_hosting
        with tempfile.TemporaryDirectory() as out:
            with mock.patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET": "", "SSO_SECRET": ""}):
                make_hosting.build(out)
            rai = os.path.join(out, "rai.rteam.info")
            for name in ("index.html", "ai.php", "net.php", "login.php", "config.php"):
                self.assertTrue(os.path.isfile(os.path.join(rai, name)), name)
            for root, _, files in os.walk(out):
                for f in files:  # на хостинге только PHP и HTML (+ необязательные настройки сервера)
                    self.assertTrue(f.endswith((".php", ".html")) or f in (".htaccess", "web.config", "ПРОЧТИ.txt"), f)
            with open(os.path.join(rai, "index.html"), encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("ai.php", page)
            self.assertIn("window.RaiNeuro", page)

    @unittest.skipUnless(__import__("shutil").which("php"), "нет PHP")
    def test_php_servers(self):
        import http.server
        import socket
        import subprocess
        import threading
        import time
        import urllib.request
        base = os.path.dirname(os.path.abspath(__file__))
        for name in os.listdir(os.path.join(base, "hosting", "rai")):
            if name.endswith(".php"):
                r = subprocess.run(["php", "-l", os.path.join(base, "hosting", "rai", name)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        def free_port():
            with socket.socket() as sk:
                sk.bind(("127.0.0.1", 0))
                return sk.getsockname()[1]
        with tempfile.TemporaryDirectory() as up, tempfile.TemporaryDirectory() as site:
            lib = os.path.join(up, "npm", "@mlc-ai", "web-llm@0.2.85", "lib")
            os.makedirs(lib)
            with open(os.path.join(lib, "index.js"), "w") as fh:
                fh.write("export const ok = 1;\n" * 1000)
            with open(os.path.join(up, "page.html"), "w", encoding="utf-8") as fh:
                fh.write("<html><head><title>Радио</title><script>var secret=1</script></head><body><nav>меню меню меню меню меню меню</nav>"
                         "<p>Радио изобрели Попов и Маркони в 1895 году.</p></body></html>")
            class Quiet(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *a, **k):
                    super().__init__(*a, directory=up, **k)

                def log_message(self, *a):
                    pass
            upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
            threading.Thread(target=upstream.serve_forever, daemon=True).start()
            uport = upstream.server_address[1]
            for name in ("ai.php", "net.php"):
                with open(os.path.join(base, "hosting", "rai", name), encoding="utf-8") as src, open(os.path.join(site, name), "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            port = free_port()
            env = dict(os.environ, AI_UPSTREAM_NPM=f"http://127.0.0.1:{uport}/npm/", AI_TEST_HTTP="1", NET_TEST_LOCAL="1")
            php = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", site], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                url = f"http://127.0.0.1:{port}/"
                for _ in range(50):
                    try:
                        urllib.request.urlopen(url + "ai.php/ping", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                self.assertTrue(json.loads(urllib.request.urlopen(url + "ai.php/ping").read())["path_info"])
                first = urllib.request.urlopen(url + "ai.php/npm/@mlc-ai/web-llm@0.2.85/lib/index.js")
                self.assertEqual(first.headers["X-Rai-AI"], "fetched")
                self.assertTrue(first.read().startswith(b"export const ok"))
                second = urllib.request.urlopen(url + "ai.php/npm/@mlc-ai/web-llm@0.2.85/lib/index.js")
                self.assertEqual(second.headers["X-Rai-AI"], "stored")       # копия на своём сайте
                self.assertIn("javascript", second.headers["Content-Type"])
                for bad in ("ai.php/npm/evil@1.0/x.js", "ai.php/hf/someone/model/resolve/main/x.bin"):
                    with self.assertRaises(urllib.error.HTTPError) as err:
                        urllib.request.urlopen(url + bad)
                    self.assertEqual(err.exception.code, 403)
                page = json.loads(urllib.request.urlopen(url + "net.php?read=" + urllib.parse.quote(f"http://127.0.0.1:{uport}/page.html")).read())
                self.assertEqual(page["title"], "Радио")
                self.assertIn("Попов и Маркони", page["text"])
                self.assertNotIn("secret", page["text"])
            finally:
                php.terminate()
                php.wait()
                upstream.shutdown()
                upstream.server_close()


    @unittest.skipUnless(__import__("shutil").which("php"), "нет PHP")
    def test_social_links(self):
        """Ссылки на TikTok, YouTube, Telegram, Instagram и сайт: PHP достаёт цифры, Rai считает вовлечённость и даёт советы."""
        import http.server
        import socket
        import subprocess
        import threading
        import time
        import urllib.request
        from datetime import datetime, timezone
        import brain as brain_mod
        import social
        from tests.social_fixtures import PAGES
        base = os.path.dirname(os.path.abspath(__file__))

        class Pages(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = urllib.parse.unquote(self.path.split("?")[0].lstrip("/"))
                if path.startswith("vm.tiktok.com/"):  # короткая ссылка TikTok
                    self.send_response(302)
                    self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/www.tiktok.com/@rai.team/video/7400000000000000001")
                    self.end_headers()
                    return
                body, ctype = PAGES.get(path, ("", ""))
                self.send_response(200 if body else 404)
                self.send_header("Content-Type", ctype or "text/plain")
                self.end_headers()
                self.wfile.write(body.encode())

            def log_message(self, *a):
                pass
        pages = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pages)
        threading.Thread(target=pages.serve_forever, daemon=True).start()
        with tempfile.TemporaryDirectory() as site:
            for name in ("net.php", "social.php"):
                with open(os.path.join(base, "hosting", "rai", name), encoding="utf-8") as src, open(os.path.join(site, name), "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            with socket.socket() as sk:
                sk.bind(("127.0.0.1", 0))
                port = sk.getsockname()[1]
            env = dict(os.environ, NET_TEST_LOCAL="1", NET_TEST_SOCIAL=f"http://127.0.0.1:{pages.server_address[1]}/")
            php = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", site], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                def get(url):
                    for _ in range(50):
                        try:
                            raw = urllib.request.urlopen(f"http://127.0.0.1:{port}/net.php?social=" + urllib.parse.quote(url, safe=""), timeout=10).read()
                            return json.loads(raw)
                        except urllib.error.URLError:
                            time.sleep(0.1)
                    raise AssertionError("PHP не ответил")
                now = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
                video = get("https://vm.tiktok.com/ZMabc/")
                self.assertEqual((video["platform"], video["kind"]), ("tiktok", "video"))
                self.assertEqual(video["stats"]["views"], 1250000)
                self.assertEqual(video["author"]["followers"], 120000)
                text, att = social.report(video, now)
                self.assertIn("| Вовлечённость (ER) | **6,0 %** — хорошо |", text)
                self.assertIn("попало в рекомендации", text)
                self.assertEqual(att[0]["type"], "photo")
                profile = get("https://www.tiktok.com/@rai.studio")
                self.assertEqual((profile["kind"], profile["author"]["videos"]), ("profile", 200))
                self.assertIn("Пустое описание профиля", social.report(profile, now)[0])
                yt = get("https://youtu.be/dQw4w9WgXcQ")
                self.assertEqual((yt["stats"]["views"], yt["stats"]["likes"], yt["duration"]), (48210, 2950, 754))
                self.assertIn("{без серверов}", yt["title"])  # фигурные скобки в строках не ломают разбор
                self.assertEqual(get("https://www.youtube.com/@raiteam")["author"]["followers"], 1230000)
                tg = get("https://t.me/raichannel")
                self.assertEqual((tg["author"]["followers"], len(tg["posts"])), (12500, 4))
                tg_text = social.report(tg, now)[0]
                self.assertIn("**28 %** — хорошо", tg_text)
                self.assertIn("[5 600 просмотров](https://t.me/raichannel/103)", tg_text)
                self.assertEqual(get("https://t.me/raichannel/103")["stats"]["views"], 5600)
                insta = get("https://www.instagram.com/rai.team/")
                self.assertEqual((insta["author"]["followers"], insta["author"]["handle"]), (15200, "rai.team"))
                post = get("https://www.instagram.com/p/ABC123/")
                self.assertEqual((post["stats"]["likes"], post["stats"]["comments"]), (1204, 87))
                web = get("https://example.com/")
                self.assertEqual((web["seo"]["h1"], web["seo"]["images_no_alt"]), (["Rai"], 1))
                self.assertIn("Картинок без alt: 1", social.report(web, now)[0])
                # Rai: данные, которые страница получила от сайта, — сразу в отчёт
                b = brain_mod.Brain(learned_path=os.path.join(site, "learned.json"))
                r = b.answer(SUN, "проанализируй https://vm.tiktok.com/ZMabc/\n[[link-data]]\n" + json.dumps(video, ensure_ascii=False))
                self.assertEqual(r["intent"], "social")
                self.assertIn("Вовлечённость (ER)", r["answer"])
                r = b.answer(SUN, "https://t.me/raichannel\n[[link-data]]\n" + json.dumps({"error": "Сайт ответил 403"}))
                self.assertIn("Сайт ответил 403", r["answer"])
            finally:
                php.terminate()
                php.wait()
                pages.shutdown()
                pages.server_close()

    def test_link_routing(self):
        import social
        self.assertTrue(social.is_link_request("https://www.tiktok.com/@user/video/1"))
        self.assertTrue(social.is_link_request("что скажешь про vm.tiktok.com/ZMabc/"))
        self.assertTrue(social.is_link_request("https://example.com"))                       # просто ссылка — разбор сайта
        self.assertTrue(social.is_link_request("проанализируй сайт https://example.com"))
        self.assertFalse(social.is_link_request("я читал https://example.com/news вчера, было интересно"))
        self.assertFalse(social.is_link_request("привет"))
        with tempfile.TemporaryDirectory() as d:
            b = Brain(learned_path=os.path.join(d, "l.json"))
            # без посредника на хостинге честно говорим, где это работает
            r = b.answer(SUN, "https://www.tiktok.com/@user/video/1")
            self.assertEqual(r["intent"], "social")
            self.assertIn("rai.rteam.info", r["answer"])
            self.assertIn("версии с интернетом", b.answer(FAST, "https://t.me/channel")["answer"])
            # «сделай сайт как …» — это код, а не анализ
            self.assertNotEqual(b.answer(SUN, "сделай сайт как https://example.com")["intent"], "social")


if __name__ == "__main__":
    unittest.main()
