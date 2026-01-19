# API References и Документация

## HeadHunter API

### Официальная документация
- **GitHub репозиторий:** https://github.com/hhru/api
- **Документация по вакансиям:** https://github.com/hhru/api/blob/master/docs/vacancies.md
- **OpenAPI спецификация:** https://api.hh.ru/openapi/specification/public
- **Redoc документация:** https://api.hh.ru/openapi/redoc
- **Dev портал:** https://dev.hh.ru

### Полезные статьи
- **Работа с API HeadHunter при помощи python:** https://habr.com/ru/articles/666062/
- **API hh.ru. Быстрый старт:** https://habr.com/ru/companies/hh/articles/303168/
- **Автоматизация сбора и анализа вакансий:** https://habr.com/ru/articles/920942/

### Основные параметры поиска вакансий (GET /vacancies)

#### Базовые параметры
- `text` (string) - Поисковый запрос (например, "Python developer")
- `area` (integer) - ID региона:
  - `1` = Москва
  - `2` = Санкт-Петербург
  - `113` = Россия
  - Другие города через справочник `/areas`

- `salary` (integer) - Минимальная зарплата
- `only_with_salary` (boolean) - Показывать только вакансии с зарплатой
- `per_page` (integer) - Количество вакансий на странице (макс 100, по умолчанию 50)
- `page` (integer) - Номер страницы (начинается с 0)
- `period` (integer) - За сколько дней искать (макс 30)

#### Опыт работы (experience)
- `noExperience` - Нет опыта
- `between1And3` - От 1 года до 3 лет
- `between3And6` - От 3 до 6 лет
- `moreThan6` - Более 6 лет

#### График работы (schedule)
- `fullDay` - Полный день
- `shift` - Сменный график
- `flexible` - Гибкий график
- `remote` - Удаленная работа
- `flyInFlyOut` - Вахтовый метод

#### Тип занятости (employment)
- `full` - Полная занятость
- `part` - Частичная занятость
- `project` - Проектная работа
- `volunteer` - Волонтерство
- `probation` - Стажировка

#### Дополнительные параметры
- `order_by` - Сортировка (справочник `/dictionaries`)
- `professional_role` - Фильтр по профессиональной роли
- `employer_id` - ID работодателя
- `vacancy_label` - Метки вакансий (справочник `/dictionaries`)

### Важные замечания
1. **User-Agent обязателен** - без него API не работает
2. **Rate limiting** - есть ограничения на количество запросов
3. **Pagination** - максимум 100 вакансий на страницу
4. **Period** - максимум 30 дней для поиска

### Примеры запросов

```python
# Базовый поиск
GET https://api.hh.ru/vacancies?text=Python&area=1&per_page=20

# Поиск с фильтрами
GET https://api.hh.ru/vacancies?text=Frontend&area=2&experience=between1And3&salary=150000&only_with_salary=true

# Удаленная работа
GET https://api.hh.ru/vacancies?text=Python&schedule=remote&experience=noExperience

# Частичная занятость с гибким графиком
GET https://api.hh.ru/vacancies?text=Дизайнер&employment=part&schedule=flexible
```

## Groq API (LLM)

### Официальная документация
- **Официальный сайт:** https://groq.com
- **API документация:** https://console.groq.com/docs
- **SDK GitHub:** https://github.com/groq/groq-python

### Используемая модель
- `llama-3.3-70b-versatile` - Llama 3.3 70B (мощная, быстрая модель)

### Параметры запроса
- `messages` - Список сообщений в формате OpenAI
- `temperature` (0.0-1.0) - Креативность ответа
- `max_tokens` - Максимальная длина ответа
- `model` - Название модели

### Особенности
- Совместимость с OpenAI API
- Высокая скорость инференса
- Поддержка streaming
- Rate limiting зависит от тарифа

## Референс: Самокат "Вау-поиск"

### Статьи о вау-поиске
- **Самокат запустил поискового ассистента:** https://new-retail.ru/novosti/retail/samokat_zapustil_poiskovogo_assistenta/
- **Вау-поиск на Retail.ru:** https://www.retail.ru/rbc/pressreleases/vau-poisk-samokat-zapustil-poiskovogo-assistenta/

### Концепция вау-поиска
Поисковый ассистент на базе ИИ, который:
- Принимает запросы в **свободном формате**
- Понимает намерения пользователя
- Собирает подборки товаров
- Предлагает рецепты и идеи
- Обучается на запросах пользователей

### Примеры использования вау-поиска
- "Собери продукты для завтрака"
- "Ингредиенты для шарлотки"
- "Подарок на новоселье"
- "Что нужно для вечернего кинопросмотра"

### Наша реализация для JobiusBot
Аналогично вау-поиску Самоката, наш "Умный поиск":
1. Принимает запросы в свободной форме
2. Парсит через LLM в структурированные параметры
3. Выполняет поиск на HH.ru с этими параметрами
4. Показывает пользователю распознанные параметры

**Примеры:**
- "Хочу удаленную работу python от 150000" → remote + salary
- "Ищу начальную позицию в IT" → noExperience
- "Работа frontend middle в Москве" → area + experience

## Telegram Bot API

### Официальная документация
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Aiogram фреймворк:** https://docs.aiogram.dev/

### Используемые компоненты
- `aiogram 3.x` - Асинхронный фреймворк для Telegram ботов
- `FSM (Finite State Machine)` - Управление состояниями диалога
- `ReplyKeyboardMarkup` - Кнопки в интерфейсе
- `InlineKeyboardMarkup` - Inline кнопки под сообщениями

## Полезные ссылки

### Python библиотеки
- **aiohttp:** https://docs.aiohttp.org/
- **asyncio:** https://docs.python.org/3/library/asyncio.html
- **pydantic:** https://docs.pydantic.dev/

### Базы данных
- **aiosqlite:** https://github.com/omnilib/aiosqlite
- **SQLite документация:** https://www.sqlite.org/docs.html

## Changelog проекта

### Версия 2.0 (Умный поиск)
- Добавлен "Умный поиск" с LLM парсингом
- Интеграция с Groq API (Llama 3.3 70B)
- Поддержка параметров schedule и employment в HH API
- FSM состояние для умного поиска
- Упрощен middleware (убрана блокировка сообщений)

### Версия 1.0 (Базовый функционал)
- Интеграция с HH API
- Обычный поиск вакансий
- Избранное
- Статистика пользователей
- Калькулятор
- Пагинация результатов
