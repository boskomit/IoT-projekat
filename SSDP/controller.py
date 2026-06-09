import socket
import requests
import struct
import time
import threading

MULTICAST_IP = "239.255.255.250"
PORT = 1900

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
ST: ssdp:all
MAN: "ssdp:discover"
MX: 2

"""
print("\n--- SENT M-SEARCH ---")
print(msg)

#sock.sendto(msg.encode(), (MULTICAST_IP, PORT))

print("Searching for devices...\n")

def send_search():
    while True:
        print("\n--- SENT M-SEARCH ---")
        print(msg)

        sock.sendto(msg.encode(), (MULTICAST_IP, PORT))
        time.sleep(5)   # svakih 5 sekundi

threading.Thread(target=send_search, daemon=True).start()

while True:
    data, addr = sock.recvfrom(1024)
    text = data.decode(errors="ignore")

    print("\n--- RECEIVED ---")
    print(text)

    # HANDLE BYEBYE
    if "ssdp:byebye" in text:
        for line in text.split("\n"):
            if "USN" in line:
                device_id = line.split(": ", 1)[1].strip()
                if device_id in devices:
                    print(f"\nDevice OFFLINE: {device_id}")
                    del devices[device_id]
                    print("Devices:", list(devices.keys()))

    # HANDLE ALIVE / RESPONSE
    if "LOCATION" in text:
        location = None
        usn = None

        for line in text.split("\n"):
            if "LOCATION" in line:
                location = line.split(": ", 1)[1].strip()
            if "USN" in line:
                usn = line.split(": ", 1)[1].strip()

        if location and usn and usn not in devices:
            print(f"\nFound device: {usn} at {location}")

            try:
                r = requests.get(location, timeout=2)
                info = r.json()

                devices[info["id"]] = info

                print("Registered:", info)
                print("Devices:", list(devices.keys()))

            except Exception as e:
                print("Failed:", e)
        elif usn in devices:
            print(f"Already known device: {usn}")