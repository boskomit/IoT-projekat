import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import struct
import time

MULTICAST_IP = "239.255.255.250"
PORT = 1900

DEVICE_ID = "temperature_sensor"
LOCATION = "http://localhost:8003/device.json"

# --- HTTP server ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/device.json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'''
{
  "id": "temperature_sensor",
  "type": "sensor",
  "mqtt_topic": "home/temp/current"
}
''')

def start_http():
    print("[temperature] HTTP on 8003")
    HTTPServer(("localhost", 8003), Handler).serve_forever()

# --- SSDP ---
def send_notify(sock):
    msg = f"""NOTIFY * HTTP/1.1
HOST: {MULTICAST_IP}:{PORT}
NTS: ssdp:alive
USN: {DEVICE_ID}
LOCATION: {LOCATION}

"""
    sock.sendto(msg.encode(), (MULTICAST_IP, PORT))
    print("\n[temperature] SENT NOTIFY")
    print(msg)

def send_byebye(sock):
    msg = f"""NOTIFY * HTTP/1.1
HOST: {MULTICAST_IP}:{PORT}
NTS: ssdp:byebye
USN: {DEVICE_ID}

"""
    sock.sendto(msg.encode(), (MULTICAST_IP, PORT))
    print("\n[temperature] SENT BYEBYE")
    print(msg)

def listen(sock):
    while True:
        data, addr = sock.recvfrom(1024)
        text = data.decode(errors="ignore")

        if "M-SEARCH" in text:
            print("\n[temperature] RECEIVED M-SEARCH")

            response = f"""HTTP/1.1 200 OK
USN: {DEVICE_ID}
LOCATION: {LOCATION}

"""
            sock.sendto(response.encode(), addr)
            print("[temperature] SENT RESPONSE")
            print(response)

# --- MAIN ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except:
    pass

sock.bind(("", PORT))

mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_IP), socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

threading.Thread(target=start_http, daemon=True).start()

try:
    time.sleep(1)
    send_notify(sock)
    listen(sock)
except KeyboardInterrupt:
    send_byebye(sock)
    print("temperature shutting down")