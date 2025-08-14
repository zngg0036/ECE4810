import requests
import time
import datetime
import RPi.GPIO as GPIO

# ---------------- CONFIG ----------------
THINGSPEAK_API_KEY = "M6LCG3VQELFY9JG4"
TELEGRAM_TOKEN = "8293759891:AAE3pE6bSDvyJvoAwAZPZ6DAeo9zURCQlbo"
TELEGRAM_CHAT_ID = "1443462038"

# Ultrasonic Sensor 1 (Front)
TRIG1 = 7
ECHO1 = 11

# Ultrasonic Sensor 2 (Side)
TRIG2 = 13
ECHO2 = 15

# Output devices
LED_RED = 29
LED_GREEN = 31
LED_YELLOW = 33
BUZZER = 36
BUTTON = 37

THRESHOLD_DISTANCE = 50  # cm
PRESENCE_DURATION = 10   # seconds
READ_INTERVAL = 3        # seconds
ALERT_INTERVAL = 30      # seconds

# ----------------------------------------
last_alert_time = 0
presence_start_time = None

def send_to_thingspeak(dist1, dist2):
    """Send both distances to ThingSpeak."""
    url = "https://api.thingspeak.com/update"
    params = {
        "api_key": THINGSPEAK_API_KEY,
        "field1": dist1,
        "field2": dist2
    }
    try:
        r = requests.get(url, params=params, timeout=5)
        print(f"[ThingSpeak] Response: {r.text}")
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

def measure_distance(TRIG, ECHO, timeout=0.02):
    """Measure distance from ultrasonic sensor."""
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if pulse_start - timeout_start > timeout:
            return -1  # Timeout, no echo received

    pulse_end = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if pulse_end - timeout_start > timeout:
            return -1  # Timeout, echo too long

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)

def setup_gpio():
    """Setup GPIO pins."""
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    # Setup ultrasonic pins
    for trig, echo in [(TRIG1, ECHO1), (TRIG2, ECHO2)]:
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        GPIO.output(trig, False)

    # Outputs
    GPIO.setup(LED_RED, GPIO.OUT)
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_YELLOW, GPIO.OUT)
    GPIO.setup(BUZZER, GPIO.OUT)


    # Button
    GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.output(LED_GREEN, False)
    GPIO.output(LED_YELLOW, False)
    GPIO.output(LED_RED, False)

def trigger_alert(dist1, dist2):

    print("No button press - RED LED and buzzer ON.")
    GPIO.output(LED_GREEN, False)
    GPIO.output(LED_RED, True)
    pwm = GPIO.PWM(BUZZER, 1000)  # 1 kHz tone
    pwm.start(90)                  # 50% duty cycle
    time.sleep(5)
    pwm.stop()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = (f"🚨 Intruder Detected!\n"
            f"📏 Sensor 1: {dist1} cm\n"
            f"📏 Sensor 2: {dist2} cm\n"
            f"🕒 Time: {timestamp}\n")
    send_to_telegram(message)

# ---------------- MAIN ----------------
try:
    setup_gpio()
    print("Starting dual sensor monitoring...")
    time.sleep(2)  # allow sensors to settle
    button_pressed_flag = False
    
    while True:
        
        # Inside main loop:
        if GPIO.input(BUTTON) == GPIO.LOW:
            print("Button pressed - Stopping Alert")
            GPIO.output(LED_GREEN, True)
            GPIO.output(LED_YELLOW, False)
            GPIO.output(LED_RED, False)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = (f"Car Unlocked :3\n"
                    f"🕒 Time: {timestamp}\n")
            send_to_telegram(message)
            break

        dist1 = measure_distance(TRIG1, ECHO1)
        dist2 = measure_distance(TRIG2, ECHO2)

        print(f"[Sensor1] {dist1} cm | [Sensor2] {dist2} cm")
        send_to_thingspeak(dist1, dist2)

        # Check presence on both sensors
        if (0 < dist1 < THRESHOLD_DISTANCE) or (0 < dist2 < THRESHOLD_DISTANCE):
            if presence_start_time is None:
                presence_start_time = time.time()
            elif time.time() - presence_start_time >= PRESENCE_DURATION:
                now = time.time()
                if now - last_alert_time > ALERT_INTERVAL:
                    # When you call trigger_alert():
                    trigger_alert(dist1, dist2)
                    last_alert_time = now
        else:
            # Reset if no one is detected
            presence_start_time = None
            GPIO.output(LED_RED, False)
            GPIO.output(LED_GREEN, False)
            GPIO.output(LED_YELLOW, True)

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("Exiting program...")
finally:
    GPIO.cleanup()
