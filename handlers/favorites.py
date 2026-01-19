import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from database import db
from keyboards import get_favorites_keyboard, get_favorite_vacancy_keyboard, get_main_menu
from hh_api import format_vacancy

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "⭐ Избранное")
@router.message(Command("favorites"))
async def cmd_favorites(message: Message):
    """
    Обработчик команды /favorites и кнопки 'Избранное'
    """
    user_id = message.from_user.id

    # Получаем избранные вакансии из БД
    favorites = await db.get_favorites(user_id)

    if not favorites:
        await message.answer(
            "📭 У вас пока нет избранных вакансий.\n\n"
            "Добавьте вакансию в избранное с помощью кнопки ⭐ под вакансией при поиске.",
            reply_markup=get_main_menu()
        )
        return

    # Показываем первую вакансию
    await show_favorite_vacancy(message, favorites, 0)


async def show_favorite_vacancy(message: Message, favorites: list, index: int):
    """
    Показать избранную вакансию по индексу

    Args:
        message: Сообщение
        favorites: Список избранных вакансий
        index: Индекс вакансии
    """
    if not favorites or index < 0 or index >= len(favorites):
        await message.answer("❌ Вакансия не найдена.")
        return

    favorite = favorites[index]

    # Формируем текст вакансии
    text = (
        f"⭐ <b>Избранная вакансия</b>\n\n"
        f"💼 <b>{favorite['vacancy_name']}</b>\n\n"
        f"🏢 {favorite['company_name']}\n"
        f"📍 {favorite['location']}\n"
        f"💰 {favorite['salary']}\n\n"
        f"Добавлено: {favorite['added_at'][:10]}"
    )

    # Создаем клавиатуру
    keyboard = get_favorite_vacancy_keyboard(
        vacancy_id=favorite['vacancy_id'],
        url=favorite['url'],
        current_index=index,
        total_count=len(favorites)
    )

    await message.answer(text, reply_markup=keyboard, disable_web_page_preview=True)


@router.callback_query(F.data.startswith("fav:"))
async def callback_add_favorite(callback: CallbackQuery):
    """
    Обработчик добавления вакансии в избранное
    """
    user_id = callback.from_user.id

    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        vacancy_id = parts[1]
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {callback.data}, error: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
        return

    # Получаем информацию о вакансии из hh_api
    from hh_api import HeadHunterAPI
    hh_api = HeadHunterAPI()

    try:
        vacancy = await hh_api.get_vacancy_by_id(vacancy_id)

        if "error" in vacancy:
            await callback.answer("❌ Не удалось получить информацию о вакансии", show_alert=True)
            return

        # Извлекаем данные с безопасным доступом к вложенным полям
        vacancy_name = vacancy.get("name", "Без названия")
        company_name = (vacancy.get("employer") or {}).get("name", "Неизвестная компания")
        location = (vacancy.get("area") or {}).get("name", "Не указано")
        url = vacancy.get("alternate_url", "")

        # Форматируем зарплату
        salary = vacancy.get("salary")
        if salary and isinstance(salary, dict):
            salary_from = salary.get("from")
            salary_to = salary.get("to")
            currency = salary.get("currency", "RUR")
            currency_symbols = {"RUR": "₽", "USD": "$", "EUR": "€", "KZT": "₸"}
            currency_symbol = currency_symbols.get(currency, currency)

            if salary_from and salary_to:
                salary_text = f"{salary_from:,} - {salary_to:,} {currency_symbol}".replace(",", " ")
            elif salary_from:
                salary_text = f"от {salary_from:,} {currency_symbol}".replace(",", " ")
            elif salary_to:
                salary_text = f"до {salary_to:,} {currency_symbol}".replace(",", " ")
            else:
                salary_text = "не указана"
        else:
            salary_text = "не указана"

        # Добавляем в БД
        success = await db.add_favorite(
            user_id=user_id,
            vacancy_id=vacancy_id,
            vacancy_name=vacancy_name,
            company_name=company_name,
            salary=salary_text,
            location=location,
            url=url
        )

        if success:
            await callback.answer("⭐ Вакансия добавлена в избранное!", show_alert=False)
        else:
            await callback.answer("ℹ️ Эта вакансия уже в избранном", show_alert=False)

    except Exception as e:
        logger.error(f"Ошибка при добавлении в избранное: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)
    finally:
        await hh_api.close()


@router.callback_query(F.data.startswith("unfav:"))
async def callback_remove_favorite(callback: CallbackQuery):
    """
    Обработчик удаления вакансии из избранного
    """
    user_id = callback.from_user.id

    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        vacancy_id = parts[1]
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {callback.data}, error: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
        return

    # Удаляем из БД
    success = await db.remove_favorite(user_id, vacancy_id)

    if success:
        await callback.answer("🗑️ Вакансия удалена из избранного", show_alert=False)
        # Можно обновить сообщение, удалив кнопку избранного
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except:
            pass
    else:
        await callback.answer("❌ Вакансия не найдена в избранном", show_alert=True)


@router.callback_query(F.data.startswith("fav_page:"))
async def callback_favorite_page(callback: CallbackQuery):
    """
    Обработчик навигации по избранным вакансиям
    """
    user_id = callback.from_user.id

    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        page_index = int(parts[1])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {callback.data}, error: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
        return

    # Получаем избранные вакансии
    favorites = await db.get_favorites(user_id)

    if not favorites:
        await callback.answer("📭 У вас нет избранных вакансий", show_alert=True)
        return

    if page_index < 0 or page_index >= len(favorites):
        await callback.answer("❌ Вакансия не найдена", show_alert=True)
        return

    favorite = favorites[page_index]

    # Формируем текст вакансии
    text = (
        f"⭐ <b>Избранная вакансия</b>\n\n"
        f"💼 <b>{favorite['vacancy_name']}</b>\n\n"
        f"🏢 {favorite['company_name']}\n"
        f"📍 {favorite['location']}\n"
        f"💰 {favorite['salary']}\n\n"
        f"Добавлено: {favorite['added_at'][:10]}"
    )

    # Создаем клавиатуру
    keyboard = get_favorite_vacancy_keyboard(
        vacancy_id=favorite['vacancy_id'],
        url=favorite['url'],
        current_index=page_index,
        total_count=len(favorites)
    )

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обновлении сообщения: {e}")
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "clear_favorites")
async def callback_clear_favorites(callback: CallbackQuery):
    """
    Обработчик очистки всех избранных вакансий
    """
    user_id = callback.from_user.id

    # Получаем все избранные и удаляем
    favorites = await db.get_favorites(user_id)

    for favorite in favorites:
        await db.remove_favorite(user_id, favorite['vacancy_id'])

    await callback.answer("🗑️ Все избранные вакансии удалены", show_alert=True)

    try:
        await callback.message.edit_text("📭 Избранное очищено.")
    except:
        pass


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """
    Обработчик для кнопок без действия (например, отображение номера страницы)
    """
    await callback.answer()
