import logging
import ssl
import time
import paho.mqtt.client as mqtt

from .const import BROKER_URI, BROKER_PORT, USERNAME, PASSWORD

_LOGGER = logging.getLogger(__name__)

class NeocontrolClient:
    def __init__(self, box_mac):
        self.box_mac = box_mac
        self.client_id = f"NSAI{int(time.time() * 1000)}"
        self.seq_num = 200
        self.topic_app = f"neo/conn/{self.box_mac}/app"
        self.topic_box = f"neo/conn/{self.box_mac}/box"
        
        # Handle paho-mqtt 2.0+ Callback API Version compatibility
        try:
            from paho.mqtt.enums import CallbackAPIVersion
            self._mqtt = mqtt.Client(CallbackAPIVersion.VERSION1, client_id=self.client_id)
        except (ImportError, AttributeError):
            # Fallback for paho-mqtt 1.x
            self._mqtt = mqtt.Client(client_id=self.client_id)
        
        self._mqtt.username_pw_set(USERNAME, PASSWORD)
        
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            context.set_ciphers('ALL:@SECLEVEL=0')
            self._mqtt.tls_set_context(context)
        except Exception:
            self._mqtt.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLS)
            self._mqtt.tls_insecure_set(True)

        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

    def connect(self):
        _LOGGER.info("Connecting to Neocontrol Cloud MQTT at %s:%s", BROKER_URI, BROKER_PORT)
        try:
            self._mqtt.connect(BROKER_URI, BROKER_PORT, 60)
            self._mqtt.loop_start()  # Runs the network loop in a background thread
        except Exception as e:
            _LOGGER.error("Failed to connect to Neocontrol MQTT: %s", e)

    def disconnect(self):
        self._mqtt.loop_stop()
        self._mqtt.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            _LOGGER.info("Successfully connected to Neocontrol MQTT")
            self._mqtt.subscribe(self.topic_box)
            self._mqtt.subscribe(f"neo/conn/{self.box_mac}/alive")
        else:
            _LOGGER.error("MQTT Connection failed with code %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            _LOGGER.warning("Unexpected disconnection from Neocontrol MQTT")

    def _on_message(self, client, userdata, msg):
        _LOGGER.debug("Received message on %s: %s", msg.topic, msg.payload.hex())
        # In the future, we can parse this to update cover status (is_closed).
        # For now, this integration is optimistic (assumes commands succeed).

    def format_payload(self, hex_template: str) -> bytes:
        """
        Takes a hex string from configuration.
        Replaces {mac} with the box MAC if present.
        Injects the dynamic sequence number.
        """
        mac_clean = self.box_mac.replace(":", "").replace("-", "").lower()
        
        # If the user included {mac} in their string, we format it
        hex_string = hex_template.replace("{mac}", mac_clean)
        
        # Some users might just supply the raw hex they sniffed, 
        # so we will manually inject the sequence number at byte offset 16 (hex index 32-34) if it matches the 28-byte packet format
        payload = bytearray.fromhex(hex_string)
        if len(payload) >= 28:
            payload[16] = self.seq_num
            self.seq_num = (self.seq_num + 1) % 256
        else:
            _LOGGER.warning("Hex payload from config is suspiciously short: %s bytes", len(payload))
            
        return bytes(payload)

    def send_command(self, hex_template: str):
        if not hex_template:
            _LOGGER.error("Cannot send empty payload")
            return
            
        payload = self.format_payload(hex_template)
        _LOGGER.debug("Publishing to %s payload: %s", self.topic_app, payload.hex())
        self._mqtt.publish(self.topic_app, payload, qos=1)
