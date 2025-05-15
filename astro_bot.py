import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
from datetime import datetime, timedelta
import requests
import schedule
import time
from skyfield.api import load
from database import add_user, get_all_users

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_LINK = "https://t.me/+lqPB3ppoz7EzMWFi"
CHANNEL_NAME = "Астрологинеss"

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


# === Астрология ===

def get_moon_phase():
    ts = load.timescale()
    t = ts.now()
    eph = load('de421.bsp')
    e = eph['earth'].at(t)
    sun = e.observe(eph['sun']).apparent()
    moon = e.observe(eph['moon']).apparent()
    phase_angle = sun.separation_from(moon).degrees

    if phase_angle < 45:
        return "Новолуние"
    elif phase_angle < 90:
        return "Растущая луна"
    elif phase_angle < 135:
        return "Первая четверть"
    elif phase_angle < 180:
        return "Почти полнолуние"
    elif phase_angle < 225:
        return "Полнолуние"
    elif phase_angle < 270:
        return "Убывающая луна"
    else:
        return "Последняя четверть"

def get_moon_sign():
    ts = load.timescale()
    t = ts.now()
    eph = load('de421.bsp')
    earth, moon = eph['earth'], eph['moon']
    observer = earth.at(t).observe(moon).apparent()
    lon = observer.ecliptic_latlon()[1].degrees

    signs = [
        "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
        "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"
    ]
    index = int(lon // 30)
    return signs[index]

def get_retrograde_planets():
    ts = load.timescale()
    t = ts.now()
    eph = load('de421.bsp')
    retrograde_planets = []

    for planet_name in ["mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]:
        planet = eph[planet_name]
        now = eph['earth'].at(t).observe(planet).apparent()
        future = eph['earth'].at(ts.utc(t.utc_datetime() + timedelta(hours=1))).observe(planet).apparent()
        if future.position.au[0] < now.position.au[0]:
            retrograde_planets.append(planet_name.capitalize())

    return retrograde_planets


# === Генерация совета ===

def generate_advice(sign):
    moon_phase = get_moon_phase()
    moon_sign = get_moon_sign()
    retrogrades = get_retrograde_planets()
    retrograde_str = ', '.join(retrogrades) if retrogrades else 'нет ретроградных планет'

    prompt = (
        f"Ты — опытный астролог. Сегодня {datetime.now().strftime('%d.%m.%Y')}. "
        f"Фаза Луны: {moon_phase}. Луна в знаке {moon_sign}. "
        f"Ретроградные планеты: {retrograde_str}. "
        f"Составь душевный, мудрый, но простой астрологический совет на 3–4 предложения для знака {sign}, "
        f"учитывая всё вышеуказанное. Избегай сложной терминологии и пиши на языке, понятном обычному человеку."
    )

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GPT ошибка:", e)
        return "⚠️ Не удалось получить совет."


# === Хендлеры ===

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Привет! Выбери свой знак зодиака ✨", reply_markup=menu)

@bot.message_handler(func=lambda msg: msg.text in zodiac_signs)
def zodiac_handler(message):
    sign = message.text
    chat_id = message.chat.id
    today = datetime.now().date().isoformat()

    if chat_id in user_data and user_data[chat_id]["date"] == today:
        bot.send_message(chat_id,
            f"🔁 Ты уже получил свой совет на сегодня!\nПодписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
            parse_mode="HTML")
        return

    tip = generate_advice(sign)
    user_data[chat_id] = {"sign": sign, "date": today}

    bot.send_message(chat_id,
        f"{zodiac_emojis[sign]} <b>Совет для {sign}:</b>\n\n{tip}\n\n🔮 Подписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
        parse_mode="HTML"
    )


# === Планировщик ===

def send_daily_horoscopes():
    users = get_all_users()
    for user in users:
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


