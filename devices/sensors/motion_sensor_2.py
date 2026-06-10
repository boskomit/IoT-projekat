from devices.base_device import BaseDevice

DEVICE_ID = "motion_sensor_2"
LOCATION = "http://localhost:8002/device.json"

device = BaseDevice(
    device_id= DEVICE_ID,
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

device.start()