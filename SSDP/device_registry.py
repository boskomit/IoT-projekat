import time

class DeviceRegistry:

    def __init__(self):
        self.devices = {}

    def register(self, usn, info, max_age = 30):
        self.devices[usn] = {
            "info" : info,
            "last_seen" : time.time(),
            "max_age" : max_age
        }

    def update_last_seen(self, usn):
        if usn in self.devices:
            self.devices[usn]["last_seen"] = time.time()

    def remove(self, usn):
        self.devices.pop(usn,None)

    def exists(self, usn):
        return usn in self.devices
    
    def get(self,usn):
        return self.devices.get(usn)
    
    def get_all(self):
        return self.devices

    def get_expired(self):
        now = time.time()

        return [usn for usn,device in self.devices.items() if now - device["last_seen"] > device["max_age"]]    