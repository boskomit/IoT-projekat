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

# --- GLOBALNA STANJA SISTEMA (Dopunjeno sa keširanjem stanja aktuatora) ---
people_count = 0          # Interni brojač prisutnih osoba
current_temperature = 0.0 # Očitana temperatura u realnom vremenu
target_temperature = 22.0 # Podrazumevana zadata temperatura

# Kontroler ovde pamti poslednje poslate komande (kešira stanje aktuatora)
trenutno_stanje_svetla = "OFF"
trenutno_stanje_roletni = "DOWN"

def log(message):
    print(f"[CONTROLLER] {message}")

def separator():
    print("-" * 40)

# --- PAMETNA LOGIKA UPRAVLJANJA ---

def proveri_osvetljenje_i_roletne(client):
    """Logika upravljanja koja šalje komande samo pri PROMENI stanja (Edge-triggered)."""
    global people_count, trenutno_stanje_svetla, trenutno_stanje_roletni
    
    if people_count == 0:
        # 1. Provera za svetlo
        if trenutno_stanje_svetla != "OFF":
            log("Kuća je prazna. Šaljem komandu za GAŠENJE svetla.")
            client.publish("home/light/control", "OFF", qos=1)
            trenutno_stanje_svetla = "OFF" # Ažuriramo keš
            
        # 2. Provera za roletne
        if trenutno_stanje_roletni != "DOWN":
            log("Kuća je prazna. Šaljem komandu za SPUŠTANJE roletni.")
            client.publish("home/blinds/control", "DOWN", qos=1)
            trenutno_stanje_roletni = "DOWN" # Ažuriramo keš
    else:
        # U kući ima ljudi (brojač > 0)
        
        # 1. Provera za svetlo - šalje se samo prvoj osobi koja kroči unutra
        if trenutno_stanje_svetla != "ON":
            log(f"Prva osoba je ušla (Ukupno: {people_count}). Palim svetlo.")
            client.publish("home/light/control", "ON", qos=1)
            trenutno_stanje_svetla = "ON"
            
        # 2. Provera za roletne - podižu se samo jednom i ostaju UP sve dok ima ljudi
        if trenutno_stanje_roletni != "UP":
            log(f"Prva osoba je ušla (Ukupno: {people_count}). PODIŽEM roletne.")
            client.publish("home/blinds/control", "UP", qos=1)
            trenutno_stanje_roletni = "UP"

def proveri_termostat(client):
    """Upravljanje grejanjem/hlađenjem na osnovu razlike u temperaturi (ARCH 2-1)."""
    global current_temperature, target_temperature
    
    # Regulacija temperature poređenjem trenutne i zadate vrednosti (QoS 1)
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
        # Centralni kontroler se pretplaćuje na senzorske topike (ARCH 1, ARCH 2 i ARCH 4)
        client.subscribe("home/door/sensor1", qos=1) # Senzor ulaza (QoS 1)
        client.subscribe("home/door/sensor2", qos=1) # Senzor izlaza (QoS 1)
        client.subscribe("home/temp/current", qos=0) # Periodična temperatura (QoS 0)
    else:
        log(f"Greška pri povezivanju na MQTT Broker, kod: {rc}")

def on_mqtt_message(client, userdata, msg):
    global people_count, current_temperature
    
    try:
        # Sve poruke u komunikaciji su predstavljene kroz JSON strukture
        payload = json.loads(msg.payload.decode())
        
        # Obrada događaja sa senzora pokreta 1 (Ulaz)
        if msg.topic == "home/door/sensor1":
            count = payload.get("people_count", 1)
            people_count += count # Brojač se inkrementira pri ulasku
            log(f"[PROMENA] Detektovan ULAZAK. Trenutno ljudi u kući: {people_count}")
            proveri_osvetljenje_i_roletne(client)
            
        # Obrada događaja sa senzora pokreta 2 (Izlaz)
        elif msg.topic == "home/door/sensor2":
            count = payload.get("people_count", 1)
            people_count -= count # Brojač se dekrementira pri izlasku
            if people_count < 0: 
                people_count = 0
            log(f"[PROMENA] Detektovan IZLAZAK. Trenutno ljudi u kući: {people_count}")
            proveri_osvetljenje_i_roletne(client)
            
        # Obrada očitavanja temperature
        elif msg.topic == "home/temp/current":
            current_temperature = payload.get("temperature", 22.0)
            log(f"[TELEMETRIJA] Senzor javio trenutnu temperaturu: {current_temperature}°C")
            proveri_termostat(client)
            
    except Exception as e:
        log(f"Greška pri parsiranju MQTT poruke: {e}")


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
        time.sleep(10)   # Povećano na 10 sekundi radi manje zasićenosti logova

# --- INICIJALIZACIJA I POKRETANJE MQTT KLIJENTA ---
mqtt_client = mqtt.Client(client_id="central_controller")
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

try:
    log("Povezujem kontroler na MQTT Broker...")
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start() # Pokreće MQTT u pozadinskoj niti, ne blokira SSDP niti
except Exception as e:
    log(f"MQTT povezivanje nije uspelo: {e}")

# Pokretanje sistemskih niti
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