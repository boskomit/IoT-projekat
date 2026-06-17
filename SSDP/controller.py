import socket
import requests
import struct
import time
import threading
import json
import paho.mqtt.client as mqtt
from device_registry import DeviceRegistry

MULTICAST_IP = "239.255.255.250"
PORT = 1900

# --- GLOBALNA STANJA SISTEMA ---
people_count = 0          
current_temperature = 0.0 
target_temperature = 22.0 

trenutno_stanje_svetla = "OFF"
trenutno_stanje_roletni = "DOWN"

def log(message):
    print(f"[CONTROLLER] {message}")

def separator():
    print("-" * 40)

# Pomoćna funkcija koja šalje trenutno aktivne SSDP ID-eve na sajt preko MQTT-a
def posalji_stanje_uredjaja_na_mqtt():
    try:
        devices = registry.get_all()
        # Izvlačimo samo ID-eve aktivnih uređaja (npr. ["motion_sensor_1", "temperature_sensor"])
        aktivni_id_evi = [info['info']['id'] for usn, info in devices.items()]
        mqtt_client.publish("home/system/devices", json.dumps(aktivni_id_evi), qos=1, retain=True)
        log(f"[SSDP -> MQTT] Poslat spisak aktivnih uređaja: {aktivni_id_evi}")
    except Exception as e:
        log(f"Greška pri slanju SSDP stanja na MQTT: {e}")

# --- PAMETNA LOGIKA UPRAVLJANJA ---

def proveri_osvetljenje_i_roletne(client):
    global people_count, trenutno_stanje_svetla, trenutno_stanje_roletni
    if people_count == 0:
        if trenutno_stanje_svetla != "OFF":
            log("Kuća je prazna. Šaljem komandu za GAŠENJE svetla.")
            client.publish("home/light/control", "OFF", qos=1)
            trenutno_stanje_svetla = "OFF"
        if trenutno_stanje_roletni != "DOWN":
            log("Kuća je prazna. Šaljem komandu za SPUŠTANJE roletni.")
            client.publish("home/blinds/control", "DOWN", qos=1)
            trenutno_stanje_roletni = "DOWN"
    else:
        if trenutno_stanje_svetla != "ON":
            log(f"Osoba je u kući (Ukupno: {people_count}). Palim svetlo.")
            client.publish("home/light/control", "ON", qos=1)
            trenutno_stanje_svetla = "ON"
        if trenutno_stanje_roletni != "UP":
            log(f"Osoba je u kući (Ukupno: {people_count}). PODIŽEM roletne.")
            client.publish("home/blinds/control", "UP", qos=1)
            trenutno_stanje_roletni = "UP"

def proveri_termostat(client):
    global current_temperature, target_temperature
    if current_temperature < target_temperature - 0.5:
        log(f"Hladno je ({current_temperature}°C). Aktiviram GREJANJE.")
        client.publish("home/hvac/control", "HEAT", qos=1)
    elif current_temperature > target_temperature + 0.5:
        log(f"Toplo je ({current_temperature}°C). Aktiviram HLAĐENJE.")
        client.publish("home/hvac/control", "COOL", qos=1)
    else:
        log(f"Temperatura je optimalna ({current_temperature}°C). Gasim HVAC.")
        client.publish("home/hvac/control", "OFF", qos=1)

# --- MQTT CALLBACK FUNKCIJE ---

def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        log("Uspešno povezan na lokalni MQTT Broker!")
        client.subscribe("home/door/sensor1", qos=1)
        client.subscribe("home/door/sensor2", qos=1)
        client.subscribe("home/temp/current", qos=0)
        client.subscribe("home/system/devices", qos=1)
        # Čim se poveže, pošalji trenutni spisak (ako već ima nečeg u registry-ju)
        posalji_stanje_uredjaja_na_mqtt()
    else:
        log(f"Greška pri povezivanju na MQTT Broker, kod: {rc}")

def on_mqtt_message(client, userdata, msg):
    global people_count, current_temperature
    try:
        if msg.topic == "home/system/devices":
            return # Kontroler ignoriše sopstvene poruke o uređajima
            
        payload = json.loads(msg.payload.decode())
        
        if msg.topic in ["home/door/sensor1", "home/door/sensor2"]:
            oznaka_senzora = "S1" if "sensor1" in msg.topic else "S2"
            count = payload.get("people_count", 1)
            event = payload.get("event", "ulazak")
            
            if event == "ulazak":
                people_count += count
            elif event == "izlazak":
                people_count = max(0, people_count - count)
                
            log(f"[PROMENA {oznaka_senzora}] Događaj: {event.upper()} ({count} osoba). Ukupno u kući: {people_count}")
            proveri_osvetljenje_i_roletne(mqtt_client)
            
        elif msg.topic == "home/temp/current":
            current_temperature = payload.get("temperature", 22.0)
            log(f"[TELEMETRIJA] Senzor javio trenutnu temperaturu: {current_temperature}°C")
            proveri_termostat(mqtt_client)
            
    except Exception as e:
        log(f"Greška pri parsiranju MQTT poruke: {e}")


def device_registered(info):
    separator()
    log(f"Registered: {info['id']}")
    show_devices()
    separator()
    posalji_stanje_uredjaja_na_mqtt() # Obavesti sajt o novom uređaju!

def register_device(usn, location):
    for attempt in range(3):
        try:
            r = requests.get(location, timeout=2)
            info = r.json()
            registry.register(usn, info)
            device_registered(info)
            return True
        except Exception:
            log(f"Connection attempt {attempt + 1}/3 failed")
            time.sleep(1)
    log(f"Failed to register {usn}")
    return False

def show_devices():
    devices = registry.get_all()
    print(f"\n[CONTROLLER] Active devices ({len(devices)}):")
    if not devices:
        print("  (none)")
        return
    for usn, info in devices.items():
        print(f"  - {info['info']['id']}")

def remove_expired_devices():
    while True:
        istekao_bilo_koji = False
        for usn in registry.get_expired():
            device = registry.get(usn)
            separator()
            log(f"Device timeout: {device['info']['id']}")
            registry.remove(usn)
            show_devices()
            separator()
            istekao_bilo_koji = True
            
        if istekao_bilo_koji:
            posalji_stanje_uredjaja_na_mqtt() # Obavesti sajt da je neko otpao!
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
                headers = parse_ssdp_message(text)
                location = headers.get("LOCATION")
                usn = headers.get("USN")
                if not location or not usn:
                    continue
                if usn in registry.get_all():
                    continue
                log(f"Device discovered: {usn}")
                register_device(usn, location)
        except socket.timeout:
            pass


registry = DeviceRegistry()

listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except:
    pass
listen_sock.bind(("", PORT))

mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_IP), socket.INADDR_ANY)
listen_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

search_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
search_sock.settimeout(2)

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
        search_sock.sendto(msg.encode(), (MULTICAST_IP, PORT))
        time.sleep(10)

mqtt_client = mqtt.Client(client_id="central_controller")
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

try:
    log("Povezujem kontroler na MQTT Broker...")
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start() 
except Exception as e:
    log(f"MQTT povezivanje nije uspelo: {e}")

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
            posalji_stanje_uredjaja_na_mqtt()

    if "ssdp:alive" in text:
        headers = parse_ssdp_message(text)
        usn = headers.get("USN")
        if usn in registry.get_all():
            registry.update_last_seen(usn)
            # Opciono možemo slati i na žive signale, ali timeout i registracija su sasvim dovoljni
        continue