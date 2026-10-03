//go:build windows

// RTeam Админ — настольное приложение (Windows).
//
// Это тонкая оболочка на движке Microsoft Edge WebView2, которая открывает
// живую админ-панель https://rteam.info/admin.php. Благодаря этому панель
// «сама обновляется»: любое изменение admin.php на хостинге сразу видно в
// приложении — пересобирать .exe не нужно.
//
// Что умеет:
//   - вход и запоминание сессии между запусками (cookie хранятся в %AppData%);
//   - если вы ещё не вошли — сам открывает страницу входа, а после входа
//     возвращает прямо в админ-панель;
//   - горячие клавиши браузера (F5 — обновить, Alt+← — назад, Ctrl+± — масштаб);
//   - внешние ссылки и target=_blank открываются внутри окна, без лишних окон;
//   - адрес можно переопределить файлом rteam.url рядом с .exe, переменной
//     окружения RTEAM_URL или первым аргументом командной строки.
package main

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/jchv/go-webview2"
)

// Адрес админ-панели по умолчанию. Можно переопределить (см. resolveURL).
const defaultURL = "https://rteam.info/admin.php"

// Заголовок окна и имя папки с данными (cookie, кэш).
const (
	windowTitle = "RTeam — Админ-панель"
	dataDirName = "RTeamAdmin"
)

// resolveURL выбирает стартовый адрес в таком порядке:
//  1. первый аргумент командной строки (если это http/https ссылка);
//  2. переменная окружения RTEAM_URL;
//  3. файл rteam.url рядом с исполняемым файлом (первая непустая строка);
//  4. адрес по умолчанию.
func resolveURL() string {
	if len(os.Args) > 1 {
		if u := strings.TrimSpace(os.Args[1]); isHTTP(u) {
			return u
		}
	}
	if u := strings.TrimSpace(os.Getenv("RTEAM_URL")); isHTTP(u) {
		return u
	}
	if exe, err := os.Executable(); err == nil {
		p := filepath.Join(filepath.Dir(exe), "rteam.url")
		if b, err := os.ReadFile(p); err == nil {
			for _, line := range strings.Split(string(b), "\n") {
				line = strings.TrimSpace(line)
				if isHTTP(line) {
					return line
				}
			}
		}
	}
	return defaultURL
}

func isHTTP(u string) bool {
	return strings.HasPrefix(u, "http://") || strings.HasPrefix(u, "https://")
}

// dataPath — папка для cookie и данных WebView2, чтобы вход запоминался.
func dataPath() string {
	if dir, err := os.UserConfigDir(); err == nil && dir != "" {
		return filepath.Join(dir, dataDirName)
	}
	if exe, err := os.Executable(); err == nil {
		return filepath.Join(filepath.Dir(exe), dataDirName)
	}
	return ""
}

// initScript выполняется при загрузке каждой страницы сайта. Он:
//   - уводит на страницу входа, если админка ответила «Доступ запрещён»;
//   - после входа доводит пользователя обратно до админ-панели;
//   - заставляет target=_blank и window.open открываться в этом же окне.
const initScript = `
(function () {
  var ADMIN = '/admin.php', LOGIN = '/login.php';
  function go(u) { try { location.replace(u); } catch (e) { location.href = u; } }
  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  // Все ссылки и window.open — в этом же окне (без новых окон WebView2).
  try {
    window.open = function (u) { if (u) location.href = u; return null; };
    document.addEventListener('click', function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[target]') : null;
      if (a && a.target && a.target.toLowerCase() === '_blank') a.removeAttribute('target');
    }, true);
  } catch (e) {}

  ready(function () {
    try {
      var path = (location.pathname || '').toLowerCase();
      var txt = (document.body ? document.body.innerText : '').trim();

      // Админка вернула «Доступ запрещён.» — нужен вход.
      if (txt === 'Доступ запрещён.') {
        try { sessionStorage.setItem('rtGotoAdmin', '1'); } catch (e) {}
        if (path.indexOf('login.php') < 0) go(LOGIN);
        return;
      }

      // Мы пришли сюда после входа — доведём до админ-панели.
      var flag = null;
      try { flag = sessionStorage.getItem('rtGotoAdmin'); } catch (e) {}
      if (flag && path.indexOf('login.php') < 0 && path.indexOf('admin.php') < 0) {
        try { sessionStorage.removeItem('rtGotoAdmin'); } catch (e) {}
        go(ADMIN);
        return;
      }
      if (path.indexOf('admin.php') >= 0) {
        try { sessionStorage.removeItem('rtGotoAdmin'); } catch (e) {}
      }
    } catch (e) {}
  });
})();
`

func main() {
	w := webview2.NewWithOptions(webview2.WebViewOptions{
		Debug:     false,
		DataPath:  dataPath(),
		AutoFocus: true,
		WindowOptions: webview2.WindowOptions{
			Title:  windowTitle,
			Width:  1280,
			Height: 820,
			Center: true,
			IconId: 1, // иконка из ресурсов (winres), группа иконок с ID 1
		},
	})
	if w == nil {
		// WebView2 не удалось создать — почти всегда не установлен Runtime.
		fatalNoWebView2()
		return
	}
	defer w.Destroy()

	w.SetSize(900, 600, webview2.HintMin) // минимальный размер окна
	w.SetTitle(windowTitle)
	w.Init(initScript)
	w.Navigate(resolveURL())
	w.Run()
}
