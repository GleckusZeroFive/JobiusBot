import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from database import db
from utils.llm_service import get_groq_service

logger = logging.getLogger(__name__)

# Константы для правила offtopic
MAX_OFFTOPIC_TOTAL = 10
MAX_CONSECUTIVE_OFFTOPIC = 3

# Ключевые слова для быстрой проверки (перед LLM) - РАСШИРЕННЫЕ
WORK_KEYWORDS = [
    'работ', 'вакан', 'резюме', 'карьер', 'зарплат', 'собеседован',
    'hh', 'junior', 'middle', 'senior', 'intern', 'developer',
    'программист', 'разработчик', 'it', 'компани', 'должност',
    'python', 'java', 'frontend', 'backend', 'devops', 'qa', 'тестировщик',
    'искать', 'ищу', 'найти', 'поиск', 'делать', 'устроиться', 'хочу работать',
    # Деятельность (что делать)
    'пилить', 'готовить', 'чинить', 'строить', 'убирать', 'водить',
    'учить', 'лечить', 'продавать', 'стричь', 'ремонтировать',
    'делать', 'работать с', 'заниматься',
    # Места работы
    'пиццерии', 'ресторан', 'кафе', 'склад', 'магазин', 'офис',
    # Общие паттерны
    'хочу', 'ищу работу', 'нужна работа'
]

# Ключевые слова согласия/продолжения
AGREEMENT_KEYWORDS = [
    'да', 'давай', 'хорошо', 'ок', 'окей', 'okay', 'согласен',
    'конечно', 'поищем', 'ищем', 'начнём', 'начинаем', 'го',
    'yeah', 'yes', 'yep', 'угу', 'ага'
]

# Ключевые слова для команд анализа результатов
ANALYSIS_KEYWORDS = [
    'проанализ', 'анализ', 'лучш', 'топ', 'отбер', 'выдел',
    'порекоменд', 'посовет', 'какие лучше', 'что выбрать',
    'analyze', 'best', 'top', 'recommend'
]

BOT_KEYWORDS = [
    'помощь', 'команд', 'функци', 'что умее', 'статистик',
    'избранн', 'калькулятор'
]

# Простые приветствия и offtopic фразы (всегда offtopic)
GREETING_KEYWORDS = [
    'привет', 'здравствуй', 'добрый день', 'добрый вечер', 'доброе утро',
    'как дела', 'как ты', 'что нового', 'как настроение'
]

# Явно offtopic темы (философия, погода, и т.д.)
OFFTOPIC_KEYWORDS = [
    'бог', 'погод', 'температур', 'анекдот', 'шутк', 'расскаж',
    'философи', 'жизн', 'любов', 'смысл', 'вселенн', 'религи'
]


class LLMMiddleware(BaseMiddleware):
    """
    Middleware для обработки сообщений через LLM
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка сообщения пользователя"""

        # Получаем сервис LLM
        groq_service = get_groq_service()

        # Пропускаем, если LLM не настроен
        if groq_service is None:
            return await handler(event, data)

        # Работаем только с текстовыми сообщениями
        if not event.text:
            return await handler(event, data)

        user_id = event.from_user.id
        user_message = event.text.strip()

        # Пропускаем команды (они обрабатываются хендлерами)
        if user_message.startswith('/'):
            # Сбрасываем consecutive при использовании команд
            await db.reset_consecutive_offtopic(user_id)
            return await handler(event, data)

        # Пропускаем сообщения от кнопок меню
        menu_buttons = ["🔍 Поиск работы", "⭐ Избранное", "📊 Статистика",
                       "🔢 Калькулятор", "❓ Помощь", "◀️ Главное меню", "🧠 Умный поиск"]
        if user_message in menu_buttons:
            await db.reset_consecutive_offtopic(user_id)
            return await handler(event, data)

        # 1. Быстрая проверка по ключевым словам
        user_message_lower = user_message.lower()

        # Проверка на команды анализа результатов - всегда релевантно
        has_analysis_keywords = any(keyword in user_message_lower for keyword in ANALYSIS_KEYWORDS)
        if has_analysis_keywords:
            # Это команда анализа, пропускаем её дальше в обработчик
            await db.reset_consecutive_offtopic(user_id)
            return await handler(event, data)

        # Проверка на простые приветствия - всегда offtopic
        is_greeting = any(keyword in user_message_lower for keyword in GREETING_KEYWORDS)
        is_offtopic_keyword = any(keyword in user_message_lower for keyword in OFFTOPIC_KEYWORDS)

        # Проверка на согласие/продолжение разговора
        is_agreement = any(keyword == user_message_lower or keyword in user_message_lower.split()
                          for keyword in AGREEMENT_KEYWORDS)

        has_work_keywords = any(keyword in user_message_lower for keyword in WORK_KEYWORDS)
        has_bot_keywords = any(keyword in user_message_lower for keyword in BOT_KEYWORDS)

        is_relevant = False
        category = "unknown"

        # Получаем последние сообщения из истории для контекста
        conversation_history = await db.get_conversation_history(user_id, limit=4)

        if is_greeting and not is_agreement:
            # Простое приветствие без признаков продолжения
            is_relevant = False
            category = "offtopic"
            logger.info(f"Обнаружено приветствие: '{user_message[:50]}...'")
        elif is_offtopic_keyword and not has_work_keywords:
            # Явная offtopic тема без признаков работы
            is_relevant = False
            category = "offtopic"
            logger.info(f"Обнаружена offtopic тема: '{user_message[:50]}...'")
        elif has_work_keywords or is_agreement:
            # Явно про работу ИЛИ согласие (может быть продолжением предложения о поиске)
            # Проверяем через LLM для лучшего понимания контекста
            try:
                classification = await groq_service.classify_message_relevance(
                    user_message,
                    conversation_context=conversation_history
                )
                is_relevant = classification.get("is_relevant", True)
                category = classification.get("category", "job_search")

                logger.info(f"LLM классификация для '{user_message[:50]}...' с контекстом: {classification}")

                if is_relevant:
                    await db.reset_consecutive_offtopic(user_id)
            except Exception as e:
                logger.error(f"Ошибка LLM классификации: {e}")
                # Fallback: если есть work keywords - считаем релевантным
                is_relevant = True if has_work_keywords else is_agreement
                category = "job_search" if has_work_keywords else "agreement"
                if is_relevant:
                    await db.reset_consecutive_offtopic(user_id)
        elif has_bot_keywords:
            # Вопрос о боте - релевантно
            is_relevant = True
            category = "bot_help"
            await db.reset_consecutive_offtopic(user_id)
        else:
            # 2. Проверяем через LLM с контекстом
            try:
                classification = await groq_service.classify_message_relevance(
                    user_message,
                    conversation_context=conversation_history
                )
                is_relevant = classification.get("is_relevant", False)
                category = classification.get("category", "unknown")

                logger.info(f"LLM классификация для '{user_message[:50]}...': {classification}")
            except Exception as e:
                logger.error(f"Ошибка классификации через LLM: {e}")
                # В случае ошибки считаем сообщение НЕ релевантным (offtopic)
                is_relevant = False
                category = "offtopic"

        # 3. Обработка результата классификации
        if is_relevant:
            # Сообщение по теме - сбрасываем счётчик consecutive
            await db.reset_consecutive_offtopic(user_id)

            # Продолжаем обычную обработку
            return await handler(event, data)

        else:
            # Сообщение НЕ по теме (offtopic)
            tracker = await db.get_offtopic_tracker(user_id)

            if tracker is None:
                # Первое offtopic сообщение
                await db.increment_offtopic(user_id, consecutive=True)
                consecutive = 1
                total = 1
            else:
                consecutive = tracker['consecutive_offtopic'] + 1
                total = tracker['offtopic_count'] + 1
                await db.increment_offtopic(user_id, consecutive=True)

            logger.info(f"Offtopic от user {user_id}: consecutive={consecutive}, total={total}")

            # Проверяем условия сброса сессии
            if consecutive >= MAX_CONSECUTIVE_OFFTOPIC and total >= MAX_OFFTOPIC_TOTAL:
                # Сброс сессии: очищаем историю диалогов и счётчики
                await db.clear_conversation_history(user_id)
                await db.reset_offtopic_tracker(user_id)

                await event.answer(
                    "🔄 Кажется, мы отошли от темы поиска работы.\n\n"
                    "Давай начнём сначала! Я здесь, чтобы помочь тебе найти работу. "
                    "Попробуй нажать 🔍 <b>Поиск работы</b> или просто напиши, "
                    "какую вакансию ищешь! 😊"
                )

                # Не продолжаем обработку
                return

            elif consecutive >= MAX_CONSECUTIVE_OFFTOPIC:
                # 3 подряд offtopic, но общий счётчик ещё не достиг 10
                remaining = MAX_OFFTOPIC_TOTAL - total
                await event.answer(
                    f"Понимаю, но давай вернёмся к поиску работы! 😊\n\n"
                    f"Я специализируюсь на помощи в карьере. "
                    f"Какую вакансию ты ищешь?"
                )

                # Не продолжаем обработку
                return

            else:
                # Мягкое напоминание - используем LLM для естественного ответа
                try:
                    response = await groq_service.get_assistant_response(
                        user_message=user_message,
                        conversation_history=conversation_history,
                        bot_capabilities=self._get_bot_capabilities()
                    )

                    if response:
                        await event.answer(response)
                        # Сохраняем в историю для контекста
                        await db.add_to_conversation_history(user_id, user_message, response)
                    else:
                        # Fallback если LLM не ответил
                        if consecutive == 1:
                            await event.answer(
                                "К сожалению, я не могу помочь с этим 😊\n"
                                "Зато отлично разбираюсь в поиске работы! Какую вакансию ищешь?"
                            )
                        else:
                            await event.answer(
                                "Понимаю, но давай всё же вернёмся к поиску работы? 🔍\n"
                                "Я помогу найти что-то интересное!"
                            )
                except Exception as llm_error:
                    logger.error(f"Ошибка при получении ответа от LLM: {llm_error}")
                    # Fallback ответ при ошибке LLM
                    await event.answer(
                        "К сожалению, я могу помочь только с поиском работы 😊\n"
                        "Напиши, какую вакансию ищешь, и я найду для тебя подходящие варианты!"
                    )

                # Не продолжаем обработку
                return

    def _get_bot_capabilities(self) -> str:
        """Возвращает описание возможностей бота"""
        return """
🔍 ПОИСК ВАКАНСИЙ на hh.ru:
- Поиск по названию (Python, Frontend, DevOps)
- Фильтры по городу (Москва, СПб, др.)
- Фильтры по зарплате (минимальная сумма)
- Фильтры по опыту (junior, middle, senior)

⭐ ИЗБРАННОЕ:
- Сохранение интересных вакансий
- Просмотр сохранённых вакансий

📊 СТАТИСТИКА:
- Количество поисков
- История запросов
- Сохранённые вакансии

🔢 КАЛЬКУЛЯТОР:
- Быстрые математические расчёты
- Полезно для расчёта зарплаты, налогов

❓ ПОМОЩЬ:
- Команды бота
- Примеры использования
"""
