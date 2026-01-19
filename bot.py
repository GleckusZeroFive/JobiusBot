import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, GROQ_API_KEYS, GROQ_MODEL
from database import db
from hh_api import HeadHunterAPI
from handlers import basic_router, search_router, favorites_router, easter_eggs_router
from middlewares.llm_middleware import LLMMiddleware
from utils.llm_service import init_groq_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле!")

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# FSM хранилище
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# LLM Middleware отключён - бот общается свободно через LLM в handlers
# if GROQ_API_KEYS:
#     dp.message.middleware(LLMMiddleware())
#     logger.info("LLM Middleware зарегистрирован")
# else:
#     logger.warning("Groq API ключи не найдены, LLM функционал отключён")

# Регистрация роутеров
dp.include_router(basic_router)
dp.include_router(favorites_router)
dp.include_router(easter_eggs_router)  # Easter eggs перед search
dp.include_router(search_router)  # search_router должен быть последним, т.к. обрабатывает все текстовые сообщения


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Инициализация базы данных...")
    await db.connect()
    logger.info("База данных готова!")

    # Загрузка городов из HeadHunter API
    logger.info("Загрузка городов из HeadHunter API...")
    from handlers.search import hh_api
    from utils.areas_cache import areas_cache

    success = await areas_cache.load_areas(hh_api)
    if success:
        city_count = len(areas_cache.areas_index)
        logger.info(f"✓ Загружено {city_count} городов из HH API")
    else:
        logger.warning("⚠ Не удалось загрузить города, используем базовый список POPULAR_AREAS")

    # Инициализация Groq LLM сервиса
    if GROQ_API_KEYS:
        init_groq_service(GROQ_API_KEYS, GROQ_MODEL)
        logger.info(f"Groq LLM сервис инициализирован с {len(GROQ_API_KEYS)} ключами")
    else:
        logger.warning("Groq API ключи не найдены, LLM функционал недоступен")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Закрытие соединений...")
    await db.close()

    # Закрываем HTTP сессию HH API
    from handlers.search import hh_api
    await hh_api.close()

    logger.info("Все соединения закрыты")


async def main():
    """Главная функция запуска бота"""
    try:
        # Запускаем инициализацию
        await on_startup()

        logger.info("Бот запущен!")

        # Удаляем все pending updates при старте
        await bot.delete_webhook(drop_pending_updates=True)

        # Запускаем polling
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        # Закрываем все соединения
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
