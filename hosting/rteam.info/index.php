<?php
/* Rteam — главная страница: сервисы (Rai, Rai Code, AI Studio) и вход в аккаунт. */
require __DIR__ . '/config.php';
$user = current_user();
page_head('Rteam — свой ИИ Rai, Code и AI Studio', $user);
$studio = STUDIO_URL . ($user ? '/sso_start.php' : '/');
?>
<main>
  <section class="hero">
    <div>
      <p class="kicker">Rteam · свой искусственный интеллект</p>
      <h1>Один аккаунт — <span>Rai</span>, Code и AI Studio</h1>
      <p class="lead">Rai отвечает на вопросы, переводит, знает погоду и курсы валют, рисует картинки и делает презентации.
        В Rai Code он пишет, проверяет и запускает программы, а AI Studio собирает и публикует сайт по описанию.</p>
      <div class="row">
        <a class="btn big" href="<?= h(RAI_URL) ?>">Открыть Rai</a>
        <?php if ($user): ?>
          <a class="btn big ghost" href="account.php">Личный кабинет</a>
        <?php else: ?>
          <a class="btn big ghost" href="login.php?tab=register">Создать аккаунт</a>
        <?php endif; ?>
      </div>
      <?php if ($user): ?>
        <p class="muted">Вы вошли как <b><?= h($user['name'] ?: $user['login']) ?></b>.</p>
      <?php endif; ?>
    </div>
    <div class="hero-art" aria-hidden="true">
      <div class="bubble q">Сделай презентацию про космос в синих тонах</div>
      <div class="bubble a"><b>Rai Pro Quasar</b> · Готово: 12 слайдов с фото и переходами</div>
      <div class="bubble q">напиши игру змейка</div>
      <div class="bubble a code">&lt;canvas id="game"&gt; … <span>▶ Запустить</span></div>
    </div>
  </section>

  <section class="cards" aria-label="Сервисы">
    <a class="card" href="<?= h(RAI_URL) ?>">
      <span class="tag">Чат</span>
      <h2>Rai</h2>
      <p>Свой ИИ без чужих API: ответы, таблицы, перевод со всех языков, погода с картинкой, валюты, поиск в интернете,
        картинки и презентации в ваших цветах. Голосовой ввод и архив чата в ZIP.</p>
      <span class="go">rai.rteam.info →</span>
    </a>
    <a class="card" href="<?= h(RAI_CODE_URL) ?>">
      <span class="tag">Программирование</span>
      <h2>Rai Code</h2>
      <p>Редактор с подсветкой, запуск Python, JavaScript и HTML прямо в браузере, ИИ-помощник: найдёт ошибку,
        исправит, объяснит по строкам и напишет программу по описанию.</p>
      <span class="go">Открыть Code →</span>
    </a>
    <a class="card" href="<?= h($studio) ?>">
      <span class="tag">Сайты</span>
      <h2>AI Studio</h2>
      <p>Опишите сайт словами — ИИ соберёт и опубликует его по адресу aistudio.rteam.info/sites/ваш-логин/.
        API-ключи для своих программ. Вход — этим же аккаунтом.</p>
      <span class="go">aistudio.rteam.info →</span>
    </a>
  </section>

  <section class="models" aria-labelledby="h-models">
    <h2 id="h-models">Модели Rai</h2>
    <div class="table-scroll"><table>
      <thead><tr><th>Модель</th><th>Для чего</th></tr></thead>
      <tbody>
        <tr><td>Pro Fast</td><td>Самая быстрая: ключевые слова, калькулятор, погода, валюты, перевод</td></tr>
        <tr><td>Pro</td><td>Поиск по смыслу, интернет, таблицы, картинки</td></tr>
        <tr><td>Pro Plus</td><td>Понимает опечатки, презентации, проверка и написание кода</td></tr>
        <tr><td>Pro Sun</td><td>Память фактов, несколько вопросов сразу, подробные ответы</td></tr>
        <tr class="top"><td>Pro Quasar ✦</td><td>Самая сильная: всё из Pro Sun, режим Code, факты из интернета в ответах, презентации до 16 слайдов с фото</td></tr>
      </tbody>
    </table></div>
  </section>
</main>
<?php page_foot();
