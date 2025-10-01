import board
import busio
import time
import logging
import json
import paho.mqtt.client as mqtt
import adafruit_veml7700
import adafruit_sht31d
from adafruit_bme280 import basic as adafruit_bme280

# when client (pc) is not connected messages are stored in this file for further restore
FAILED_MSGS_FILE = "failed_messages.txt"

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MQTT
BROKER = "vitilink.local"
client = mqtt.Client()
logging.info("Connecting to broker")

if client.connect(BROKER, 1883, 60) != 0:
	logging.error("Could not connect to broker. Check IP and port.")
	exit(1)

def sauvegarder_message(payload):
	message = {
		"timestamp": int(time.time() * 1e9),
		"data": json.loads(payload)
	}
	with open(FAILED_MSGS_FILE, "a") as f:
		f.write(json.dumps(message) + "\n")
	logging.info("[MQTT] Message stocké localement.")

def restaurer_messages():
	try:
		with open(FAILED_MSGS_FILE, "r") as f:
			lines = f.readlines()
		
		for line in lines:
			message = json.loads(line)
			timestamp = message["timestamp"]
			data = message["data"]

			payload = json.dumps(data)
			client.publish("capteurs/test", payload)
			logging.info(f"[RESTORE] Message restauré: {payload} (timestamp: {timestamp})")

		open(FAILED_MSGS_FILE, "w").close()
		logging.info("[RESTORE] Tous les messages ont été renvoyés et le fichier vidé.")

	except Exception as e:
		logging.error(f"[RESTORE] Erreur pendant la restauration: {e}")

def on_message(client, userdata, msg):
	if msg.topic == "cmd/restore":
		logging.info("[CMD] Reçu commande RESTORE")
		restaurer_messages()

client.on_message = on_message
client.subscribe("cmd/restore")

# I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Capteurs
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
sht31d = adafruit_sht31d.SHT31D(i2c)
veml7700 = adafruit_veml7700.VEML7700(i2c)

client.loop_start() #listens to messages too (in case of restore query for exemple)

while True:
	try:
		data = {
			"bme280_temp": round(bme280.temperature, 1),
			"bme280_hum": round(bme280.humidity, 1),
			"bme280_press": round(bme280.pressure, 1),
			"sht_temp": round(sht31d.temperature, 1),
			"sht_hum": round(sht31d.relative_humidity, 1),
			"light": veml7700.light
		}

		payload = json.dumps(data)
		logging.info(f"[MQTT] Envoi: {payload}")
		pub = client.publish("capteurs/test", payload)

		if not pub.wait_for_publish(timeout=2) or not pub.is_published():
			logging.warning("[MQTT] Échec d'envoi, sauvegarde du message.")
			sauvegarder_message(payload)

	except Exception as e:
		logging.error(f"[ERREUR] Lecture capteur ou publication échouée: {e}")

	time.sleep(10)
