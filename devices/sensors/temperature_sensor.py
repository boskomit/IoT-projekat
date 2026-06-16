import threading
import time
import random
from devices.base_device import BaseDevice

# ... ostatak tvog koda za temperaturu ostaje isti

DEVICE_ID = "temperature_sensor"
LOCATION = "http://localhost:8003/device.json"

device = BaseDevice(
    device_id= DEVICE_ID,
    device_type="sensor",
    location=LOCATION,
    http_port=8003,
    device_description="""
    {
        "id":"temperature_sensor",
        "type":"sensor"
    }
    """
)

def simulate_temperature():
    # Kratka pauza da se uređaj prvo uspešno poveže na MQTT
    time.sleep(2)
    current_temp = 22.0
    
    while True:
        # Simuliramo blago variranje temperature
        current_temp += random.uniform(-0.4, 0.4)
        current_temp = round(current_temp, 1)
        
        payload = {"temperature": current_temp}
        
        # Slanje na topik sa QoS 0 (zahtev ARCH 4)
        device.publish_data("home/temp/current", payload, qos=0)
        
        # Šalje novo stanje svakih 8 sekundi
        time.sleep(8)

# Pokrećemo simulaciju u pozadinskoj niti pre blokirajućeg start-a
threading.Thread(target=simulate_temperature, daemon=True).start()

device.start()