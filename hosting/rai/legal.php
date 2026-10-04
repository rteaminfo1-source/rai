<?php
/*
 * Общий вид документов Rai: правила (rules.php), пользовательское соглашение (terms.php),
 * политика конфиденциальности (privacy.php). Дата редакции — всегда сегодняшняя (ставится автоматически).
 */
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/moderation.php';

const LEGAL_DOCS = [
    'rules.php' => 'Правила',
    'terms.php' => 'Пользовательское соглашение',
    'privacy.php' => 'Политика конфиденциальности',
];

/**
 * $doc: ['file', 'title', 'lead', 'sections' => [[заголовок, html], …]]
 * Разделы нумеруются сами; в тексте можно писать {date}, {site}, {studio} и ссылки на другие документы.
 */
function legal_render(array $doc) {
    $user = current_user();
    $today = legal_date();
    $vars = ['{date}' => $today, '{site}' => 'rai.rteam.info', '{studio}' => 'aistudio.rteam.info',
             '{rules}' => '<a href="rules.php">Правилах Сервиса</a>', '{terms}' => '<a href="terms.php">Пользовательском соглашении</a>',
             '{privacy}' => '<a href="privacy.php">Политике конфиденциальности</a>',
             '{contacts}' => '<a href="https://rteam.info/" rel="noopener">rteam.info</a> (раздел «Контакты»)'];
    page_head($doc['title'] . ' — Rai', $user);
    ?>
<main class="legal">
  <nav class="legal-docs" aria-label="Документы">
    <?php foreach (LEGAL_DOCS as $file => $name): ?>
      <a href="<?= h($file) ?>"<?= $file === $doc['file'] ? ' aria-current="page"' : '' ?>><?= h($name) ?></a>
    <?php endforeach; ?>
  </nav>
  <header class="legal-head">
    <p class="kicker">Документы Rai · Rteam</p>
    <h1><?= h($doc['title']) ?></h1>
    <p class="legal-date"><span>Редакция от</span> <time datetime="<?= date('Y-m-d') ?>"><?= h($today) ?></time></p>
    <?php if (!empty($doc['lead'])): ?><p class="lead"><?= strtr($doc['lead'], $vars) ?></p><?php endif; ?>
  </header>
  <div class="legal-body">
    <aside class="legal-toc" aria-label="Содержание">
      <b>Содержание</b>
      <ol>
        <?php foreach ($doc['sections'] as $i => $s): ?><li><a href="#s<?= $i + 1 ?>"><?= h($s[0]) ?></a></li><?php endforeach; ?>
      </ol>
    </aside>
    <article class="legal-text">
      <?php foreach ($doc['sections'] as $i => $s): ?>
        <section id="s<?= $i + 1 ?>">
          <h2><span><?= $i + 1 ?></span><?= h($s[0]) ?></h2>
          <?= strtr($s[1], $vars) ?>
        </section>
      <?php endforeach; ?>
    </article>
  </div>
</main>
<?php
    page_foot();
}
