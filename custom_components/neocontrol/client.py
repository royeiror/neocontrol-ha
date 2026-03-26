import logging
import ssl
import time
import socket
import threading
import paho.mqtt.client as mqtt

from .const import BROKER_URI, BROKER_PORT, USERNAME, PASSWORD

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 9325

class NeocontrolClient:
    def __init__(self, box_mac):
        self.box_mac = box_mac
        self.client_id = f"NSAI{int(time.time() * 1000)}"
        self.seq_num = 200
        self.topic_app = f"neo/conn/{self.box_mac}/app"
        self.topic_box = f"neo/conn/{self.box_mac}/box"
        
        self.callbacks = []
        self._stop_event = threading.Event()
        self._udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

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
        _LOGGER.info("Starting Neocontrol Client (MQTT + UDP)")
        try:
            # Connect to MQTT cloud
            self._mqtt.connect(BROKER_URI, BROKER_PORT, 60)
            self._mqtt.loop_start()  
            
            # Start UDP Listener for local feedback
            threading.Thread(target=self._udp_listener_loop, daemon=True).start()
        except Exception as e:
            _LOGGER.error("Failed to initialize Neocontrol client: %s", e)

    def disconnect(self):
        self._stop_event.set()
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        self._udp_sock.close()

    def register_callback(self, callback):
        """Register callback for status updates."""
        self.callbacks.append(callback)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            _LOGGER.info("Successfully connected to Neocontrol Cloud MQTT")
            self._mqtt.subscribe(self.topic_box)
        else:
            _LOGGER.error("Cloud MQTT Connection failed with code %s", rc)

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            _LOGGER.warning("Unexpected disconnection from Neocontrol MQTT")

    def _on_message(self, client, userdata, msg):
        _LOGGER.debug("Cloud MQTT message on %s: %s", msg.topic, msg.payload.hex())
        self._on_binary_message(msg.payload)

    def _udp_listener_loop(self):
        """Background thread to listen for UDP broadcasts from the gateway."""
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listen_sock.bind(('', UDP_PORT))
        except Exception as e:
            _LOGGER.error("Failed to bind UDP listener on port %s: %s", UDP_PORT, e)
            return

        listen_sock.settimeout(1.0)
        _LOGGER.info("UDP Listener active on port %s", UDP_PORT)

        while not self._stop_event.is_set():
            try:
                data, addr = listen_sock.recvfrom(1024)
                if len(data) >= 28:
                    self._on_binary_message(data)
            except socket.timeout:
                continue
            except Exception as e:
                _LOGGER.error("UDP Listener error: %s", e)
                break
        listen_sock.close()

    def _on_binary_message(self, data: bytes):
        """Handle incoming binary status/feedback (common for MQTT and UDP)."""
        # MAC is at offset 3-8 (or 9-14 depending on direction, but usually fixed in 28-byte packets)
        # Sequence number is at 16. Type at 21, SubType at 22.
        # We notify all registered entities to check if this message is for them.
        for callback in self.callbacks:
            callback(data)

    def format_payload(self, hex_template: str) -> bytes:
        mac_clean = self.box_mac.replace(":", "").replace("-", "").lower()
        hex_string = hex_template.replace("{mac}", mac_clean)
        payload = bytearray.fromhex(hex_string)
        if len(payload) >= 28:
            payload[16] = self.seq_num
            self.seq_num = (self.seq_num + 1) % 256
        return bytes(payload)

    def send_command(self, hex_template: str):
        if not hex_template:
            return
            
        payload = self.format_payload(hex_template)
        
        # 1. Send via Cloud MQTT
        _LOGGER.debug("Publishing to Cloud: %s", payload.hex())
        self._mqtt.publish(self.topic_app, payload, qos=1)

        # 2. Send via Local UDP Broadcast (Low latency redundancy)
        try:
            _LOGGER.debug("Broadcasting to LAN (port %s): %s", UDP_PORT, payload.hex())
            self._udp_sock.sendto(payload, ('255.255.255.255', UDP_PORT))
        except Exception as e:
            _LOGGER.warning("Local UDP broadcast failed: %s", e)
