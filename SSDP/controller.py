import socket
import requests
import struct
import time
import threading

def log(message):
    print(f"[CONTROLLER] {message}")

def separator():
    print("-" * 40)

def device_registered(info):

    separator()

    log(f"Registered: {info['id']}")

    show_devices()

    separator()

def show_devices():

    print( f"\n[CONTROLLER] Active devices ({len(devices)}):")

    if not devices:
        print("  (none)")
        return

    for usn, info in devices.items():
        print(f"  - {info['id']}")

MULTICAST_IP = "239.255.255.250"
PORT = 1900

def parse_ssdp_message(text):

    headers = {}

    for line in text.splitlines():

        line = line.strip()

        if ": " in line:

            key, value = line.split(": ", 1)

            headers[key] = value

    return headers

devices = {}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except:
    pass

sock.bind(("", PORT))

# join multicast group
mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_IP), socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

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

        sock.sendto(msg.encode(), (MULTICAST_IP, PORT))
        time.sleep(5)   # svakih 5 sekundi

threading.Thread(target=send_search, daemon=True).start()

while True:
    data, addr = sock.recvfrom(1024)
    text = data.decode(errors="ignore")

    if text.startswith("M-SEARCH"):
        continue

    if("project-iot:" not in text and "urn:project-iot:" not in text):
        continue

    #print("\n--- RECEIVED ---")
    #print(text)

    # HANDLE BYEBYE
    if "ssdp:byebye" in text:

        headers = parse_ssdp_message(text)

        usn = headers.get("USN")
        device_id = headers.get("device_id")

        if usn and usn in devices:

            log(f"Device offline: {device_id}")
            del devices[usn]
            show_devices()

    # HANDLE ALIVE / RESPONSE
    if "LOCATION" in text:

        headers = parse_ssdp_message(text)

        location = headers.get("LOCATION")
        usn = headers.get("USN")

        if not location or not usn:
            continue

        if usn in devices:
            continue

        log(f"Device discovered: {usn}")

        success = False

        for attempt in range(3):

            try:

                r = requests.get(location, timeout=2)

                info = r.json()

                devices[usn] = info

                device_registered(info)
                

                success = True
                break

            except Exception:

                print(
                    f"[CONTROLLER] "
                    f"Connection attempt {attempt + 1}/3 failed"
                )

                time.sleep(1)

        if not success:

            print(
                f"[CONTROLLER] "
                f"Failed to register {usn}"
            )

