; Красивый установщик Rai (NSIS) — подключается electron-builder'ом.
; Картинки (боковая панель и шапка) задаются в package.json (installerSidebar / installerHeader),
; здесь — только тёплые русские тексты мастера. Задаём их в customHeader: electron-builder вставляет
; этот макрос ДО страниц MUI, а сами эти тексты он не трогает, поэтому конфликтов нет.

!macro customHeader
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
!macroend

; Приятное сообщение в конце установки (не заменяет страницы мастера — безопасно).
!macro customInstall
  DetailPrint "Rai установлен — ум внутри, интернет не нужен."
!macroend
