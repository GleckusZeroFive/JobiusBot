from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    """Состояния для процесса поиска вакансий"""
    waiting_for_query = State()
    waiting_for_city = State()
    waiting_for_experience = State()
    waiting_for_salary = State()
    browsing_results = State()

    # Умный поиск с LLM
    waiting_for_smart_query = State()
