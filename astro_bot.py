import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
from datetime import datetime
import requests
import schedule
import time
import swisseph as swe
from database import add_user, get_all_users, update_user_activity, set_user_sign, init_db

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

# === Кнопки ===
zodiac_signs = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
zodiac_emojis = {"Овен": "♈️", "Телец": "♉️", "Близнецы": "♊️", "Рак": "♋️", "Лев": "♌️", "Дева": "♍️", "Весы": "♎️", "Скорпион": "♏️",
                 "Стрелец": "♐️", "Козерог": "♑️", "Водолей": "♒️", "Рыбы": "♓️"}
menu = ReplyKeyboardMarkup(resize_keyboard=True)
for sign in zodiac_signs:
    menu.add(KeyboardButton(sign))
menu.add(KeyboardButton("🪐 По натальной карте"))

# === Геолокация ===
def get_coordinates_by_city(city_name):
    try:
        url = f"https://api.opencagedata.com/geocode/v1/json?q={city_name}&key={OPENCAGE_API_KEY}&language=ru"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data["results"]:
            return data["results"][0]["geometry"]["lat"], data["results"][0]["geometry"]["lng"]
    except Exception as e:
        print("Geo error:", e)
    return None, None

# === Астрология ===
swe.set_ephe_path("ephe")
PLANETS = {
    'Солнце': swe.SUN, 'Луна': swe.MOON, 'Меркурий': swe.MERCURY,
    'Венера': swe.VENUS, 'Марс': swe.MARS, 'Юпитер': swe.JUPITER, 'Сатурн': swe.SATURN
}
ASPECTS = {'Соединение': 0, 'Оппозиция': 180, 'Трин': 120, 'Квадрат': 90, 'Секстиль': 60}
def deg_diff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)

def find_aspect(angle):
    for name, asp in ASPECTS.items():
        if deg_diff(angle, asp) <= 6:
            return name
    return None

def get_transits(birth_date, birth_time, lat, lon):
    day, month, year = map(int, birth_date.split('.'))
    hour, minute = map(int, birth_time.split(':'))
    birth_utc = hour + minute / 60
    jd_birth = swe.julday(year, month, day, birth_utc)
    jd_now = swe.julday(datetime.utcnow().year, datetime.utcnow().month, datetime.utcnow().day, 12)

    natal = {}
    transit = {}

    for name, code in PLANETS.items():
        lonlatdist, _ = swe.calc_ut(jd_birth, code)
        lon = lonlatdist[0]
        natal[name] = lon

        lonlatdist_tr, _ = swe.calc_ut(jd_now, code)
        lon_tr = lonlatdist_tr[0]
        transit[name] = lon_tr

    result = []
    for t_name, t_lon in transit.items():
        for n_name, n_lon in natal.items():
            angle = deg_diff(t_lon, n_lon)
            asp = find_aspect(angle)
            if asp:
                result.append(f"{t_name} {asp} к натальному {n_name} ({round(angle,1)}°)")
    return result

def generate_natal_analysis(birth_date, birth_time, city):
    lat, lon = get_coordinates_by_city(city)
    if not lat:
        return f"⚠️ Не удалось определить координаты города: {city}"
    aspects = get_transits(birth_date, birth_time, lat, lon)
    today = datetime.now().strftime('%d.%m.%Y')
    if not aspects:
        return f"Сегодня, {today}, нет значимых транзитов."
    text = '\n'.join(f"• {a}" for a in aspects)
    prompt = (
        f"Ты — астролог. Клиент родился {birth_date} в {birth_time} в городе {city}. "
        f"Сегодня {today}. Аспекты:\n{text}\n"
        f"Составь подробный прогноз в стиле личной консультации."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(e)
        return "⚠️ Не удалось получить прогноз."

# === Хендлеры ===
@bot.message_handler(commands=["start"])
def start(message):
    add_user(message.chat.id)
    bot.send_message(message.chat.id, "Привет! Выбери знак зодиака или рассчитай натальную карту ✨", reply_markup=menu)

@bot.message_handler(func=lambda msg: msg.text == "🪐 По натальной карте")
def start_natal(msg):
    user_steps[msg.chat.id] = {}
    bot.send_message(msg.chat.id, "📅 Введи дату рождения (ДД.ММ.ГГГГ)")

@bot.message_handler(func=lambda msg: msg.chat.id in user_steps and "birth_date" not in user_steps[msg.chat.id])
def get_date(msg):
    user_steps[msg.chat.id]["birth_date"] = msg.text.strip()
    bot.send_message(msg.chat.id, "🕓 Введи время рождения (ЧЧ:ММ)")

@bot.message_handler(func=lambda msg: msg.chat.id in user_steps and "birth_time" not in user_steps[msg.chat.id])
def get_time(msg):
    user_steps[msg.chat.id]["birth_time"] = msg.text.strip()
    bot.send_message(msg.chat.id, "🌍 Введи город рождения")

@bot.message_handler(func=lambda msg: msg.chat.id in user_steps and "birth_time" in user_steps[msg.chat.id])
def get_city(msg):
    chat_id = msg.chat.id
    birth_date = user_steps[chat_id]["birth_date"]
    birth_time = user_steps[chat_id]["birth_time"]
    city = msg.text.strip()
    today = datetime.now().date().isoformat()

    if chat_id in user_data and user_data[chat_id].get("natal_date") == today:
        bot.send_message(chat_id,
            f'🔁 Ты уже получил свою натальную карту на сегодня!\nПодписывайся на <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a>',
            parse_mode="HTML")
        return

    tip = generate_natal_analysis(birth_date, birth_time, city)
    user_data[chat_id] = {"natal_date": today}
    bot.send_message(chat_id,
        f"🪐 <b>Натальная карта на сегодня:</b>\n\n{tip}\n\n🔮 Подписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
        parse_mode="HTML")
    user_steps.pop(chat_id)

@bot.message_handler(func=lambda msg: msg.text in zodiac_signs)
def zodiac_handler(msg):
    chat_id = msg.chat.id
    today = datetime.now().date().isoformat()
    set_user_sign(chat_id, msg.text)
    update_user_activity(chat_id, today)
    if chat_id in user_data and user_data[chat_id].get("date") == today:
        bot.send_message(chat_id,
            f'🔁 Ты уже получил свой прогноз на сегодня!\nПодписывайся на <a href="{CHANNEL_LINK}">{CHANNEL_NAME}</a>',
            parse_mode="HTML")
        return
    prompt = f"Составь гороскоп на сегодня для знака {msg.text} ({today}) в 3–4 предложениях."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        tip = response.choices[0].message.content.strip()
    except:
        tip = "⚠️ Не удалось получить прогноз."
    user_data[chat_id] = {"date": today}
    bot.send_message(chat_id,
        f"{zodiac_emojis[msg.text]} <b>Совет для {msg.text}:</b>\n\n{tip}\n\n🔮 Подписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
        parse_mode="HTML")

@bot.message_handler(commands=["stats"])
def stats(message):
    if message.from_user.id not in ADMIN_ID:
        bot.send_message(message.chat.id, "⛔️ Нет доступа.")
        return
    users = get_all_users()
    total = len(users)
    today = datetime.now().date().isoformat()
    active = sum(1 for u in users if u["last_active"] == today)
    bot.send_message(message.chat.id,
        f"📊 Статистика:\n👥 Всего: {total}\n✅ Активны сегодня: {active}", parse_mode="HTML")

# === Планировщик ===
def send_daily_horoscopes():
    users = get_all_users()
    for user in users:
        if not user["sign"]:
            continue
        prompt = f"Краткий гороскоп для {user['sign']} на сегодня."
        try:
            r = openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
            bot.send_message(user["chat_id"], f"🌞 Доброе утро!\n\n{r.choices[0].message.content.strip()}")
        except Exception as e:
            print(f"Ошибка {user['chat_id']}: {e}")

schedule.every().day.at("08:00").do(send_daily_horoscopes)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

import threading
init_db()
threading.Thread(target=run_scheduler).start()
bot.polling()



