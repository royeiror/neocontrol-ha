import socket
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
_LOGGER = logging.getLogger(__name__)

UDP_PORT = 9325

def start_sniffer():
    """Listens for Neocontrol binary packets on the local network (UDP)."""
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Allow multiple listeners on the same port
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except Exception:
        pass

    # Bind to the Neocontrol port
    try:
        sock.bind(('', UDP_PORT))
    except Exception as e:
        _LOGGER.error(f"Error: Could not bind to port {UDP_PORT}. Make sure no other sniffer is running.")
        _LOGGER.error(f"Details: {e}")
        return

    _LOGGER.info(f"--- Neocontrol UDP Sniffer Active ---")
    _LOGGER.info(f"Listening on port {UDP_PORT}...")
    _LOGGER.info(f"Press Ctrl+C to stop.\n")

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            if len(data) >= 28:
                hex_payload = data.hex()
                _LOGGER.info(f"[{addr[0]}] Captured Payload: {hex_payload}")
    except KeyboardInterrupt:
        _LOGGER.info("\nSniffer stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    start_sniffer()
