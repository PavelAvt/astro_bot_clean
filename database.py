import sqlite3

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            birth_date TEXT,
            birth_time TEXT,
            lat REAL,
            lon REAL,
            city TEXT,
            sign TEXT,
            joined TEXT,
            last_active TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_user(chat_id, birth_date=None, birth_time=None, lat=None, lon=None, city=None, sign=None):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (chat_id, birth_date, birth_time, lat, lon, city, sign, joined, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now'), DATE('now'))
    """, (chat_id, birth_date, birth_time, lat, lon, city, sign))
    conn.commit()
    conn.close()


def set_user_sign(chat_id, sign):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET sign = ? WHERE chat_id = ?", (sign, chat_id))
    conn.commit()
    conn.close()


def update_user_activity(chat_id, date):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_active = ? WHERE chat_id = ?", (date, chat_id))
    conn.commit()
    conn.close()


def get_all_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, sign, last_active FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [{"chat_id": row[0], "sign": row[1], "last_active": row[2]} for row in rows]

