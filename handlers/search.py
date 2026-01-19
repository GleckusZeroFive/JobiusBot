import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from hh_api import HeadHunterAPI, format_vacancy, POPULAR_AREAS, EXPERIENCE_LEVELS
from database import db
from keyboards import get_vacancy_keyboard
from utils import search_manager, areas_cache
from utils.states import SearchStates
from utils.llm_service import get_groq_service
from config import MAX_VACANCIES_SHOW

logger = logging.getLogger(__name__)
router = Router()

# Инициализация HH API клиента
hh_api = HeadHunterAPI()


@router.message(Command("search"))
async def cmd_search(message: Message):
    """Обработчик команды /search"""
    user_id = message.from_user.id
    command_text = message.text.replace("/search", "").strip()

    if not command_text:
        await message.answer(
            "❌ Укажите запрос для поиска!\n\n"
            "<b>Примеры:</b>\n"
            "• <code>/search Python developer</code>\n"
            "• <code>/search Хочу удаленную работу python от 150к</code>\n"
            "• <code>/search Backend middle СПб 150000</code>",
        )
        return

    await perform_unified_search(message, user_id, command_text)


async def try_smart_parse(query: str) -> dict:
    """
    Пытается распарсить запрос через LLM.
    Возвращает словарь с параметрами или None при ошибке.
    """
    groq_service = get_groq_service()
    if groq_service is None:
        return None

    try:
        parsed_params = await groq_service.parse_smart_search_query(query)
        logger.info(f"LLM успешно распарсил запрос: {parsed_params}")
        return parsed_params
    except Exception as e:
        logger.warning(f"LLM-парсинг не удался: {e}")
        return None


def fallback_parse(query: str) -> dict:
    """
    Fallback парсинг через regex (старый метод).
    Всегда возвращает хоть что-то.
    """
    parts = query.split()
    text_query = []
    params = {}

    for part in parts:
        if part.isdigit() and 'salary' not in params:
            params['salary'] = int(part)
        elif 'area_id' not in params:
            # Пробуем найти город через areas_cache
            area_id = areas_cache.find_city(part) if areas_cache.is_loaded else None
            if area_id:
                params['area_id'] = area_id
                params['area_name'] = areas_cache.get_city_name(area_id)
            elif part.lower() in POPULAR_AREAS:
                # Fallback на старый словарь
                params['area_id'] = POPULAR_AREAS[part.lower()]
                params['area_name'] = part.lower()
            elif part.lower() in EXPERIENCE_LEVELS and 'experience' not in params:
                params['experience'] = EXPERIENCE_LEVELS[part.lower()]
                params['experience_name'] = part.lower()
            else:
                text_query.append(part)
        elif part.lower() in EXPERIENCE_LEVELS and 'experience' not in params:
            params['experience'] = EXPERIENCE_LEVELS[part.lower()]
            params['experience_name'] = part.lower()
        else:
            text_query.append(part)

    params['text'] = " ".join(text_query) if text_query else query
    logger.info(f"Fallback парсинг: {params}")
    return params


@router.message(F.text)
async def handle_text_message(message: Message):
    """Обработчик текстовых сообщений - ПОЛНОСТЬЮ LLM-based, без keyword ограничений"""
    user_text = message.text
    user_id = message.from_user.id

    logger.info(f"Получено сообщение от {user_id}: {user_text}")

    # Проверяем математику (единственная keyword-проверка которую оставляем)
    if any(op in user_text for op in ['+', '-', '*', '/', '(', ')']):
        allowed_chars = set('0123456789+-*/().% ')
        if all(c in allowed_chars for c in user_text.strip()):
            from handlers.basic import calculate
            result = calculate(user_text)
            await message.answer(result)
            return

    # Используем LLM для ВСЕХ остальных сообщений
    groq_service = get_groq_service()
    if not groq_service:
        # Если LLM недоступен - fallback на простой поиск
        await perform_unified_search(message, user_id, user_text)
        return

    try:
        # Получаем историю разговора и текущую сессию
        conversation_history = await db.get_conversation_history(user_id, limit=6)
        session = search_manager.get_session(user_id)

        # Понимаем намерение пользователя через LLM
        intent_result = await groq_service.understand_user_intent(
            user_message=user_text,
            conversation_history=conversation_history
        )

        logger.info(f"Intent: '{user_text}' -> {intent_result}")

        intent = intent_result.get("intent")

        # Обработка намерений
        if intent == "question_about_results":
            # Вопрос о результатах
            if session and session.current_results:
                # Проверяем, просит ли пользователь показать лучшие вакансии
                top_keywords = ["топ", "лучш", "самы", "подходящ", "оптимальн", "интересн"]
                if any(keyword in user_text.lower() for keyword in top_keywords):
                    # Пользователь хочет увидеть топовые вакансии - показываем первые 3
                    await message.answer("🏆 Вот самые подходящие вакансии из найденных:")

                    for vacancy in session.current_results[:3]:
                        vacancy_id = vacancy.get("id")
                        vacancy_text = format_vacancy(vacancy)
                        url = vacancy.get("alternate_url", "")
                        is_favorite = await db.is_favorite(user_id, vacancy_id)

                        keyboard = get_vacancy_keyboard(
                            vacancy_id=vacancy_id,
                            url=url,
                            is_favorite=is_favorite
                        )

                        await message.answer(vacancy_text, reply_markup=keyboard, disable_web_page_preview=True)
                else:
                    # Обычный вопрос - генерируем текстовый ответ
                    vacancies_info = "\n".join([
                        f"- {v.get('name', 'Без названия')} "
                        f"(График: {v.get('schedule', {}).get('name', 'Не указано')})"
                        for v in session.current_results[:3]
                    ])

                    prompt = f"""Пользователь спрашивает: "{user_text}"

Последние показанные вакансии:
{vacancies_info}

Ответь на вопрос конкретно, используя информацию о вакансиях. Будь кратким."""

                    response = await groq_service.get_completion(
                        [{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=200
                    )

                    if response:
                        await message.answer(response)
                        await db.add_to_conversation_history(user_id, user_text, response)
                    else:
                        await message.answer("Могу поискать что-то ещё?")
            else:
                await message.answer("Сначала выполните поиск, чтобы я мог ответить на вопросы о результатах!")
            return

        elif intent == "refine_search":
            # Уточнение предыдущего поиска
            if session and session.search_query:
                city = intent_result.get("city")
                await refine_existing_search(message, user_id, user_text, session, city)
            else:
                # Нет предыдущего поиска - выполняем новый
                await perform_unified_search(message, user_id, user_text)
            return

        elif intent in ["new_search", "continue_previous"]:
            # Новый поиск или продолжение
            # Если LLM уже распарсил параметры - используем их напрямую
            search_query = intent_result.get("search_query", user_text)
            city = intent_result.get("city")

            # Формируем параметры для smart search
            parsed_params = {"text": search_query}
            if city:
                parsed_params["area"] = city

            # Используем напрямую perform_smart_search с готовыми параметрами
            status_msg = await message.answer("🔍 Анализирую запрос...")

            try:
                await status_msg.delete()
            except:
                pass

            # Показываем что поняли
            params_description = f"🔍 Ищу: <b>{search_query}</b>\n"
            if city:
                params_description += f"📍 Город: {city.title()}\n"

            await message.answer(params_description)
            await perform_smart_search(message, user_id, parsed_params)
            return

        elif intent == "offtopic":
            # Offtopic - генерируем ответ через LLM
            response = await groq_service.get_assistant_response(
                user_message=user_text,
                conversation_history=conversation_history,
                bot_capabilities="""
🔍 Поиск работы на hh.ru
⭐ Избранное
📊 Статистика
🔢 Калькулятор
"""
            )

            if response:
                await message.answer(response)
                # Сохраняем в историю
                await db.add_to_conversation_history(user_id, user_text, response)
            else:
                await message.answer("Я помогаю искать работу! Какую вакансию ищете?")
            return

    except Exception as e:
        logger.error(f"Ошибка LLM обработки: {e}")
        # Fallback на простой поиск
        await perform_unified_search(message, user_id, user_text)


async def perform_unified_search(message: Message, user_id: int, query: str):
    """
    Умный поиск с fallback на обычный парсинг.
    Сначала пробует LLM, если не работает — использует regex.

    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        query: Поисковый запрос
    """
    status_msg = await message.answer("🔍 Анализирую запрос...")

    # Пробуем умный парсинг через LLM
    parsed = await try_smart_parse(query)

    if parsed is not None:
        # LLM успешно распарсил
        logger.info(f"Используем LLM-парсинг для '{query}'")
        try:
            await status_msg.delete()
        except:
            pass

        # Показываем что поняли
        params_description = f"🔍 Ищу: <b>{parsed.get('text', query)}</b>\n"

        if 'area' in parsed:
            params_description += f"📍 Город: {parsed['area'].title()}\n"
        if 'salary' in parsed:
            params_description += f"💰 От {parsed['salary']:,} ₽\n".replace(",", " ")
        if 'experience' in parsed:
            exp_map = {
                "noExperience": "Без опыта",
                "between1And3": "Junior (1-3 года)",
                "between3And6": "Middle (3-6 лет)",
                "moreThan6": "Senior (6+ лет)"
            }
            params_description += f"📊 Опыт: {exp_map.get(parsed['experience'], parsed['experience'])}\n"
        if 'schedule' in parsed:
            schedule_map = {
                "remote": "Удаленная работа",
                "flexible": "Гибкий график",
                "fullDay": "Полный день"
            }
            params_description += f"🕐 График: {schedule_map.get(parsed['schedule'], parsed['schedule'])}\n"
        if 'employment' in parsed:
            employment_map = {
                "full": "Полная занятость",
                "part": "Частичная занятость",
                "project": "Проектная работа"
            }
            params_description += f"💼 Занятость: {employment_map.get(parsed['employment'], parsed['employment'])}\n"

        await message.answer(params_description)
        await perform_smart_search(message, user_id, parsed)
    else:
        # Fallback на обычный парсинг
        logger.info(f"LLM недоступен, используем fallback для '{query}'")
        try:
            await status_msg.delete()
        except:
            pass

        parsed = fallback_parse(query)

        if not parsed.get('text'):
            await message.answer("❌ Укажите название позиции или ключевые слова для поиска!")
            return

        await perform_search(message, user_id, parsed['text'],
                           area_id=parsed.get('area_id'),
                           salary=parsed.get('salary'),
                           experience=parsed.get('experience'))


async def perform_search(message: Message, user_id: int, query: str,
                        area_id: int = None, salary: int = None, experience: str = None,
                        schedule: str = None, employment: str = None):
    """
    Выполняет поиск вакансий и отображает результаты с пагинацией

    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        query: Поисковый запрос (текст для поиска)
        area_id: ID города (опционально)
        salary: Минимальная зарплата (опционально)
        experience: Уровень опыта (опционально)
    """
    search_text = query

    if not search_text:
        await message.answer("❌ Укажите название позиции или ключевые слова для поиска!")
        return

    # Добавляем/обновляем пользователя в БД
    user = message.from_user
    await db.add_user(user_id, user.username, user.first_name, user.last_name)

    # Отправляем уведомление о поиске
    status_msg = await message.answer("🔍 Ищу вакансии...")

    try:
        # Выполняем поиск через HH API
        result = await hh_api.search_vacancies(
            text=search_text,
            area=area_id,
            salary=salary,
            only_with_salary=bool(salary),
            experience=experience,
            schedule=schedule,
            employment=employment,
            per_page=MAX_VACANCIES_SHOW
        )

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except Exception as del_error:
            logger.warning(f"Не удалось удалить статусное сообщение: {del_error}")

        items = result.get("items", [])
        found = result.get("found", 0)

        if not items:
            await message.answer(
                f"😔 Ничего не найдено по запросу: <b>{search_text}</b>\n\n"
                "Попробуйте изменить запрос или убрать фильтры.",
            )
            return

        # Фильтруем вакансии через LLM для повышения релевантности
        groq_service = get_groq_service()
        if groq_service and len(items) > 0:  # Фильтруем если есть вакансии
            try:
                # Получаем название города для фильтрации
                from utils.areas_cache import areas_cache
                area_name = areas_cache.get_city_name(area_id) if area_id else None

                filter_result = await groq_service.filter_vacancies_by_relevance(
                    vacancies=items,
                    user_query=search_text,  # Оригинальный запрос пользователя
                    min_relevance=50,
                    area_name=area_name
                )

                filtered_items = [item["vacancy"] for item in filter_result["filtered_vacancies"]]
                filtered_count = filter_result["filtered_count"]

                if filtered_items:
                    items = filtered_items
                    logger.info(f"LLM фильтрация: {filter_result['total_count']} -> {len(items)} (отфильтровано: {filtered_count})")

                    # Уведомляем пользователя если отфильтровали много
                    if filtered_count > 3:
                        await message.answer(
                            f"🎯 Отфильтровал {filtered_count} менее подходящих вакансий\n"
                            f"Показываю самые релевантные вашему запросу"
                        )
            except Exception as e:
                logger.error(f"Ошибка LLM фильтрации: {e}")
                # Продолжаем с оригинальным списком

        # Сохраняем поиск в историю
        search_params = json.dumps({
            "area": area_id,
            "salary": salary,
            "experience": experience
        })
        await db.add_search_history(user_id, search_text, search_params, found)
        await db.update_search_count(user_id)

        # Создаем сессию поиска для пагинации
        session = search_manager.create_session(
            user_id=user_id,
            search_query=search_text,
            results=items,
            total_found=found,
            search_params={
                "area": area_id,
                "salary": salary,
                "experience": experience
            }
        )

        # Формируем заголовок с результатами
        area_text = ""
        if area_id:
            # Используем areas_cache для получения названия города
            city_name = areas_cache.get_city_name(area_id) if areas_cache.is_loaded else None
            if city_name:
                area_text = f" в городе <b>{city_name}</b>"
            else:
                # Fallback на POPULAR_AREAS
                for city, cid in POPULAR_AREAS.items():
                    if cid == area_id:
                        area_text = f" в городе <b>{city.title()}</b>"
                        break

        salary_text = f" с зарплатой от <b>{salary:,} ₽</b>".replace(",", " ") if salary else ""

        exp_text = ""
        if experience:
            for level_name, level_code in EXPERIENCE_LEVELS.items():
                if level_code == experience:
                    exp_text = f" уровень <b>{level_name}</b>"
                    break

        header = (
            f"🔍 Найдено <b>{found}</b> вакансий по запросу: <b>{search_text}</b>"
            f"{area_text}{salary_text}{exp_text}\n\n"
            f"Показываю первые {len(items)} вакансий:\n"
        )

        await message.answer(header)

        # Показываем первую страницу результатов
        await show_search_results(message, user_id, page=0)

    except Exception as e:
        logger.error(f"Ошибка при поиске вакансий: {e}")
        try:
            await status_msg.delete()
        except:
            pass
        await message.answer("❌ Произошла ошибка при поиске вакансий. Попробуйте позже.")


async def show_search_results(message: Message, user_id: int, page: int = 0):
    """
    Показывает результаты поиска для указанной страницы

    Args:
        message: Сообщение
        user_id: ID пользователя
        page: Номер страницы
    """
    session = search_manager.get_session(user_id)

    if not session:
        await message.answer("❌ Сессия поиска не найдена. Выполните новый поиск.")
        return

    # Получаем вакансии для страницы
    vacancies = session.set_page(page)
    total_pages = session.get_total_pages()

    if not vacancies:
        await message.answer("❌ Нет вакансий для отображения.")
        return

    # Отправляем каждую вакансию отдельным сообщением с кнопками
    for i, vacancy in enumerate(vacancies):
        try:
            vacancy_id = vacancy.get("id")
            vacancy_text = format_vacancy(vacancy)
            url = vacancy.get("alternate_url", "")

            # Проверяем, находится ли вакансия в избранном
            is_favorite = await db.is_favorite(user_id, vacancy_id)

            # Создаем клавиатуру с кнопками
            keyboard = get_vacancy_keyboard(
                vacancy_id=vacancy_id,
                url=url,
                is_favorite=is_favorite,
                current_page=page,
                total_pages=total_pages
            )

            await message.answer(
                vacancy_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

        except Exception as v_error:
            logger.error(f"Ошибка при отправке вакансии {vacancy.get('id', 'unknown')}: {v_error}")


@router.callback_query(F.data.startswith("page:"))
async def callback_page_navigation(callback: CallbackQuery):
    """Обработчик навигации по страницам результатов поиска"""
    user_id = callback.from_user.id

    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        page = int(parts[1])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {callback.data}, error: {e}")
        await callback.answer("❌ Ошибка обработки данных", show_alert=True)
        return

    session = search_manager.get_session(user_id)

    if not session:
        await callback.answer("❌ Сессия поиска истекла. Выполните новый поиск.", show_alert=True)
        return

    # Показываем новую страницу
    await show_search_results(callback.message, user_id, page)
    await callback.answer(f"Страница {page + 1} из {session.get_total_pages()}")


async def perform_smart_search(message: Message, user_id: int, parsed_params: dict):
    """
    Выполняет умный поиск вакансий с LLM-распарсенными параметрами

    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        parsed_params: Параметры поиска из LLM (text, area, salary, experience, schedule, employment)
    """
    search_text = parsed_params.get("text")

    if not search_text:
        await message.answer("❌ Не удалось определить ключевые слова для поиска.")
        return

    # Преобразуем названия городов в ID
    area_id = None
    if "area" in parsed_params:
        from utils.areas_cache import areas_cache
        area_name = parsed_params["area"].lower()
        # Используем areas_cache для поиска города
        area_id = areas_cache.find_city(area_name) if areas_cache.is_loaded else None
        if not area_id and area_name in POPULAR_AREAS:
            # Fallback на POPULAR_AREAS
            area_id = POPULAR_AREAS[area_name]
        if not area_id:
            logger.warning(f"Город '{area_name}' не найден в кеше, поиск по всей России")

    salary = parsed_params.get("salary")
    experience = parsed_params.get("experience")
    schedule = parsed_params.get("schedule")
    employment = parsed_params.get("employment")

    # Добавляем/обновляем пользователя в БД
    user = message.from_user
    await db.add_user(user_id, user.username, user.first_name, user.last_name)

    # Отправляем уведомление о поиске
    status_msg = await message.answer("🔍 Ищу вакансии...")

    try:
        # Выполняем поиск через HH API
        result = await hh_api.search_vacancies(
            text=search_text,
            area=area_id,
            salary=salary,
            only_with_salary=bool(salary),
            experience=experience,
            schedule=schedule,
            employment=employment,
            per_page=MAX_VACANCIES_SHOW
        )

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except Exception:
            pass

        items = result.get("items", [])
        found = result.get("found", 0)

        if not items:
            await message.answer(
                f"😔 Ничего не найдено по запросу: <b>{search_text}</b>\n\n"
                "Попробуйте изменить параметры поиска.",
            )
            return

        # Фильтруем вакансии через LLM для повышения релевантности
        groq_service = get_groq_service()
        if groq_service and len(items) > 0:  # Фильтруем если есть вакансии
            try:
                # Получаем название города для фильтрации
                from utils.areas_cache import areas_cache
                area_name = areas_cache.get_city_name(area_id) if area_id else None

                filter_result = await groq_service.filter_vacancies_by_relevance(
                    vacancies=items,
                    user_query=search_text,  # Оригинальный запрос пользователя
                    min_relevance=50,
                    area_name=area_name
                )

                filtered_items = [item["vacancy"] for item in filter_result["filtered_vacancies"]]
                filtered_count = filter_result["filtered_count"]

                if filtered_items:
                    items = filtered_items
                    logger.info(f"LLM фильтрация: {filter_result['total_count']} -> {len(items)} (отфильтровано: {filtered_count})")

                    # Уведомляем пользователя если отфильтровали много
                    if filtered_count > 3:
                        await message.answer(
                            f"🎯 Отфильтровал {filtered_count} менее подходящих вакансий\n"
                            f"Показываю самые релевантные вашему запросу"
                        )
            except Exception as e:
                logger.error(f"Ошибка LLM фильтрации: {e}")
                # Продолжаем с оригинальным списком

        # Сохраняем поиск в историю
        search_params = json.dumps({
            "area": area_id,
            "salary": salary,
            "experience": experience,
            "schedule": schedule,
            "employment": employment,
            "smart_search": True
        })
        await db.add_search_history(user_id, search_text, search_params, found)
        await db.update_search_count(user_id)

        # Создаем сессию поиска для пагинации
        session = search_manager.create_session(
            user_id=user_id,
            search_query=search_text,
            results=items,
            total_found=found,
            search_params={
                "area": area_id,
                "salary": salary,
                "experience": experience,
                "schedule": schedule,
                "employment": employment
            }
        )

        # Формируем заголовок с результатами
        header = f"🧠 Умный поиск нашёл <b>{found}</b> вакансий\n\n"
        header += f"Показываю первые {len(items)} вакансий:\n"

        await message.answer(header)

        # Показываем первую страницу результатов
        await show_search_results(message, user_id, page=0)

    except Exception as e:
        logger.error(f"Ошибка при умном поиске: {e}")
        try:
            await status_msg.delete()
        except:
            pass
        await message.answer("❌ Произошла ошибка при поиске вакансий. Попробуйте позже.")


async def perform_vacancy_analysis(message: Message, user_id: int, session):
    """
    Анализирует вакансии из текущей сессии поиска и показывает лучшие

    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        session: SearchSession с результатами поиска
    """
    groq_service = get_groq_service()

    if not groq_service:
        await message.answer(
            "❌ Анализ недоступен: LLM сервис не настроен.\n\n"
            "Показываю первые результаты без анализа."
        )
        await show_search_results(message, user_id, page=0)
        return

    status_msg = await message.answer("🤔 Анализирую вакансии...")

    try:
        # Выполняем анализ через LLM
        analysis_result = await groq_service.analyze_vacancies(
            vacancies=session.results,
            original_query=session.search_query,
            top_n=5
        )

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except:
            pass

        top_indices = analysis_result.get("top_indices", [])
        analysis_text = analysis_result.get("analysis", "")

        if not top_indices:
            await message.answer("❌ Не удалось проанализировать вакансии. Показываю все результаты.")
            await show_search_results(message, user_id, page=0)
            return

        # Сохраняем результат анализа в сессии
        from datetime import datetime
        session.last_analysis = {
            "top_indices": top_indices,
            "analysis_text": analysis_text,
            "original_query": session.search_query
        }
        session.analysis_timestamp = datetime.now()

        # Формируем сообщение с анализом
        header = (
            f"✨ <b>Анализ вакансий по запросу:</b> {session.search_query}\n\n"
            f"💡 <b>Вывод:</b> {analysis_text}\n\n"
            f"🏆 <b>Топ-{len(top_indices)} лучших вакансий:</b>\n"
        )

        await message.answer(header)

        # Показываем отобранные вакансии
        for rank, idx in enumerate(top_indices, 1):
            if idx < len(session.results):
                vacancy = session.results[idx]
                vacancy_text = format_vacancy(vacancy)

                # Добавляем номер в рейтинге
                ranking_header = f"<b>#{rank} место</b>\n\n"

                keyboard = get_vacancy_keyboard(
                    vacancy_id=vacancy['id'],
                    url=vacancy['alternate_url'],
                    is_favorite=False
                )

                await message.answer(ranking_header + vacancy_text, reply_markup=keyboard)

        # Предлагаем посмотреть остальные вакансии
        if len(session.results) > len(top_indices):
            remaining = len(session.results) - len(top_indices)
            await message.answer(
                f"📋 Остальные вакансии ({remaining} шт.) доступны через обычный поиск.\n"
                f"Чтобы увидеть все результаты, выполните поиск снова."
            )

    except Exception as e:
        logger.error(f"Ошибка при анализе вакансий: {e}")
        try:
            await status_msg.delete()
        except:
            pass
        await message.answer(
            "❌ Произошла ошибка при анализе вакансий.\n\n"
            "Показываю первые результаты без анализа."
        )
        await show_search_results(message, user_id, page=0)


async def explain_analysis_criteria(message: Message, session):
    """
    Объясняет пользователю критерии, по которым были выбраны лучшие вакансии

    Args:
        message: Сообщение пользователя
        session: SearchSession с сохранённым анализом
    """
    if not session.last_analysis:
        await message.answer("❌ Информация об анализе не найдена.")
        return

    analysis_text = session.last_analysis.get("analysis_text", "")
    original_query = session.last_analysis.get("original_query", "")

    # Формируем детальное объяснение
    explanation = (
        f"📊 <b>Критерии отбора вакансий</b>\n\n"
        f"Я проанализировал все найденные вакансии по запросу <b>«{original_query}»</b> "
        f"и выбрал лучшие на основе следующих критериев:\n\n"
        f"<b>1. Релевантность запросу</b>\n"
        f"   • Соответствие должности и требований вашему запросу\n"
        f"   • Наличие ключевых навыков и технологий\n\n"
        f"<b>2. Условия труда</b>\n"
        f"   • Указанная зарплата (приоритет вакансиям с чёткой суммой)\n"
        f"   • График работы и тип занятости\n"
        f"   • Локация и возможность удалённой работы\n\n"
        f"<b>3. Качество описания</b>\n"
        f"   • Детальность требований и обязанностей\n"
        f"   • Понятность условий работы\n"
        f"   • Отсутствие расплывчатых формулировок\n\n"
        f"<b>4. Репутация компании</b>\n"
        f"   • Известность и стабильность работодателя\n"
        f"   • Профессионализм описания вакансии\n\n"
    )

    # Добавляем пользовательские параметры поиска, если они есть
    search_params = session.search_params
    user_preferences = []

    if search_params.get("experience"):
        exp_mapping = {
            "noExperience": "без опыта",
            "between1And3": "1-3 года",
            "between3And6": "3-6 лет",
            "moreThan6": "более 6 лет"
        }
        exp_text = exp_mapping.get(search_params["experience"], search_params["experience"])
        user_preferences.append(f"опыт работы: {exp_text}")

    if search_params.get("salary"):
        user_preferences.append(f"зарплата от {search_params['salary']:,} ₽".replace(",", " "))

    if search_params.get("schedule"):
        schedule_mapping = {
            "remote": "удалённая работа",
            "flexible": "гибкий график",
            "fullDay": "полный день"
        }
        schedule_text = schedule_mapping.get(search_params["schedule"], search_params["schedule"])
        user_preferences.append(f"график: {schedule_text}")

    if user_preferences:
        explanation += f"<b>Учтены ваши параметры:</b>\n   • " + "\n   • ".join(user_preferences) + "\n\n"

    # Добавляем анализ от LLM
    explanation += f"<b>Мой вывод:</b>\n{analysis_text}"

    await message.answer(explanation)


async def show_worst_vacancies(message: Message, session):
    """
    Показывает худшие вакансии из результатов поиска с объяснением

    Args:
        message: Сообщение пользователя
        session: SearchSession с результатами
    """
    groq_service = get_groq_service()

    if not groq_service:
        # Показываем последние 3 вакансии без LLM анализа
        await message.answer(
            "⚠️ <b>Примеры менее подходящих вакансий</b>\n\n"
            "Показываю последние вакансии из результатов поиска. "
            "Они могут быть менее релевантны вашему запросу, иметь неполное описание "
            "или неуказанные условия труда."
        )

        worst_indices = list(range(max(0, len(session.results) - 3), len(session.results)))
        for idx in worst_indices:
            if idx < len(session.results):
                vacancy = session.results[idx]
                vacancy_text = format_vacancy(vacancy)
                keyboard = get_vacancy_keyboard(
                    vacancy_id=vacancy['id'],
                    url=vacancy['alternate_url'],
                    is_favorite=False
                )
                await message.answer(vacancy_text, reply_markup=keyboard)
        return

    status_msg = await message.answer("🔍 Анализирую наименее подходящие вакансии...")

    try:
        # Используем LLM для поиска худших вакансий
        from datetime import datetime

        # Создаём промпт для поиска худших
        vacancy_summaries = []
        for idx, v in enumerate(session.results[:20]):
            salary_info = "не указана"
            if v.get('salary'):
                if v['salary'].get('from') and v['salary'].get('to'):
                    salary_info = f"{v['salary']['from']:,} - {v['salary']['to']:,} {v['salary'].get('currency', 'RUB')}".replace(',', ' ')
                elif v['salary'].get('from'):
                    salary_info = f"от {v['salary']['from']:,} {v['salary'].get('currency', 'RUB')}".replace(',', ' ')
                elif v['salary'].get('to'):
                    salary_info = f"до {v['salary']['to']:,} {v['salary'].get('currency', 'RUB')}".replace(',', ' ')

            requirement = v.get('snippet', {}).get('requirement', 'нет данных')
            responsibility = v.get('snippet', {}).get('responsibility', 'нет данных')

            import re
            requirement = re.sub(r'<[^>]+>', '', requirement) if requirement else 'нет данных'
            responsibility = re.sub(r'<[^>]+>', '', responsibility) if responsibility else 'нет данных'

            vacancy_summaries.append({
                "index": idx,
                "name": v.get('name', 'Без названия'),
                "company": v.get('employer', {}).get('name', 'Неизвестно'),
                "salary": salary_info,
                "requirement": requirement[:150],
                "responsibility": responsibility[:150]
            })

        system_prompt = f"""Ты - карьерный консультант. Найди 3 НАИМЕНЕЕ подходящие вакансии из списка.

КРИТЕРИИ ХУДШИХ ВАКАНСИЙ:
1. Нерелевантность запросу "{session.search_query}"
2. Отсутствие зарплаты или неясные условия
3. Расплывчатое описание требований и обязанностей
4. Несоответствие профессиональному уровню

ФОРМАТ ОТВЕТА (JSON):
{{
    "worst_indices": [18, 15, 12],
    "explanation": "Краткое объяснение (2-3 предложения): почему эти вакансии наименее подходящие"
}}

Отвечай ТОЛЬКО в формате JSON без дополнительного текста."""

        vacancies_text = "\n\n".join([
            f"Вакансия {v['index']}:\n"
            f"📌 {v['name']}\n"
            f"🏢 {v['company']}\n"
            f"💰 {v['salary']}\n"
            f"Требования: {v['requirement']}\n"
            f"Обязанности: {v['responsibility']}"
            for v in vacancy_summaries
        ])

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Список вакансий:\n\n{vacancies_text}"}
        ]

        response = await groq_service.get_completion(messages, temperature=0.3, max_tokens=400)

        # Удаляем markdown блоки
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()

        result = json.loads(response)
        worst_indices = result.get("worst_indices", [])[:3]
        explanation = result.get("explanation", "")

        # Удаляем статусное сообщение
        try:
            await status_msg.delete()
        except:
            pass

        if not worst_indices:
            worst_indices = list(range(max(0, len(session.results) - 3), len(session.results)))
            explanation = "Показываю последние вакансии из результатов."

        # Сохраняем информацию о худших вакансиях
        session.last_worst = {
            "worst_indices": worst_indices,
            "explanation": explanation
        }
        session.analysis_timestamp = datetime.now()

        header = (
            f"⚠️ <b>Наименее подходящие вакансии</b>\n\n"
            f"💡 <b>Почему они хуже:</b>\n{explanation}\n\n"
            f"⬇️ <b>Примеры менее подходящих вакансий:</b>\n"
        )

        await message.answer(header)

        # Показываем худшие вакансии
        for rank, idx in enumerate(worst_indices, 1):
            if idx < len(session.results):
                vacancy = session.results[idx]
                vacancy_text = format_vacancy(vacancy)

                keyboard = get_vacancy_keyboard(
                    vacancy_id=vacancy['id'],
                    url=vacancy['alternate_url'],
                    is_favorite=False
                )

                await message.answer(f"<b>Пример {rank}</b>\n\n" + vacancy_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при анализе худших вакансий: {e}")
        try:
            await status_msg.delete()
        except:
            pass

        # Fallback: показываем последние вакансии
        await message.answer(
            "⚠️ <b>Примеры менее подходящих вакансий</b>\n\n"
            "Показываю последние вакансии из результатов поиска."
        )

        worst_indices = list(range(max(0, len(session.results) - 3), len(session.results)))
        for idx in worst_indices:
            if idx < len(session.results):
                vacancy = session.results[idx]
                vacancy_text = format_vacancy(vacancy)
                keyboard = get_vacancy_keyboard(
                    vacancy_id=vacancy['id'],
                    url=vacancy['alternate_url'],
                    is_favorite=False
                )
                await message.answer(vacancy_text, reply_markup=keyboard)


async def refine_existing_search(message: Message, user_id: int, user_text: str, session, mentioned_city: str = None):
    """
    Уточняет существующий поиск с новыми параметрами (город, зарплата и т.д.)

    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        user_text: Текст сообщения
        session: Текущая сессия поиска
        mentioned_city: Упомянутый город (если найден)
    """
    # Извлекаем оригинальный запрос
    original_query = session.search_query

    # Пытаемся извлечь новые параметры
    groq_service = get_groq_service()

    if groq_service:
        # Используем LLM для парсинга уточнений
        try:
            # Создаём контекстный запрос для LLM
            combined_query = f"{original_query}, {user_text}"
            parsed_params = await groq_service.parse_smart_search_query(combined_query)

            # Берём город и другие параметры из нового парсинга
            area_id = None
            if parsed_params.get("area"):
                from utils.areas_cache import areas_cache
                area_name = parsed_params["area"].lower()
                area_id = areas_cache.find_city(area_name)

            # Если город не распознан LLM, но был упомянут напрямую
            if not area_id and mentioned_city:
                from utils.areas_cache import areas_cache
                area_id = areas_cache.find_city(mentioned_city)

            salary = parsed_params.get("salary")
            experience = parsed_params.get("experience")
            schedule = parsed_params.get("schedule")
            employment = parsed_params.get("employment")

            # Формируем сообщение о том, что ищем
            refine_msg_parts = [f"🔍 Уточняю поиск: <b>{original_query}</b>"]

            if area_id:
                from utils.areas_cache import areas_cache
                city_name = areas_cache.get_city_name(area_id)
                if city_name:
                    refine_msg_parts.append(f"📍 Город: {city_name}")

            if salary:
                refine_msg_parts.append(f"💰 Зарплата: от {salary:,} ₽".replace(",", " "))

            if experience:
                exp_mapping = {
                    "noExperience": "без опыта",
                    "between1And3": "1-3 года",
                    "between3And6": "3-6 лет",
                    "moreThan6": "более 6 лет"
                }
                exp_text = exp_mapping.get(experience, experience)
                refine_msg_parts.append(f"📊 Опыт: {exp_text}")

            if schedule:
                schedule_mapping = {
                    "remote": "удалённая работа",
                    "flexible": "гибкий график",
                    "fullDay": "полный день"
                }
                schedule_text = schedule_mapping.get(schedule, schedule)
                refine_msg_parts.append(f"🕐 График: {schedule_text}")

            await message.answer("\n".join(refine_msg_parts))

            # Выполняем поиск с уточнёнными параметрами
            await perform_search(
                message=message,
                user_id=user_id,
                query=original_query,
                area_id=area_id,
                salary=salary,
                experience=experience,
                schedule=schedule,
                employment=employment
            )
            return

        except Exception as e:
            logger.error(f"Ошибка при уточнении поиска через LLM: {e}")

    # Fallback: простой парсинг
    from hh_api import POPULAR_AREAS

    area_id = None
    if mentioned_city:
        area_id = POPULAR_AREAS.get(mentioned_city)

    if area_id:
        await message.answer(
            f"🔍 Уточняю поиск: <b>{original_query}</b>\n"
            f"📍 Город: {mentioned_city.title()}"
        )

        await perform_search(
            message=message,
            user_id=user_id,
            query=original_query,
            area_id=area_id
        )
    else:
        # Не смогли распознать уточнение - выполняем обычный поиск
        await perform_unified_search(message, user_id, user_text)

