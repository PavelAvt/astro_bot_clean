import sqlite3

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            sign TEXT,
            last_active TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(chat_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    conn.close()

def set_user_sign(chat_id, sign):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET sign = ? WHERE chat_id = ?", (sign, chat_id))
    conn.commit()
    conn.close()

def update_user_activity(chat_id, date_str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_active = ? WHERE chat_id = ?", (date_str, chat_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, sign, last_active FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [{"chat_id": row[0], "sign": row[1], "last_active": row[2]} for row in rows]
