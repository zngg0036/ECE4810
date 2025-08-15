import requests
import time
import datetime
import RPi.GPIO as GPIO
import json

# ---------------- CONFIG ----------------
MASTER_SERVER = "http://192.168.137.119:5000/update"  # Change to Master Pi IP
FIELD_NUMBER = 2  # Change 1–4 for each Pi
LOCATION_NAME = {
    1: "Entrance",
    2: "Corridor",
    3: "Workbench A",
    4: "Exit"
}[FIELD_NUMBER]

TRIGGER_PIN = 7
ECHO_PIN = 11
READ_INTERVAL = 1  # seconds
# ----------------------------------------

def measure_distance():
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
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIGGER_PIN, False)

def send_to_master(distance):
    try:
        requests.post(MASTER_SERVER, json={
            "field": FIELD_NUMBER,
            "location": LOCATION_NAME,
            "distance": distance
        }, timeout=5)
        print(f"[Sent to Master] {LOCATION_NAME}: {distance} cm")
    except Exception as e:
        print(f"[Error sending to Master] {e}")

# ---------------- MAIN ----------------
try:
    setup_gpio()
    time.sleep(2)
    while True:
        dist = measure_distance()
        send_to_master(dist)
        time.sleep(READ_INTERVAL)
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()
