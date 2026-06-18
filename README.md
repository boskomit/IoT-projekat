# Smart Home IoT System

Projekat implementira simulaciju Smart Home IoT sistema korištenjem MQTT i SSDP protokola.

Sistem omogućava:

* automatsko otkrivanje uređaja pomoću SSDP-a
* komunikaciju između uređaja pomoću MQTT-a
* upravljanje osvjetljenjem na osnovu prisutnosti osoba
* automatsko upravljanje roletnama
* regulaciju temperature putem HVAC sistema
* praćenje rada sistema preko Web Dashboard-a

---

# Arhitektura sistema

Sistem se sastoji od:

## Senzori

* Motion Sensor 1
* Motion Sensor 2
* Temperature Sensor

## Aktuatori

* Light Actuator
* Blinds Actuator
* Thermostat Actuator

## Centralni kontroler

Kontroler:

* održava SSDP mrežu
* registruje uređaje
* obrađuje MQTT poruke
* održava broj prisutnih osoba
* upravlja osvjetljenjem
* upravlja roletnama
* upravlja HVAC sistemom

## Web Dashboard

Dashboard prikazuje:

* broj prisutnih osoba
* temperaturu
* stanje svjetla
* stanje roletni
* stanje HVAC sistema
* MQTT log
* listu aktivnih SSDP uređaja

---

# MQTT Topici

## Senzori

| Topic             | Opis                              |
| ----------------- | --------------------------------- |
| home/door/sensor1 | Događaji sa prvog motion senzora  |
| home/door/sensor2 | Događaji sa drugog motion senzora |
| home/temp/current | Trenutna temperatura              |

## Aktuatori

| Topic               | Opis               |
| ------------------- | ------------------ |
| home/light/control  | Komande za svjetlo |
| home/blinds/control | Komande za roletne |
| home/hvac/control   | Komande za HVAC    |

## Sistemski topici

| Topic               | Opis                                 |
| ------------------- | ------------------------------------ |
| home/system/devices | Lista trenutno aktivnih SSDP uređaja |

---

# MQTT Instalacija

## Mosquitto broker

```bash
sudo apt update
sudo apt install mosquitto mosquitto-clients

sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

## Python MQTT biblioteka

```bash
sudo apt update
sudo apt install python3-paho-mqtt
```

---

# Konfiguracija Mosquitto brokera

Kreirati konfiguracioni fajl:

```bash
sudo nano /etc/mosquitto/conf.d/MqttIotPodesavanja.conf
```

Sadržaj:

```conf
pid_file /run/mosquitto/mosquitto.pid

persistence true
persistence_location /var/lib/mosquitto/

log_dest file /var/log/mosquitto/mosquitto.log

allow_anonymous true

listener 1883 0.0.0.0

listener 9001 0.0.0.0
protocol websockets

include_dir /etc/mosquitto/conf.d
```

Nakon izmjene:

```bash
sudo systemctl restart mosquitto
```

---

# Test MQTT komunikacije

Terminal 1:

```bash
mosquitto_sub -t "test/topik"
```

Terminal 2:

```bash
mosquitto_pub -t "test/topik" -m "Pozdrav iz drugog taba"
```

Ako je konfiguracija ispravna poruka će se pojaviti u prvom terminalu.

---

# Pokretanje sistema

## 1. Pokrenuti kontroler

```bash
cd SSDP

python3 controller.py
```

---

## 2. Pokrenuti senzore

Motion Sensor 1:

```bash
python3 -m devices.sensors.motion_sensor_1
```

Motion Sensor 2:

```bash
python3 -m devices.sensors.motion_sensor_2
```

Temperature Sensor:

```bash
python3 -m devices.sensors.temperature_sensor
```

---

## 3. Pokrenuti aktuatore

Light Actuator:

```bash
python3 -m devices.actuators.light_actuator
```

Blinds Actuator:

```bash
python3 -m devices.actuators.blinds_actuator
```

Thermostat Actuator:

```bash
python3 -m devices.actuators.thermostat_actuator
```

---

# SSDP Funkcionalnosti

Svi uređaji koriste SSDP za automatsko otkrivanje.

Prilikom pokretanja:

* uređaj šalje SSDP alive poruku
* kontroler registruje uređaj
* uređaj postaje vidljiv na dashboard-u

Tokom rada:

* uređaj šalje alive poruku svakih 15 sekundi
* kontroler prati aktivnost uređaja

Prilikom gašenja:

* Ctrl+C šalje SSDP byebye poruku
* uređaj se odmah uklanja iz registra

Ako se uređaj ugasi bez byebye poruke:

* kontroler automatski uklanja uređaj nakon 30 sekundi timeout-a

---

# Simulacija Motion Senzora

Motion senzori podržavaju simulaciju ulaska i izlaska osoba.

## Motion Sensor 1

| Komanda | Događaj         |
| ------- | --------------- |
| w       | ulazak 1 osobe  |
| s       | izlazak 1 osobe |
| SPACE+w | ulazak 2 osobe  |
| SPACE+s | izlazak 2 osobe |

Iste komande podržava i Motion Sensor 2.

---

# Logika sistema

## Osvjetljenje

Kada broj osoba postane veći od 0:

```text
ON
```

Kada broj osoba postane 0:

```text
OFF
```

---

## Roletne

Kada postoji barem jedna osoba u kući:

```text
UP
```

Kada je kuća prazna:

```text
DOWN
```

---

## HVAC

Ako je temperatura manja od zadate:

```text
HEAT
```

Ako je temperatura veća od zadate:

```text
COOL
```

Ako je temperatura u dozvoljenom opsegu:

```text
OFF
```

---

# Struktura projekta

```text
IoT-projekat/
│
├── controller.py
├── device_registry.py
├── dashboard.html
│
├── devices/
│   ├── __init__.py
│   │
│   ├── base_device.py
│   │
│   ├── sensors/
│   │   ├── __init__.py
│   │   ├── motion_sensor_1.py
│   │   ├── motion_sensor_2.py
│   │   └── temperature_sensor.py
│   │
│   └── actuators/
│       ├── __init__.py
│       ├── light_actuator.py
│       ├── blinds_actuator.py
│       └── thermostat_actuator.py
│
└── README.md
```

---

# Napomene

* SSDP koristi multicast adresu 239.255.255.250:1900
* MQTT broker koristi port 1883
* Dashboard koristi MQTT preko WebSocket-a na portu 9001
* QoS 1 koristi se za događaje i komande aktuatora
* QoS 0 koristi se za temperaturnu telemetriju
* Dashboard automatski prikazuje online/offline status uređaja
* Sistem je projektovan tako da se novi senzori i aktuatori mogu lako dodati bez izmjena postojeće arhitekture

