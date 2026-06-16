import json
from devices.base_device import BaseDevice

DEVICE_ID = "thermostat_actuator"
LOCATION = "http://localhost:8006/device.json"

class ThermostatActuator(BaseDevice):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = "OFF"  # Početni režim rada termostata

    def handle_actuator_command(self, topic, payload):
        if payload in ["HEAT", "COOL", "OFF"]:
            self.state = payload
            self.log(f"FIZIČKA AKCIJA -> Režim termostata promenjen na: **{self.state}**")
        else:
            self.log(f"Greška: Primljena nepoznata komanda za termostat: {payload}")

device = ThermostatActuator(
    device_id=DEVICE_ID,
    device_type="actuator",
    location=LOCATION,
    http_port=8006,
    device_description='{"id":"thermostat_actuator", "type":"actuator"}'
)

device.start()