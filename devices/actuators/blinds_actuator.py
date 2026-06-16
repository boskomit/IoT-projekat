import json
from devices.base_device import BaseDevice

DEVICE_ID = "blinds_actuator"
LOCATION = "http://localhost:8004/device.json"

class BlindsActuator(BaseDevice):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = "UP"  # Početno stanje roletni (podignute)

    def handle_actuator_command(self, topic, payload):
        if payload in ["UP", "DOWN", "STOP"]:
            self.state = payload
            self.log(f"FIZIČKA AKCIJA -> Motor pokrenut! Roletne idu: **{self.state}**")
        else:
            self.log(f"Greška: Primljena nepoznata komanda za roletne: {payload}")

device = BlindsActuator(
    device_id=DEVICE_ID,
    device_type="actuator",
    location=LOCATION,
    http_port=8004,
    device_description='{"id":"blinds_actuator", "type":"actuator"}'
)

device.start()