#!/bin/bash
# Скрипт для остановки бота

# Определяем корень проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SCRIPT_DIR" == */scripts ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi
cd "$PROJECT_ROOT"

echo "🛑 Останавливаю бота..."

# Находим все процессы бота
PIDS=$(pgrep -f "python.*bot.py")

if [ -z "$PIDS" ]; then
    echo "ℹ️  Бот не запущен"
    exit 0
fi

# Останавливаем все найденные процессы
echo "Найдены процессы: $PIDS"
pkill -f "python.*bot.py"

# Ждём немного
sleep 2

# Проверяем, остановился ли бот
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "⚠️  Бот не остановился, принудительно завершаю..."
    pkill -9 -f "python.*bot.py"
    sleep 1
fi

if ! pgrep -f "python.*bot.py" > /dev/null; then
    echo "✅ Бот остановлен"
else
    echo "❌ Не удалось остановить бота"
    exit 1
fi
