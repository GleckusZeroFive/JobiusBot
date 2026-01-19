#!/bin/bash
# Скрипт для перезапуска бота

# Определяем корень проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SCRIPT_DIR" == */scripts ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi
cd "$PROJECT_ROOT"

echo "🔄 Перезапускаю бота..."

# Останавливаем бота
bash "$(dirname "$0")/stop.sh"

# Ждём немного
sleep 1

# Запускаем снова
bash "$(dirname "$0")/start.sh"
