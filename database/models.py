import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List, Dict
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """
    Класс для работы с базой данных SQLite
    """

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.connection = None

    async def connect(self):
        """Подключение к базе данных"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        await self.init_db()
        logger.info(f"Подключено к базе данных: {self.db_path}")

    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.connection:
            await self.connection.close()
            logger.info("Соединение с базой данных закрыто")

    async def init_db(self):
        """Инициализация таблиц базы данных"""
        async with self.connection.cursor() as cursor:
            # Таблица пользователей
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    search_count INTEGER DEFAULT 0,
                    preferences TEXT
                )
            """)

            # Таблица избранных вакансий
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    vacancy_id TEXT NOT NULL,
                    vacancy_name TEXT,
                    company_name TEXT,
                    salary TEXT,
                    location TEXT,
                    url TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, vacancy_id)
                )
            """)

            # Таблица истории поисков
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    search_query TEXT,
                    search_params TEXT,
                    results_count INTEGER,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица диалогов для LLM
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Таблица для отслеживания offtopic сообщений
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS offtopic_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    offtopic_count INTEGER DEFAULT 0,
                    consecutive_offtopic INTEGER DEFAULT 0,
                    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id)
                )
            """)

            await self.connection.commit()
            logger.info("Таблицы базы данных инициализированы")

    # --- Работа с пользователями ---

    async def add_user(self, user_id: int, username: str = None,
                      first_name: str = None, last_name: str = None):
        """Добавить или обновить пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_active = CURRENT_TIMESTAMP
            """, (user_id, username, first_name, last_name))
            await self.connection.commit()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM users WHERE user_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def update_search_count(self, user_id: int):
        """Увеличить счетчик поисков пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                UPDATE users
                SET search_count = search_count + 1,
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            await self.connection.commit()

    # --- Работа с избранным ---

    async def add_favorite(self, user_id: int, vacancy_id: str,
                          vacancy_name: str = None, company_name: str = None,
                          salary: str = None, location: str = None, url: str = None):
        """Добавить вакансию в избранное"""
        try:
            async with self.connection.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO favorites (user_id, vacancy_id, vacancy_name,
                                         company_name, salary, location, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, vacancy_id, vacancy_name, company_name,
                     salary, location, url))
                await self.connection.commit()
                return True
        except aiosqlite.IntegrityError:
            # Вакансия уже в избранном
            return False

    async def remove_favorite(self, user_id: int, vacancy_id: str):
        """Удалить вакансию из избранного"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                DELETE FROM favorites
                WHERE user_id = ? AND vacancy_id = ?
            """, (user_id, vacancy_id))
            await self.connection.commit()
            return cursor.rowcount > 0

    async def get_favorites(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Получить список избранных вакансий пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM favorites
                WHERE user_id = ?
                ORDER BY added_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def is_favorite(self, user_id: int, vacancy_id: str) -> bool:
        """Проверить, находится ли вакансия в избранном"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT 1 FROM favorites
                WHERE user_id = ? AND vacancy_id = ?
            """, (user_id, vacancy_id))
            row = await cursor.fetchone()
            return row is not None

    # --- Работа с историей поиска ---

    async def add_search_history(self, user_id: int, search_query: str,
                                search_params: str, results_count: int):
        """Добавить запись в историю поиска"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO search_history (user_id, search_query, search_params, results_count)
                VALUES (?, ?, ?, ?)
            """, (user_id, search_query, search_params, results_count))
            await self.connection.commit()

    async def get_search_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получить историю поиска пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM search_history
                WHERE user_id = ?
                ORDER BY searched_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Работа с диалогами для LLM ---

    async def add_message(self, user_id: int, role: str, content: str):
        """Добавить сообщение в историю диалога"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO conversations (user_id, role, content)
                VALUES (?, ?, ?)
            """, (user_id, role, content))
            await self.connection.commit()

    async def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Получить историю диалога пользователя

        Returns:
            List of dicts with keys: role, content, created_at
            Formatted for LLM API (ready to use as conversation context)
        """
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT role, content, created_at FROM conversations
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            # Возвращаем в хронологическом порядке, форматируем для LLM
            return [{"role": row['role'], "content": row['content']} for row in reversed(rows)]

    async def add_to_conversation_history(self, user_id: int, user_message: str, bot_response: str):
        """
        Добавить пару сообщений (пользователь + бот) в историю диалога

        Args:
            user_id: ID пользователя
            user_message: Сообщение пользователя
            bot_response: Ответ бота
        """
        await self.add_message(user_id, "user", user_message)
        await self.add_message(user_id, "assistant", bot_response)

    async def clear_conversation_history(self, user_id: int):
        """Очистить историю диалога пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                DELETE FROM conversations WHERE user_id = ?
            """, (user_id,))
            await self.connection.commit()

    # --- Работа с отслеживанием offtopic сообщений ---

    async def get_offtopic_tracker(self, user_id: int) -> Optional[Dict]:
        """Получить статистику offtopic сообщений пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM offtopic_tracker WHERE user_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def increment_offtopic(self, user_id: int, consecutive: bool = True):
        """
        Увеличить счётчик offtopic сообщений

        Args:
            user_id: ID пользователя
            consecutive: True если offtopic сообщение идёт подряд, False если нет
        """
        async with self.connection.cursor() as cursor:
            # Проверяем, есть ли запись
            tracker = await self.get_offtopic_tracker(user_id)

            if tracker is None:
                # Создаём новую запись
                await cursor.execute("""
                    INSERT INTO offtopic_tracker (user_id, offtopic_count, consecutive_offtopic)
                    VALUES (?, 1, 1)
                """, (user_id,))
            else:
                # Обновляем существующую
                if consecutive:
                    await cursor.execute("""
                        UPDATE offtopic_tracker
                        SET offtopic_count = offtopic_count + 1,
                            consecutive_offtopic = consecutive_offtopic + 1
                        WHERE user_id = ?
                    """, (user_id,))
                else:
                    # Сбрасываем consecutive, но увеличиваем общий счётчик
                    await cursor.execute("""
                        UPDATE offtopic_tracker
                        SET offtopic_count = offtopic_count + 1,
                            consecutive_offtopic = 1
                        WHERE user_id = ?
                    """, (user_id,))

            await self.connection.commit()

    async def reset_consecutive_offtopic(self, user_id: int):
        """Сбросить счётчик последовательных offtopic сообщений"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                UPDATE offtopic_tracker
                SET consecutive_offtopic = 0
                WHERE user_id = ?
            """, (user_id,))
            await self.connection.commit()

    async def reset_offtopic_tracker(self, user_id: int):
        """Полностью сбросить счётчики offtopic для пользователя"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                UPDATE offtopic_tracker
                SET offtopic_count = 0,
                    consecutive_offtopic = 0,
                    last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            await self.connection.commit()


# Глобальный экземпляр базы данных
db = Database()
