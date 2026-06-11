from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import socket
import struct
import time
import signal
import sys

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


class BaseDevice:

    def __init__(self, device_id, device_type, location, http_port, device_description):

        self.device_id = device_id
        self.device_type = device_type
        self.location = location
        self.http_port = http_port
        self.device_description = device_description

    def log(self, message):
        print(f"[{self.device_id}] {message}")

    def start_http(self):

        description = self.device_description

        class Handler(BaseHTTPRequestHandler):

            def log_message(self, format, *args):
                pass

            def do_GET(inner_self):

                if inner_self.path == "/device.json":

                    inner_self.send_response(200)
                    inner_self.send_header("Content-type", "application/json")
                    inner_self.end_headers()

                    inner_self.wfile.write(description.encode())

        threading.Thread(target=lambda:
            HTTPServer(
                ("localhost", self.http_port),
                Handler
            ).serve_forever(),
            daemon=True
        ).start()

        self.log(f"HTTP server started on port {self.http_port}")

    def send_notify(self, sock):

        msg = (
        f"NOTIFY * HTTP/1.1\n"
        f"HOST: {MULTICAST_IP}:{PORT}\n"
        f"CACHE-CONTROL: max-age=30\n"
        f"NT: urn:project-iot:{self.device_type}\n"
        f"NTS: ssdp:alive\n"
        f"USN: project-iot:{self.device_id}\n"
        f"LOCATION: {self.location}\n\n"
        )

        sock.sendto(msg.encode(),(MULTICAST_IP,PORT))
        self.log("Alive notification sent")

    def send_byebye(self, sock):
        msg = f"""NOTIFY * HTTP/1.1
        HOST: {MULTICAST_IP}:{PORT}
        NT: urn:project-iot:{self.device_type}
        NTS: ssdp:byebye
        USN: project-iot:{self.device_id} 

        """

        sock.sendto(msg.encode(),(MULTICAST_IP,PORT))

        self.log("Byebye notification sent")

    def handle_search(self,sock):

        while True:

            data, addr = sock.recvfrom(1024)

            text = data.decode(errors = "ignore")

            headers = parse_ssdp_message(text)

            #print(headers)

            if (text.startswith("M-SEARCH") and headers.get("MAN") == '"ssdp:discover"' and headers.get("ST") == "urn:project-iot:device"):

                self.log("MAN validation passed")

                response = (
                    f"HTTP/1.1 200 OK\n"
                    f"ST: urn:project-iot:{self.device_type}\n"
                    f"USN: project-iot:{self.device_id}\n"
                    f"LOCATION: {self.location}\n\n"
                )

                self.log("Discovery request received")

                sock.sendto(response.encode(), addr)
                
                self.log("Discovery response sent")

    def create_ssdp_socket(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)

        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except:
            pass

        sock.bind(("", PORT))

        mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_IP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP,socket.IP_ADD_MEMBERSHIP,mreq)

        return sock
    
    def start(self):

        sock = self.create_ssdp_socket()

        def singal_handler(sig, frame):
            self.shutdown(sock)

        signal.signal(signal.SIGINT, singal_handler)

        self.start_http()

        time.sleep(0.5)

        self.send_notify(sock)

        threading.Thread(target=self.send_alive_periodically, args=(sock,),daemon=True).start()

        self.handle_search(sock)

    def shutdown(self, sock):

        self.log("Shutting down...")

        self.send_byebye(sock)

        time.sleep(0.2)

        sys.exit(0)

    def send_alive_periodically(self, sock):

        while True:

            time.sleep(15)

            self.send_notify(sock)





        
        
