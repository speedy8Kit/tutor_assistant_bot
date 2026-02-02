import os
from telegram import Bot
from config import BASE_CONFIG

def init_bot() -> Bot:
    bot = Bot(token=BASE_CONFIG.bot_config.bot_token)
    return bot
