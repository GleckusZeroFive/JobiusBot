import aiohttp
import logging
import html
import re

logger = logging.getLogger(__name__)

class HeadHunterAPI:
    """
    Клиент для работы с API HeadHunter (hh.ru)
    Документация: https://github.com/hhru/api
    """

    BASE_URL = "https://api.hh.ru"

    def __init__(self):
        self.session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать aiohttp сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def search_vacancies(
        self,
        text: str = None,
        area: int = None,
        salary: int = None,
        only_with_salary: bool = False,
        experience: str = None,
        schedule: str = None,
        employment: str = None,
        per_page: int = 10,
        page: int = 0,
        period: int = 30
    ) -> dict:
        """
        Поиск вакансий на hh.ru

        Args:
            text: Текст для поиска (например, "Python developer")
            area: ID региона (1 = Москва, 2 = СПб, 113 = Россия)
            salary: Минимальная зарплата
            only_with_salary: Показывать только вакансии с указанной зарплатой
            experience: Опыт работы (noExperience, between1And3, between3And6, moreThan6)
            schedule: График работы (fullDay, shift, flexible, remote, flyInFlyOut)
            employment: Тип занятости (full, part, project, volunteer, probation)
            per_page: Количество вакансий на странице (макс 100)
            page: Номер страницы (начинается с 0)
            period: За сколько дней искать (макс 30)

        Returns:
            dict: Ответ от API с вакансиями
        """
        session = await self._get_session()

        # Формируем параметры запроса
        params = {
            "per_page": min(per_page, 100),  # Макс 100
            "page": page,
            "period": min(period, 30)  # Макс 30 дней
        }

        if text:
            params["text"] = text
        if area:
            params["area"] = area
        if salary:
            params["salary"] = salary
        if only_with_salary:
            params["only_with_salary"] = "true"
        if experience:
            params["experience"] = experience
        if schedule:
            params["schedule"] = schedule
        if employment:
            params["employment"] = employment

        try:
            url = f"{self.BASE_URL}/vacancies"
            logger.info(f"Запрос к HH API: {url} с параметрами {params}")

            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                logger.info(f"Получено {data.get('found', 0)} вакансий, показано {len(data.get('items', []))}")
                return data

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при запросе к HH API: {e}")
            return {"items": [], "found": 0, "error": str(e)}

    async def get_vacancy_by_id(self, vacancy_id: str) -> dict:
        """
        Получить детальную информацию о вакансии по ID

        Args:
            vacancy_id: ID вакансии

        Returns:
            dict: Детальная информация о вакансии
        """
        session = await self._get_session()

        try:
            url = f"{self.BASE_URL}/vacancies/{vacancy_id}"
            logger.info(f"Запрос детальной информации о вакансии {vacancy_id}")

            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при получении вакансии {vacancy_id}: {e}")
            return {"error": str(e)}

    async def get_areas(self) -> list:
        """
        Получить список всех регионов

        Returns:
            list: Список регионов с их ID
        """
        session = await self._get_session()

        try:
            url = f"{self.BASE_URL}/areas"
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при получении списка регионов: {e}")
            return []


def clean_html(text: str) -> str:
    """
    Очищает HTML от неподдерживаемых Telegram тегов.
    Оставляет только разрешённые теги: b, i, u, s, code, pre, a

    Args:
        text: Текст с HTML

    Returns:
        str: Очищенный текст
    """
    if not text:
        return ""

    # Декодируем HTML entities
    text = html.unescape(text)

    # Удаляем неподдерживаемые теги, оставляя их содержимое
    # highlighttext и другие неподдерживаемые теги от HH
    text = re.sub(r'<highlighttext[^>]*>', '<b>', text, flags=re.IGNORECASE)
    text = re.sub(r'</highlighttext>', '</b>', text, flags=re.IGNORECASE)

    # Удаляем все остальные неподдерживаемые теги, но оставляем текст
    allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'strong', 'em']
    # Паттерн для поиска всех тегов
    tag_pattern = re.compile(r'<(/?)(\w+)[^>]*>', re.IGNORECASE)

    def replace_tag(match):
        closing = match.group(1)
        tag_name = match.group(2).lower()

        # Если тег разрешён, оставляем его (упрощённо)
        if tag_name in allowed_tags:
            # strong -> b, em -> i
            if tag_name == 'strong':
                tag_name = 'b'
            elif tag_name == 'em':
                tag_name = 'i'
            return f'<{closing}{tag_name}>'
        else:
            # Иначе удаляем тег, оставляя содержимое
            return ''

    text = tag_pattern.sub(replace_tag, text)

    # Удаляем множественные пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def format_vacancy(vacancy: dict) -> str:
    """
    Форматирует вакансию для отображения в Telegram

    Args:
        vacancy: Словарь с данными вакансии

    Returns:
        str: Отформатированный текст вакансии
    """
    # Название вакансии
    name = vacancy.get("name", "Без названия")

    # Компания
    employer = vacancy.get("employer", {})
    company_name = employer.get("name", "Неизвестная компания")

    # Зарплата
    salary = vacancy.get("salary")
    if salary:
        salary_from = salary.get("from")
        salary_to = salary.get("to")
        currency = salary.get("currency", "RUR")

        # Конвертируем валюту в символ
        currency_symbols = {
            "RUR": "₽",
            "USD": "$",
            "EUR": "€",
            "KZT": "₸"
        }
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

    # Локация
    area = vacancy.get("area", {})
    location = area.get("name", "Не указано")

    # Опыт
    experience = vacancy.get("experience", {})
    exp_text = experience.get("name", "Не указан")

    # График работы
    schedule = vacancy.get("schedule", {})
    schedule_text = schedule.get("name", "")

    # Ссылка
    url = vacancy.get("alternate_url", "")

    # Snippet - краткое описание
    snippet = vacancy.get("snippet", {})
    requirement = snippet.get("requirement", "")
    responsibility = snippet.get("responsibility", "")

    # Очищаем HTML в описаниях
    requirement = clean_html(requirement)
    responsibility = clean_html(responsibility)
    name = clean_html(name)
    company_name = clean_html(company_name)

    # Формируем текст
    text = f"💼 <b>{name}</b>\n\n"
    text += f"🏢 {company_name}\n"
    text += f"📍 {location}"

    if schedule_text:
        text += f" • {schedule_text}"

    text += f"\n💰 {salary_text}\n"
    text += f"📊 Опыт: {exp_text}\n"

    if requirement:
        # Ограничиваем длину описания
        if len(requirement) > 300:
            requirement = requirement[:297] + "..."
        text += f"\n<b>Требования:</b>\n{requirement}\n"

    if responsibility:
        # Ограничиваем длину описания
        if len(responsibility) > 300:
            responsibility = responsibility[:297] + "..."
        text += f"\n<b>Обязанности:</b>\n{responsibility}\n"

    text += f"\n🔗 <a href='{url}'>Ссылка на вакансию</a>"

    return text


# Популярные регионы для быстрого доступа
POPULAR_AREAS = {
    "москва": 1,
    "moscow": 1,
    "спб": 2,
    "санкт-петербург": 2,
    "saint-petersburg": 2,
    "екатеринбург": 3,
    "новосибирск": 4,
    "казань": 88,
    "нижний новгород": 66,
    "россия": 113
}

# Уровни опыта для быстрого доступа
EXPERIENCE_LEVELS = {
    "junior": "between1And3",
    "джуниор": "between1And3",
    "джун": "between1And3",
    "middle": "between3And6",
    "миддл": "between3And6",
    "мидл": "between3And6",
    "senior": "moreThan6",
    "сеньор": "moreThan6",
    "синьор": "moreThan6",
    "lead": "moreThan6",
    "лид": "moreThan6",
    "intern": "noExperience",
    "интерн": "noExperience",
    "стажер": "noExperience",
    "стажёр": "noExperience",
    "без опыта": "noExperience",
    "безопыта": "noExperience"
}
