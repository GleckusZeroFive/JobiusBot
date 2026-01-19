from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_vacancy_keyboard(vacancy_id: str, url: str, is_favorite: bool = False,
                         current_page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """
    Создает inline-клавиатуру для вакансии

    Args:
        vacancy_id: ID вакансии
        url: Ссылка на вакансию
        is_favorite: Находится ли вакансия в избранном
        current_page: Текущая страница
        total_pages: Всего страниц

    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Первая строка: Ссылка на вакансию
    builder.row(
        InlineKeyboardButton(text="🔗 Открыть вакансию", url=url)
    )

    # Вторая строка: Добавить/Удалить из избранного
    if is_favorite:
        builder.row(
            InlineKeyboardButton(
                text="❌ Удалить из избранного",
                callback_data=f"unfav:{vacancy_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="⭐ Добавить в избранное",
                callback_data=f"fav:{vacancy_id}"
            )
        )

    # Третья строка: Навигация (если больше одной страницы)
    if total_pages > 1:
        nav_buttons = []

        if current_page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{current_page - 1}")
            )

        # Показываем номер текущей страницы
        nav_buttons.append(
            InlineKeyboardButton(text=f"📄 {current_page + 1}/{total_pages}", callback_data="noop")
        )

        if current_page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page:{current_page + 1}")
            )

        builder.row(*nav_buttons)

    return builder.as_markup()


def get_favorites_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для меню избранного

    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Показать все избранные", callback_data="show_favorites")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Очистить избранное", callback_data="clear_favorites")
    )

    return builder.as_markup()


def get_favorite_vacancy_keyboard(vacancy_id: str, url: str,
                                  current_index: int = 0,
                                  total_count: int = 1) -> InlineKeyboardMarkup:
    """
    Создает inline-клавиатуру для вакансии из избранного

    Args:
        vacancy_id: ID вакансии
        url: Ссылка на вакансию
        current_index: Текущий индекс в списке
        total_count: Всего вакансий

    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Первая строка: Ссылка на вакансию
    builder.row(
        InlineKeyboardButton(text="🔗 Открыть вакансию", url=url)
    )

    # Вторая строка: Удалить из избранного
    builder.row(
        InlineKeyboardButton(
            text="❌ Удалить из избранного",
            callback_data=f"unfav:{vacancy_id}"
        )
    )

    # Третья строка: Навигация (если больше одной вакансии)
    if total_count > 1:
        nav_buttons = []

        if current_index > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"fav_page:{current_index - 1}")
            )

        # Показываем номер текущей вакансии
        nav_buttons.append(
            InlineKeyboardButton(text=f"📄 {current_index + 1}/{total_count}", callback_data="noop")
        )

        if current_index < total_count - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="Вперед ➡️", callback_data=f"fav_page:{current_index + 1}")
            )

        builder.row(*nav_buttons)

    return builder.as_markup()


def get_search_filters_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с фильтрами для поиска

    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📍 Выбрать город", callback_data="filter:city"),
        InlineKeyboardButton(text="💼 Уровень опыта", callback_data="filter:experience")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Указать зарплату", callback_data="filter:salary"),
        InlineKeyboardButton(text="🔍 Искать", callback_data="filter:search")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить фильтры", callback_data="filter:reset")
    )

    return builder.as_markup()


def get_cities_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с популярными городами

    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    builder = InlineKeyboardBuilder()

    cities = [
        ("Москва", "city:1"),
        ("Санкт-Петербург", "city:2"),
        ("Екатеринбург", "city:3"),
        ("Новосибирск", "city:4"),
        ("Казань", "city:88"),
        ("Нижний Новгород", "city:66"),
    ]

    for city_name, callback_data in cities:
        builder.row(
            InlineKeyboardButton(text=city_name, callback_data=callback_data)
        )

    builder.row(
        InlineKeyboardButton(text="🇷🇺 Вся Россия", callback_data="city:113")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_filters")
    )

    return builder.as_markup()


def get_experience_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с уровнями опыта

    Returns:
        InlineKeyboardMarkup: Готовая клавиатура
    """
    builder = InlineKeyboardBuilder()

    experience_levels = [
        ("Без опыта (Intern)", "exp:noExperience"),
        ("1-3 года (Junior)", "exp:between1And3"),
        ("3-6 лет (Middle)", "exp:between3And6"),
        ("Более 6 лет (Senior)", "exp:moreThan6"),
    ]

    for level_name, callback_data in experience_levels:
        builder.row(
            InlineKeyboardButton(text=level_name, callback_data=callback_data)
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_filters")
    )

    return builder.as_markup()
