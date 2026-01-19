import logging
import difflib
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class AreasCache:
    """
    Кеш городов и регионов из HeadHunter API

    Загружает полное дерево регионов при инициализации и строит индекс
    для быстрого поиска городов по названию с поддержкой нечеткого поиска.
    """

    def __init__(self):
        self.areas_index: Dict[str, int] = {}  # {"москва": 1, ...}
        self.id_to_name: Dict[int, str] = {}   # {1: "Москва", ...}
        self.aliases: Dict[str, str] = {
            "питер": "санкт-петербург",
            "спб": "санкт-петербург",
            "мск": "москва",
            "нн": "нижний новгород",
            "екб": "екатеринбург",
            "нск": "новосибирск",
            "краснодар": "краснодар",
            "владивосток": "владивосток",
            "воронеж": "воронеж",
            "красноярск": "красноярск",
            "самара": "самара",
            "уфа": "уфа",
            "ростов": "ростов-на-дону",
            "омск": "омск",
            "челябинск": "челябинск",
        }
        self.popular_cities: List[str] = []
        self.is_loaded = False

    async def load_areas(self, hh_api) -> bool:
        """
        Загрузить города из HeadHunter API и построить индекс

        Args:
            hh_api: Экземпляр HeadHunterAPI для запроса к API

        Returns:
            bool: True если загрузка успешна, False при ошибке
        """
        try:
            logger.info("Загрузка регионов из HeadHunter API...")
            areas_tree = await hh_api.get_areas()

            if not areas_tree:
                logger.error("API вернул пустой список регионов")
                return False

            # Рекурсивно обходим дерево и извлекаем все города
            self._build_index(areas_tree)

            # Устанавливаем популярные города (топ-30 крупнейших городов России)
            self.popular_cities = [
                "москва", "санкт-петербург", "новосибирск", "екатеринбург",
                "казань", "нижний новгород", "челябинск", "самара", "омск",
                "ростов-на-дону", "уфа", "красноярск", "пермь", "воронеж",
                "волгоград", "краснодар", "саратов", "тюмень", "тольятти",
                "ижевск", "барнаул", "ульяновск", "иркутск", "хабаровск",
                "ярославль", "владивосток", "махачкала", "томск", "оренбург",
                "кемерово"
            ]

            self.is_loaded = True
            logger.info(f"Успешно загружено {len(self.areas_index)} городов/регионов")
            return True

        except Exception as e:
            logger.error(f"Ошибка при загрузке городов из API: {e}")
            self.is_loaded = False
            return False

    def _build_index(self, areas: List[Dict], level: int = 0):
        """
        Рекурсивно обходит дерево регионов и строит индекс

        Args:
            areas: Список регионов/городов из API
            level: Уровень вложенности (для отладки)
        """
        for area in areas:
            area_id = int(area.get("id"))
            area_name = area.get("name", "").strip()
            child_areas = area.get("areas", [])

            if not area_name:
                continue

            # Сохраняем в индекс (lowercase для поиска)
            area_name_lower = area_name.lower()
            self.areas_index[area_name_lower] = area_id
            self.id_to_name[area_id] = area_name

            # Рекурсивно обрабатываем дочерние элементы
            if child_areas:
                self._build_index(child_areas, level + 1)

    def find_city(self, city_name: str) -> Optional[int]:
        """
        Найти ID города по названию с поддержкой нечеткого поиска

        Args:
            city_name: Название города (любой регистр)

        Returns:
            Optional[int]: ID города или None если не найден

        Examples:
            >>> cache.find_city("Москва")  # Exact match
            1
            >>> cache.find_city("Питер")  # Alias
            2
            >>> cache.find_city("Влодивосток")  # Fuzzy match
            75
        """
        if not self.is_loaded:
            logger.warning("Кеш городов не загружен, используйте POPULAR_AREAS")
            return None

        if not city_name:
            return None

        city_lower = city_name.lower().strip()

        # 1. Точное совпадение
        if city_lower in self.areas_index:
            logger.debug(f"Найден город (точное совпадение): {city_name} -> {self.areas_index[city_lower]}")
            return self.areas_index[city_lower]

        # 2. Алиасы (сокращения)
        if city_lower in self.aliases:
            aliased_city = self.aliases[city_lower]
            if aliased_city in self.areas_index:
                logger.debug(f"Найден город (алиас): {city_name} -> {aliased_city} -> {self.areas_index[aliased_city]}")
                return self.areas_index[aliased_city]

        # 3. Нечеткий поиск (для опечаток)
        matches = difflib.get_close_matches(city_lower, self.areas_index.keys(), n=1, cutoff=0.8)
        if matches:
            matched_city = matches[0]
            logger.info(f"Найден город (нечеткий поиск): {city_name} -> {matched_city} -> {self.areas_index[matched_city]}")
            return self.areas_index[matched_city]

        logger.debug(f"Город не найден: {city_name}")
        return None

    def get_city_name(self, area_id: int) -> Optional[str]:
        """
        Получить название города по ID

        Args:
            area_id: ID региона/города

        Returns:
            Optional[str]: Название города или None если не найден
        """
        if not self.is_loaded:
            return None

        return self.id_to_name.get(area_id)

    def get_popular_cities(self) -> List[str]:
        """
        Получить список популярных городов для LLM промпта

        Returns:
            List[str]: Список названий городов (lowercase)
        """
        if not self.is_loaded or not self.popular_cities:
            # Fallback на базовый список
            return ["москва", "санкт-петербург", "екатеринбург", "новосибирск", "казань"]

        return self.popular_cities


# Глобальный синглтон
areas_cache = AreasCache()
