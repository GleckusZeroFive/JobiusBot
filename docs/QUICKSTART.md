# Быстрый старт JobiusBot

## Локально (для разработки)

```bash
# 1. Установите зависимости
./start.sh

# 2. Бот запущен!
# Проверьте статус:
./status.sh

# 3. Остановить
./stop.sh

# 4. Перезапустить
./restart.sh

# 5. Логи
./logs.sh
./logs.sh -f    # в реальном времени
```

## На VPS (для продакшена)

```bash
# 1. Подключитесь к серверу
ssh user@your-server-ip

# 2. Установите Python 3.9+
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git

# 3. Скопируйте проект
git clone <URL> JobiusBot
cd JobiusBot

# 4. Настройте .env
cp .env.example .env
nano .env  # Вставьте токены

# 5. Запустите
./start.sh

# 6. (Опционально) Настройте автозапуск
# См. DEPLOY.md
```

## Полезные команды

| Команда | Описание |
|---------|----------|
| `./start.sh` | Запустить бота |
| `./stop.sh` | Остановить бота |
| `./restart.sh` | Перезапустить бота |
| `./status.sh` | Проверить статус |
| `./logs.sh` | Показать последние 50 строк логов |
| `./logs.sh -f` | Логи в реальном времени |
| `./logs.sh -e` | Только ошибки |

## Команды бота в Telegram

| Команда | Пример |
|---------|--------|
| `/search [запрос]` | `/search Python` |
| `/search [запрос] [уровень]` | `/search Python junior` |
| `/search [запрос] [город]` | `/search Python Москва` |
| `/search [запрос] [зарплата]` | `/search Python 150000` |
| `/search [всё вместе]` | `/search Python middle СПб 200000` |
| `/calc [выражение]` | `/calc 2 + 2` |
| Просто текст | `DevOps` (автопоиск) |

## Фильтры

**Уровни:** junior, middle, senior, lead, intern
**Города:** Москва, СПб, Екатеринбург, Новосибирск, Казань
**Зарплата:** любое число (минимум)

## Структура проекта

```
JobiusBot/
├── bot.py              # Основной код бота
├── hh_api.py          # API клиент для hh.ru
├── requirements.txt    # Python зависимости
├── .env               # Токены (не коммитить!)
├── .env.example       # Пример конфигурации
├── start.sh           # Запуск
├── stop.sh            # Остановка
├── restart.sh         # Перезапуск
├── status.sh          # Статус
├── logs.sh            # Просмотр логов
├── logs/              # Директория с логами
│   └── bot.log        # Логи бота
├── README.md          # Полная документация
├── DEPLOY.md          # Инструкция по деплою
└── QUICKSTART.md      # Этот файл
```

## Что дальше?

- **Полная документация:** [README.md](README.md)
- **Деплой на VPS:** [DEPLOY.md](DEPLOY.md)
- **Исходный код бота:** [bot.py](bot.py)
- **API клиент hh.ru:** [hh_api.py](hh_api.py)
