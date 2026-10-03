"""Собственная обработка текста Rai: нормализация, стемминг, TF-IDF поиск.

Никаких внешних библиотек и сервисов — только стандартный Python.
"""

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[a-zа-я0-9]+")

# Слова-«шум»: почти не несут смысла для поиска ответа.
# Вопросительные слова (что, как, кто…) специально оставлены — они различают вопросы.
STOPWORDS = {
    "и", "в", "во", "на", "а", "ну", "же", "ли", "бы", "то", "пожалуйста", "плиз",
    "please", "the", "a", "an", "is", "are", "to", "of", "rai", "рай", "бот",
    "слушай", "скажи", "подскажи", "расскажи", "мне", "эй", "вот", "это", "у", "с", "со",
}

# Окончания русского языка, от длинных к коротким.
_ENDINGS = sorted(
    """
    иями ями ами иях ях ах ией ией ов ев ей ий ый ой ая яя ое ее ие ые ого его ому ему
    ыми ими ую юю ешь ете ишь ите ает яет ет ит ут ют ат ят ать ять ить еть уть ть
    ла ло ли ил ыл ал ял ом ем ам ям ость ости ение ения ением ении иться аться ешься
    а я о е и ы у ю ь й
    """.split(),
    key=len,
    reverse=True,
)
_EN_ENDINGS = ("ing", "ed", "es", "s")


def normalize(text: str) -> str:
    text = (text or "").lower().replace("ё", "е")
    return " ".join(_WORD_RE.findall(text))


def stem(word: str) -> str:
    """Простой собственный стеммер: отрезает типичные окончания."""
    if word.isdigit() or len(word) <= 3:
        return word
    if re.fullmatch(r"[a-z]+", word):
        for end in _EN_ENDINGS:
            if word.endswith(end) and len(word) - len(end) >= 3:
                return word[: -len(end)]
        return word
    for refl in ("ся", "сь"):
        if word.endswith(refl) and len(word) - 2 >= 3:
            word = word[:-2]
            break
    for end in _ENDINGS:
        if word.endswith(end) and len(word) - len(end) >= 3:
            return word[: -len(end)]
    return word


def tokens(text: str, keep_stopwords: bool = False) -> list:
    words = normalize(text).split()
    return [stem(w) for w in words if keep_stopwords or w not in STOPWORDS]


def trigrams(text: str) -> list:
    """Буквенные триграммы — дают устойчивость к опечаткам."""
    grams = []
    for w in normalize(text).split():
        if w in STOPWORDS:
            continue
        w = f"#{w}#"
        grams.extend("~" + w[i : i + 3] for i in range(len(w) - 2))
    return grams


def features(text: str, fuzzy: bool) -> Counter:
    feats = Counter(tokens(text))
    if fuzzy:
        feats.update(trigrams(text))
    return feats


class TfidfIndex:
    """Мини-поисковик: находит документ, наиболее похожий на запрос."""

    def __init__(self, docs, fuzzy: bool = False):
        # docs: список (ключ, текст)
        self.fuzzy = fuzzy
        self.keys = []
        raw = []
        df = Counter()
        for key, text in docs:
            f = features(text, fuzzy)
            if not f:
                continue
            self.keys.append(key)
            raw.append(f)
            df.update(f.keys())
        n = max(len(raw), 1)
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self.vectors = [self._weigh(f) for f in raw]

    def _weigh(self, feats: Counter) -> dict:
        vec = {}
        for t, c in feats.items():
            w = self.idf.get(t)
            if w is None:
                continue
            # Слова весят больше, чем отдельные триграммы.
            vec[t] = (1 + math.log(c)) * w * (0.35 if t.startswith("~") else 1.0)
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, text: str, limit: int = None) -> list:
        """Вернуть [(ключ, сходство 0..1)], лучшее сходство на ключ."""
        q = self._weigh(features(text, self.fuzzy))
        if not q:
            return []
        best = {}
        for key, vec in zip(self.keys, self.vectors):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())
            if score > best.get(key, 0.0):
                best[key] = score
        return sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]


class KeywordIndex:
    """Самый быстрый поиск (Pro Fast): доля общих основ слов."""

    def __init__(self, docs):
        self.docs = [(key, set(tokens(text))) for key, text in docs]
        self.docs = [(k, s) for k, s in self.docs if s]

    def search(self, text: str, limit: int = None) -> list:
        q = set(tokens(text))
        if not q:
            return []
        best = {}
        for key, words in self.docs:
            common = len(q & words)
            if not common:
                continue
            score = common / len(q | words)
            if score > best.get(key, 0.0):
                best[key] = score
        return sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]


# Общие слова: на одних только них совпадение не считается уверенным.
GENERIC = {
    stem(w)
    for w in """
    что такое такой такая как какой какая какие кто где зачем почему когда сколько
    ты тебя тебе я меня мне мой моя мое твой есть можно нужно надо хочу сделать делать
    этот был была будет мы вы вас нас он она они про для из от до по за над под при
    не нет да или еще уже очень так где-то
    """.split()
}

# Слова-«довески»: не меняют смысл короткой реплики («спасибо большое», «привет, бро», «как дела сегодня»).
FILLER = {
    stem(w)
    for w in """
    сегодня сейчас теперь тогда вообще просто большое огромное всем все друг дружище бро братан ребята народ
    дорогой дорогая милый милая конечно правда реально сильно снова опять тут здесь вам тебе тоже ещё
    помоги помогите подскажи подскажите вопрос
    """.split()
}

_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`"
_RU = "йцукенгшщзхъфывапролджэячсмитьбюё"
_LAYOUT = str.maketrans(_EN, _RU)


def levenshtein(a: str, b: str, limit: int = 3) -> int:
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


# Частые русские слова: корректор их не «исправляет» в слова из базы («всем» ≠ «время»).
COMMON = set("""
я ты он она оно мы вы они меня тебя его её ее нас вас их мне тебе ему ей нам вам им мной тобой ним ней нами вами ими
мой моя моё мое мои твой твоя твоё твое твои свой своя своё свое свои наш наша наше наши ваш ваша ваше ваши
этот эта это эти тот та то те такой такая такое такие весь вся всё все всех всем всеми сам сама само сами
кто что где куда откуда когда почему зачем как какой какая какое какие который которая которое которые чей сколько
и а но или да нет не ни же ли бы вот ну даже уже ещё еще тоже также только лишь именно почти очень совсем слишком
в во на с со к ко у о об от до по за из изо над под при про без для через между перед после около вокруг среди
сегодня вчера завтра сейчас теперь потом тогда всегда никогда иногда часто редко рано поздно скоро давно недавно
здесь тут там туда сюда везде нигде всюду далеко близко рядом вверх вниз вперёд назад дома домой
хорошо плохо нормально отлично ладно конечно наверное может можно нельзя надо нужно хочу хочешь хотим хотите хотят
быть был была было были буду будешь будет будем будете будут есть нет стал стала стало стали
делать сделать делаю делаешь делает делаем сделай сделайте сделал сделала сделали
говорить сказать говорю говорит сказал сказала скажи скажите знать знаю знаешь знает знаем знаете знают
думать думаю думаешь думает понимать понимаю понимаешь понял поняла понятно видеть вижу видишь видел видела
смотреть посмотреть смотрю смотришь посмотри посмотрите читать прочитать читаю читаешь писать написать пишу пишешь напиши
идти иду идёшь идет идёт пошёл пошел пошла ехать еду едешь поехать жить живу живёшь живет живёт работать работаю работает
любить люблю любишь любит нравится нравятся хотеть мочь могу можешь может можем могут помочь помоги помогите помогу
дать дай дайте давай давайте взять возьми найти найди нашёл нашел нашла искать ищу ищешь купить куплю
играть играю играешь играет учить учу учиться учусь учишься спать сплю есть ем ешь пить пью
человек люди мама папа брат сестра друг друзья подруга семья ребёнок ребенок дети сын дочь муж жена бабушка дедушка
день дня дни дней ночь утро вечер неделя месяц год года лет время раз минута час часа часов
дом город страна мир жизнь работа школа дело слово вопрос ответ деньги вещь место сторона рука голова глаза
хороший хорошая хорошее хорошие плохой новый новая новое новые старый большой маленький первый последний
главный нужный важный интересный красивый весёлый веселый грустный скучно грустно весело страшно больно
спасибо пожалуйста привет пока здравствуй здравствуйте извини извините прости простите
фильм фильмы кино книга книги песня музыка игра игры стих стихи история рассказ сказка
""".split())


class SpellChecker:
    """Собственный корректор: исправляет опечатки и неверную раскладку (ghbdtn → привет)."""

    def __init__(self, texts):
        self.vocab = set()
        for t in texts:
            self.vocab.update(normalize(t).split())
        self.stems = {stem(w) for w in self.vocab}
        self._ordered = sorted(self.vocab)  # одинаковый ответ при каждом запуске

    def _known(self, word: str) -> bool:
        return (word in self.vocab or stem(word) in self.stems or word in COMMON
                or word in STOPWORDS or stem(word) in GENERIC or stem(word) in FILLER)

    def _closest(self, word: str):
        limit = 1 if len(word) <= 5 else 2
        best, best_key = None, None
        for v in self._ordered:
            if abs(len(v) - len(word)) > limit:
                continue
            # В коротких словах первую букву почти не путают: «всем» не «врем».
            if len(word) <= 5 and v[0] != word[0]:
                continue
            d = levenshtein(word, v, limit)
            if d > limit:
                continue
            key = (d, v[0] != word[0], abs(len(v) - len(word)), v)
            if best_key is None or key < best_key:
                best, best_key = v, key
        return best

    def correct_word(self, word: str) -> str:
        if word.isdigit() or self._known(word):
            return word
        if re.fullmatch(r"[a-z\[\];',.`]+", word):
            swapped = word.translate(_LAYOUT)
            if self._known(swapped):
                return swapped
        if len(word) < 4:
            return word
        return self._closest(word) or word

    def correct(self, text: str) -> str:
        # Раскладку проверяем по исходному тексту: normalize() выкидывает [];',.`
        raw = (text or "").lower().replace("ё", "е").split()
        out = []
        for chunk in raw:
            if re.fullmatch(r"[a-z\[\];',.`]+", chunk.strip("?!")):
                fixed = self.correct_word(chunk.strip("?!"))
                if fixed != chunk.strip("?!"):
                    out.append(fixed)
                    continue
            out.extend(self.correct_word(w) for w in normalize(chunk).split())
        return " ".join(out)
