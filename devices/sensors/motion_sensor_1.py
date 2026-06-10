from devices.base_device import BaseDevice

DEVICE_ID = "motion_sensor_1"
LOCATION = "http://localhost:8001/device.json"

device = BaseDevice(
    device_id= DEVICE_ID,
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

device.start()