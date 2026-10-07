<?php
/* AI Studio — рабочее место: ИИ создаёт сайт, предпросмотр, публикация, API-ключи, чат Rai. */
require __DIR__ . '/config.php';
$user = require_user();
$name = $user['username'];
$csrf = csrf_token();
$chat = rtrim(RAI_URL, '/') . '/chat.html';  // сам чат Rai с rai.rteam.info прямо в студии (а не главная с тарифами)
$initial = mb_strtoupper(mb_substr($user['name'] ?: $name, 0, 1));
?>
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Студия — AI Studio Rteam</title>
<meta name="csrf" content="<?= h($csrf) ?>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Unbounded:wght@600;700;800&family=Onest:wght@400;500;600;700&family=JetBrains+Mono&display=swap">
<meta name="theme-color" content="#07070b">
<?php include __DIR__ . '/assets/style.php'; ?>
</head>
<body class="studio-page">
<header class="topbar">
  <a class="brand" href="studio.php"><i>✦</i>AI <span>Studio</span></a>
  <nav>
    <a href="<?= h(RAI_URL) ?>">Rai — основной ИИ</a>
    <a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>
    <a href="<?= h(ACCOUNT_URL) ?>/account.php">Кабинет</a>
    <span class="me"><span class="ava"><?php if (!empty($user['avatar'])): ?><img alt="" src="<?= h($user['avatar']) ?>" referrerpolicy="no-referrer"><?php else: ?><?= h($initial) ?><?php endif; ?></span><?= h($user['name'] ?: $name) ?></span>
    <form method="post" action="auth.php" style="margin:0">
      <input type="hidden" name="csrf" value="<?= h($csrf) ?>"><input type="hidden" name="action" value="logout">
      <button class="btn ghost small" type="submit">Выйти</button>
    </form>
  </nav>
</header>

<main class="studio">
  <div class="work">
    <?php if (isset($_GET['welcome'])): ?>
      <p class="okmsg">Добро пожаловать, <?= h($user['name'] ?: $name) ?>! Опишите свой первый сайт ниже.</p>
    <?php endif; ?>

    <section class="panel" aria-labelledby="h-site">
      <h2 id="h-site">Ваш сайт</h2>
      <div class="row"><span id="pubState" class="status-pill">Проверяю…</span>
        <a id="siteLink" class="url" href="<?= h(site_url($name)) ?>" target="_blank" rel="noopener"><?= h(site_url($name)) ?></a></div>
      <p class="muted" style="margin:0">Папка сайта: <span class="mono">sites/<?= h($name) ?>/</span>. Файлы в ней создаёт только ИИ студии.</p>
    </section>

    <section class="panel" aria-labelledby="h-ai">
      <h2 id="h-ai">ИИ-конструктор</h2>
      <div class="ai-mode" id="aiMode" role="group" aria-label="Чем делать сайт">
        <button type="button" data-mode="template"><b>⚡ Конструктор Rai</b><small>мгновенно, ничего не скачивает: свои разделы, тексты и дизайн по описанию</small></button>
        <button type="button" data-mode="neuro"><b>🧠 Внешняя нейросеть</b><small>необязательно: придумывает тексты сама, но сначала скачивает модель (0,5–5 ГБ)</small></button>
      </div>
      <div class="neuro-bar" id="neuroBar">
        <div class="row">
          <span id="neuroState" class="status-pill">Нейросеть включится сама при создании сайта</span>
          <button class="btn ghost small" id="neuroOn" type="button">Включить сейчас</button>
          <span id="neuroLeft" class="muted small" hidden></span>
        </div>
        <div class="progress" id="neuroProgress" hidden><i id="neuroProgressBar"></i></div>
        <div class="row">
          <select id="neuroModel" class="input" aria-label="Модель нейросети">
            <option value="auto">Модель: лучшая для этого компьютера</option>
            <option value="fast">Лайт</option>
            <option value="normal">Стандарт</option>
            <option value="strong">Про</option>
            <option value="coder">Код</option>
            <option value="max">Макс</option>
          </select>
          <select id="neuroHow" class="input" aria-label="Как делать сайт">
            <option value="auto">Авто: по силе модели</option>
            <option value="spec">Тексты нейросети + дизайн студии</option>
            <option value="code">Весь код пишет нейросеть (свой дизайн)</option>
          </select>
        </div>
        <p class="muted small" id="neuroHint">Нейросеть работает прямо в вашем браузере, на вашей видеокарте: первый раз модель скачивается
          (0,6–5 ГБ), дальше — из кэша. «Тексты + дизайн студии» — быстро и надёжно на любой модели; «весь код» — свой дизайн,
          лучше с моделями Про, Код и Макс. Тот же аккаунт и тариф, что в чате Rai.</p>
      </div>
      <label class="field" for="prompt">Опишите сайт словами</label>
      <textarea id="prompt" placeholder="Например: сайт кофейни «Зерно» в тёмных тонах с разделами меню, отзывы и контакты. Почта zerno@mail.ru"></textarea>
      <div class="chips" id="examples">
        <button type="button">Портфолио программиста, синий цвет</button>
        <button type="button">Сайт кофейни «Зерно» в тёмных тонах с меню и отзывами</button>
        <button type="button">Лендинг для телеграм-бота, чёрно-красный</button>
        <button type="button">Онлайн-школа рисования с курсами и ценами</button>
        <button type="button">Сайт нашего клана в Minecraft</button>
      </div>
      <div class="row"><button class="btn" id="genBtn" type="button">Создать сайт</button>
        <button class="btn ghost" id="stopBtn" type="button" hidden>■ Остановить</button></div>
      <p class="ai-step" id="aiStep" aria-live="polite" hidden></p>
      <label class="field" for="edit">Что изменить?</label>
      <div class="row">
        <input id="edit" class="input" style="flex:1;min-width:200px"
               placeholder="добавь раздел цены · сделай синим · перепиши отзывы смешнее · переименуй в «…»">
        <button class="btn ghost" id="editBtn" type="button">Изменить</button>
      </div>
      <div class="log" id="log" aria-live="polite"></div>
    </section>

    <section class="panel" aria-labelledby="h-prev">
      <div class="row" style="justify-content:space-between">
        <h2 id="h-prev">Предпросмотр</h2>
        <div class="row">
          <button class="btn" id="pubBtn" type="button">Опубликовать</button>
          <a class="btn ghost" id="openBtn" href="<?= h(site_url($name)) ?>" target="_blank" rel="noopener">Открыть сайт</a>
          <a class="btn ghost" id="zipBtn" href="actions.php?a=zip">Скачать ZIP</a>
          <button class="btn ghost" id="unpubBtn" type="button">Снять с публикации</button>
        </div>
      </div>
      <iframe class="preview" id="preview" title="Предпросмотр сайта" sandbox="allow-scripts"></iframe>
    </section>

    <section class="panel" aria-labelledby="h-api">
      <h2 id="h-api">API-ключ</h2>
      <p class="muted" style="margin:0">Ключ даёт доступ к ИИ студии из ваших программ: создать, изменить и опубликовать сайт.
        Храните его в секрете; ключ показывается один раз.</p>
      <div class="row">
        <input id="keyLabel" class="input" placeholder="Название ключа (необязательно)" maxlength="40" style="flex:1;min-width:180px">
        <button class="btn" id="keyBtn" type="button">Получить API-ключ</button>
      </div>
      <div id="newKey" class="newkey" hidden></div>
      <div class="table-scroll"><table class="keys"><thead><tr><th>Ключ</th><th>Название</th><th>Создан</th><th>Использован</th><th></th></tr></thead>
        <tbody id="keys"><tr><td colspan="5" class="muted">Ключей пока нет.</td></tr></tbody></table></div>
      <details>
        <summary>Как пользоваться API</summary>
        <pre><code>curl -X POST "<?= h(STUDIO_URL) ?>/api.php?a=generate" \
  -H "Authorization: Bearer ВАШ_КЛЮЧ" -H "Content-Type: application/json" \
  -d '{"prompt": "сайт пекарни «Булка» с меню и контактами"}'

curl -X POST "<?= h(STUDIO_URL) ?>/api.php?a=edit" \
  -H "Authorization: Bearer ВАШ_КЛЮЧ" -H "Content-Type: application/json" \
  -d '{"instruction": "добавь раздел отзывы"}'

curl "<?= h(STUDIO_URL) ?>/api.php?a=site" -H "Authorization: Bearer ВАШ_КЛЮЧ"</code></pre>
        <p class="muted">Ответ — JSON с адресом сайта. Лимит: <?= (int)API_LIMIT_PER_HOUR ?> запросов в час.</p>
      </details>
    </section>
  </div>

  <aside class="panel chat" aria-label="Чат Rai">
    <div class="head"><h2>Чат Rai</h2><a href="<?= h($chat) ?>" target="_blank" rel="noopener">Открыть отдельно ↗</a></div>
    <iframe src="<?= h($chat) ?>" title="Чат Rai" allow="microphone; clipboard-read; clipboard-write; fullscreen" loading="lazy"></iframe>
  </aside>
</main>
<footer class="foot"><span>© <?= date('Y') ?> Rteam</span><a href="<?= h(RAI_URL) ?>">rai.rteam.info</a><a href="<?= h(GITHUB_URL) ?>" rel="noopener">GitHub</a>
  <a href="<?= h(rtrim(RAI_URL, '/')) ?>/rules.php">Правила</a><a href="<?= h(rtrim(RAI_URL, '/')) ?>/terms.php">Соглашение</a><a href="<?= h(rtrim(RAI_URL, '/')) ?>/privacy.php">Конфиденциальность</a></footer>
<script>window.STUDIO_RAI = <?= json_encode(rtrim(ACCOUNT_URL, '/'), JSON_UNESCAPED_SLASHES) ?>;</script>
<script src="assets/neuro.php"></script>
<?php include __DIR__ . '/assets/studio_ai.php'; ?>
<?php include __DIR__ . '/assets/script.php'; ?>
</body>
</html>
