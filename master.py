from flask import Flask, request
import requests
import threading
import time
import datetime
import RPi.GPIO as GPIO
import socket

# ---------------- CONFIG ----------------
THINGSPEAK_API_KEY = "M6LCG3VQELFY9JG4"
TELEGRAM_TOKEN = "8293759891:AAE3pE6bSDvyJvoAwAZPZ6DAeo9zURCQlbo"
TELEGRAM_CHAT_ID = "1443462038"
THRESHOLD_DISTANCE = 20       # cm
ALERT_INTERVAL = 10           # seconds between alerts
UPDATE_INTERVAL = 15          # ThingSpeak minimum interval
TRIGGER_PIN = 7
ECHO_PIN = 11
MAX_DISTANCE = 150            # cm, outlier filter
# ----------------------------------------

app = Flask(__name__)
readings = {1: None, 2: None, 3: None, 4: None}
locations = {1: "Entrance", 2: "Corridor", 3: "Workbench A", 4: "Exit"}
last_alert_time = 0


# ------------ FLASK ENDPOINT ------------
@app.route("/update", methods=["POST"])
def update():
    data = request.get_json()
    field = int(data.get("field"))
    distance = data.get("distance")
    readings[field] = distance
    print(f"[Data Received] {locations[field]}: {distance} cm")
    return "OK", 200


# ------------ ULTRASONIC ------------
def setup_gpio():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIGGER_PIN, False)


def measure_distance():
    GPIO.output(TRIGGER_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIGGER_PIN, False)

    pulse_start = time.time()
    pulse_end = time.time()

    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)


# ------------ BACKGROUND THREADS ------------
def local_sensor_loop():
    """Reads from master's own ultrasonic sensor for Field 3."""
    while True:
        distance = measure_distance()
        if distance > MAX_DISTANCE:
            print("[Workbench A] Outlier detected:", distance)
        else:
            readings[3] = distance
            print(f"[Workbench A] Distance: {distance} cm")
        time.sleep(1)  # Sensor read frequency


def send_to_thingspeak():
    global last_alert_time
    while True:
        if any(v is not None for v in readings.values()):
            # ✅ Wait a few seconds to allow slave data to arrive
            print("[ThingSpeak] Waiting 3s for all slave data...")
            time.sleep(3)

            params = {"api_key": THINGSPEAK_API_KEY}
            for field, value in readings.items():
                if value is not None:
                    params[f"field{field}"] = value

            try:
                r = requests.get("https://api.thingspeak.com/update", params=params, timeout=5)
                print("[ThingSpeak] Response:", r.text)
            except Exception as e:
                print("[ThingSpeak] Error:", e)

            # Alerts
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


# ------------ TELEGRAM ALERTS ------------
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
        print("[Telegram] Message sent")
    except Exception as e:
        print("[Telegram] Error:", e)


# ------------ MAIN ------------
if __name__ == "__main__":
    setup_gpio()
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"🌐 Master Pi running on: http://{local_ip}:5000")

    threading.Thread(target=local_sensor_loop, daemon=True).start()
    threading.Thread(target=send_to_thingspeak, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
