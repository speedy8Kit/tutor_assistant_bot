"""
Основной модуль бота с правильными импортами.
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram.ext import Application

# Импортируем наши модули
from tutors_assistant.database import Database
from tutors_assistant.handlers.commands import setup_handlers

# Загружаем конфигурацию
load_dotenv()


class TutorBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN не найден в .env файле")

        self.db = Database()
        self.app = Application.builder().token(self.token).build()

    def setup(self):
        """Настройка всех компонентов бота"""
        setup_handlers(self.app, self.db)

    def run(self):
        """Запуск бота"""
        print("🤖 Запускаю Tutors Assistant...")
        self.app.run_polling(allowed_updates=None)


def main():
    """Главная функция для запуска"""
    bot = TutorBot()
    bot.setup()
    bot.run()


if __name__ == "__main__":
    main()
