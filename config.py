import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Database
DATABASE_PATH = os.getenv('DATABASE_PATH', 'jobius.db')

# HeadHunter API
HH_BASE_URL = "https://api.hh.ru"

# Пагинация
VACANCIES_PER_PAGE = 3
MAX_VACANCIES_SHOW = 20

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Groq API (LLM)
GROQ_API_KEY_1 = os.getenv('GROQ_API_KEY_1', '')
GROQ_API_KEY_2 = os.getenv('GROQ_API_KEY_2', '')
GROQ_API_KEY_3 = os.getenv('GROQ_API_KEY_3', '')
GROQ_API_KEY_4 = os.getenv('GROQ_API_KEY_4', '')

# Собираем все ключи в список (только непустые)
GROQ_API_KEYS = [key for key in [GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3, GROQ_API_KEY_4] if key]

# Модель для LLM (по умолчанию llama-3.3-70b-versatile)
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
