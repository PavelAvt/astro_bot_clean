import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
from datetime import datetime
import requests
import schedule
import time
import swisseph as swe
import math
from database import add_user, get_all_users, update_user_activity, set_user_sign

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")
CHANNEL_LINK = "https://t.me/+lqPB3ppoz7EzMWFi"
CHANNEL_NAME = "Астрологинеss"
ADMIN_ID = [5197052541, 673687798]

bot = telebot.TeleBot(BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
user_data = {}
user_steps = {}

# === Меню ===
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
menu.add(KeyboardButton("🪐 По натальной карте"))

# === Геокодинг ===
def get_coordinates_by_city(city_name):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={city_name}&key={OPENCAGE_API_KEY}&language=ru"
    try:
        response = requests.get(url)
        data = response.json()
        if data["results"]:
            lat = data["results"][0]["geometry"]["lat"]
            lon = data["results"][0]["geometry"]["lng"]
            return lat, lon
        else:
            return None, None
    except Exception as e:
        print("Ошибка геокодинга:", e)
        return None, None

# === Swiss Ephemeris ===
swe.set_ephe_path("ephe")
PLANETS = {
    'Солнце': swe.SUN, 'Луна': swe.MOON, 'Меркурий': swe.MERCURY,
    'Венера': swe.VENUS, 'Марс': swe.MARS, 'Юпитер': swe.JUPITER, 'Сатурн': swe.SATURN
}
ASPECTS = {'Соединение': 0, 'Оппозиция': 180, 'Трин': 120, 'Квадрат': 90, 'Секстиль': 60}

def deg_diff(a, b):
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)

def find_aspect(angle):
    for name, asp_angle in ASPECTS.items():
        if deg_diff(angle, asp_angle) <= 6:
            return name
    return None

def get_transits(birth_date, birth_time, lat, lon):
    day, month, year = map(int, birth_date.split('.'))
    hour, minute = map(int, birth_time.split(':'))
    birth_utc = hour + minute / 60
    jd_birth = swe.julday(year, month, day, birth_utc)
    jd_now = swe.julday(datetime.utcnow().year, datetime.utcnow().month, datetime.utcnow().day, 12)

    natal_positions = {name: swe.calc_ut(jd_birth, code)[0] for name, code in PLANETS.items()}
    transit_positions = {name: swe.calc_ut(jd_now, code)[0] for name, code in PLANETS.items()}

    aspects_found = []
    for t_name, t_lon in transit_positions.items():
        for n_name, n_lon in natal_positions.items():
            angle = deg_diff(t_lon, n_lon)
            aspect = find_aspect(angle)
            if aspect:
                aspects_found.append(f"{t_name} {aspect} к натальному {n_name} ({round(angle, 1)}°)")
    return aspects_found

def generate_natal_analysis(birth_date, birth_time, city):
    lat, lon = get_coordinates_by_city(city)
    if lat is None or lon is None:
        return "⚠️ Не удалось определить координаты города."
    aspects = get_transits(birth_date, birth_time, lat, lon)
    today = datetime.now().strftime('%d.%m.%Y')
    if not aspects:
        return f"Сегодня, {today}, нет сильных транзитов. Это хороший день для баланса и спокойствия."
    aspect_text = '\n'.join(f"• {a}" for a in aspects)
    prompt = (
        f"Ты — профессиональный астролог. Клиент родился {birth_date} в {birth_time} в городе {city} "
        f"(широта: {lat}, долгота: {lon}). Сегодня {today}. Вот транзиты:\n{aspect_text}\n"
        f"Поясни, как это повлияет на его день. Сделай красивый прогноз на 3–5 абзацев, как личную консультацию."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GPT ошибка:", e)
        return "⚠️ Не удалось получить астропрогноз."

# === Обработчики ===
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    add_user(chat_id)
    bot.send_message(chat_id, "Привет! Выбери свой знак зодиака или натальную карту ✨", reply_markup=menu)

@bot.message_handler(func=lambda msg: msg.text == "🪐 По натальной карте")
def natal_start(message):
    user_steps[message.chat.id] = {}
    bot.send_message(message.chat.id, "📅 Введи свою дату рождения в формате ДД.ММ.ГГГГ")

@bot.message_handler(func=lambda msg: user_steps.get(msg.chat.id, {}).get("step") is None and "." in msg.text)
def natal_date(message):
    user_steps[message.chat.id]["birth_date"] = message.text.strip()
    user_steps[message.chat.id]["step"] = "time"
    bot.send_message(message.chat.id, "🕓 Введи своё время рождения в формате ЧЧ:ММ")

@bot.message_handler(func=lambda msg: user_steps.get(msg.chat.id, {}).get("step") == "time")
def natal_time(message):
    user_steps[message.chat.id]["birth_time"] = message.text.strip()
    user_steps[message.chat.id]["step"] = "city"
    bot.send_message(message.chat.id, "🌍 Введи город рождения")

@bot.message_handler(func=lambda msg: user_steps.get(msg.chat.id, {}).get("step") == "city")
def natal_city(message):
    chat_id = message.chat.id
    birth_date = user_steps[chat_id]["birth_date"]
    birth_time = user_steps[chat_id]["birth_time"]
    city = message.text.strip()
    today = datetime.now().date().isoformat()

    if chat_id in user_data and user_data[chat_id].get("natal_date") == today:
        bot.send_message(chat_id,
            f'🔁 Ты уже получил свою натальную карту на сегодня!\nПодписывайся на <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a>',
            parse_mode="HTML")
        return

    tip = generate_natal_analysis(birth_date, birth_time, city)
    user_data[chat_id] = {"natal_date": today}
    bot.send_message(chat_id, f"🪐 <b>Натальная карта на сегодня:</b>\n\n{tip}", parse_mode="HTML")

@bot.message_handler(func=lambda msg: msg.text in zodiac_signs)
def zodiac_handler(message):
    sign = message.text
    chat_id = message.chat.id
    today = datetime.now().date().isoformat()
    set_user_sign(chat_id, sign)
    update_user_activity(chat_id, today)
    if chat_id in user_data and user_data[chat_id].get("date") == today:
        bot.send_message(chat_id,
            f'🔁 Ты уже получил свой прогноз на сегодня!\nПодписывайся на <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a>',
            parse_mode="HTML")
        return
    prompt = (
        f"Ты — опытный астролог. Сегодня {datetime.now().strftime('%d.%m.%Y')}. "
        f"Составь краткий и мудрый прогноз на день для знака {sign}, учитывая эмоциональный фон дня."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        tip = response.choices[0].message.content.strip()
    except:
        tip = "⚠️ Не удалось получить совет."
    user_data[chat_id] = {"sign": sign, "date": today}
    bot.send_message(chat_id, f"{zodiac_emojis[sign]} <b>Совет для {sign}:</b>\n\n{tip}", parse_mode="HTML")

@bot.message_handler(commands=["stats"])
def stats(message):
    if message.from_user.id not in ADMIN_ID:
        bot.send_message(message.chat.id, "⛔️ У тебя нет доступа к статистике.")
        return
    users = get_all_users()
    total = len(users)
    today = datetime.now().date().isoformat()
    active_today = sum(1 for u in users if u["last_active"] == today)
    bot.send_message(message.chat.id, f"📊 Статистика:\n👥 Всего: {total}\n✅ Активны сегодня: {active_today}", parse_mode="HTML")

# === Планировщик ===
def send_daily_horoscopes():
    users = get_all_users()
    for user in users:
        if not user["sign"]:
            continue
        prompt = f"Ты — астролог. Сегодня {datetime.now().strftime('%d.%m.%Y')}. Составь короткий совет для знака {user['sign']}."
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            tip = response.choices[0].message.content.strip()
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



