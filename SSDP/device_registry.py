import threading
import time

class DeviceRegistry:

    def __init__(self):
        self.devices = {}
        self.lock = threading.Lock()

    def register(self, usn, info, max_age = 30):
        with self.lock:
            self.devices[usn] = {
                "info" : info,
                "last_seen" : time.time(),
                "max_age" : max_age
            }

    def update_last_seen(self, usn):
        with self.lock:
            if usn in self.devices:
                self.devices[usn]["last_seen"] = time.time()

    def remove(self, usn):
        with self.lock:
            self.devices.pop(usn,None)

    def exists(self, usn):
        with self.lock:
            return usn in self.devices
    
    def get(self,usn):
        with self.lock:
            device = self.devices.get(usn)
            return device.copy() if device else None
    
    def get_all(self):
        with self.lock:
            return {usn: device.copy() for usn, device in self.devices.items()}

    def get_expired(self):
        with self.lock:
            now = time.time()
            return [
                usn
                for usn, device in self.devices.items()
                if now - device["last_seen"] > device["max_age"]
            ]