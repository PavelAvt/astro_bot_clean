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
            sign TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(chat_id, birth_date, birth_time, lat, lon, city, sign):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (chat_id, birth_date, birth_time, lat, lon, city, sign)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (chat_id, birth_date, birth_time, lat, lon, city, sign))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, sign FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [{"chat_id": row[0], "sign": row[1]} for row in rows]
