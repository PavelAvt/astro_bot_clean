import schedule
import time
from threading import Thread
from database import get_all_users
from astro_bot import bot, generate_advice

def send_daily_horoscopes():
    users = get_all_users()
    for user in users:
        try:
            tip = generate_advice(user["sign"])
            bot.send_message(user["chat_id"], f"🌞 Доброе утро!\n\n{tip}")
        except Exception as e:
            print(f"Ошибка при отправке пользователю {user['chat_id']}: {e}")

def run_scheduler():
    schedule.every().day.at("08:00").do(send_daily_horoscopes)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Запуск в отдельном потоке
Thread(target=run_scheduler).start()
