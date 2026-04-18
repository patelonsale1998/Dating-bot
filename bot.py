import requests
import time

# ===== CONFIG =====
TOKEN = "8450433036:AAFmuzOeD1NzN5hdQM7puEzDq9Om7ihJ3bk"
ADMIN_ID = 123456789
URL = f"https://api.telegram.org/bot{TOKEN}/"

# ===== STORAGE =====
users = {}
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

# ===== GET UPDATES =====
def get_updates(offset=None):
    return requests.get(URL + "getUpdates", params={"timeout": 100, "offset": offset}).json()

# ===== MATCH SYSTEM =====
def match(user_id):
    u = users[user_id]
    queue = queue_female if u["gender"] == "male" else queue_male

    if queue:
        partner = queue.pop(0)

        active[user_id] = partner
        active[partner] = user_id

        send(user_id, "❤️ Matched!")
        send(partner, "❤️ Matched!")
    else:
        queue.append(user_id)
        send(user_id, "🔎 Searching partner...")

# ===== HANDLE =====
def handle(update):
    m = update.get("message")
    if not m:
        return

    chat_id = m["chat"]["id"]
    text = m.get("text", "")

    # ===== ADMIN =====
    if chat_id == ADMIN_ID:
        if text == "/admin":
            send(chat_id, "/users /active /stats")
            return

        if text == "/users":
            send(chat_id, str(users))
            return

        if text == "/active":
            send(chat_id, str(active))
            return

        if text == "/stats":
            send(chat_id, f"Users: {len(users)}")
            return

    # ===== START =====
    if text == "/start":
        users[chat_id] = {
            "state": "gender",
            "name": m["from"].get("first_name")
        }
        send(chat_id, "👤 Male or Female?")
        return

    # ===== PROFILE CARD =====
    if text == "/profile":
        u = users.get(chat_id, {})
        caption = f"""
👤 {u.get('name')}
🎂 {u.get('age')}
🏙 {u.get('city')}
⚧ {u.get('gender')}
"""
        if u.get("photo"):
            send_photo(chat_id, u["photo"], caption)
        else:
            send(chat_id, caption)
        return

    # ===== CHAT =====
    if chat_id in active:
        send(active[chat_id], text)
        return

    if chat_id not in users:
        return

    state = users[chat_id]["state"]

    # ===== GENDER =====
    if state == "gender":
        users[chat_id]["gender"] = text.lower()
        users[chat_id]["state"] = "age"
        send(chat_id, "🎂 Enter age")
        return

    # ===== AGE =====
    if state == "age":
        users[chat_id]["age"] = text
        users[chat_id]["state"] = "city"
        send(chat_id, "🏙 Enter city")
        return

    # ===== CITY =====
    if state == "city":
        users[chat_id]["city"] = text
        users[chat_id]["state"] = "photo"
        send(chat_id, "📸 Send photo")
        return

    # ===== PHOTO =====
    if "photo" in m and state == "photo":
        users[chat_id]["photo"] = m["photo"][-1]["file_id"]
        users[chat_id]["state"] = "done"
        match(chat_id)
        return

# ===== LOOP =====
offset = None
while True:
    data = get_updates(offset)
    for u in data["result"]:
        offset = u["update_id"] + 1
        handle(u)
    time.sleep(1)
