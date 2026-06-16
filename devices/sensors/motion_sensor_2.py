import threading
import time
from devices.base_device import BaseDevice

DEVICE_ID = "motion_sensor_2"
LOCATION = "http://localhost:8002/device.json"

device = BaseDevice(
    device_id=DEVICE_ID,
    device_type="sensor",
    location=LOCATION,
    http_port=8002,
    device_description="""
    {
        "id":"motion_sensor_2",
        "type":"sensor"
    }
    """
)

def simulate_motion_output():
    time.sleep(2)
    print(f"\n[{DEVICE_ID}] >>> NAPREDNI INTERAKTIVNI MOD <<<")
    print("Komande za kucanje:")
    print("  - w + ENTER         -> ULAZAK 1 osobe")
    print("  - SPACE + w + ENTER -> ULAZAK 2 osobe")
    print("  - s + ENTER         -> IZLAZAK 1 osobe")
    print("  - SPACE + s + ENTER -> IZLAZAK 2 osobe")
    
    while True:
        user_input = input()
        
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

        # Publikuje na svoj topik sensor2
        device.publish_data("home/door/sensor2", payload, qos=1)

threading.Thread(target=simulate_motion_output, daemon=True).start()

device.start()