.PHONY: start stop restart status logs help

# Цвета для вывода
GREEN=\033[0;32m
NC=\033[0m # No Color

help:
	@echo "$(GREEN)JobiusBot - Управление ботом$(NC)"
	@echo ""
	@echo "Доступные команды:"
	@echo "  make start    - Запустить бота"
	@echo "  make stop     - Остановить бота"
	@echo "  make restart  - Перезапустить бота"
	@echo "  make status   - Проверить статус"
	@echo "  make logs     - Показать последние логи"
	@echo "  make logs-f   - Логи в реальном времени"
	@echo "  make logs-e   - Только ошибки"
	@echo ""
	@echo "Или используйте скрипты напрямую:"
	@echo "  ./start.sh, ./stop.sh, ./restart.sh, ./status.sh, ./logs.sh"

start:
	@./start.sh

stop:
	@./stop.sh

restart:
	@./restart.sh

status:
	@./status.sh

logs:
	@./logs.sh

logs-f:
	@./logs.sh -f

logs-e:
	@./logs.sh -e
