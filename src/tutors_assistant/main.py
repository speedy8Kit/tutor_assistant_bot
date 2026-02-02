from bot.config import BASE_CONFIG
from bot.logger import get_logger

# Загружаем переменные окружения из .env файла

# def days_to_new_year():
#     today = datetime.date.today()
#     new_year = datetime.date(today.year + 1, 1, 1)
#     delta = new_year - today
#     return delta.days

# def pushup_reminder():
#     days_left = days_to_new_year()
#     pushups = 100 - days_left
#     if pushups < 0:
#         pushups = 0
#     message = f"Привет! Сегодня нужно сделать {pushups} отжиманий. Осталось {days_left} дней до Нового года!"
#     bot.send_message(chat_id=CHAT_ID, text=message)



if __name__ == "__main__":
    logger = get_logger()
    # Запускаем функцию раз в день в 9 утра
    # schedule.every().day.at("09:00").do(pushup_reminder)

    # print("Бот для ежедневных напоминаний запущен!")
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)
    logger.info("Пишу сообщение")