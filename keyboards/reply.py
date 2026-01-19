from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Создает главное меню с кнопками

    Returns:
        ReplyKeyboardMarkup: Главное меню
    """
    builder = ReplyKeyboardBuilder()

    # Первая строка: Поиск и Избранное
    builder.row(
        KeyboardButton(text="🔍 Поиск работы"),
        KeyboardButton(text="⭐ Избранное")
    )

    # Вторая строка: Калькулятор и Статистика
    builder.row(
        KeyboardButton(text="🔢 Калькулятор"),
        KeyboardButton(text="📊 Статистика")
    )

    return builder.as_markup(resize_keyboard=True)


def get_search_menu() -> ReplyKeyboardMarkup:
    """
    Создает меню для поиска с фильтрами

    Returns:
        ReplyKeyboardMarkup: Меню поиска
    """
    builder = ReplyKeyboardBuilder()

    # Первая строка: Города
    builder.row(
        KeyboardButton(text="📍 Москва"),
        KeyboardButton(text="📍 Санкт-Петербург")
    )

    # Вторая строка: Уровни
    builder.row(
        KeyboardButton(text="💼 Junior"),
        KeyboardButton(text="💼 Middle"),
        KeyboardButton(text="💼 Senior")
    )

    # Третья строка: Назад
    builder.row(
        KeyboardButton(text="◀️ Главное меню")
    )

    return builder.as_markup(resize_keyboard=True)


def get_back_button() -> ReplyKeyboardMarkup:
    """
    Создает кнопку "Назад в меню"

    Returns:
        ReplyKeyboardMarkup: Кнопка назад
    """
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="◀️ Главное меню"))
    return builder.as_markup(resize_keyboard=True)
