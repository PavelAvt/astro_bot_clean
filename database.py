import sqlite3
from datetime import datetime

def get_connection():
    return sqlite3.connect("users.db")

def init_db():
    conn = get_connection()
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
    today = datetime.now().date().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users 
        (chat_id, birth_date, birth_time, lat, lon, city, sign, joined, last_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (chat_id, birth_date, birth_time, lat, lon, city, sign, today, today))
    conn.commit()
    conn.close()

def update_user_activity(chat_id, date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET last_active = ? WHERE chat_id = ?
    """, (date_str, chat_id))
    conn.commit()
    conn.close()

def set_user_sign(chat_id, sign):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET sign = ? WHERE chat_id = ?
    """, (sign, chat_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, sign, last_active FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [
        {"chat_id": row[0], "sign": row[1], "last_active": row[2]}
        for row in rows
    ]
