"""Зрение Rai: словарь понятий для распознавания картинок (vision_labels.json).

Rai узнаёт на картинке не только текст, но и всё остальное: небо, солнце, закат, море, людей, животных, еду,
машины, здания, скриншоты, графики… Для этого в браузере работает модель CLIP (часть, которая «смотрит» на
картинку), а «отпечатки» понятий из этого словаря считаются здесь, на GitHub, один раз — так браузеру не нужно
скачивать вторую половину модели.

    python tools/build_vision.py -o vision_labels.json      # нужны torch, transformers, pillow

Запускается в workflow «Зрение Rai» (.github/workflows/vision.yml). После сборки сам проверяет себя на фото
из Википедии и печатает, что увидел.
"""

import argparse
import base64
import io
import json
import os
import sys
import urllib.parse
import urllib.request

MODEL = "openai/clip-vit-base-patch32"        # в браузере — та же модель: Xenova/clip-vit-base-patch32 (ONNX)
BROWSER_MODEL = "Xenova/clip-vit-base-patch32"

# (раздел, по-русски, по-английски). Английское — для модели, русское — для ответа.
GROUPS = ["Небо и погода", "Природа", "Город и здания", "Люди", "Животные", "Растения", "Еда и напитки", "Транспорт",
          "Дом и вещи", "Техника", "Экран и документы", "Спорт и отдых", "Космос", "Искусство и стиль", "События"]
VOCAB = {
    "Небо и погода": """
        небо|the sky; голубое небо|a clear blue sky; солнце|the sun; яркое солнце|the bright sun shining; закат|a sunset;
        рассвет|a sunrise; облака|clouds in the sky; тучи|dark storm clouds; гроза|a thunderstorm; молния|lightning;
        радуга|a rainbow; дождь|rain; снег|snow falling; снегопад|a snowstorm; туман|fog; луна|the moon; полная луна|a full moon;
        звёздное небо|a starry night sky; северное сияние|the northern lights aurora; ночное небо|the night sky;
        сумерки|twilight; солнечный день|a sunny day; пасмурная погода|an overcast day; иней|frost; радужный ореол|a halo around the sun""",
    "Природа": """
        море|the sea; океан|the ocean; волны|ocean waves; пляж|a beach; песок|sand; горы|mountains; заснеженные горы|snowy mountains;
        вулкан|a volcano; лес|a forest; хвойный лес|a pine forest; джунгли|a jungle; поле|a field; луг|a meadow; степь|a steppe;
        река|a river; озеро|a lake; водопад|a waterfall; пустыня|a desert; дюны|sand dunes; скалы|rocks and cliffs; пещера|a cave;
        остров|an island; ледник|a glacier; айсберг|an iceberg; холмы|hills; каньон|a canyon; болото|a swamp; родник|a spring stream;
        берег|a coastline; сельская местность|the countryside; осень|autumn foliage; зима|a winter landscape; весна|spring blossoms;
        лето|a summer landscape; пейзаж|a landscape; природа|nature; камни|stones; лёд|ice; огонь|fire; костёр|a campfire""",
    "Город и здания": """
        город|a city; ночной город|a city at night; улица|a street; дорога|a road; шоссе|a highway; мост|a bridge; небоскрёб|a skyscraper;
        многоэтажка|an apartment building; дом|a house; деревянный дом|a wooden house; деревня|a village; церковь|a church;
        православный храм|an orthodox church with domes; собор|a cathedral; мечеть|a mosque; замок|a castle; дворец|a palace;
        крепость|a fortress; башня|a tower; памятник|a monument; статуя|a statue; фонтан|a fountain; площадь|a town square;
        парк|a city park; набережная|an embankment; порт|a harbor; маяк|a lighthouse; вокзал|a train station; аэропорт|an airport;
        метро|a subway station; магазин|a shop; торговый центр|a shopping mall; рынок|a market; кафе|a cafe; ресторан|a restaurant;
        офис|an office; школа|a school; больница|a hospital; стадион|a stadium; завод|a factory; стройка|a construction site;
        руины|ruins; кремль|a kremlin; Эйфелева башня|the Eiffel tower; пирамиды|the pyramids; интерьер|a room interior;
        кухня|a kitchen; спальня|a bedroom; гостиная|a living room; ванная|a bathroom; класс|a classroom; библиотека|a library; музей|a museum""",
    "Люди": """
        человек|a person; мужчина|a man; женщина|a woman; ребёнок|a child; малыш|a baby; подросток|a teenager; пожилой человек|an elderly person;
        группа людей|a group of people; толпа|a crowd; семья|a family; друзья|friends together; пара|a couple; портрет|a portrait;
        селфи|a selfie; лицо|a face; улыбка|a smiling face; руки|hands; школьники|schoolchildren; студенты|students; спортсмен|an athlete;
        врач|a doctor; полицейский|a police officer; солдат|a soldier; музыкант|a musician; певец|a singer on stage;
        повар|a chef cooking; рабочий|a worker; бизнесмен|a businessman in a suit; невеста|a bride; танцующие люди|people dancing""",
    "Животные": """
        кошка|a cat; котёнок|a kitten; собака|a dog; щенок|a puppy; лошадь|a horse; корова|a cow; свинья|a pig; овца|a sheep; коза|a goat;
        курица|a chicken; петух|a rooster; утка|a duck; гусь|a goose; кролик|a rabbit; хомяк|a hamster; попугай|a parrot; птица|a bird;
        голубь|a pigeon; воробей|a sparrow; ворона|a crow; орёл|an eagle; сова|an owl; лебедь|a swan; пингвин|a penguin; фламинго|a flamingo;
        медведь|a bear; белый медведь|a polar bear; волк|a wolf; лиса|a fox; заяц|a hare; белка|a squirrel; ёж|a hedgehog; олень|a deer;
        лось|a moose; лев|a lion; тигр|a tiger; леопард|a leopard; слон|an elephant; жираф|a giraffe; зебра|a zebra; носорог|a rhinoceros;
        бегемот|a hippopotamus; обезьяна|a monkey; горилла|a gorilla; панда|a panda; коала|a koala; кенгуру|a kangaroo; верблюд|a camel;
        рыба|a fish; аквариумные рыбки|aquarium fish; акула|a shark; дельфин|a dolphin; кит|a whale; черепаха|a turtle; змея|a snake;
        ящерица|a lizard; крокодил|a crocodile; лягушка|a frog; бабочка|a butterfly; пчела|a bee; божья коровка|a ladybug; паук|a spider;
        муравей|an ant; стрекоза|a dragonfly; улитка|a snail; краб|a crab; осьминог|an octopus; медуза|a jellyfish; динозавр|a dinosaur""",
    "Растения": """
        цветы|flowers; роза|a rose; тюльпан|a tulip; ромашка|a daisy; подсолнух|a sunflower; лилия|a lily; орхидея|an orchid; букет|a bouquet;
        дерево|a tree; берёза|a birch tree; ель|a fir tree; сосна|a pine tree; дуб|an oak tree; пальма|a palm tree; сакура|a cherry blossom tree;
        листья|leaves; трава|grass; кактус|a cactus; комнатное растение|a potted plant; грибы|mushrooms; ягоды|berries; сад|a garden; клумба|a flower bed""",
    "Еда и напитки": """
        еда|food; завтрак|breakfast; обед|a lunch plate; пицца|a pizza; бургер|a burger; картофель фри|french fries; суши|sushi; паста|pasta;
        суп|soup; борщ|borscht soup; салат|a salad; стейк|a steak; шашлык|grilled meat skewers; курица гриль|roast chicken; рыба на тарелке|a fish dish;
        пельмени|dumplings; блины|pancakes; хлеб|bread; бутерброд|a sandwich; торт|a cake; пирожное|a pastry; печенье|cookies; шоколад|chocolate;
        мороженое|ice cream; конфеты|candies; фрукты|fruits; яблоко|an apple; банан|a banana; апельсин|an orange; клубника|strawberries;
        арбуз|a watermelon; виноград|grapes; овощи|vegetables; помидор|a tomato; огурец|a cucumber; морковь|carrots; картофель|potatoes;
        яйца|eggs; сыр|cheese; кофе|a cup of coffee; чай|a cup of tea; сок|juice; вода в стакане|a glass of water; вино|wine; пиво|beer; коктейль|a cocktail""",
    "Транспорт": """
        машина|a car; спортивная машина|a sports car; грузовик|a truck; автобус|a bus; троллейбус|a trolleybus; трамвай|a tram; поезд|a train;
        электричка|a commuter train; метропоезд|a subway train; самолёт|an airplane; вертолёт|a helicopter; корабль|a ship; лодка|a boat;
        яхта|a yacht; велосипед|a bicycle; мотоцикл|a motorcycle; самокат|a scooter; трактор|a tractor; такси|a taxi; пробка|a traffic jam;
        парковка|a parking lot; ракета|a rocket launch; воздушный шар|a hot air balloon; танк|a tank; скорая помощь|an ambulance""",
    "Дом и вещи": """
        стол|a table; стул|a chair; диван|a sofa; кровать|a bed; шкаф|a wardrobe; книжная полка|a bookshelf; лампа|a lamp; окно|a window;
        дверь|a door; зеркало|a mirror; часы|a clock; наручные часы|a wristwatch; книга|a book; книги|books; тетрадь|a notebook; ручка|a pen;
        карандаши|pencils; рюкзак|a backpack; сумка|a bag; чемодан|a suitcase; одежда|clothes; платье|a dress; обувь|shoes; кроссовки|sneakers;
        очки|glasses; шапка|a hat; зонт|an umbrella; игрушка|a toy; плюшевый мишка|a teddy bear; кукла|a doll; мяч|a ball; подарок|a gift box;
        ключи|keys; деньги|money; монеты|coins; кружка|a mug; тарелка|a plate; бутылка|a bottle; свеча|a candle; гитара|a guitar;
        пианино|a piano; скрипка|a violin; барабаны|drums; ёлка|a christmas tree; воздушные шары|balloons""",
    "Техника": """
        компьютер|a desktop computer; ноутбук|a laptop; монитор|a computer monitor; клавиатура|a keyboard; мышь компьютерная|a computer mouse;
        смартфон|a smartphone; планшет|a tablet; телевизор|a television; наушники|headphones; колонка|a speaker; камера|a camera;
        фотоаппарат|a photo camera; игровая приставка|a game console; джойстик|a gamepad; принтер|a printer; робот|a robot; дрон|a drone;
        микрофон|a microphone; провода|cables; микросхема|a circuit board; сервер|server racks; холодильник|a refrigerator;
        стиральная машина|a washing machine; микроволновка|a microwave""",
    "Экран и документы": """
        скриншот|a screenshot; скриншот сайта|a screenshot of a website; скриншот телефона|a screenshot of a phone app; чат переписка|a chat conversation screenshot;
        программный код|computer code on a screen; таблица|a spreadsheet table; график|a chart graph; диаграмма|a pie chart diagram; схема|a diagram scheme;
        карта|a map; документ|a text document; страница книги|a book page with text; рукописный текст|handwritten text; математические формулы|math formulas;
        тест с вариантами ответов|a quiz with multiple choice answers; презентация|a presentation slide; логотип|a logo; иконка|an icon;
        мем|a meme with caption text; комикс|a comic; видеоигра|a video game screenshot; майнкрафт|minecraft game; рабочий стол компьютера|a computer desktop screen;
        сообщение об ошибке|an error message dialog; QR-код|a qr code; штрихкод|a barcode; чек|a receipt; паспорт|an identity document; билет|a ticket;
        плакат|a poster; объявление|an advertisement banner; меню|a restaurant menu; расписание|a schedule timetable; флаг|a flag; герб|a coat of arms""",
    "Спорт и отдых": """
        футбол|soccer football; баскетбол|basketball; хоккей|ice hockey; теннис|tennis; волейбол|volleyball; бокс|boxing; плавание|swimming;
        бег|running; лыжи|skiing; сноуборд|snowboarding; коньки|ice skating; велоспорт|cycling race; гимнастика|gymnastics; йога|yoga;
        тренажёрный зал|a gym; шахматы|chess; рыбалка|fishing; поход|hiking; палатка|a camping tent; пикник|a picnic; концерт|a concert;
        танцы|dancing; праздник|a party celebration; салют|fireworks; свадьба|a wedding; день рождения|a birthday party; Новый год|new year celebration;
        аттракционы|an amusement park; бассейн|a swimming pool; отпуск на море|a beach vacation""",
    "Космос": """
        космос|outer space; галактика|a galaxy; спиральная галактика|a spiral galaxy; туманность|a nebula; звёзды|stars in space; планета|a planet;
        Земля из космоса|the earth from space; Марс|the planet mars; Юпитер|the planet jupiter; Сатурн с кольцами|saturn with rings; Луна вблизи|the moon surface;
        Солнце вблизи|the sun surface; солнечное затмение|a solar eclipse; лунное затмение|a lunar eclipse; комета|a comet; метеор|a meteor shower;
        чёрная дыра|a black hole; космонавт|an astronaut; космическая станция|a space station; спутник|a satellite; телескоп|a telescope; Млечный Путь|the milky way""",
    "Искусство и стиль": """
        рисунок|a drawing; детский рисунок|a child's drawing; картина|a painting; акварель|a watercolor painting; карандашный набросок|a pencil sketch;
        аниме|an anime illustration; мультфильм|a cartoon; пиксельная графика|pixel art; 3D-модель|a 3d render; граффити|graffiti;
        абстракция|abstract art; чёрно-белое фото|a black and white photo; старое фото|an old vintage photo; узор|a pattern; текстура|a texture;
        скульптура|a sculpture; мозаика|a mosaic; вышивка|embroidery; оригами|origami""",
    "События": """
        пожар|a building on fire; авария|a car accident; наводнение|a flood; митинг|a protest rally; парад|a parade; выступление|a speech on stage;
        урок|a lesson in a classroom; экзамен|an exam; совещание|a business meeting; видеозвонок|a video call; спортивный матч|a sports match;
        соревнование|a competition; выставка|an exhibition; очередь|a queue of people; ремонт|home renovation; переезд|moving boxes""",
}
TEMPLATES = ["a photo of {}.", "a close-up photo of {}.", "an image of {}.", "a picture showing {}."]
SCREEN_TEMPLATES = ["{}.", "an image of {}.", "a screenshot showing {}."]


def vocab():
    out = []
    for g, block in VOCAB.items():
        for part in block.replace("\n", " ").split(";"):
            part = part.strip()
            if not part:
                continue
            ru, en = [x.strip() for x in part.split("|", 1)]
            out.append((GROUPS.index(g), ru, en))
    return out


def text_features(model, inputs):
    """Вектор текста в общем пространстве CLIP (одинаково во всех версиях transformers)."""
    out = model.text_model(input_ids=inputs["input_ids"], attention_mask=inputs.get("attention_mask"))
    return model.text_projection(out.pooler_output)


def image_features(model, pixel_values):
    out = model.vision_model(pixel_values=pixel_values)
    return model.visual_projection(out.pooler_output)


def build():
    import torch
    from transformers import CLIPModel, CLIPTokenizer
    model = CLIPModel.from_pretrained(MODEL).eval()
    tok = CLIPTokenizer.from_pretrained(MODEL)
    labels = vocab()
    embs = []
    with torch.no_grad():
        for g, ru, en in labels:
            temps = SCREEN_TEMPLATES if GROUPS[g] == "Экран и документы" else TEMPLATES
            inputs = tok([t.format(en) for t in temps], padding=True, return_tensors="pt")
            e = text_features(model, inputs)
            e = e / e.norm(dim=-1, keepdim=True)
            e = e.mean(dim=0)
            embs.append(e / e.norm())
    m = torch.stack(embs)                          # N × 512, длина каждого = 1
    scale = float(m.abs().max())
    q = torch.clamp((m / scale * 127).round(), -127, 127).to(torch.int8)
    data = {
        "model": MODEL, "browser_model": BROWSER_MODEL, "dim": m.shape[1], "scale": scale / 127,
        "logit_scale": float(model.logit_scale.exp()),
        "groups": GROUPS, "labels": [[g, ru, en] for g, ru, en in labels],
        "emb": base64.b64encode(q.numpy().tobytes()).decode(),
    }
    return data, model


def self_test(data, model):
    """Проверка на фото из Википедии: что увидит Rai."""
    import numpy as np
    import torch
    from PIL import Image
    from transformers import CLIPProcessor
    proc = CLIPProcessor.from_pretrained(MODEL)
    emb = np.frombuffer(base64.b64decode(data["emb"]), dtype=np.int8).reshape(-1, data["dim"]).astype("float32") * data["scale"]
    for title in ["Закат", "Кошка", "Москва", "Радуга", "Джомолунгма", "Пицца", "Галактика Андромеды", "Футбол"]:
        try:
            api = "https://ru.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
            req = urllib.request.Request(api, headers={"User-Agent": "RaiVisionBuilder/1.0 (https://github.com/rteaminfo1-source/rai)"})
            src = json.load(urllib.request.urlopen(req, timeout=30)).get("thumbnail", {}).get("source")
            req = urllib.request.Request(src, headers={"User-Agent": "RaiVisionBuilder/1.0"})
            img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB")
        except Exception as e:
            print(title, "— нет картинки:", e)
            continue
        with torch.no_grad():
            v = image_features(model, proc(images=img, return_tensors="pt")["pixel_values"])[0].numpy()
        v = v / np.linalg.norm(v)
        sims = emb @ v
        p = np.exp((sims - sims.max()) * data["logit_scale"])
        p /= p.sum()
        top = np.argsort(-p)[:5]
        print(f"{title}: " + ", ".join(f"{data['labels'][i][1]} {p[i]:.0%}" for i in top))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--output", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vision_labels.json"))
    parser.add_argument("--no-test", action="store_true")
    args = parser.parse_args()
    data, model = build()
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("понятий:", len(data["labels"]), "→", args.output, os.path.getsize(args.output) // 1024, "КБ", file=sys.stderr)
    if not args.no_test:
        self_test(data, model)


if __name__ == "__main__":
    main()
