from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import socket
import struct
import time
import signal
import sys
#mqtt broker importi
import paho.mqtt.client as mqtt
import json

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
        self.mqtt_client = mqtt.Client(client_id=self.device_id)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

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
        
        msg = (
            f"NOTIFY * HTTP/1.1\n"
            f"HOST: {MULTICAST_IP}:{PORT}\n"
            f"NT: urn:project-iot:{self.device_type}\n"
            f"NTS: ssdp:byebye\n"
            f"USN: project-iot:{self.device_id}\n\n"
        )

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

        self.start_mqtt()

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

    # Dodaj ove nove metode unutar BaseDevice klase:
    def start_mqtt(self):
        try:
            self.log("Connecting to MQTT Broker...")
            self.mqtt_client.connect("localhost", 1883, 60)
            self.mqtt_client.loop_start()  # Pokreće MQTT petnju u pozadinskoj niti
        except Exception as e:
            self.log(f"MQTT Connection failed: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log("Connected to MQTT Broker!")
            # Automatska pretplata za aktuatore (QoS 1)
            if self.device_id == "light_actuator":
                self.mqtt_client.subscribe("home/light/control", qos=1)
            elif self.device_id == "blinds_actuator":
                self.mqtt_client.subscribe("home/blinds/control", qos=1)
            elif self.device_id == "thermostat_actuator":
                self.mqtt_client.subscribe("home/hvac/control", qos=1)
        else:
            self.log(f"MQTT Connection refused with code {rc}")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode()
        self.log(f"Received MQTT command on [{msg.topic}]: {payload}")
        
        # SADA STVARNO PROSLEĐUJEMO KOMANDU AKTUATORU:
        self.handle_actuator_command(msg.topic, payload)
    def publish_data(self, topic, payload, qos=0):
        try:
            json_payload = json.dumps(payload)
            self.mqtt_client.publish(topic, json_payload, qos=qos)
            self.log(f"Published to [{topic}] (QoS {qos}): {json_payload}")
        except Exception as e:
            self.log(f"Failed to publish MQTT message: {e}")





        
        
