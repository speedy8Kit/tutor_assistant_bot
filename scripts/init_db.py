#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
Запуск: docker-compose run --rm bot python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from tutor_assistant.database import init_database, create_tables


async def main():
    """Основная функция инициализации"""
    print("🔧 Инициализация базы данных...")

    # Инициализируем соединение
    await init_database()

    # Создаем таблицы
    await create_tables()

    print("✅ База данных успешно инициализирована")


if __name__ == "__main__":
    asyncio.run(main())
