//go:build windows

package main

import (
	"os/exec"
	"syscall"
	"unsafe"
)

// fatalNoWebView2 показывает понятное окно, если WebView2 Runtime не установлен,
// и предлагает открыть страницу загрузки. На Windows 10/11 Runtime обычно уже есть.
func fatalNoWebView2() {
	const url = "https://developer.microsoft.com/microsoft-edge/webview2/"
	const text = "Не удалось запустить встроенный браузер (WebView2).\r\n\r\n" +
		"Скорее всего, не установлен компонент «Microsoft Edge WebView2 Runtime».\r\n" +
		"Он бесплатный и ставится один раз.\r\n\r\n" +
		"Нажмите «ОК», чтобы открыть страницу загрузки, затем установите\r\n" +
		"«Evergreen Standalone Installer» и запустите приложение снова."
	const title = "RTeam — Админ-панель"

	// MB_OKCANCEL | MB_ICONERROR = 0x1 | 0x10
	if messageBox(text, title, 0x00000011) == 1 /* IDOK */ {
		// Открываем страницу загрузки в системном браузере.
		_ = exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	}
}

func messageBox(text, title string, flags uint32) int {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	t, _ := syscall.UTF16PtrFromString(text)
	c, _ := syscall.UTF16PtrFromString(title)
	ret, _, _ := proc.Call(
		0,
		uintptr(unsafe.Pointer(t)),
		uintptr(unsafe.Pointer(c)),
		uintptr(flags),
	)
	return int(ret)
}
