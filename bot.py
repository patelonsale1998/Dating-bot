import requests
import time
import math
import random

# ===== CONFIG =====
TOKEN = "8450433036:AAFmuzOeD1NzN5hdQM7puEzDq9Om7ihJ3bk"
ADMIN_ID = 123456789#
URL = f"https://api.telegram.org/bot{TOKEN}/"

# ===== DATA =====
users = {}
waiting_male = []
waiting_female = []
active_chats = {}

auto_messages = [
    "Hi 😊",
    "Where are you from?",
    "Tell me about yourself",
    "Nice to meet you 😉"
]

# ===== API =====
def send(chat_id, text):
    requests.post(URL + "sendMessage", data={"chat_id": chat_id, "text": text})

def send_photo(chat_id, file_id):
    requests.post(URL + "sendPhoto", data={"chat_id": chat_id, "photo": file_id})

def get_updates(offset=None):
    r = requests.get(URL + "getUpdates", params={"timeout": 100, "offset": offset})
    return r.json()

# ===== DISTANCE =====
def distance(u1, u2):
    lat1, lon1 = u1["lat"], u1["lon"]
    lat2, lon2 = u2["lat"], u2["lon"]

    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ===== MATCH =====
def connect(u1, u2):
    active_chats[u1] = u2
    active_chats[u2] = u1

    send_photo(u1, users[u2]["photo"])
    send_photo(u2, users[u1]["photo"])

    send(u1, "❤️ Partner found")
    send(u2, "❤️ Partner found")

    send(u1, random.choice(auto_messages))
    send(u2, random.choice(auto_messages))

def try_match(user_id):
    profile = users[user_id]
    queue = waiting_female if profile["gender"] == "male" else waiting_male

    # distance match first
    for partner in queue:
        p = users.get(partner)
        if not p:
            continue
        if distance(profile, p) <= 50:
            queue.remove(partner)
            connect(user_id, partner)
            return True

    # fallback any
    for partner in queue:
        queue.remove(partner)
        connect(user_id, partner)
        return True

    return False

def add_to_queue(user_id):
    if try_match(user_id):
        return
    if users[user_id]["gender"] == "male":
        waiting_male.append(user_id)
    else:
        waiting_female.append(user_id)

# ===== HANDLE =====
def handle(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/myid":
        send(chat_id, str(chat_id))
        return

    # ===== ADMIN PANEL =====
    if chat_id == ADMIN_ID:

        if text == "/admin":
            send(chat_id, "/stats\n/users\n/active\n/waiting")
            return

        if text == "/stats":
            send(chat_id,
                f"Users: {len(users)}\n"
                f"Active chats: {len(active_chats)//2}\n"
                f"Waiting male: {len(waiting_male)}\n"
                f"Waiting female: {len(waiting_female)}"
            )
            return

        if text == "/users":
            msg = "Users:\n"
            for uid, data in users.items():
                msg += f"{uid} | {data.get('gender')} | {data.get('city')}\n"
            send(chat_id, msg[:4000])
            return

        if text == "/active":
            msg = "Active:\n"
            for u, p in active_chats.items():
                msg += f"{u} <-> {p}\n"
            send(chat_id, msg[:4000])
            return

        if text == "/waiting":
            send(chat_id,
                f"Male: {waiting_male}\n"
                f"Female: {waiting_female}"
            )
            return

    # ===== START =====
    if text == "/start":
        users[chat_id] = {
            "state": "gender",
            "username": message["from"].get("username"),
            "name": message["from"].get("first_name")
        }
        send(chat_id, "Male or Female?")
        return

    # ===== NEXT =====
    if text == "/next":
        if chat_id in active_chats:
            partner = active_chats.pop(chat_id)
            active_chats.pop(partner, None)
            send(chat_id, "Searching next...")
            add_to_queue(chat_id)
            add_to_queue(partner)
        return

    # ===== STOP =====
    if text == "/stop":
        if chat_id in active_chats:
            partner = active_chats.pop(chat_id)
            active_chats.pop(partner, None)
            send(chat_id, "Chat stopped")
            send(partner, "Partner left")
        return

    # ===== CHAT =====
    if chat_id in active_chats:
        send(active_chats[chat_id], text)
        return

    if chat_id not in users:
        return

    state = users[chat_id]["state"]

    if state == "gender":
        users[chat_id]["gender"] = text.lower()
        users[chat_id]["state"] = "age"
        send(chat_id, "Enter age")
        return

    if state == "age":
        if not text.isdigit():
            send(chat_id, "Enter valid age")
            return
        users[chat_id]["age"] = int(text)
        users[chat_id]["state"] = "city"
        send(chat_id, "Enter city")
        return

    if state == "city":
        users[chat_id]["city"] = text
        users[chat_id]["state"] = "photo"
        send(chat_id, "Send photo 📸")
        return

    if "photo" in message and state == "photo":
        users[chat_id]["photo"] = message["photo"][-1]["file_id"]
        users[chat_id]["state"] = "location"
        send(chat_id, "Share location 📍")
        return

    if "location" in message and state == "location":
        loc = message["location"]
        users[chat_id]["lat"] = loc["latitude"]
        users[chat_id]["lon"] = loc["longitude"]
        users[chat_id]["state"] = "search"
        send(chat_id, "Searching nearby users...")
        add_to_queue(chat_id)

# ===== LOOP =====
def main():
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates["result"]:
            offset = update["update_id"] + 1
            handle(update)
        time.sleep(1)

if __name__ == "__main__":
    main()
