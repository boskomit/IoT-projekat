from devices.base_device import BaseDevice

DEVICE_ID = "thermostat_actuator"
LOCATION = "http://localhost:8006/device.json"

device = BaseDevice(
    device_id= DEVICE_ID,
    device_type="actuator",
    location=LOCATION,
    http_port=8006,
    device_description="""
    {
        "id":"thermostat_actuator",
        "type":"actuator"
    }
    """
)

device.start()