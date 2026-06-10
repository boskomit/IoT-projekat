from devices.base_device import BaseDevice

DEVICE_ID = "light_actuator"
LOCATION = "http://localhost:8005/device.json"

device = BaseDevice(
    device_id= DEVICE_ID,
    device_type="actuator",
    location=LOCATION,
    http_port=8005,
    device_description="""
    {
        "id":"light_actuator",
        "type":"actuator"
    }
    """
)

device.start()