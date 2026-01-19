# Development Guide

## Быстрые команды

### Запуск проекта

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python bot.py

# Запуск в фоне (Linux)
nohup python bot.py > bot.log 2>&1 &

# Просмотр логов
tail -f bot.log
```

### Работа с базой данных

```bash
# Открыть SQLite БД
sqlite3 database.db

# Показать все таблицы
.tables

# Показать пользователей
SELECT * FROM users;

# Показать последние поиски
SELECT * FROM search_history ORDER BY created_at DESC LIMIT 10;

# Показать избранное
SELECT * FROM favorites;

# Очистить историю (осторожно!)
DELETE FROM search_history;

# Сброс счетчика поисков
UPDATE users SET search_count = 0;
```

### SQL запросы для аналитики

```sql
-- Топ-10 поисковых запросов
SELECT search_query, COUNT(*) as count
FROM search_history
GROUP BY search_query
ORDER BY count DESC
LIMIT 10;

-- Количество умных поисков
SELECT COUNT(*) as smart_searches
FROM search_history
WHERE search_params LIKE '%"smart_search": true%';

-- Средняя зарплата в запросах
SELECT AVG(CAST(json_extract(search_params, '$.salary') AS INTEGER)) as avg_salary
FROM search_history
WHERE json_extract(search_params, '$.salary') IS NOT NULL;

-- Популярные города
SELECT json_extract(search_params, '$.area') as city, COUNT(*) as count
FROM search_history
WHERE json_extract(search_params, '$.area') IS NOT NULL
GROUP BY city
ORDER BY count DESC;

-- Самые активные пользователи
SELECT u.first_name, u.username, u.search_count, COUNT(f.id) as favorites_count
FROM users u
LEFT JOIN favorites f ON u.user_id = f.user_id
GROUP BY u.user_id
ORDER BY u.search_count DESC
LIMIT 10;
```

### Проверка синтаксиса

```bash
# Проверка всех файлов
python -m py_compile bot.py handlers/*.py utils/*.py middlewares/*.py

# Проверка конкретного файла
python -m py_compile handlers/search.py

# Линтер (если установлен)
pylint handlers/search.py
flake8 handlers/search.py
```

### Тестирование

```bash
# Запуск unit тестов (если есть)
pytest tests/

# Запуск с verbose
pytest -v tests/

# Запуск конкретного теста
pytest tests/test_llm_service.py::test_parse_simple_query

# Coverage отчет
pytest --cov=. tests/
```

## Полезные Python команды

### Тестирование LLM парсинга

```python
# test_llm.py
import asyncio
from utils.llm_service import groq_service, init_groq_service
from config import GROQ_API_KEYS, GROQ_MODEL

async def main():
    # Инициализация
    init_groq_service(GROQ_API_KEYS, GROQ_MODEL)

    # Тестовые запросы
    queries = [
        "Хочу удаленную работу python от 150000",
        "Junior frontend в Москве",
        "Работа для студента с гибким графиком",
        "Middle DevOps в СПб на удаленку от 200000"
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Запрос: {query}")
        result = await groq_service.parse_smart_search_query(query)
        print(f"Результат: {result}")

asyncio.run(main())
```

Запуск:
```bash
python test_llm.py
```

### Тестирование HH API

```python
# test_hh.py
import asyncio
from hh_api import HeadHunterAPI

async def main():
    hh = HeadHunterAPI()

    # Тест базового поиска
    result = await hh.search_vacancies(
        text="Python",
        area=1,
        per_page=5
    )
    print(f"Найдено: {result['found']}")
    print(f"Показано: {len(result['items'])}")

    # Тест с schedule и employment
    result2 = await hh.search_vacancies(
        text="Frontend",
        schedule="remote",
        employment="full",
        per_page=5
    )
    print(f"\nС фильтрами найдено: {result2['found']}")

    await hh.close()

asyncio.run(main())
```

### Массовое тестирование запросов

```python
# benchmark.py
import asyncio
import time
from utils.llm_service import groq_service, init_groq_service
from config import GROQ_API_KEYS, GROQ_MODEL

async def benchmark():
    init_groq_service(GROQ_API_KEYS, GROQ_MODEL)

    queries = [
        "Python удаленно 150000",
        "Junior frontend Москва",
        "Middle backend СПб 200000",
        "Senior DevOps remote 300000",
        "Студент подработка гибкий график"
    ] * 10  # 50 запросов

    start = time.time()
    tasks = [groq_service.parse_smart_search_query(q) for q in queries]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    print(f"Выполнено {len(queries)} запросов за {elapsed:.2f}s")
    print(f"Среднее время: {elapsed/len(queries):.2f}s")

asyncio.run(benchmark())
```

## Git команды (если проект под git)

```bash
# Инициализация репозитория
git init

# Добавить .gitignore
echo ".env
__pycache__/
*.pyc
*.db
venv/
.vscode/
*.log" > .gitignore

# Первый коммит
git add .
git commit -m "Initial commit"

# Создать ветку для новой фичи
git checkout -b feature/smart-search

# Коммит изменений
git add .
git commit -m "Add smart search with LLM parsing"

# Вернуться на main
git checkout main

# Слить ветку
git merge feature/smart-search

# Отправить в remote
git remote add origin https://github.com/username/JobiusBot.git
git push -u origin main
```

## Docker (опционально)

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  bot:
    build: .
    env_file:
      - .env
    volumes:
      - ./database.db:/app/database.db
    restart: unless-stopped
```

### Команды Docker

```bash
# Собрать образ
docker build -t jobius-bot .

# Запустить контейнер
docker run -d --name jobius --env-file .env jobius-bot

# Просмотр логов
docker logs -f jobius

# Остановить
docker stop jobius

# Перезапустить
docker restart jobius

# Docker Compose
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## Отладка

### Python Debugger (pdb)

```python
# Добавить в код
import pdb; pdb.set_trace()

# Или для async кода
import asyncio
async def debug():
    await asyncio.sleep(0)
    import pdb; pdb.set_trace()
```

### Логирование

```python
# Временное увеличение уровня логирования
import logging
logging.getLogger('handlers.search').setLevel(logging.DEBUG)

# Добавить логирование в код
logger.debug(f"Parsed params: {parsed_params}")
logger.info(f"User {user_id} started smart search")
logger.warning(f"LLM returned empty response")
logger.error(f"Failed to parse JSON: {e}")
```

### Интерактивная отладка

```bash
# Python REPL
python

>>> from utils.llm_service import groq_service
>>> import asyncio
>>> asyncio.run(groq_service.parse_smart_search_query("test"))
```

## Мониторинг в production

### systemd service (Linux)

```ini
# /etc/systemd/system/jobius-bot.service
[Unit]
Description=Jobius Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/JobiusBot
ExecStart=/home/your_user/JobiusBot/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Команды:
```bash
# Включить автозапуск
sudo systemctl enable jobius-bot

# Запустить
sudo systemctl start jobius-bot

# Статус
sudo systemctl status jobius-bot

# Логи
sudo journalctl -u jobius-bot -f

# Перезапустить
sudo systemctl restart jobius-bot
```

### Простой мониторинг с cron

```bash
# /usr/local/bin/check_bot.sh
#!/bin/bash

if ! pgrep -f "python bot.py" > /dev/null; then
    echo "Bot is down, restarting..."
    cd /home/user/JobiusBot
    nohup python bot.py > bot.log 2>&1 &
fi
```

```bash
# Добавить в crontab
crontab -e

# Проверять каждые 5 минут
*/5 * * * * /usr/local/bin/check_bot.sh
```

## Environment Variables

```bash
# Экспорт переменных (временно)
export TELEGRAM_BOT_TOKEN="your_token"
export GROQ_API_KEY_1="your_key"

# Загрузка из .env
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('TELEGRAM_BOT_TOKEN'))"

# Проверка переменных
python -c "from config import BOT_TOKEN, GROQ_API_KEYS; print(f'Token: {BOT_TOKEN[:10]}...'); print(f'Keys: {len(GROQ_API_KEYS)}')"
```

## Performance Profiling

### cProfile

```python
# profile_bot.py
import cProfile
import pstats
from pstats import SortKey

cProfile.run('asyncio.run(main())', 'bot_stats')

# Анализ результатов
p = pstats.Stats('bot_stats')
p.sort_stats(SortKey.CUMULATIVE).print_stats(20)
```

### Memory profiling

```bash
# Установка
pip install memory_profiler

# Использование
@profile
def my_function():
    # код
    pass

# Запуск
python -m memory_profiler handlers/search.py
```

## Backup и восстановление

### Backup базы данных

```bash
# Простое копирование
cp database.db database_backup_$(date +%Y%m%d).db

# Dump в SQL
sqlite3 database.db .dump > backup.sql

# Cron для автоматического бэкапа
0 2 * * * cp /path/to/database.db /path/to/backups/db_$(date +\%Y\%m\%d).db
```

### Восстановление

```bash
# Из бэкапа
cp database_backup_20260119.db database.db

# Из SQL dump
sqlite3 database.db < backup.sql
```

## Обновление зависимостей

```bash
# Показать устаревшие пакеты
pip list --outdated

# Обновить конкретный пакет
pip install --upgrade aiogram

# Обновить все
pip install --upgrade -r requirements.txt

# Создать requirements.txt
pip freeze > requirements.txt
```

## Tips & Tricks

### Быстрая проверка API ключей

```bash
# Проверка Telegram token
curl "https://api.telegram.org/bot<TOKEN>/getMe"

# Проверка Groq API
curl -X POST "https://api.groq.com/openai/v1/chat/completions" \
  -H "Authorization: Bearer <GROQ_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "test"}]}'
```

### Очистка кеша Python

```bash
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### Проверка портов

```bash
# Проверить что порт не занят (если используете webhook)
netstat -tulpn | grep 8080

# Убить процесс на порту
lsof -ti:8080 | xargs kill -9
```

## Troubleshooting

### Проблема: ModuleNotFoundError

```bash
# Проверить PYTHONPATH
echo $PYTHONPATH

# Установить
export PYTHONPATH=/path/to/JobiusBot:$PYTHONPATH

# Или запускать как модуль
python -m bot
```

### Проблема: Database locked

```bash
# Проверить процессы использующие БД
lsof database.db

# Закрыть
kill -9 <PID>

# Или скопировать и пересоздать
cp database.db database_backup.db
rm database.db
python -c "from database import db; import asyncio; asyncio.run(db.connect())"
```

### Проблема: Rate limit Groq API

```python
# Добавить retry с exponential backoff
import asyncio
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
async def call_llm():
    # LLM вызов
    pass
```

## Useful Resources

- **Python asyncio docs:** https://docs.python.org/3/library/asyncio.html
- **aiogram docs:** https://docs.aiogram.dev/
- **SQLite docs:** https://www.sqlite.org/docs.html
- **Groq API:** https://console.groq.com/docs
- **HH API:** https://github.com/hhru/api

## Контакты для разработки

- **Issues:** (добавить ссылку на GitHub)
- **Discussions:** (добавить ссылку)
- **Telegram dev chat:** (если есть)
