from typing import List, Dict, Any
from config import VACANCIES_PER_PAGE


class SearchSession:
    """
    Класс для хранения сессии поиска с результатами и пагинацией
    """

    def __init__(self, user_id: int, search_query: str, results: List[Dict],
                 total_found: int, search_params: Dict[str, Any] = None):
        """
        Args:
            user_id: ID пользователя
            search_query: Поисковый запрос
            results: Список вакансий
            total_found: Всего найдено вакансий
            search_params: Параметры поиска (город, зарплата, опыт и т.д.)
        """
        self.user_id = user_id
        self.search_query = search_query
        self.results = results
        self.total_found = total_found
        self.search_params = search_params or {}
        self.current_page = 0
        self.last_analysis = None  # Хранит результат последнего анализа
        self.last_worst = None  # Хранит результат анализа худших вакансий
        self.analysis_timestamp = None  # Время последнего анализа

    def get_page(self, page_number: int) -> List[Dict]:
        """
        Получить вакансии для указанной страницы

        Args:
            page_number: Номер страницы (начиная с 0)

        Returns:
            List[Dict]: Список вакансий для страницы
        """
        start_idx = page_number * VACANCIES_PER_PAGE
        end_idx = start_idx + VACANCIES_PER_PAGE
        return self.results[start_idx:end_idx]

    def get_total_pages(self) -> int:
        """
        Получить общее количество страниц

        Returns:
            int: Количество страниц
        """
        return (len(self.results) + VACANCIES_PER_PAGE - 1) // VACANCIES_PER_PAGE

    def has_next_page(self) -> bool:
        """Есть ли следующая страница"""
        return self.current_page < self.get_total_pages() - 1

    def has_prev_page(self) -> bool:
        """Есть ли предыдущая страница"""
        return self.current_page > 0

    def next_page(self) -> List[Dict]:
        """Перейти на следующую страницу"""
        if self.has_next_page():
            self.current_page += 1
        return self.get_page(self.current_page)

    def prev_page(self) -> List[Dict]:
        """Перейти на предыдущую страницу"""
        if self.has_prev_page():
            self.current_page -= 1
        return self.get_page(self.current_page)

    def set_page(self, page_number: int) -> List[Dict]:
        """
        Установить конкретную страницу

        Args:
            page_number: Номер страницы (начиная с 0)

        Returns:
            List[Dict]: Список вакансий для страницы
        """
        if 0 <= page_number < self.get_total_pages():
            self.current_page = page_number
        return self.get_page(self.current_page)


class SearchSessionManager:
    """
    Менеджер для управления сессиями поиска пользователей
    """

    def __init__(self):
        self.sessions: Dict[int, SearchSession] = {}

    def create_session(self, user_id: int, search_query: str, results: List[Dict],
                      total_found: int, search_params: Dict[str, Any] = None) -> SearchSession:
        """
        Создать новую сессию поиска

        Args:
            user_id: ID пользователя
            search_query: Поисковый запрос
            results: Список вакансий
            total_found: Всего найдено вакансий
            search_params: Параметры поиска

        Returns:
            SearchSession: Созданная сессия
        """
        session = SearchSession(user_id, search_query, results, total_found, search_params)
        self.sessions[user_id] = session
        return session

    def get_session(self, user_id: int) -> SearchSession | None:
        """
        Получить сессию пользователя

        Args:
            user_id: ID пользователя

        Returns:
            SearchSession | None: Сессия или None
        """
        return self.sessions.get(user_id)

    def clear_session(self, user_id: int):
        """
        Очистить сессию пользователя

        Args:
            user_id: ID пользователя
        """
        if user_id in self.sessions:
            del self.sessions[user_id]

    def has_session(self, user_id: int) -> bool:
        """
        Проверить, есть ли активная сессия у пользователя

        Args:
            user_id: ID пользователя

        Returns:
            bool: True если есть сессия
        """
        return user_id in self.sessions


# Глобальный экземпляр менеджера сессий
search_manager = SearchSessionManager()
