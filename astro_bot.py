import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
from datetime import datetime
import schedule
import time
from skyfield.api import load
from database import init_db, add_user, get_all_users, update_user_activity, set_user_sign

# === Инициализация БД ===
init_db()

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_LINK = "https://t.me/+lqPB3ppoz7EzMWFi"
CHANNEL_NAME = "Астрологинеss"
ADMIN_IDS = [5197052541, 673687798]

bot = telebot.TeleBot(BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
user_data = {}

zodiac_signs = [
    "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
    "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"
]

zodiac_emojis = {
    "Овен": "♈️", "Телец": "♉️", "Близнецы": "♊️", "Рак": "♋️",
    "Лев": "♌️", "Дева": "♍️", "Весы": "♎️", "Скорпион": "♏️",
    "Стрелец": "♐️", "Козерог": "♑️", "Водолей": "♒️", "Рыбы": "♓️"
}

menu = ReplyKeyboardMarkup(resize_keyboard=True)
for sign in zodiac_signs:
    menu.add(KeyboardButton(sign))


# === Астрология: фаза и знак Луны ===

def get_moon_data():
    ts = load.timescale()
    t = ts.now()
    eph = load('de421.bsp')
    e = eph['earth'].at(t)

    sun = e.observe(eph['sun']).apparent()
    moon = e.observe(eph['moon']).apparent()

    phase_angle = sun.separation_from(moon).degrees
    if phase_angle < 45:
        phase = "Новолуние"
    elif phase_angle < 90:
        phase = "Растущая Луна"
    elif phase_angle < 135:
        phase = "Первая четверть"
    elif phase_angle < 180:
        phase = "Почти полнолуние"
    elif phase_angle < 225:
        phase = "Полнолуние"
    elif phase_angle < 270:
        phase = "Убывающая Луна"
    else:
        phase = "Последняя четверть"

    lon = moon.ecliptic_latlon()[1].degrees
    moon_signs = zodiac_signs
    moon_sign = moon_signs[int(lon // 30)]

    return phase, moon_sign


# === Генерация прогноза ===

def generate_advice(sign):
    moon_phase, moon_sign = get_moon_data()
    date_str = datetime.now().strftime("%d.%m.%Y")

    prompt = (
        f"Ты — опытный астролог. Сегодня {date_str}. "
        f"Фаза Луны: {moon_phase}, Луна в знаке: {moon_sign}. "
        f"Составь настоящий астрологический прогноз на день для знака {sign}. "
        f"Прогноз должен быть основан на лунной фазе, лунном знаке и особенностях знака {sign}. "
        f"Пиши конкретно, по существу, не слишком обобщённо и не слишком длинно — 3–5 предложений. "
        f"Стиль: как у профессионального астролога, без повторов и лишнего."
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GPT ошибка:", e)
        return "⚠️ Не удалось получить прогноз."


# === Telegram-хендлеры ===

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    add_user(chat_id)
    bot.send_message(chat_id, "Привет! Выбери свой знак зодиака ✨", reply_markup=menu)

@bot.message_handler(func=lambda msg: msg.text in zodiac_signs)
def zodiac_handler(message):
    sign = message.text
    chat_id = message.chat.id
    today = datetime.now().date().isoformat()

    set_user_sign(chat_id, sign)
    update_user_activity(chat_id, today)

    if chat_id in user_data and user_data[chat_id]["date"] == today:
        bot.send_message(chat_id,
            f"🔁 Ты уже получил свой прогноз на сегодня!\nПодписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
            parse_mode="HTML")
        return

    tip = generate_advice(sign)
    user_data[chat_id] = {"sign": sign, "date": today}

    bot.send_message(chat_id,
        f"{zodiac_emojis[sign]} <b>Прогноз для {sign}:</b>\n\n{tip}\n\n🔮 Подписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
        parse_mode="HTML"
    )

@bot.message_handler(commands=["stats"])
def stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔️ У тебя нет доступа к статистике.")
        return

    users = get_all_users()
    total_users = len(users)
    today = datetime.now().date().isoformat()
    active_today = sum(1 for u in users if u["last_active"] == today)

    bot.send_message(message.chat.id,
        f"📊 <b>Статистика</b>:\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"✅ Активны сегодня: <b>{active_today}</b>",
        parse_mode="HTML"
    )


# === Планировщик ===

def send_daily_horoscopes():
    users = get_all_users()
    for user in users:
        if not user["sign"]:
            continue
        tip = generate_advice(user["sign"])
        try:
            bot.send_message(user["chat_id"], f"🌞 Доброе утро!\n\n{tip}")
        except Exception as e:
            print(f"Ошибка отправки {user['chat_id']}: {e}")

schedule.every().day.at("08:00").do(send_daily_horoscopes)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

import threading
threading.Thread(target=run_scheduler).start()

bot.polling()






