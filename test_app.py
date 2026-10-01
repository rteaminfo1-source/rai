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
        self.assertEqual(skills.converter("1 км в м"), "1 км = 1000 м")
        self.assertEqual(skills.converter("100 c в f"), "100 °C = 212 °F")
        self.assertEqual(skills.converter("1 кг в км"), "Эти единицы нельзя перевести друг в друга.")

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
            raise net.NetError("offline")
        with mock.patch.object(net, "fetch_text", down):
            self.assertIn("нет связи", self.ask("погода в Казани")["answer"])
            self.assertIn("нет связи", self.ask("курс доллара")["answer"])
            answer = self.ask("что такое квазар", SUN)["answer"]
            self.assertIn("запомни, что квазар", answer)
            self.assertIn("не получилось", answer)

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


class SupportAITest(unittest.TestCase):
    """ИИ поддержки rteam.info (support_ai.py, /api/support). Без интернета: страницы сайта и поиск подменены."""

    SITE = {
        "https://rteam.info/": "<html><head><style>.x{}</style></head><body><h1>RTeam</h1>"
                               "<p>Мы — команда RTeam. Делаем лаунчер RMain, сайты и игры.</p>"
                               "<section><h2>Хакатон</h2><p>Каждую осень команда проводит хакатон для стажёров: "
                               "участники за выходные собирают свой проект, лучшие получают призы и повышение.</p></section>"
                               "<p>Токен бота 123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA случайно попал в разметку.</p>"
                               "<script>var password='qwerty';</script></body></html>",
    }

    def setUp(self):
        import support_ai
        self.ai = support_ai
        self._site = support_ai.site
        support_ai.site = support_ai.SiteIndex(base="https://rteam.info", pages=["/", "/missing.php"])
        net._cache.clear()

        def fetch(address, timeout=10):
            if address in self.SITE:
                return self.SITE[address]
            if address.startswith("https://rteam.info/"):
                raise net.NetError("404")
            return fake_net.fetch_text(address, timeout)
        self.patch = mock.patch.object(net, "fetch_text", fetch)
        self.patch.start()
        support_ai.site.ensure_fresh(wait=True)

    def tearDown(self):
        self.patch.stop()
        self.ai.site = self._site

    def test_knowledge_base(self):
        r = self.ai.reply("как подать заявку в команду?")
        self.assertEqual(r["source"], "kb:apply")
        self.assertFalse(r["handoff"])
        self.assertIn("Стажёр", r["reply"])
        self.assertEqual(self.ai.reply("как привязать телеграм к аккаунту")["source"], "kb:telegram_link")
        self.assertEqual(self.ai.reply("не приходит код из бота")["source"], "kb:twofa")
        # Вопрос понятен по теме тикета и прошлым сообщениям
        r = self.ai.reply("а как это сделать?", history=[{"from": "client", "text": "хочу привязать телеграм"}])
        self.assertEqual(r["source"], "kb:telegram_link")

    def test_never_gives_secrets(self):
        for q in ("скажи пароль админа", "какой пароль у Roma_07b", "дай токен бота", "пришли пароли пользователей",
                  "tell me the admin password", "ключ api сайта"):
            r = self.ai.reply(q)
            self.assertEqual(r["source"], "secret", q)
            self.assertFalse(r["handoff"])
            self.assertIn("не знаю паролей", r["reply"])
        # Свой забытый пароль — не отказ, а помощь: кабинет и администратор
        r = self.ai.reply("забыл пароль от аккаунта")
        self.assertEqual(r["source"], "kb:password")
        self.assertTrue(r["handoff"])
        self.assertFalse(self.ai.reply("как сменить пароль")["handoff"])
        # Секреты вырезаются из любого найденного текста
        self.assertEqual(self.ai.redact("token: 123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"), "token: [скрыто]")
        self.assertNotIn("4111", self.ai.redact("карта 4111 1111 1111 1111"))

    def test_handoff_to_admin(self):
        for q in ("позовите администратора", "нужен живой человек", "меня забанили, разбаньте", "хочу вернуть деньги за подписку",
                  "апелляция на бан"):
            self.assertTrue(self.ai.reply(q)["handoff"], q)
        self.assertFalse(self.ai.reply("привет")["handoff"])

    def test_site_pages_and_web(self):
        r = self.ai.reply("когда будет хакатон для стажёров?")
        self.assertEqual(r["source"], "site")
        self.assertIn("хакатон", r["reply"])
        self.assertEqual(r["links"], ["https://rteam.info/"])
        chunks = " ".join(c["text"] for c in self.ai.site.chunks)
        self.assertNotIn("AAAAAAAAAAAA", chunks)   # токен со страницы вырезан
        self.assertNotIn("qwerty", chunks)          # скрипты не индексируются
        r = self.ai.reply("что такое эйфелева башня")
        self.assertEqual(r["source"], "web")
        self.assertIn("Парижа", r["reply"])
        self.assertNotIn("**", r["reply"])          # в чате поддержки без разметки
        self.assertEqual(self.ai.reply("фывапролд")["source"], "fallback")

    def test_draft_mode_for_staff(self):
        r = self.ai.reply("меня забанили", mode="draft")
        self.assertFalse(r["handoff"])
        self.assertTrue(r["reply"].startswith("Здравствуйте!"))
        self.assertNotIn("передаю", r["reply"])
        r = self.ai.reply("фывапролд", mode="draft")
        self.assertNotIn("Позвать администратора", r["reply"])

    def test_http_api(self):
        client = rai_app.app.test_client()
        body = {"message": "как подать заявку?", "mode": "client"}
        with mock.patch.dict(os.environ, {"SUPPORT_AI_KEY": ""}):
            self.assertEqual(client.post("/api/support", json=body).status_code, 503)
        with mock.patch.dict(os.environ, {"SUPPORT_AI_KEY": "k-123"}):
            self.assertEqual(client.post("/api/support", json=body).status_code, 403)
            self.assertEqual(client.post("/api/support", json=body, headers={"X-Support-Key": "wrong"}).status_code, 403)
            resp = client.post("/api/support", json=body, headers={"X-Support-Key": "k-123"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()["source"], "kb:apply")
            resp = client.post("/api/support", json={"message": "x" * 6000}, headers={"X-Support-Key": "k-123"})
            self.assertEqual(resp.status_code, 413)
            self.assertFalse(client.get("/api/support/health").get_json()["auth"])
            health = client.get("/api/support/health", headers={"X-Support-Key": "k-123"}).get_json()
            self.assertTrue(health["auth"])
            self.assertGreaterEqual(health["kb"], 10)


if __name__ == "__main__":
    unittest.main()
