import socket
import requests
import struct
import time
import threading
from device_registry import DeviceRegistry

MULTICAST_IP = "239.255.255.250"
PORT = 1900


def log(message):
    print(f"[CONTROLLER] {message}")

def separator():
    print("-" * 40)

def device_registered(info):

    separator()

    log(f"Registered: {info['id']}")

    show_devices()

    separator()

def register_device(usn, location):

    for attempt in range(3):

        try:

            r = requests.get(location, timeout=2)

            info = r.json()

            registry.register(usn, info)

            device_registered(info)

            return True

        except Exception:

            log(
                f"Connection attempt "
                f"{attempt + 1}/3 failed"
            )

            time.sleep(1)

    log(f"Failed to register {usn}")

    return False

def show_devices():

    devices = registry.get_all()

    print( f"\n[CONTROLLER] Active devices ({len(devices)}):")

    if not devices:
        print("  (none)")
        return

    for usn, info in devices.items():
        print(f"  - {info['info']['id']}")

def remove_expired_devices():

    while True:

        for usn in registry.get_expired():

            device = registry.get(usn)

            separator()

            log(
                f"Device timeout: "
                f"{device['info']['id']}"
            )

            registry.remove(usn)

            show_devices()

            separator()

        time.sleep(5)

def parse_ssdp_message(text):

    headers = {}

    for line in text.splitlines():

        line = line.strip()

        if ": " in line:

            key, value = line.split(": ", 1)

            headers[key] = value

    return headers

def receive_search_responses():

    while True:

        try:

            data, addr = search_sock.recvfrom(1024)

            text = data.decode(errors="ignore")

            if "HTTP/1.1 200 OK" in text:

                print("DISCOVERY RESPONSE RECEIVED")

                headers = parse_ssdp_message(text)

                location = headers.get("LOCATION")
                usn = headers.get("USN")

                if not location or not usn:
                    continue

                if usn in registry.get_all():
                    continue

                log(f"Device discovered: {usn}")

                register_device(usn,location)

        except socket.timeout:
            pass


# DEVICES KEPT HERE
registry = DeviceRegistry()

# SOCKET FOR ALIVE AND BYEBYE
listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except:
    pass

listen_sock.bind(("", PORT))

# join multicast group
mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_IP), socket.INADDR_ANY)
listen_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

# SOCKET FOR SEARCH MESSAGES AND RESPONSES
search_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
search_sock.settimeout(2)

# send M-SEARCH
msg = """M-SEARCH * HTTP/1.1
HOST: 239.255.255.250:1900
ST: urn:project-iot:device
MAN: "ssdp:discover"
MX: 2

"""

print("\n" + "=" * 40)
print("      IoT SSDP Controller")
print("=" * 40)

show_devices()

def send_search():
    while True:
        log("Searching for IoT devices...")
        #show_devices()

        search_sock.sendto(msg.encode(), (MULTICAST_IP, PORT))
        time.sleep(5)   # svakih 5 sekundi

threading.Thread(target=send_search, daemon=True).start()
threading.Thread(target=remove_expired_devices, daemon=True).start()
threading.Thread(target=receive_search_responses, daemon=True).start()

while True:
    data, addr = listen_sock.recvfrom(1024)
    text = data.decode(errors="ignore")

    if text.startswith("M-SEARCH"):
        continue

    if("project-iot:" not in text and "urn:project-iot:" not in text):
        continue

    # HANDLE BYEBYE
    if "ssdp:byebye" in text:

        headers = parse_ssdp_message(text)

        usn = headers.get("USN")

        if usn and usn in registry.get_all():

            device = registry.get(usn)

            separator()

            log(f"Device offline: {device['info']['id']}")
            registry.remove(usn)
            show_devices()

            separator()

    # HANDLE ALIVE

    if "ssdp:alive" in text:

        headers = parse_ssdp_message(text)

        usn = headers.get("USN")

        if usn in registry.get_all():

            registry.update_last_seen(usn)
        
        continue


