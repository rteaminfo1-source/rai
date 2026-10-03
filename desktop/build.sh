#!/usr/bin/env bash
# Сборка RTeamAdmin.exe для Windows (amd64). CGO не требуется.
set -euo pipefail
cd "$(dirname "$0")"

# 1) Ресурсы Windows: иконка, манифест (DPI-aware, запуск без админа), версия.
if command -v go-winres >/dev/null 2>&1; then
  go-winres make --arch amd64
else
  go run github.com/tc-hib/go-winres@v0.3.3 make --arch amd64
fi

# 2) Сборка .exe без окна консоли.
mkdir -p build
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 \
  go build -ldflags="-H windowsgui -s -w" -o build/RTeamAdmin.exe .

echo "Готово: build/RTeamAdmin.exe"
