import json
from devices.base_device import BaseDevice

DEVICE_ID = "light_actuator"
LOCATION = "http://localhost:8005/device.json"

# Pravimo klasu koja nasleđuje BaseDevice kako bismo joj dodali stanje svetla
class LightActuator(BaseDevice):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = "OFF"  # Početno stanje svetla

    def handle_actuator_command(self, topic, payload):
        # Validacija i izvršavanje komande
        if payload in ["ON", "OFF"]:
            self.state = payload
            self.log(f"FIZIČKA AKCIJA -> Prekidač prebačen! Svetlo je sada: **{self.state}**")
        else:
            self.log(f"Greška: Primljena nepoznata komanda za svetlo: {payload}")

# Instanciramo našu novu klasu aktuatora
device = LightActuator(
    device_id=DEVICE_ID,
    device_type="actuator",
    location=LOCATION,
    http_port=8005,
    device_description='{"id":"light_actuator", "type":"actuator"}'
)

device.start()