from devices.base_device import BaseDevice

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

device.start()