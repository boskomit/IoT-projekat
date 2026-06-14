from devices.base_device import BaseDevice

DEVICE_ID = "blinds_actuator"
LOCATION = "http://localhost:8004/device.json"

device = BaseDevice(
    device_id= DEVICE_ID,
    device_type="actuator",
    location=LOCATION,
    http_port=8004,
    device_description="""
    {
        "id":"blinds_actuator",
        "type":"actuator"
    }
    """
)

device.start()