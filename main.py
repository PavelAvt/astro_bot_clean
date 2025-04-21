import threading
import time
from astro_bot import bot
from jobs import scheduler
# Запускаем планировщик в отдельном потоке
def run_scheduler():
    while True:
        scheduler.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler).start()
    bot.polling(none_stop=True)
