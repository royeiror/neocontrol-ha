import time
import ssl
import sys
import paho.mqtt.client as mqtt

BROKER_URI = "iot.neocontrolglobal.com"
BROKER_PORT = 9420
USERNAME = "NM8Y6tUQ9SZcp6bx"
PASSWORD = "LFuBH4hsVnbBC98n"
TOPIC_APP = "neo/conn/+/app"
TOPIC_BOX = "neo/conn/+/box"

CLIENT_ID = f"NSAI{int(time.time() * 1000)}"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Successfully connected to Neocontrol Cloud MQTT Broker!")
        client.subscribe(TOPIC_APP)
        client.subscribe(TOPIC_BOX)
        # Flush stdout so we see it in the redirected file immediately
        sys.stdout.flush()
    else:
        print(f"Failed to connect, return code {rc}")
        sys.stdout.flush()

def on_message(client, userdata, msg):
    print(f"\n--- New Message on {msg.topic} ---")
    print(f"Data (Hex): {msg.payload.hex()}")
    sys.stdout.flush()

client = mqtt.Client(client_id=CLIENT_ID)
client.username_pw_set(USERNAME, PASSWORD)

try:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.set_ciphers('ALL:@SECLEVEL=0')
    client.tls_set_context(context)
except Exception as e:
    client.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS)
    client.tls_insecure_set(True)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")
sys.stdout.flush()
try:
    client.connect(BROKER_URI, BROKER_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    client.disconnect()
except Exception as e:
    print(f"Error connecting: {e}")
