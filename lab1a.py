import requests
import time
import datetime
import RPi.GPIO as GPIO

# ---------------- CONFIG ----------------
THINGSPEAK_API_KEY = "M6LCG3VQELFY9JG4"  # Replace with your API key
FIELD_NUMBER = 2  # Change 1, 2, 3, or 4 for each Pi
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
THRESHOLD_DISTANCE = 50  # cm
READ_INTERVAL = 15  # seconds between ThingSpeak updates
ALERT_INTERVAL = 30  # seconds before re-sending an alert
# ----------------------------------------

last_alert_time = 0

def send_to_thingspeak(distance):
    """Send distance reading to ThingSpeak."""
    url = f"https://api.thingspeak.com/update"
    params = {"api_key": THINGSPEAK_API_KEY, f"field{FIELD_NUMBER}": distance}
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"[ThingSpeak] Response: {response.text}")
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

    while True:
        distance = measure_distance()
        
        # Outlier check
        if distance > 150:
            print(f"[{LOCATION_NAME}] Outlier detected: {distance} cm")
        else:
            print(f"[{LOCATION_NAME}] Distance: {distance} cm")
            send_to_thingspeak(distance)
    
            # Send alert if person detected
            if 0 < distance < THRESHOLD_DISTANCE:
                now = time.time()
                if now - last_alert_time > ALERT_INTERVAL:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    message = (f"🚨 Motion Detected!\n"
                               f"📍 Location: {LOCATION_NAME}\n"
                               f"📏 Distance: {distance} cm\n"
                               f"🕒 Time: {timestamp}")
                    send_to_telegram(message)
                    last_alert_time = now
    
        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("Exiting program...")
finally:
    GPIO.cleanup()
