; Красивый установщик Rai (NSIS) — подключается electron-builder'ом.
; Картинки (боковая панель и шапка) задаются в package.json (installerSidebar / installerHeader),
; здесь — только тёплые русские тексты мастера. Задаём их в customHeader: electron-builder вставляет
; этот макрос ДО страниц MUI, а сами эти тексты он не трогает, поэтому конфликтов нет.

!macro customHeader
  ; фирменная тёмная тема для ВСЕХ страниц мастера (фон и текст в цветах Rai) — установщик выглядит как приложение
  !ifndef MUI_BGCOLOR
    !define MUI_BGCOLOR "141420"
  !endif
  !ifndef MUI_TEXTCOLOR
    !define MUI_TEXTCOLOR "F5F5F7"
  !endif
  !ifndef MUI_WELCOMEPAGE_TITLE
    !define MUI_WELCOMEPAGE_TITLE "Rai — ваш ИИ-помощник"
  !endif
  !ifndef MUI_WELCOMEPAGE_TEXT
    !define MUI_WELCOMEPAGE_TEXT "Сейчас установим Rai: чат, код, презентации и распознавание картинок.$\r$\n$\r$\nЭто обычное приложение — весь ум внутри, работает без интернета.$\r$\n$\r$\nНажмите «Далее», чтобы продолжить."
  !endif
  !ifndef MUI_FINISHPAGE_TITLE
    !define MUI_FINISHPAGE_TITLE "Готово — Rai установлен"
  !endif
  !ifndef MUI_FINISHPAGE_TEXT
    !define MUI_FINISHPAGE_TEXT "Rai готов к работе. Запускайте и спрашивайте что угодно — он думает сам."
  !endif

  ; --- страница копирования файлов тоже фирменная: плавный прогресс, тёмный лог в цветах Rai, шапка с логотипом
  !ifndef MUI_INSTFILESPAGE_PROGRESSBAR
    !define MUI_INSTFILESPAGE_PROGRESSBAR "smooth"
  !endif
  !ifndef MUI_INSTFILESPAGE_COLORS
    !define MUI_INSTFILESPAGE_COLORS "F5F5F7 141420"
  !endif
  !ifndef MUI_HEADERIMAGE
    !define MUI_HEADERIMAGE
  !endif
  !ifndef MUI_HEADERIMAGE_RIGHT
    !define MUI_HEADERIMAGE_RIGHT
  !endif
  ; спросить по-человечески при отмене
  !ifndef MUI_ABORTWARNING
    !define MUI_ABORTWARNING
  !endif
  !ifndef MUI_ABORTWARNING_TEXT
    !define MUI_ABORTWARNING_TEXT "Точно прервать установку Rai?"
  !endif
!macroend

; Приятное сообщение в конце установки (не заменяет страницы мастера — безопасно).
!macro customInstall
  DetailPrint "Rai установлен — ум внутри, интернет не нужен."
!macroend
