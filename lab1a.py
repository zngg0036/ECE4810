import requests
import time
import datetime
import RPi.GPIO as GPIO
import json

# ---------------- CONFIG ----------------
THINGSPEAK_API_KEY = "M6LCG3VQELFY9JG4"  # ThingSpeak Write API Key
FIELD_NUMBER = 2  # Change this per Raspberry Pi (1-4)

LOCATION_NAME = {
    1: "Entrance",
    2: "Corridor",
    3: "Workbench A",
    4: "Exit"
}[FIELD_NUMBER]

TELEGRAM_TOKEN = "8293759891:AAE3pE6bSDvyJvoAwAZPZ6DAeo9zURCQlbo"
TELEGRAM_CHAT_ID = "1443462038"

TRIGGER_PIN = 7
ECHO_PIN = 11
THRESHOLD_DISTANCE = 20  # cm
READ_INTERVAL = 15       # seconds between sensor readings
SEND_INTERVAL = 15       # seconds between ThingSpeak bulk sends
ALERT_INTERVAL = 10      # seconds before re-sending an alert
# ----------------------------------------

last_alert_time = 0
data_buffer = []  # Store readings before bulk send

def send_bulk_to_thingspeak():
    """Send buffered distance readings to ThingSpeak in bulk JSON."""
    global data_buffer
    if not data_buffer:
        return

    url = "https://api.thingspeak.com/channels/update.json"  # No channel_id needed
    try:
        for entry in data_buffer:
            payload = {
                "api_key": THINGSPEAK_API_KEY,
                f"field{FIELD_NUMBER}": entry[f"field{FIELD_NUMBER}"]
            }
            response = requests.post(url, data=payload, timeout=5)
            print(f"[ThingSpeak] Response: {response.text}")
            if response.status_code != 200:
                print(f"[ThingSpeak] Error sending data: {response.status_code}")
        data_buffer.clear()  # Clear buffer only if successful
    except Exception as e:
        print(f"[ThingSpeak] Error: {e}")

def send_to_telegram(message):
    """Send alert to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
        print("[Telegram] Message sent")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

def measure_distance():
    """Measure distance from ultrasonic sensor."""
    GPIO.output(TRIGGER_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIGGER_PIN, False)

    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)

def setup_gpio():
    """Setup GPIO pins."""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIGGER_PIN, False)

# ---------------- MAIN ----------------
try:
    setup_gpio()
    print(f"Starting sensor at {LOCATION_NAME} (Field {FIELD_NUMBER})")
    time.sleep(2)  # allow sensor to settle

    last_send_time = time.time()
