; Красивый установщик Rai (NSIS, assisted) — подключается electron-builder'ом.
; Картинки (боковая панель-градиент и шапка) задаются в package.json (installerSidebar / installerHeader),
; здесь — фирменные цвета фона, тёплые русские тексты и брендирование страницы копирования.
; Все !define — через !ifndef, чтобы не конфликтовать с тем, что задаёт electron-builder.

!macro customHeader
  ; фирменный тёмный фон во ВСЕХ окнах мастера (в цвет градиента боковой панели) — красивый фон везде
  !ifndef MUI_BGCOLOR
    !define MUI_BGCOLOR "141420"
  !endif
  !ifndef MUI_TEXTCOLOR
    !define MUI_TEXTCOLOR "F5F5F7"
  !endif

  ; экран приветствия
  !ifndef MUI_WELCOMEPAGE_TITLE
    !define MUI_WELCOMEPAGE_TITLE "Rai — ваш ИИ-помощник"
  !endif
  !ifndef MUI_WELCOMEPAGE_TEXT
    !define MUI_WELCOMEPAGE_TEXT "Сейчас установим Rai: чат, код, презентации и распознавание картинок.$\r$\n$\r$\nЭто обычное приложение — весь ум внутри, работает без интернета.$\r$\n$\r$\nНажмите «Далее», чтобы продолжить."
  !endif
  ; экран завершения
  !ifndef MUI_FINISHPAGE_TITLE
    !define MUI_FINISHPAGE_TITLE "Готово — Rai установлен"
  !endif
  !ifndef MUI_FINISHPAGE_TEXT
    !define MUI_FINISHPAGE_TEXT "Rai готов к работе. Запускайте и спрашивайте что угодно — он думает сам."
  !endif

  ; страница копирования файлов — тоже фирменная: плавный прогресс, тёмный лог в цветах Rai, шапка с логотипом
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

  ; спросить по-человечески, если нажали «отмена»
  !ifndef MUI_ABORTWARNING
    !define MUI_ABORTWARNING
  !endif
  !ifndef MUI_ABORTWARNING_TEXT
    !define MUI_ABORTWARNING_TEXT "Точно прервать установку Rai?"
  !endif
!macroend

; Строка в журнале установки — весь ум Rai внутри, интернет не нужен.
!macro customInstall
  DetailPrint "Rai установлен — ум внутри, интернет не нужен."
!macroend
