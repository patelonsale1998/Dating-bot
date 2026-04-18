import requests
import time
import sqlite3

TOKEN = "8450433036:AAFmuzOeD1NzN5hdQM7puEzDq9Om7ihJ3bk"
ADMIN_ID = 123456789
URL = f"https://api.telegram.org/bot{TOKEN}/"

# ===== DB SETUP =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY,
gender TEXT,
age TEXT,
city TEXT,
photo TEXT
)
""")
conn.commit()

# ===== ACTIVE MEMORY =====
queue_male = []
queue_female = []
active = {}

# ===== SEND =====
def send(chat_id, text):
    requests.post(URL + "sendMessage", data={"chat_id": chat_id, "text": text})

def send_photo(chat_id, photo, caption):
    requests.post(URL + "sendPhoto", data={
        "chat_id": chat_id,
        "photo": photo,
        "caption": caption
    })

def get_updates(offset=None):
    return requests.get(URL + "getUpdates", params={"timeout": 100, "offset": offset}).json()

# ===== DB HELPERS =====
def save_user(uid, field, value):
    cur.execute("SELECT id FROM users WHERE id=?", (uid,))
    if cur.fetchone():
        cur.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, uid))
    else:
        cur.execute("INSERT INTO users (id, {0}) VALUES (?, ?)".format(field), (uid, value))
    conn.commit()

def get_user(uid):
    cur.execute("SELECT * FROM users WHERE id=?", (uid,))
    return cur.fetchone()

# ===== MATCH =====
def match(uid, gender):
    queue = queue_female if gender == "male" else queue_male

    if queue:
        partner = queue.pop(0)
        active[uid] = partner
        active[partner] = uid

        send(uid, "❤️ Matched!")
        send(partner, "❤️ Matched!")
    else:
        queue.append(uid)
        send(uid, "🔎 Searching...")

# ===== ADMIN DASHBOARD =====
def admin_panel(chat_id):
    send(chat_id, """
👑 ADMIN PANEL

/users - total users
/active - active chats
/broadcast msg - send msg to all
""")

# ===== LOOP =====
def handle(update):
    m = update.get("message")
    if not m:
        return

    chat_id = m["chat"]["id"]
    text = m.get("text", "")

    # ===== ADMIN =====
    if chat_id == ADMIN_ID:
        if text == "/admin":
            admin_panel(chat_id)
            return

        if text == "/users":
            cur.execute("SELECT COUNT(*) FROM users")
            send(chat_id, str(cur.fetchone()[0]))
            return

        if text == "/active":
            send(chat_id, str(active))
            return

        if text.startswith("/broadcast"):
            msg = text.replace("/broadcast", "")
            cur.execute("SELECT id FROM users")
            for u in cur.fetchall():
                send(u[0], msg)
            return

    # ===== START =====
    if text == "/start":
        send(chat_id, "👤 Male or Female?")
        save_user(chat_id, "gender", "")
        return

    # ===== PROFILE FLOW =====
    user = get_user(chat_id)

    if user and not user[1]:
        save_user(chat_id, "gender", text.lower())
        send(chat_id, "🎂 Age?")
        return

    if user and not user[2]:
        save_user(chat_id, "age", text)
        send(chat_id, "🏙 City?")
        return

    if user and not user[3]:
        save_user(chat_id, "city", text)
        send(chat_id, "📸 Send photo")
        return

    if "photo" in m:
        photo = m["photo"][-1]["file_id"]
        save_user(chat_id, "photo", photo)

        gender = user[1]
        match(chat_id, gender)
        return

    # ===== CHAT =====
    if chat_id in active:
        send(active[chat_id], text)
        return

# ===== RUN =====
offset = None
while True:
    data = get_updates(offset)
    for u in data["result"]:
        offset = u["update_id"] + 1
        handle(u)
    time.sleep(1)
