import pytchat
import sqlite3
import json
import re
import time

video_id = "ВСТАВЬ_ТУТ_ID_ТВОЕЙ_ТРАНСЛЯЦИИ"
db_file = "pixels.db"
json_file = "pixels.json"
rate_limit_seconds = 60  # Ограничение: 1 пиксель в минуту

# ============ БАЗА ============

def init_db():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pixels (
            x INTEGER,
            y INTEGER,
            color TEXT,
            user TEXT,
            PRIMARY KEY (x, y)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_limits (
            user TEXT PRIMARY KEY,
            last_action REAL
        )
    """)
    conn.commit()
    conn.close()

def can_user_draw(user):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT last_action FROM user_limits WHERE user=?", (user,))
    result = cursor.fetchone()
    now = time.time()

    if result is None or now - result[0] > rate_limit_seconds:
        cursor.execute("REPLACE INTO user_limits (user, last_action) VALUES (?, ?)", (user, now))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

# ============ ПИКСЕЛЬ + JSON ============

def update_pixel(x, y, color, user):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO pixels (x, y, color, user) VALUES (?, ?, ?, ?)",
                   (x, y, color, user))
    conn.commit()
    conn.close()
    print(f"✅ Обновлено: ({x}, {y}) = {color} от {user}")

def export_json():
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT x, y, color FROM pixels")
    data = [{"x": x, "y": y, "color": color} for x, y, color in cursor.fetchall()]
    conn.close()
    with open(json_file, "w") as f:
        json.dump(data, f)
    print("📤 Файл pixels.json обновлён.")

def parse_message(msg, author):
    match = re.match(r"/pixel (\d+) (\d+) (#\w{6})", msg)
    if match:
        x, y, color = int(match.group(1)), int(match.group(2)), match.group(3)

        if not (0 <= x <= 999 and 0 <= y <= 999):
            print(f"🚫 Неверные координаты: ({x},{y})")
            return

        if can_user_draw(author):
            update_pixel(x, y, color, author)
            export_json()
        else:
            print(f"⏳ @{author} рисовал слишком недавно — подожди!")

def main():
    init_db()
    chat = pytchat.create(video_id=video_id)
    print("🚀 Парсинг чата начался...")

    while chat.is_alive():
        for c in chat.get().sync_items():
            print(f"{c.author.name}: {c.message}")
            parse_message(c.message, c.author.name)

if __name__ == "__main__":
    main()

