import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from database import db
from keyboards import get_main_menu
from utils.states import SearchStates

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user = message.from_user

    # Добавляем пользователя в БД
    await db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    await message.answer(
        f"👋 Привет, <b>{user.first_name}</b>! Я <b>Jobius</b> - умный бот для поиска работы.\n\n"
        "Используй кнопки меню внизу для быстрого доступа к функциям!\n\n"
        "<b>Что я умею:</b>\n"
        "🔍 Искать вакансии на hh.ru (понимаю естественный язык!)\n"
        "⭐ Сохранять понравившиеся вакансии\n"
        "📊 Показывать твою статистику\n"
        "🔢 Считать математику\n\n"
        "Просто напиши что ищешь, например:\n"
        "• <i>Python developer</i>\n"
        "• <i>Хочу удаленку от 150к</i>\n"
        "• <i>Junior frontend в Москве</i>",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "◀️ Главное меню")
async def btn_main_menu(message: Message):
    """Обработчик кнопки 'Главное меню'"""
    await message.answer(
        "📱 <b>Главное меню</b>\n\n"
        "Выбери действие с помощью кнопок внизу:",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "🔍 Поиск работы")
async def btn_search(message: Message):
    """Обработчик кнопки 'Поиск работы'"""
    await message.answer(
        "🔍 <b>Поиск вакансий</b>\n\n"
        "Напиши запрос для поиска работы в любой форме!\n\n"
        "<b>Примеры:</b>\n"
        "• Python developer\n"
        "• Хочу удаленную работу python от 150к\n"
        "• Frontend junior Москва\n"
        "• Backend middle СПб 200000\n"
        "• Ищу начальную позицию в IT с гибким графиком\n\n"
        "💡 Бот понимает естественный язык и автоматически разберет твой запрос!",
        reply_markup=get_main_menu()
    )




@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "📚 <b>Справка по использованию бота</b>\n\n"
        "<b>🔍 Поиск вакансий:</b>\n"
        "Нажми кнопку 'Поиск работы' или просто напиши запрос в любой форме!\n\n"
        "<b>Примеры запросов:</b>\n"
        "• Python\n"
        "• Python junior Москва\n"
        "• Хочу удаленку python от 150к\n"
        "• Backend middle СПб 200000\n"
        "• Ищу начальную позицию в IT\n\n"
        "💡 Бот понимает естественный язык!\n\n"
        "<b>⭐ Избранное:</b>\n"
        "Нажми кнопку ⭐ под вакансией, чтобы добавить в избранное\n"
        "Просмотр: кнопка 'Избранное' в меню\n\n"
        "<b>📊 Статистика:</b>\n"
        "Кнопка 'Статистика' покажет твою активность\n\n"
        "<b>🔢 Калькулятор:</b>\n"
        "Кнопка 'Калькулятор' или просто напиши выражение: 2 + 2",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "📊 Статистика")
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Обработчик команды /stats и кнопки 'Статистика'"""
    user_id = message.from_user.id

    # Получаем данные пользователя из БД
    user = await db.get_user(user_id)
    favorites = await db.get_favorites(user_id)
    search_history = await db.get_search_history(user_id, limit=5)

    if not user:
        await message.answer("❌ Данные не найдены. Попробуйте /start", reply_markup=get_main_menu())
        return

    # Формируем статистику
    stats_text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"👤 Пользователь: {user['first_name']}\n"
        f"🔍 Всего поисков: {user['search_count']}\n"
        f"⭐ Избранных вакансий: {len(favorites)}\n"
        f"📅 Дата регистрации: {user['created_at'][:10]}\n"
        f"🕒 Последняя активность: {user['last_active'][:10]}\n"
    )

    if search_history:
        stats_text += "\n<b>🕰️ Последние поиски:</b>\n"
        for i, search in enumerate(search_history[:5], 1):
            stats_text += f"{i}. {search['search_query']} ({search['results_count']} результатов)\n"

    await message.answer(stats_text, reply_markup=get_main_menu())


@router.message(F.text == "🔢 Калькулятор")
async def btn_calc(message: Message):
    """Обработчик кнопки 'Калькулятор'"""
    await message.answer(
        "🔢 <b>Калькулятор</b>\n\n"
        "Напиши математическое выражение для вычисления.\n\n"
        "<b>Примеры:</b>\n"
        "• 2 + 2\n"
        "• (100 - 20) * 3\n"
        "• 2 ** 10\n\n"
        "Поддерживаются операции: +, -, *, /, **, %, ()",
        reply_markup=get_main_menu()
    )


@router.message(Command("calc"))
async def cmd_calc(message: Message):
    """Обработчик команды /calc - калькулятор"""
    expression = message.text.replace("/calc", "").strip()

    if not expression:
        await message.answer(
            "🔢 Укажите математическое выражение!\n\n"
            "<b>Примеры:</b>\n"
            "• <code>/calc 2 + 2</code>\n"
            "• <code>/calc (100 - 20) * 3</code>\n"
            "• <code>/calc 2 ** 10</code>",
            reply_markup=get_main_menu()
        )
        return

    result = calculate(expression)
    await message.answer(result, reply_markup=get_main_menu())


def calculate(expression: str) -> str:
    """
    Безопасно вычисляет математическое выражение.
    """
    try:
        expression = expression.strip()

        # Проверяем допустимые символы
        allowed_chars = set('0123456789+-*/().% ')
        if not all(c in allowed_chars for c in expression):
            return "❌ Ошибка: используйте только цифры и операторы +, -, *, /, **, %, ()"

        # Вычисляем в безопасном контексте
        result = eval(expression, {"__builtins__": None}, {})

        # Форматируем результат
        if isinstance(result, float):
            if result.is_integer():
                return f"= {int(result)}"
            else:
                return f"= {result:.6f}".rstrip('0').rstrip('.')
        else:
            return f"= {result}"

    except ZeroDivisionError:
        return "❌ Ошибка: деление на ноль!"
    except SyntaxError:
        return "❌ Ошибка: неправильный формат выражения"
    except Exception as e:
        logger.error(f"Ошибка при вычислении '{expression}': {e}")
        return f"❌ Ошибка при вычислении: {str(e)}"
