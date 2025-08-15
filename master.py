from flask import Flask, request
import requests
import threading
import time
import datetime

# ---------------- CONFIG ----------------
THINGSPEAK_API_KEY = "YOUR_WRITE_KEY"
TELEGRAM_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"
THRESHOLD_DISTANCE = 20
ALERT_INTERVAL = 10
UPDATE_INTERVAL = 15  # ThingSpeak rate limit
# ----------------------------------------

app = Flask(__name__)
readings = {1: None, 2: None, 3: None, 4: None}
locations = {1: "Entrance", 2: "Corridor", 3: "Workbench A", 4: "Exit"}
last_alert_time = 0

@app.route("/update", methods=["POST"])
def update():
    data = request.get_json()
    field = int(data.get("field"))
    distance = data.get("distance")
    readings[field] = distance
    print(f"[Data Received] {locations[field]}: {distance} cm")
    return "OK", 200

def send_to_thingspeak():
    while True:
        if any(v is not None for v in readings.values()):
            params = {"api_key": THINGSPEAK_API_KEY}
            for field, value in readings.items():
                if value is not None:
                    params[f"field{field}"] = value
            try:
                r = requests.get("https://api.thingspeak.com/update", params=params, timeout=5)
                print("[ThingSpeak] Response:", r.text)
            except Exception as e:
                print("[ThingSpeak] Error:", e)

            # Check alerts for all fields
            global last_alert_time
            now = time.time()
            for field, value in readings.items():
                if value is not None and 0 < value < THRESHOLD_DISTANCE:
                    if now - last_alert_time > ALERT_INTERVAL:
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        message = (f"🚨 Motion Detected!\n"
                                   f"📍 Location: {locations[field]}\n"
                                   f"📏 Distance: {value} cm\n"
                                   f"🕒 Time: {timestamp}")
                        send_to_telegram(message)
                        last_alert_time = now
        time.sleep(UPDATE_INTERVAL)

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
        print("[Telegram] Message sent")
    except Exception as e:
        print("[Telegram] Error:", e)

if __name__ == "__main__":
    threading.Thread(target=send_to_thingspeak, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
