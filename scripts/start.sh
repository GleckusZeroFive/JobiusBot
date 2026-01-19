#!/bin/bash
# Скрипт для запуска бота

# Определяем корень проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$SCRIPT_DIR" == */scripts ]]; then
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
else
    PROJECT_ROOT="$SCRIPT_DIR"
fi
cd "$PROJECT_ROOT"

# Проверяем, не запущен ли уже бот
if pgrep -f "python.*bot.py" > /dev/null; then
    echo "❌ Бот уже запущен!"
    echo "Используйте ./stop.sh чтобы остановить или ./restart.sh для перезапуска"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создаю виртуальное окружение..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден!"
    echo "Скопируйте .env.example в .env и добавьте токены"
    exit 1
fi

# Создаём директорию для логов если её нет
mkdir -p logs

# Запускаем бота
echo "🚀 Запускаю бота..."
nohup ./venv/bin/python bot.py > logs/bot.log 2>&1 &
BOT_PID=$!

# Ждём немного и проверяем, что бот запустился
sleep 2

if ps -p $BOT_PID > /dev/null; then
    echo "✅ Бот успешно запущен! PID: $BOT_PID"
    echo "📝 Логи: logs/bot.log"
    echo ""
    echo "Полезные команды:"
    echo "  ./scripts/stop.sh     - остановить бота"
    echo "  ./scripts/restart.sh  - перезапустить бота"
    echo "  ./scripts/status.sh   - проверить статус бота"
    echo "  ./scripts/logs.sh     - посмотреть логи"
else
    echo "❌ Ошибка при запуске бота!"
    echo "Проверьте логи: tail -50 logs/bot.log"
    exit 1
fi
