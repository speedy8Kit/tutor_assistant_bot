from telegram import Bot
from tutor_assistant.config import BASE_CONFIG


def init_bot() -> Bot:
    bot = Bot(token=BASE_CONFIG.bot_config.bot_token)
    return bot
