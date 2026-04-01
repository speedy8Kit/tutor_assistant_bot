import asyncio
from telegram import Bot
from config import BASE_CONFIG
from logger import get_logger


async def send_message_async(text):
    """Асинхронная функция для отправки сообщения"""
    chat_id = None
    bot = Bot()
    await bot.send_message(chat_id=chat_id, text=text)
    print("✅ Сообщение отправлено!")


def main():
    """Основная функция"""
    logger = get_logger()
    logger.info("🤖 Telegram Bot - Отправка сообщений")
    logger.info("=" * 40)
    logger.info(f"💬 Config: {BASE_CONFIG}")
    logger.info("=" * 40)

    asyncio.run(send_message_async("считаю до пяти"))
    for i in range(1, 6):
        asyncio.run(send_message_async(i))


if __name__ == "__main__":
    main()
