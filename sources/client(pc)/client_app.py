import time
import json
import threading
import tkinter as tk
import math
import random
import socket
from tkinter import messagebox
from influxdb import InfluxDBClient
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta

MQTT_BROKER_LOCAL = "vitilink.local"
MQTT_PORT = 1883
MQTT_TOPIC = "capteurs/test"
MQTT_VITILINK = "vitilink.local"
INFLUXDB_HOST = "localhost"
INFLUXDB_PORT = 8086
INFLUXDB_DBNAME = "iot_data"

influx_client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT)
if INFLUXDB_DBNAME not in [db['name'] for db in influx_client.get_list_database()]:
    influx_client.create_database(INFLUXDB_DBNAME)
influx_client.switch_database(INFLUXDB_DBNAME)


class Gauges:
    def __init__(self, canvas, x, y, label, max_val, alarm_threshold):
        self.canvas = canvas
        self.x, self.y = x, y
        self.label = label
        self.max_val = max_val
        self.alarm_threshold = alarm_threshold
        self.value = 0
        self.bg = self.canvas.create_oval(
            x-85, y-85, x+85, y+85, outline="#222", width=14)
        self.arc = self.canvas.create_arc(
            x-80, y-80, x+80, y+80, start=135, extent=0, style=tk.ARC, width=18, outline="cyan")
        self.value_text = self.canvas.create_text(
            x, y + 10, text="", font=("Orbitron", 20, "bold"), fill="cyan")
        self.label_text = self.canvas.create_text(
            x, y + 135, text=label, font=("Orbitron", 11), fill="#888")

    def update(self, val):
        self.value = min(max(val, 0), self.max_val)
        ratio = self.value / self.max_val
        angle = ratio * 270
        color = "#00FF88" if ratio < 0.4 else "#FFFF00" if ratio < 0.75 else "#FF0033"
        self.canvas.itemconfig(self.arc, extent=angle, outline=color)
        self.canvas.itemconfig(
            self.value_text, text=f"{self.value:.1f}", fill=color)
        self.canvas.itemconfig(
            self.label_text, fill="red" if self.value >= self.alarm_threshold else "#888")


class VitilinkUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🌌 Vigne Connectée — Futuristic Dashboard")
        width, height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}")
        self.root.config(bg="#0C0C0C")
        self.collecting = False

        tk.Label(root, text="MONITORING TEMPS RÉEL", font=(
            "Orbitron", 24, "bold"), bg="#0C0C0C", fg="#00FF88").pack(pady=15)
        self.canvas = tk.Canvas(
            root, width=880, height=300, bg="#0C0C0C", highlightthickness=0)
        self.canvas.pack()
        self.g1 = Gauges(self.canvas, 160, 140, "🌡️Température (°C)", 38, 30)
        self.g2 = Gauges(self.canvas, 440, 140, "💧 Humidité (%)", 100, 90)
        self.g3 = Gauges(self.canvas, 720, 140,
                         "☀️ Ensoleillement", 100000, 60000)

        self.buttons = tk.Frame(root, bg="#0C0C0C")
        self.buttons.pack(pady=25)
        self.start_btn = tk.Button(self.buttons, text="▶ DÉMARRER", font=(
            "Orbitron", 12), width=14, bg="#00FF88", fg="#000", relief="flat", command=self.start)
        self.start_btn.grid(row=0, column=0, padx=12)
        self.stop_btn = tk.Button(self.buttons, text="⛔ ARRÊTER", font=(
            "Orbitron", 12), width=14, bg="#FF0033", fg="white", relief="flat", command=self.stop)
        self.stop_btn.grid(row=0, column=1, padx=12)
        self.search_btn = tk.Button(self.buttons, text="🔍 RECHERCHER VITILINK", font=(
            "Orbitron", 12), width=22, bg="#6666FF", fg="white", relief="flat", command=self.search_vitilink)
        self.search_btn.grid(row=0, column=3, padx=12)
        self.restore_btn = tk.Button(self.buttons, text="🔁 RESTAURER", font=(
            "Orbitron", 12), width=18, bg="#ffaa00", fg="#000", relief="flat", command=self.restore_data)
        self.restore_btn.grid(row=0, column=4, padx=12)

        self.graph_zone = tk.Frame(root, bg="#0C0C0C")
        self.graph_zone.pack(pady=10)
        self.metric_var = tk.StringVar(value="sht_temp")
        self.metric_menu = tk.OptionMenu(
            self.graph_zone, self.metric_var, "sht_temp", "sht_hum", "bme280_temp", "bme280_hum", "light")
        self.metric_menu.config(font=("Orbitron", 10), bg="#111", fg="white")
        self.metric_menu.grid(row=0, column=0, padx=10)
        self.days_var = tk.IntVar(value=5)
        tk.Entry(self.graph_zone, textvariable=self.days_var,
                 width=5).grid(row=0, column=1)
        self.graph_btn = tk.Button(self.graph_zone, text="📊 AFFICHER HISTORIQUE",
                                   command=self.plot_history, font=("Orbitron", 11), bg="#444", fg="white")
        self.graph_btn.grid(row=0, column=2, padx=10)
        self.plot_canvas = None

    def restore_data(self):
        try:
            restore_client.publish("cmd/restore", "RESTORE")
            messagebox.showinfo(
                "Restoration", "Demande de restauration envoyée à Vitilink.")
        except Exception as e:
            messagebox.showerror(
                "Erreur", f"Impossible d'envoyer la requête RESTORE.\n\n{e}")

    def start(self):
        global client_local
        if not self.collecting:
            self.collecting = True
            print("[UI] Reconnexion au broker MQTT...")
            try:
                client_local.reconnect()
            except:
                client_local = mqtt.Client()
                client_local.on_connect = on_connect_local
                client_local.on_message = on_message_local
                client_local.connect(MQTT_BROKER_LOCAL, MQTT_PORT, 60)
                threading.Thread(
                    target=client_local.loop_forever, daemon=True).start()
            print("[UI] Reconnexion effectuée.")

    def stop(self):
        self.collecting = False
        client_local.disconnect()
        print("[UI] Déconnexion du broker MQTT local.")

    def update_loop(self):
        while self.collecting:
            self.g1.update(random.uniform(12, 34))
            self.g2.update(random.uniform(35, 90))
            self.g3.update(random.uniform(200, 1100))
            time.sleep(4)

    def simulate(self):
        self.collecting = True
        threading.Thread(target=self.update_loop, daemon=True).start()

    def update_from_data(self, data):
        try:
            fields = data["data"] if "data" in data else data
            self.g1.update(float(fields["sht_temp"]))
            self.g2.update(float(fields["sht_hum"]))
            self.g3.update(float(fields["light"]))
        except:
            pass

    def search_vitilink(self):
        try:
            ip = socket.gethostbyname("vitilink.local")
            messagebox.showinfo("VITILINK DÉTECTÉ",
                                f"vitilink.local trouvé à l'adresse : {ip}")
        except Exception as e:
            messagebox.showerror(
                "Erreur", f"Impossible de résoudre vitilink.local\n\n{e}")

    def plot_history(self):
        metric_map = {
            "sht_temp": "Temp. Extérieure",
            "sht_hum": "Hum. Extérieure",
            "bme280_temp": "Temp. Intérieur",
            "bme280_hum": "Hum. Intérieur",
            "light": "Luminosité"
        }
        metric_key = self.metric_var.get()
        field_name = metric_map.get(metric_key, metric_key)
        days = self.days_var.get()

        now = datetime.utcnow()
        start_time = now - timedelta(days=days)
        start_time_str = start_time.replace(
            microsecond=0).isoformat() + "Z"

        print("[DEBUG] Date actuelle UTC :", now.isoformat() + "Z")
        print("[DEBUG] Date de début UTC :", start_time_str)

        query = f'SELECT "{metric_key}" FROM mesures_capteurs WHERE time > \'{start_time_str}\''
        print(f"[DEBUG] Requête Influx : {query}")
        result = influx_client.query(query)
        points = list(result.get_points())

        if not points:
            messagebox.showinfo(
                "Aucune donnée", "Pas de données disponibles pour cet intervalle.")
            return

        times = []
        for p in points:
            try:
                times.append(datetime.strptime(
                    p['time'], "%Y-%m-%dT%H:%M:%S.%fZ"))
            except ValueError:
                times.append(datetime.strptime(
                    p['time'], "%Y-%m-%dT%H:%M:%SZ"))

        print("[DEBUG] Premières dates récupérées :")
        for t in times[:5]:
            print(" -", t)

        values = [p[metric_key] for p in points]

        if self.plot_canvas:
            self.plot_canvas.get_tk_widget().destroy()

        fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
        ax.plot(times, values, label=field_name, color="cyan")
        ax.set_title(f"{field_name} sur {days} jours")
        ax.set_ylabel(field_name)
        ax.set_xlabel("Date")
        ax.grid(True)
        fig.autofmt_xdate()

        self.plot_canvas = FigureCanvasTkAgg(fig, master=self.graph_zone)
        self.plot_canvas.draw()
        self.plot_canvas.get_tk_widget().grid(row=1, column=0, columnspan=3, pady=10)


def on_connect_local(client, userdata, flags, rc):
    print("[MQTT] Connecté au broker local avec le code", rc)
    client.subscribe(MQTT_TOPIC)


def on_message_local(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] Message reçu : {payload}")
    try:
        data = json.loads(payload)
        timestamp = int(data["timestamp"]) if "timestamp" in data else int(
            time.time() * 1e9)
        fields_data = data["data"] if "data" in data else data
        fields = {
            "Temp. Intérieur": float(fields_data["bme280_temp"]),
            "Hum. Intérieur": float(fields_data["bme280_hum"]),
            "Pression Intérieure": float(fields_data["bme280_press"]),
            "Temp. Extérieure": float(fields_data["sht_temp"]),
            "Hum. Extérieure": float(fields_data["sht_hum"]),
            "Luminosité": float(fields_data["light"])
        }
        json_body = [{
            "measurement": "mesures_capteurs",
            "tags": {"source": "raspberry"},
            "fields": fields,
            "time": timestamp
        }]
        influx_client.write_points(json_body)
        if app.collecting:
            app.update_from_data(data)
            print("[InfluxDB] Données insérées avec succès.")
    except Exception as e:
        print("[ERREUR] Format JSON ou insertion :", e)


if __name__ == "__main__":
    root = tk.Tk()
    app = VitilinkUI(root)

    client_local = mqtt.Client()
    client_local.on_connect = on_connect_local
    client_local.on_message = on_message_local
    client_local.connect(MQTT_BROKER_LOCAL, MQTT_PORT, 60)
    threading.Thread(target=client_local.loop_forever, daemon=True).start()

    restore_client = mqtt.Client()
    try:
        restore_client.connect(MQTT_VITILINK, MQTT_PORT, 60)
    except Exception as e:
        messagebox.showinfo(
            "Info", f"Connexion à vitilink.local échouée.\n\n{e}")

    root.mainloop()
