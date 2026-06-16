import threading
import time
from devices.base_device import BaseDevice

DEVICE_ID = "motion_sensor_1"
LOCATION = "http://localhost:8001/device.json"

device = BaseDevice(
    device_id=DEVICE_ID,
    device_type="sensor",
    location=LOCATION,
    http_port=8001,
    device_description="""
    {
        "id":"motion_sensor_1",
        "type":"sensor"
    }
    """
)

def simulate_motion_input():
    time.sleep(2)
    print(f"\n[{DEVICE_ID}] >>> NAPREDNI INTERAKTIVNI MOD <<<")
    print("Komande za kucanje:")
    print("  - w + ENTER         -> ULAZAK 1 osobe")
    print("  - SPACE + w + ENTER -> ULAZAK 2 osobe")
    print("  - s + ENTER         -> IZLAZAK 1 osobe")
    print("  - SPACE + s + ENTER -> IZLAZAK 2 osobe")
    
    while True:
        user_input = input() # Čeka unos i ENTER
        
        # Mapiranje tvojih komandi na događaje i broj ljudi
        if user_input == "w":
            event, count = "ulazak", 1
        elif user_input == " w":
            event, count = "ulazak", 2
        elif user_input == "s":
            event, count = "izlazak", 1
        elif user_input == " s":
            event, count = "izlazak", 2
        else:
            print(f"[{DEVICE_ID}] Nepoznata komanda! Unesi: w, ' w', s ili ' s'")
            continue

        payload = {
            "event": event,
            "people_count": count
        }

        # Publikuje na svoj topik sensor1
        device.publish_data("home/door/sensor1", payload, qos=1)

threading.Thread(target=simulate_motion_input, daemon=True).start()

device.start()