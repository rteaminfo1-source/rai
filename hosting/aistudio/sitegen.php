<?php
/*
 * ИИ-конструктор сайтов AI Studio: из описания словами делает сайт и правит его по просьбам.
 * Работает на самом хостинге (PHP), без внешних сервисов. Сайт описывается «спецификацией»
 * (массив: название, тема, цвета, разделы), из неё собирается готовый index.html.
 */

// ---------------------------------------------------------------- словари
const SG_TYPES = [
    'cafe'      => ['words' => ['кафе', 'ресторан', 'кофейн', 'пиццер', 'бар ', 'пекарн', 'кондитер', 'еда', 'бургер', 'суши'],
                    'title' => 'Уютное кафе', 'tagline' => 'Вкусно, тепло и по-домашнему',
                    'sections' => ['about', 'menu', 'gallery', 'reviews', 'contacts']],
    'shop'      => ['words' => ['магазин', 'shop', 'товар', 'продаж', 'каталог', 'одежд', 'цветочн', 'букет'],
                    'title' => 'Интернет-магазин', 'tagline' => 'Лучшие товары с быстрой доставкой',
                    'sections' => ['about', 'products', 'features', 'reviews', 'contacts']],
    'portfolio' => ['words' => ['портфолио', 'резюме', 'обо мне', 'личный', 'программист', 'разработчик', 'дизайнер', 'фотограф', 'художник'],
                    'title' => 'Моё портфолио', 'tagline' => 'Проекты, навыки и контакты',
                    'sections' => ['about', 'skills', 'projects', 'contacts']],
    'blog'      => ['words' => ['блог', 'статьи', 'новост', 'дневник', 'журнал'],
                    'title' => 'Мой блог', 'tagline' => 'Заметки, идеи и истории',
                    'sections' => ['about', 'posts', 'contacts']],
    'landing'   => ['words' => ['лендинг', 'стартап', 'продукт', 'приложени', 'сервис', 'платформ', 'бот'],
                    'title' => 'Новый сервис', 'tagline' => 'Решаем задачу быстро и просто',
                    'sections' => ['features', 'how', 'prices', 'faq', 'contacts']],
    'school'    => ['words' => ['школ', 'курс', 'обучени', 'урок', 'репетитор', 'академи', 'учеб'],
                    'title' => 'Онлайн-школа', 'tagline' => 'Учитесь в своём темпе с поддержкой преподавателей',
                    'sections' => ['about', 'courses', 'prices', 'faq', 'contacts']],
    'event'     => ['words' => ['свадьб', 'мероприяти', 'праздник', 'день рождения', 'конференц', 'фестивал', 'вечеринк'],
                    'title' => 'Наше событие', 'tagline' => 'Ждём вас — будет здорово!',
                    'sections' => ['about', 'schedule', 'gallery', 'contacts']],
    'music'     => ['words' => ['музык', 'групп', 'исполнител', 'диджей', 'dj', 'рэп', 'песн'],
                    'title' => 'Музыкальная группа', 'tagline' => 'Новые треки и концерты',
                    'sections' => ['about', 'tracks', 'schedule', 'gallery', 'contacts']],
    'gaming'    => ['words' => ['игр', 'гейм', 'клан', 'minecraft', 'майнкрафт', 'киберспорт', 'сервер'],
                    'title' => 'Игровой проект', 'tagline' => 'Играем вместе — присоединяйся',
                    'sections' => ['about', 'features', 'team', 'contacts']],
    'personal'  => ['words' => ['личный сайт', 'про себя', 'про мою', 'про моего', 'про мой', 'про моё', 'хобби', 'семь'],
                    'title' => 'Мой сайт', 'tagline' => 'Всё самое интересное — здесь',
                    'sections' => ['about', 'gallery', 'contacts']],
    'business'  => ['words' => ['компани', 'бизнес', 'услуг', 'фирм', 'агентств', 'студи', 'ремонт', 'салон'],
                    'title' => 'Наша компания', 'tagline' => 'Делаем работу качественно и в срок',
                    'sections' => ['about', 'services', 'reviews', 'contacts']],
];

const SG_SECTIONS = [
    'about'    => ['о нас', 'обо мне', 'о компании', 'о проекте', 'about'],
    'services' => ['услуг'],
    'prices'   => ['цен', 'тариф', 'прайс', 'стоимост'],
    'reviews'  => ['отзыв'],
    'contacts' => ['контакт', 'связ', 'адрес'],
    'gallery'  => ['галере', 'фото', 'картин', 'работы в фото'],
    'menu'     => ['меню'],
    'products' => ['товар', 'каталог', 'продукц'],
    'projects' => ['проект', 'работ', 'кейс'],
    'skills'   => ['навык', 'умени', 'технолог'],
    'posts'    => ['стать', 'пост', 'запис', 'новост'],
    'faq'      => ['вопрос', 'faq', 'чаво'],
    'team'     => ['команд', 'сотрудник', 'участник'],
    'schedule' => ['расписани', 'программ', 'афиш', 'концерт'],
    'courses'  => ['курс', 'урок', 'программы обучения'],
    'features' => ['преимуществ', 'возможност', 'почему мы', 'особенност'],
    'how'      => ['как это работает', 'как работает', 'этап', 'шаг'],
    'tracks'   => ['трек', 'песн', 'альбом', 'музык'],
];

const SG_SECTION_TITLES = [
    'about' => 'О нас', 'services' => 'Услуги', 'prices' => 'Цены', 'reviews' => 'Отзывы', 'contacts' => 'Контакты',
    'gallery' => 'Галерея', 'menu' => 'Меню', 'products' => 'Товары', 'projects' => 'Проекты', 'skills' => 'Навыки',
    'posts' => 'Статьи', 'faq' => 'Вопросы и ответы', 'team' => 'Команда', 'schedule' => 'Расписание',
    'courses' => 'Курсы', 'features' => 'Преимущества', 'how' => 'Как это работает', 'tracks' => 'Треки', 'text' => 'Раздел',
];

const SG_COLORS = [
    'красн' => '#e10600', 'алый' => '#ff2a2a', 'бордов' => '#8b0f1a', 'син' => '#1e5bff', 'голуб' => '#2aa7e8',
    'зелен' => '#1f9d55', 'зелён' => '#1f9d55', 'желт' => '#f5b800', 'жёлт' => '#f5b800', 'оранж' => '#ff7a00',
    'фиолет' => '#7c3aed', 'розов' => '#ff4f93', 'бирюз' => '#14b8a6', 'золот' => '#c9a227', 'коричн' => '#8b5a2b',
    'сер' => '#6b7280',
];

const SG_PALETTES = [  // [фон, текст, акцент, поверхность] для светлой и тёмной темы
    'light' => ['#faf8f5', '#1d1a17', '#e10600', '#ffffff'],
    'dark'  => ['#0c0c0e', '#f2f0f0', '#ff2a2a', '#17171a'],
];

// ---------------------------------------------------------------- разбор описания
function sg_lower($s) { return mb_strtolower(str_replace(['Ё', 'ё'], ['Е', 'е'], (string)$s)); }

function sg_has($text, $words) {
    foreach ($words as $w) {
        if (strpos($text, sg_lower($w)) !== false) return true;
    }
    return false;
}

function sg_detect_type($low) {
    foreach (SG_TYPES as $type => $info) {
        if (sg_has($low, $info['words'])) return $type;
    }
    return 'business';
}

function sg_section_kind($name) {
    $low = sg_lower(trim($name));
    foreach (SG_SECTIONS as $kind => $words) {
        if (sg_has($low, $words)) return $kind;
    }
    return 'text';
}

function sg_title_case($s) {
    $s = trim($s);
    return mb_strtoupper(mb_substr($s, 0, 1)) . mb_substr($s, 1);
}

/** Название из «кавычек», «под названием X», «сайт для X». */
function sg_extract_name($prompt) {
    if (preg_match('/[«"“]([^»"”]{2,60})[»"”]/u', $prompt, $m)) return trim($m[1]);
    if (preg_match('/(?:под названием|называется|с названием|бренд|компании|кафе|магазина?|группы|школы|клана?)\s+([A-ZА-ЯЁ0-9][\w\-\.]*(?:\s+[A-ZА-ЯЁ0-9][\w\-\.]*){0,3})/u', $prompt, $m)) {
        return trim($m[1]);
    }
    return null;
}

function sg_extract_sections($prompt) {
    // «с разделами: о нас, услуги, цены и контакты» / «разделы о нас, отзывы»
    if (!preg_match('/(?:раздел\w*|блок\w*|секци\w*)\s*:?\s*(.+?)(?:\.|;|$)/u', $prompt, $m)) return [];
    $parts = preg_split('/\s*(?:,|\sи\s|\+)\s*/u', $m[1]);
    $out = [];
    foreach ($parts as $p) {
        $p = trim($p, " \t«»\"'");
        if ($p === '' || mb_strlen($p) > 40) continue;
        $out[] = $p;
    }
    return $out;
}

function sg_extract_color($low) {
    foreach (SG_COLORS as $word => $hex) {
        if (strpos($low, $word) !== false) return $hex;
    }
    return null;
}

function sg_extract_contacts($prompt, &$spec) {
    if (preg_match('/[\w.+-]+@[\w-]+\.[\w.-]+/u', $prompt, $m)) $spec['contacts']['email'] = $m[0];
    if (preg_match('/(?:\+7|8|\+\d{1,3})[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}/u', $prompt, $m)) $spec['contacts']['phone'] = trim($m[0]);
    if (preg_match('/(?:адрес|находимся)\s*:?\s*([^.;\n]{5,80})/u', $prompt, $m)) $spec['contacts']['address'] = trim($m[1]);
    if (preg_match('/(?:telegram|телеграм)\s*:?\s*@?([A-Za-z0-9_]{4,32})/u', $prompt, $m)) $spec['contacts']['telegram'] = $m[1];
}

// ---------------------------------------------------------------- содержимое разделов
function sg_default_section($kind, $type, $name) {
    $title = SG_SECTION_TITLES[$kind] ?? 'Раздел';
    $n = $name;
    switch ($kind) {
        case 'about':
            $texts = [
                'cafe' => "«{$n}» — место, куда хочется возвращаться. Готовим из свежих продуктов, варим ароматный кофе и всегда рады гостям.",
                'shop' => "«{$n}» — магазин, где легко найти нужное. Проверяем каждый товар, быстро доставляем и помогаем с выбором.",
                'portfolio' => ($n === SG_TYPES['portfolio']['title'] ? 'Привет!' : "Привет! Я {$n}.")
                               . ' Создаю проекты, которые решают реальные задачи, и постоянно учусь новому.',
                'blog' => "Здесь я пишу о том, что меня вдохновляет: идеи, опыт, полезные находки.",
                'school' => "«{$n}» — обучение с практикой и поддержкой. Короткие уроки, домашние задания и обратная связь от преподавателей.",
                'event' => "Приглашаем вас разделить с нами этот день. Здесь вся информация о событии.",
                'music' => "{$n} — музыка, в которую вкладываем душу. Пишем песни, играем концерты и ждём вас в зале.",
                'gaming' => "{$n} — сообщество игроков. Турниры, совместные игры и дружная атмосфера.",
                'personal' => "Этот сайт — {$n}. Здесь фотографии, истории и всё самое интересное.",
                'business' => "«{$n}» — команда профессионалов. Работаем честно, по договору и с гарантией результата.",
            ];
            return ['kind' => 'about', 'title' => $type === 'portfolio' ? 'Обо мне' : 'О нас', 'text' => $texts[$type] ?? $texts['business']];
        case 'services':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Консультация', 'text' => 'Разберёмся в задаче и предложим решение.'],
                ['title' => 'Работа под ключ', 'text' => 'Сделаем всё сами — от плана до результата.'],
                ['title' => 'Поддержка', 'text' => 'Остаёмся на связи и помогаем после сдачи.'],
            ]];
        case 'features':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Быстро', 'text' => 'Результат без долгого ожидания.'],
                ['title' => 'Надёжно', 'text' => 'Проверенные решения и честные условия.'],
                ['title' => 'Удобно', 'text' => 'Всё понятно с первого взгляда.'],
            ]];
        case 'prices':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Старт', 'price' => '990 ₽', 'text' => 'Всё необходимое, чтобы начать.'],
                ['title' => 'Стандарт', 'price' => '2 490 ₽', 'text' => 'Оптимально для большинства.'],
                ['title' => 'Премиум', 'price' => '4 990 ₽', 'text' => 'Максимум возможностей и поддержка.'],
            ]];
        case 'reviews':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Анна', 'text' => 'Всё понравилось, обязательно вернусь ещё!'],
                ['title' => 'Дмитрий', 'text' => 'Быстро, качественно и с вниманием к деталям.'],
                ['title' => 'Мария', 'text' => 'Рекомендую друзьям — лучший выбор.'],
            ]];
        case 'menu':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Капучино', 'price' => '190 ₽', 'text' => 'Эспрессо с нежной молочной пеной'],
                ['title' => 'Сырники', 'price' => '320 ₽', 'text' => 'Со сметаной и ягодным соусом'],
                ['title' => 'Паста карбонара', 'price' => '450 ₽', 'text' => 'Сливочный соус, бекон, пармезан'],
                ['title' => 'Чизкейк', 'price' => '290 ₽', 'text' => 'Классический нью-йоркский'],
            ]];
        case 'products':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Товар 1', 'price' => '1 200 ₽', 'text' => 'Короткое описание товара.'],
                ['title' => 'Товар 2', 'price' => '2 400 ₽', 'text' => 'Короткое описание товара.'],
                ['title' => 'Товар 3', 'price' => '3 600 ₽', 'text' => 'Короткое описание товара.'],
            ]];
        case 'projects':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Проект «Альфа»', 'text' => 'Сайт для небольшого бизнеса: дизайн, вёрстка, запуск.'],
                ['title' => 'Проект «Бета»', 'text' => 'Телеграм-бот, который экономит команде 5 часов в неделю.'],
                ['title' => 'Проект «Гамма»', 'text' => 'Игра на Python, сделанная за выходные.'],
            ]];
        case 'skills':
            return ['kind' => $kind, 'title' => $title, 'tags' => ['HTML', 'CSS', 'JavaScript', 'Python', 'PHP', 'Git', 'Figma']];
        case 'posts':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'С чего всё началось', 'date' => date('d.m.Y'), 'text' => 'Первая запись блога: рассказываю, зачем он нужен.'],
                ['title' => '5 полезных привычек', 'date' => date('d.m.Y', time() - 86400 * 7), 'text' => 'Маленькие шаги, которые меняют многое.'],
                ['title' => 'Мои любимые инструменты', 'date' => date('d.m.Y', time() - 86400 * 14), 'text' => 'Подборка того, чем пользуюсь каждый день.'],
            ]];
        case 'faq':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Как начать?', 'text' => 'Напишите нам — ответим в течение дня и всё расскажем.'],
                ['title' => 'Сколько это стоит?', 'text' => 'Цены указаны выше, а точную сумму назовём после короткого разговора.'],
                ['title' => 'Можно ли вернуть деньги?', 'text' => 'Да, если что-то пошло не так, вернём деньги в течение 14 дней.'],
            ]];
        case 'team':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Алексей', 'text' => 'Основатель'], ['title' => 'Ирина', 'text' => 'Дизайн'], ['title' => 'Максим', 'text' => 'Разработка'],
            ]];
        case 'schedule':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => '18:00', 'text' => 'Сбор гостей'], ['title' => '19:00', 'text' => 'Начало программы'], ['title' => '22:00', 'text' => 'Финал и фото на память'],
            ]];
        case 'courses':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Основы', 'text' => '8 уроков для старта с нуля.'],
                ['title' => 'Практика', 'text' => 'Реальные задачи и проверка домашних заданий.'],
                ['title' => 'Проект', 'text' => 'Свой проект в портфолио к концу курса.'],
            ]];
        case 'how':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Оставьте заявку', 'text' => 'Это займёт минуту.'],
                ['title' => 'Обсудим детали', 'text' => 'Уточним задачу и сроки.'],
                ['title' => 'Получите результат', 'text' => 'Точно в срок.'],
            ]];
        case 'tracks':
            return ['kind' => $kind, 'title' => $title, 'items' => [
                ['title' => 'Первый трек', 'text' => '3:24'], ['title' => 'Ночной город', 'text' => '4:02'], ['title' => 'Домой', 'text' => '3:47'],
            ]];
        case 'gallery':
            return ['kind' => $kind, 'title' => $title, 'count' => 6];
        case 'contacts':
            return ['kind' => $kind, 'title' => $title, 'text' => 'Напишите или позвоните — ответим быстро.'];
    }
    return ['kind' => 'text', 'title' => sg_title_case($name), 'text' => 'Здесь будет текст этого раздела. Попросите ИИ: «измени раздел «' . sg_title_case($name) . '» на: …».'];
}

// ---------------------------------------------------------------- новая спецификация
function sg_new_spec($prompt, $username) {
    $prompt = trim(mb_substr((string)$prompt, 0, 2000));
    $low = sg_lower($prompt);
    $type = sg_detect_type($low);
    $info = SG_TYPES[$type];
    $name = sg_extract_name($prompt) ?: $info['title'];
    if ($type === 'personal' && !sg_extract_name($prompt) && preg_match('/\b(?:про|о|об)\s+(.{3,50}?)[.!,]?$/u', $prompt, $m)) {
        $name = 'Про ' . trim($m[1]);  // «сайт про мою собаку» -> «Про мою собаку»
    }

    $dark = sg_has($low, ['тёмн', 'темн', 'черн', 'чёрн', 'ночн', 'dark']);
    if (sg_has($low, ['светл', 'бел', 'light'])) $dark = false;
    $accent = sg_extract_color($low);
    if (sg_has($low, ['черно-красн', 'чёрно-красн', 'rteam'])) { $dark = true; $accent = '#e10600'; }

    $spec = [
        'version' => 1, 'type' => $type, 'owner' => $username,
        'title' => $name, 'tagline' => $info['tagline'],
        'theme' => $dark ? 'dark' : 'light', 'accent' => $accent ?: SG_PALETTES[$dark ? 'dark' : 'light'][2],
        'seed' => crc32($username . $name . microtime()), 'sections' => [], 'contacts' => [],
        'prompt' => $prompt, 'updated' => time(),
    ];
    if (preg_match('/(?:слоган|девиз)\s*:?\s*[«"]?([^»".\n]{3,80})/u', $prompt, $m)) $spec['tagline'] = trim($m[1]);

    $wanted = sg_extract_sections($prompt);
    $kinds = [];
    foreach ($wanted as $w) {
        $kind = sg_section_kind($w);
        $kinds[] = [$kind, $w];
    }
    if (!$kinds) {
        foreach ($info['sections'] as $k) $kinds[] = [$k, SG_SECTION_TITLES[$k]];
    }
    $seen = [];
    foreach ($kinds as $pair) {
        list($kind, $label) = $pair;
        if ($kind !== 'text' && isset($seen[$kind])) continue;
        $seen[$kind] = true;
        $spec['sections'][] = sg_default_section($kind, $type, $kind === 'text' ? $label : $name);
    }
    if (!isset($seen['contacts'])) $spec['sections'][] = sg_default_section('contacts', $type, $name);
    sg_extract_contacts($prompt, $spec);
    return $spec;
}

// ---------------------------------------------------------------- правки
function sg_find_section(&$spec, $name) {
    $kind = sg_section_kind($name);
    $low = sg_lower(trim($name, " «»\"'"));
    foreach ($spec['sections'] as $i => $s) {
        if (sg_lower($s['title']) === $low || ($kind !== 'text' && $s['kind'] === $kind)) return $i;
    }
    return null;
}

/** Применить правку словами. Возвращает [спецификация, что сделано]. */
function sg_edit_spec($spec, $instruction) {
    $text = trim(mb_substr((string)$instruction, 0, 1000));
    $low = sg_lower($text);
    $done = [];

    if (preg_match('/(?:переименуй|назови|название|заголовок)(?:\s+сайта?)?\s*(?:на|в|:)?\s*[«"]?([^»"\n]{2,60})[»"]?\s*$/u', $text, $m)) {
        $spec['title'] = trim($m[1]);
        $done[] = 'новое название: «' . $spec['title'] . '»';
    } elseif (preg_match('/(?:слоган|подзаголовок|девиз)\s*(?:на|:)?\s*[«"]?([^»"\n]{2,120})[»"]?\s*$/u', $text, $m)) {
        $spec['tagline'] = trim($m[1]);
        $done[] = 'новый слоган';
    }

    if (preg_match('/(?:измени|поменяй|замени|напиши)\s+(?:текст\s+)?(?:в\s+)?(?:раздел[еа]?|блок[еа]?)\s*[«"]?(.+?)[»"]?(?:\s+на(?=[\s:])\s*:?|\s*:)\s*(.{3,})$/us', $text, $m)) {
        $i = sg_find_section($spec, $m[1]);
        if ($i !== null) {
            $spec['sections'][$i]['text'] = trim($m[2]);
            unset($spec['sections'][$i]['items'], $spec['sections'][$i]['tags']);
            if (!in_array($spec['sections'][$i]['kind'], ['about', 'contacts', 'text'], true)) $spec['sections'][$i]['kind'] = 'text';
            $done[] = 'обновил раздел «' . $spec['sections'][$i]['title'] . '»';
        } else {
            $done[] = 'не нашёл раздел «' . trim($m[1]) . '»';
        }
    } elseif (preg_match('/(?:добавь|создай|нужен|нужна|сделай)\s+(?:ещё\s+)?(?:раздел\w*|блок\w*|секци\w*)\s*:?\s*(.+)$/u', $text, $m)) {
        foreach (preg_split('/\s*(?:,|\sи\s)\s*/u', $m[1]) as $name) {
            $name = trim($name, " .«»\"'");
            if ($name === '') continue;
            $kind = sg_section_kind($name);
            if ($kind !== 'text' && sg_find_section($spec, $name) !== null) { $done[] = "раздел «{$name}» уже есть"; continue; }
            $section = sg_default_section($kind, $spec['type'], $kind === 'text' ? $name : $spec['title']);
            $contactsAt = null;
            foreach ($spec['sections'] as $j => $s) if ($s['kind'] === 'contacts') $contactsAt = $j;
            if ($contactsAt === null) $spec['sections'][] = $section;
            else array_splice($spec['sections'], $contactsAt, 0, [$section]);
            $done[] = 'добавил раздел «' . $section['title'] . '»';
        }
    } elseif (preg_match('/(?:убери|удали|скрой)\s+(?:раздел\w*|блок\w*|секци\w*)?\s*[«"]?(.+?)[»"]?\s*$/u', $text, $m)) {
        $i = sg_find_section($spec, $m[1]);
        if ($i !== null) {
            $done[] = 'убрал раздел «' . $spec['sections'][$i]['title'] . '»';
            array_splice($spec['sections'], $i, 1);
        } else {
            $done[] = 'не нашёл раздел «' . trim($m[1]) . '»';
        }
    }

    if (sg_has($low, ['тёмн', 'темн', 'черн', 'чёрн', 'ночн'])) { $spec['theme'] = 'dark'; $done[] = 'тёмная тема'; }
    elseif (sg_has($low, ['светл', 'бел'])) { $spec['theme'] = 'light'; $done[] = 'светлая тема'; }
    $color = sg_extract_color($low);
    if ($color && !preg_match('/раздел|название|слоган/u', $low)) { $spec['accent'] = $color; $done[] = 'новый цвет акцента'; }
    if (sg_has($low, ['другой дизайн', 'по-другому', 'перемешай', 'новые картинки', 'другие картинки'])) {
        $spec['seed'] = crc32(microtime()); $done[] = 'новые картинки';
    }
    $before = $spec['contacts'];
    sg_extract_contacts($text, $spec);
    if ($spec['contacts'] !== $before) $done[] = 'обновил контакты';

    $spec['updated'] = time();
    if (!$done) {
        return [$spec, null];
    }
    return [$spec, implode(', ', array_unique($done))];
}

// ---------------------------------------------------------------- картинки (SVG)
function sg_mix($a, $b, $t) {
    $ca = sscanf($a, '#%02x%02x%02x'); $cb = sscanf($b, '#%02x%02x%02x');
    $r = [];
    for ($i = 0; $i < 3; $i++) $r[] = (int)round($ca[$i] + ($cb[$i] - $ca[$i]) * $t);
    return vsprintf('#%02x%02x%02x', $r);
}

function sg_art($seed, $w, $h, $accent, $bg, $label = '') {
    mt_srand($seed);
    $parts = [];
    $parts[] = sprintf('<rect width="%d" height="%d" fill="%s"/>', $w, $h, $bg);
    $colors = [$accent, sg_mix($accent, '#ffffff', 0.35), sg_mix($accent, '#000000', 0.45), sg_mix($bg, $accent, 0.18)];
    for ($i = 0; $i < 14; $i++) {
        $c = $colors[mt_rand(0, 3)];
        $op = mt_rand(20, 85) / 100;
        if (mt_rand(0, 2) === 0) {
            $parts[] = sprintf('<circle cx="%d" cy="%d" r="%d" fill="%s" opacity="%.2f"/>', mt_rand(0, $w), mt_rand(0, $h), mt_rand(20, (int)($h / 2)), $c, $op);
        } elseif (mt_rand(0, 1)) {
            $x = mt_rand(0, $w); $y = mt_rand(0, $h); $s = mt_rand(40, (int)($h * 0.8));
            $parts[] = sprintf('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" opacity="%.2f" transform="rotate(%d %d %d)"/>', $x, $y, $s, (int)($s * 0.6), $c, $op, mt_rand(0, 90), $x, $y);
        } else {
            $parts[] = sprintf('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="%d" opacity="%.2f"/>', mt_rand(0, $w), mt_rand(0, $h), mt_rand(0, $w), mt_rand(0, $h), $c, mt_rand(2, 10), $op);
        }
    }
    if ($label !== '') {
        $parts[] = sprintf('<text x="24" y="%d" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#ffffff" opacity=".92">%s</text>', $h - 26, h($label));
    }
    mt_srand();
    $svg = sprintf('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">%s</svg>', $w, $h, implode('', $parts));
    return 'data:image/svg+xml;base64,' . base64_encode($svg);
}

// ---------------------------------------------------------------- сборка HTML
function sg_render($spec) {
    if (!empty($spec['html'])) return $spec['html'];  // сайт написала нейросеть Rai (уже очищен при сохранении)
    $dark = ($spec['theme'] ?? 'light') === 'dark';
    list($bg, $fg, , $surface) = SG_PALETTES[$dark ? 'dark' : 'light'];
    $accent = preg_match('/^#[0-9a-f]{6}$/i', $spec['accent'] ?? '') ? $spec['accent'] : '#e10600';
    $muted = sg_mix($fg, $bg, 0.45);
    $line = sg_mix($fg, $bg, 0.85);
    $seed = (int)($spec['seed'] ?? 1);
    $title = h($spec['title']);
    $hero = sg_art($seed, 1200, 700, $accent, $dark ? '#111114' : sg_mix($bg, $accent, 0.08));

    $nav = '';
    $body = '';
    foreach ($spec['sections'] as $i => $s) {
        $id = 's' . ($i + 1);
        $nav .= '<a href="#' . $id . '">' . h($s['title']) . '</a>';
        $body .= '<section id="' . $id . '" class="sec sec-' . h($s['kind']) . '"><div class="wrap"><h2>' . h($s['title']) . '</h2>';
        $items = $s['items'] ?? [];
        switch ($s['kind']) {
            case 'about': case 'text':
                $body .= '<p class="lead">' . nl2br(h($s['text'] ?? '')) . '</p>';
                break;
            case 'skills':
                $body .= '<div class="tags">';
                foreach ($s['tags'] ?? [] as $t) $body .= '<span>' . h($t) . '</span>';
                $body .= '</div>';
                break;
            case 'gallery':
                $body .= '<div class="gallery">';
                for ($k = 0; $k < (int)($s['count'] ?? 6); $k++) {
                    $body .= '<img alt="Фото ' . ($k + 1) . '" src="' . sg_art($seed + $k + 7, 600, 420, $accent, $dark ? '#16161a' : sg_mix($bg, $accent, 0.12)) . '">';
                }
                $body .= '</div>';
                break;
            case 'reviews':
                $body .= '<div class="grid">';
                foreach ($items as $it) $body .= '<blockquote class="card"><p>«' . h($it['text']) . '»</p><cite>— ' . h($it['title']) . '</cite></blockquote>';
                $body .= '</div>';
                break;
            case 'faq':
                foreach ($items as $it) $body .= '<details class="card"><summary>' . h($it['title']) . '</summary><p>' . h($it['text']) . '</p></details>';
                break;
            case 'how': case 'schedule':
                $body .= '<ol class="steps">';
                foreach ($items as $it) $body .= '<li><b>' . h($it['title']) . '</b><span>' . h($it['text']) . '</span></li>';
                $body .= '</ol>';
                break;
            case 'menu': case 'tracks':
                $body .= '<ul class="list">';
                foreach ($items as $it) {
                    $body .= '<li><div><b>' . h($it['title']) . '</b><small>' . h($it['text']) . '</small></div>'
                          . (isset($it['price']) ? '<span class="price">' . h($it['price']) . '</span>' : '') . '</li>';
                }
                $body .= '</ul>';
                break;
            case 'team':
                $body .= '<div class="grid">';
                foreach ($items as $it) {
                    $body .= '<div class="card person"><div class="ava">' . h(mb_substr($it['title'], 0, 1)) . '</div><b>' . h($it['title']) . '</b><small>' . h($it['text']) . '</small></div>';
                }
                $body .= '</div>';
                break;
            case 'contacts':
                $c = $spec['contacts'] ?? [];
                $body .= '<p class="lead">' . h($s['text'] ?? '') . '</p><div class="contacts">';
                if (!empty($c['email'])) $body .= '<a class="btn" href="mailto:' . h($c['email']) . '">' . h($c['email']) . '</a>';
                if (!empty($c['phone'])) $body .= '<a class="btn ghost" href="tel:' . h(preg_replace('/[^\d+]/', '', $c['phone'])) . '">' . h($c['phone']) . '</a>';
                if (!empty($c['telegram'])) $body .= '<a class="btn ghost" href="https://t.me/' . h($c['telegram']) . '" rel="noopener">Telegram: @' . h($c['telegram']) . '</a>';
                if (!empty($c['address'])) $body .= '<p class="addr">' . h($c['address']) . '</p>';
                if (!$c) $body .= '<p class="addr">Добавьте контакты: попросите ИИ «добавь почту name@mail.ru и телефон +7 900 000-00-00».</p>';
                $body .= '</div>';
                break;
            default:  // services, features, prices, products, projects, posts, courses
                $body .= '<div class="grid">';
                foreach ($items as $k => $it) {
                    $pic = in_array($s['kind'], ['products', 'projects', 'posts'], true)
                        ? '<img alt="" src="' . sg_art($seed + 31 * ($k + 1) + $i, 600, 360, $accent, $dark ? '#16161a' : sg_mix($bg, $accent, 0.1)) . '">' : '';
                    $body .= '<article class="card">' . $pic . (isset($it['date']) ? '<small>' . h($it['date']) . '</small>' : '')
                          . '<h3>' . h($it['title']) . '</h3><p>' . h($it['text']) . '</p>'
                          . (isset($it['price']) ? '<div class="price">' . h($it['price']) . '</div>' : '') . '</article>';
                }
                $body .= '</div>';
        }
        $body .= '</div></section>';
    }

    $owner = h($spec['owner'] ?? '');
    $year = date('Y');
    $studio = h(STUDIO_URL);
    $desc = h($spec['tagline']);
    $tagline = h($spec['tagline']);
    // Текст на кнопках: белый на тёмном акценте, чёрный на светлом (жёлтом, бирюзовом…)
    $rgb = sscanf($accent, '#%02x%02x%02x');
    $lum = (0.2126 * $rgb[0] + 0.7152 * $rgb[1] + 0.0722 * $rgb[2]) / 255;
    $ink = $lum > 0.6 ? '#111111' : '#ffffff';
    $hdr = $dark ? 'rgba(12,12,14,.86)' : 'rgba(250,248,245,.9)';

    return <<<HTML
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{$title}</title>
<meta name="description" content="{$desc}">
<meta name="generator" content="AI Studio Rteam">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@700;800&family=Onest:wght@400;500;700&display=swap">
<style>
:root{--bg:{$bg};--fg:{$fg};--muted:{$muted};--line:{$line};--surface:{$surface};--accent:{$accent};--ink:{$ink}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 "Onest","Segoe UI",system-ui,sans-serif}
a{color:var(--accent)}img{max-width:100%;display:block}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
header{position:sticky;top:0;z-index:10;background:{$hdr};backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
header .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:64px}
.logo{font:800 20px/1 "Unbounded","Arial Black",sans-serif;color:var(--fg);text-decoration:none}
.logo span{color:var(--accent)}
nav{display:flex;gap:18px;flex-wrap:wrap}nav a{color:var(--fg);text-decoration:none;font-weight:500;font-size:15px}
nav a:hover{color:var(--accent)}
#menu{display:none;background:none;border:1px solid var(--line);color:var(--fg);border-radius:10px;padding:8px 12px;font:inherit}
.hero{position:relative;overflow:hidden;border-bottom:1px solid var(--line)}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.55}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,var(--bg) 18%,transparent 78%)}
.hero .wrap{position:relative;z-index:1;padding:110px 20px 100px}
.hero h1{font:800 clamp(38px,7vw,76px)/1.02 "Unbounded","Arial Black",sans-serif;margin:0 0 18px;letter-spacing:-.02em;max-width:14ch}
.hero p{font-size:clamp(18px,2.4vw,22px);color:var(--fg);margin:0 0 30px;max-width:40ch}
.btn{display:inline-block;background:var(--accent);color:var(--ink);padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:700}
.btn.ghost{background:transparent;color:var(--fg);border:1px solid var(--line)}
.sec{padding:84px 0;border-bottom:1px solid var(--line)}
.sec h2{font:800 clamp(28px,4vw,40px)/1.1 "Unbounded","Arial Black",sans-serif;margin:0 0 30px;letter-spacing:-.01em}
.lead{font-size:20px;max-width:62ch;margin:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:22px;margin:0;display:flex;flex-direction:column;gap:8px}
.card img{border-radius:10px;margin:-6px -6px 6px;width:calc(100% + 12px);max-width:none;aspect-ratio:5/3;object-fit:cover}
.card h3{margin:0;font-size:20px}.card p{margin:0;color:var(--muted)}.card small{color:var(--muted)}
.price{font:800 22px/1 "Unbounded","Arial Black",sans-serif;color:var(--accent);margin-top:auto}
blockquote.card p{color:var(--fg);font-size:18px}cite{color:var(--muted);font-style:normal}
details.card{margin-bottom:12px}summary{cursor:pointer;font-weight:700;font-size:18px}
.tags{display:flex;flex-wrap:wrap;gap:10px}.tags span{border:1px solid var(--accent);border-radius:999px;padding:8px 16px;font-weight:500}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.gallery img{border-radius:12px;aspect-ratio:10/7;object-fit:cover;width:100%}
.steps{list-style:none;counter-reset:s;padding:0;margin:0;display:grid;gap:14px}
.steps li{counter-increment:s;display:flex;gap:18px;align-items:baseline;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 22px}
.steps li::before{content:counter(s,decimal-leading-zero);font:800 22px/1 "Unbounded",sans-serif;color:var(--accent)}
.steps b{min-width:120px}
.list{list-style:none;padding:0;margin:0;max-width:720px}
.list li{display:flex;justify-content:space-between;gap:20px;padding:16px 0;border-bottom:1px dashed var(--line)}
.list small{display:block;color:var(--muted)}
.person{align-items:center;text-align:center}.ava{width:72px;height:72px;border-radius:50%;background:var(--accent);color:var(--ink);display:grid;place-items:center;font:800 28px/1 "Unbounded",sans-serif}
.contacts{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-top:24px}.addr{width:100%;color:var(--muted);margin:6px 0 0}
footer{padding:36px 0;color:var(--muted);font-size:14px}footer .wrap{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media (max-width:760px){#menu{display:block}nav{display:none;position:absolute;left:0;right:0;top:64px;background:var(--bg);flex-direction:column;padding:16px 20px;border-bottom:1px solid var(--line)}
nav.open{display:flex}.steps li{flex-direction:column;gap:6px}.sec{padding:60px 0}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
</head>
<body>
<header><div class="wrap"><a class="logo" href="#top">{$title}<span>.</span></a>
<button id="menu" type="button" aria-label="Меню">Меню</button><nav id="nav">{$nav}</nav></div></header>
<main id="top">
<section class="hero"><img alt="" src="{$hero}"><div class="wrap"><h1>{$title}</h1><p>{$tagline}</p><a class="btn" href="#s1">Подробнее</a></div></section>
{$body}
</main>
<footer><div class="wrap"><span>© {$year} {$title}</span><span>Сайт создан ИИ в <a href="{$studio}" rel="noopener">AI Studio Rteam</a> · {$owner}</span></div></footer>
<script>
document.getElementById("menu").onclick=function(){document.getElementById("nav").classList.toggle("open")};
document.querySelectorAll("#nav a").forEach(function(a){a.onclick=function(){document.getElementById("nav").classList.remove("open")}});
</script>
</body>
</html>
HTML;
}

// ---------------------------------------------------------------- черновик и публикация
function sg_load($username) { return load_json('specs/' . $username . '.json', null); }

function sg_save($username, $spec) { save_json('specs/' . $username . '.json', $spec); }

/** Публикация: только ИИ-конструктор пишет файлы сайта — один index.html в папку пользователя. */
function sg_publish($username, $spec) {
    if (!valid_username($username)) throw new RuntimeException('bad username');
    $dir = SITES_DIR . '/' . $username;
    if (!is_dir($dir)) mkdir($dir, 0755, true);
    file_put_contents($dir . '/index.html', sg_render($spec), LOCK_EX);
    $spec['published'] = time();
    sg_save($username, $spec);
    return site_url($username);
}

function sg_unpublish($username) {
    if (!valid_username($username)) return;
    $file = site_file($username);
    if (is_file($file)) unlink($file);
    $dir = dirname($file);
    if (is_dir($dir) && count(scandir($dir)) === 2) rmdir($dir);
}

// ---------------------------------------------------------------- сайт от нейросети Rai (studio_ai.php)
const SG_HTML_MAX = 400000;

/**
 * Очистить HTML, который написала нейросеть: сайты открываются на том же адресе, что и студия, поэтому никаких скриптов,
 * обработчиков событий, javascript:-ссылок, встроенных окон и перенаправлений — только разметка и стили.
 */
function sg_clean_html($html) {
    $h = (string)$html;
    $h = preg_replace('#^\s*```[a-z]*\s*|\s*```\s*$#i', '', $h);                       // обёртка ```html … ```
    $h = preg_replace('#<(script|iframe|frame|frameset|object|embed|applet|noscript|template)\b[^>]*>.*?</\1\s*>#is', '', $h);
    $h = preg_replace('#<(script|iframe|frame|frameset|object|embed|applet|base|portal)\b[^>]*/?>#is', '', $h);
    $h = preg_replace('#<meta\b[^>]*http-equiv\s*=\s*["\']?\s*(refresh|set-cookie)[^>]*>#is', '', $h);
    $h = preg_replace('#<link\b(?![^>]*\brel\s*=\s*["\']?(stylesheet|preconnect|icon)\b)[^>]*>#is', '', $h);
    $h = preg_replace('#\s+on[a-z]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)#is', '', $h);
    $h = preg_replace('#\s(href|src|action|formaction|xlink:href|poster|background|data)\s*=\s*(["\']?)\s*(javascript|vbscript|data:text/html|data:application)[^"\'>]*\2#is', ' $1="#"', $h);
    $h = preg_replace('#(expression\s*\(|url\s*\(\s*["\']?\s*javascript:)#is', '(', $h);
    $h = preg_replace('#<form\b([^>]*)\saction\s*=\s*(["\']?)(?!mailto:|\#)[^"\'>\s]*\2#is', '<form$1 action="#"', $h);
    if (!preg_match('#<html\b#i', $h)) {
        $h = "<!DOCTYPE html>\n<html lang=\"ru\">\n<head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"></head>\n<body>\n" . $h . "\n</body>\n</html>";
    }
    if (!preg_match('#<meta\b[^>]*charset#i', $h)) $h = preg_replace('#<head\b[^>]*>#i', '$0<meta charset="utf-8">', $h, 1);
    if (!preg_match('#</html>\s*$#i', $h)) $h .= "\n</body></html>";
    if (stripos($h, 'AI Studio Rteam') === false) {
        $badge = '<p style="text-align:center;font:12px/1.4 system-ui,sans-serif;opacity:.6;margin:24px 0">Сайт создан в <a href="' . h(STUDIO_URL) . '" style="color:inherit">AI Studio Rteam</a></p>';
        $h = preg_match('#</body>#i', $h) ? preg_replace('#</body>#i', $badge . '</body>', $h, 1) : $h . $badge;
    }
    return $h;
}

/** Сохранить сайт от нейросети (страница студии). */
function studio_save_html($username, $html, $prompt, $title) {
    $html = trim((string)$html);
    if (strlen($html) < 200) return ['error' => 'Нейросеть вернула слишком мало кода — попробуйте ещё раз.'];
    if (strlen($html) > SG_HTML_MAX) return ['error' => 'Сайт получился слишком большим (больше 400 КБ).'];
    $clean = sg_clean_html($html);
    if (!$title && preg_match('#<title>(.*?)</title>#is', $clean, $m)) $title = html_entity_decode(strip_tags($m[1]), ENT_QUOTES, 'UTF-8');
    $old = sg_load($username);
    $spec = ['title' => mb_substr(trim((string)$title) ?: 'Мой сайт', 0, 80), 'html' => $clean, 'mode' => 'neuro',
             'prompt' => mb_substr((string)$prompt, 0, 2000), 'updated' => time(), 'sections' => []];
    if ($old && !empty($old['published'])) $spec['published'] = $old['published'];
    sg_save($username, $spec);
    return ['message' => 'Сохранено: «' . $spec['title'] . '».', 'spec' => $spec];
}

// ---------------------------------------------------------------- тексты от нейросети + дизайн студии
const SG_KINDS = ['about', 'text', 'services', 'features', 'prices', 'reviews', 'menu', 'products', 'projects', 'skills',
                  'posts', 'faq', 'team', 'schedule', 'courses', 'how', 'tracks', 'gallery', 'contacts'];
const SG_ITEM_KINDS = ['services', 'features', 'prices', 'reviews', 'menu', 'products', 'projects', 'posts', 'faq', 'team',
                       'schedule', 'courses', 'how', 'tracks'];

/** Строка из ответа нейросети: без тегов, без лишних пробелов, не длиннее $max символов. */
function sg_str($v, $max) {
    if (!is_scalar($v)) return '';
    $s = trim(preg_replace('/\s+/u', ' ', strip_tags(html_entity_decode((string)$v, ENT_QUOTES, 'UTF-8'))));
    return mb_strlen($s) > $max ? rtrim(mb_substr($s, 0, $max - 1)) . '…' : $s;
}

/**
 * Спецификация сайта, которую написала нейросеть (JSON: название, слоган, тема, цвет, разделы с текстами, контакты),
 * — проверить и привести к виду, который понимает sg_render(): только известные виды разделов, разумные длины,
 * контакты из описания клиента — всегда на месте, раздел «Контакты» — последним.
 */
function sg_clean_spec($in, $username, $prompt, $fresh = true) {
    if (!is_array($in)) return null;
    $prompt = trim(mb_substr((string)$prompt, 0, 2000));
    $theme = sg_lower($in['theme'] ?? '') === 'dark' ? 'dark' : 'light';
    $accent = preg_match('/^#[0-9a-f]{6}$/i', (string)($in['accent'] ?? '')) ? strtolower($in['accent']) : null;
    $want = sg_extract_color(sg_lower($prompt));   // в новом сайте цвет, который назвал клиент, главнее выбора нейросети
    $spec = [
        'version' => 1, 'type' => sg_detect_type(sg_lower($prompt)), 'owner' => $username,
        'title' => sg_str($in['title'] ?? '', 60) ?: (sg_extract_name($prompt) ?: 'Мой сайт'),
        'tagline' => sg_str($in['tagline'] ?? '', 160), 'theme' => $theme,
        'accent' => ($fresh ? $want : null) ?: ($accent ?: ($want ?: SG_PALETTES[$theme][2])),
        'seed' => crc32($username . microtime()), 'sections' => [], 'contacts' => [],
        'prompt' => $prompt, 'updated' => time(), 'mode' => 'neuro-spec',
    ];
    if (!empty($in['seed']) && is_numeric($in['seed'])) $spec['seed'] = (int)$in['seed'];

    $contacts = null;
    foreach (array_slice(is_array($in['sections'] ?? null) ? array_values($in['sections']) : [], 0, 12) as $s) {
        if (!is_array($s)) continue;
        $title = sg_str($s['title'] ?? '', 60);
        $kind = sg_lower(sg_str($s['kind'] ?? '', 20));
        if (in_array($kind, ['hero', 'main', 'header', 'intro', 'banner'], true)) {   // главный экран делает сама студия
            if ($spec['tagline'] === '') $spec['tagline'] = sg_str($s['text'] ?? ($s['tagline'] ?? ''), 160);
            continue;
        }
        if (!in_array($kind, SG_KINDS, true)) $kind = sg_section_kind($title . ' ' . $kind);
        $sec = ['kind' => $kind, 'title' => $title ?: (SG_SECTION_TITLES[$kind] ?? 'Раздел')];
        $text = sg_str($s['text'] ?? '', 1500);
        $items = [];
        foreach (array_slice(is_array($s['items'] ?? null) ? array_values($s['items']) : [], 0, 12) as $it) {
            if (is_string($it)) $it = ['title' => $it];
            if (!is_array($it)) continue;
            $row = ['title' => sg_str($it['title'] ?? ($it['name'] ?? ($it['question'] ?? '')), 90),
                    'text' => sg_str($it['text'] ?? ($it['description'] ?? ($it['answer'] ?? '')), 500)];
            foreach (['price' => 40, 'date' => 30] as $f => $max) {
                $v = sg_str($it[$f] ?? '', $max);
                if ($v !== '') $row[$f] = $v;
            }
            if ($row['title'] === '' && $row['text'] === '') continue;
            if ($row['title'] === '') { $row['title'] = $row['text']; $row['text'] = ''; }
            $items[] = $row;
        }
        $tags = [];
        foreach (array_slice(is_array($s['tags'] ?? null) ? $s['tags'] : [], 0, 24) as $t) {
            $t = sg_str($t, 32);
            if ($t !== '') $tags[] = $t;
        }
        if ($kind === 'contacts') {
            $sec['text'] = $text ?: 'Напишите или позвоните — ответим быстро.';
            $contacts = $sec;
            continue;
        }
        if ($kind === 'skills') {
            if (!$tags) $tags = array_map(function ($it) { return $it['title']; }, $items);
            if (!$tags) { if ($text === '') continue; $kind = 'text'; } else $sec['tags'] = array_slice($tags, 0, 24);
        } elseif ($kind === 'gallery') {
            $sec['count'] = max(3, min(12, (int)($s['count'] ?? 6) ?: 6));
        } elseif (in_array($kind, SG_ITEM_KINDS, true)) {
            if (!$items) {
                if ($text === '') continue;
                $kind = 'text';
            } else {
                $sec['items'] = $items;
            }
        } else {  // about, text — абзац; если нейросеть дала список — склеиваем в текст
            if ($text === '' && $items) $text = implode(' ', array_map(function ($it) { return trim($it['title'] . '. ' . $it['text'], ' .') . '.'; }, $items));
            if ($text === '') continue;
        }
        $sec['kind'] = $kind;
        if ($kind === 'text' || $kind === 'about') $sec['text'] = $text;
        $spec['sections'][] = $sec;
    }
    if (count($spec['sections']) < 1) return null;
    $spec['sections'][] = $contacts ?: sg_default_section('contacts', $spec['type'], $spec['title']);

    $c = is_array($in['contacts'] ?? null) ? $in['contacts'] : [];
    $email = sg_str($c['email'] ?? '', 120);
    if (filter_var($email, FILTER_VALIDATE_EMAIL) && !preg_match('/example\.|test@|mail@mail|name@/i', $email)) $spec['contacts']['email'] = $email;
    $phone = sg_str($c['phone'] ?? '', 40);
    if (preg_match('/^\+?[\d\s()\-]{7,}$/', $phone) && !preg_match('/0{3}[\s-]*0{2}[\s-]*0{2}|123[\s-]*45[\s-]*67|x{2}/i', $phone)) $spec['contacts']['phone'] = $phone;
    $tg = preg_replace('#^(?:https?://)?(?:t\.me/|@)#i', '', sg_str($c['telegram'] ?? '', 60));
    if (preg_match('/^[A-Za-z0-9_]{4,32}$/', $tg)) $spec['contacts']['telegram'] = $tg;
    $addr = sg_str($c['address'] ?? '', 160);
    if (mb_strlen($addr) >= 5) $spec['contacts']['address'] = $addr;
    if (!$fresh) return $spec;   // правка: контакты уже проверены при создании (или их поменял сам клиент)
    // нейросеть могла выдумать почту и телефон — всё, что клиент написал сам, важнее
    $own = ['contacts' => []];
    sg_extract_contacts($prompt, $own);
    foreach ($own['contacts'] as $k => $v) $spec['contacts'][$k] = $v;
    if (!$own['contacts'] && !preg_match('/контакт|почт|телефон|адрес|телеграм|telegram|@/u', sg_lower($prompt))) {
        // клиент контактов не давал — выдуманные почту и телефон не публикуем (только адрес и текст)
        unset($spec['contacts']['email'], $spec['contacts']['phone'], $spec['contacts']['telegram']);
    }
    return $spec;
}

/** То, что нужно странице студии для правок нейросетью: разделы и оформление (без служебных полей). */
function sg_public_spec($spec) {
    if (!$spec || !empty($spec['html'])) return null;
    $out = [];
    foreach (['title', 'tagline', 'theme', 'accent', 'sections', 'contacts', 'seed'] as $k) if (isset($spec[$k])) $out[$k] = $spec[$k];
    return $out;
}

/** Сохранить сайт «тексты нейросети + дизайн студии» (страница студии, studio_ai.php). */
function studio_save_spec($username, $json, $prompt, $fresh = true) {
    $in = is_array($json) ? $json : json_decode((string)$json, true);
    if (strlen(is_string($json) ? $json : '') > 200000) return ['error' => 'Слишком большой ответ нейросети.'];
    $old = sg_load($username);
    if ($prompt === '' && $old) $prompt = (string)($old['prompt'] ?? '');
    $spec = sg_clean_spec($in, $username, $prompt, $fresh);
    if (!$spec) return ['error' => 'Нейросеть не написала ни одного раздела — попробуйте ещё раз.'];
    if (!$fresh && $old && empty($old['html']) && isset($old['seed']) && empty($in['seed'])) $spec['seed'] = $old['seed'];
    if ($old && !empty($old['published'])) $spec['published'] = $old['published'];
    sg_save($username, $spec);
    $names = array_map(function ($s) { return $s['title']; }, $spec['sections']);
    return ['message' => 'Готово: сайт «' . $spec['title'] . '» — разделы: ' . implode(', ', $names) . '.', 'spec' => $spec];
}

// ---------------------------------------------------------------- действия (общие для студии и API)
function studio_generate($username, $prompt, $publish = false) {
    $prompt = trim((string)$prompt);
    if (mb_strlen($prompt) < 3) return ['error' => 'Опишите сайт хотя бы парой слов.'];
    $spec = sg_new_spec($prompt, $username);
    $old = sg_load($username);
    if ($old && !empty($old['published'])) $spec['published'] = $old['published'];
    sg_save($username, $spec);
    $names = array_map(function ($s) { return $s['title']; }, $spec['sections']);
    $out = ['message' => 'Готово: сайт «' . $spec['title'] . '» — разделы: ' . implode(', ', $names) . '.', 'spec' => $spec];
    if ($publish) $out['url'] = sg_publish($username, $spec);
    return $out;
}

function studio_edit($username, $instruction, $publish = false) {
    $spec = sg_load($username);
    if (!$spec) return ['error' => 'Сначала создайте сайт: опишите его словами.'];
    if (!empty($spec['html'])) return ['error' => 'Этот сайт написала нейросеть Rai — правьте его тоже с нейросетью (переключатель «Нейросеть» в студии) или создайте заново шаблоном.'];
    list($spec, $done) = sg_edit_spec($spec, $instruction);
    if ($done === null) {
        return ['error' => 'Не понял правку. Примеры: «добавь раздел цены», «убери раздел отзывы», «сделай тёмным», ' .
                           '«цвет синий», «переименуй в «Кофе & Ко»», «измени раздел о нас на: …», «добавь почту name@mail.ru».'];
    }
    sg_save($username, $spec);
    $out = ['message' => 'Сделано: ' . $done . '.', 'spec' => $spec];
    if ($publish) $out['url'] = sg_publish($username, $spec);
    return $out;
}
