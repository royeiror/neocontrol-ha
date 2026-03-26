import logging
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_PAYLOAD_OPEN,
    CONF_PAYLOAD_CLOSE,
    CONF_PAYLOAD_STOP,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Neocontrol covers (legacy platform setup)."""
    # This is handled via discovery.load_platform in the old setup
    # But since we migrated to config entries, we can skip this if called directly.
    pass

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Neocontrol covers from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    shutters_config = data["shutters"]

    entities = []
    for s_conf in shutters_config:
        entities.append(NeocontrolShutter(client, s_conf))

    async_add_entities(entities)

class NeocontrolShutter(CoverEntity):
    """Representation of a Neocontrol/Somfy Shutter."""

    def __init__(self, client, config):
        """Initialize the cover."""
        self._client = client
        self._name = config[CONF_NAME]
        self._payload_open = config[CONF_PAYLOAD_OPEN]
        self._payload_close = config[CONF_PAYLOAD_CLOSE]
        self._payload_stop = config.get(CONF_PAYLOAD_STOP, "")
        
        self._attr_icon = "mdi:window-shutter"
        self._attr_name = self._name
        self._attr_unique_id = f"{self._client.box_mac}_{self._name}"
        
        # Internal state
        self._is_closed: bool | None = None

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._client.register_callback(self._handle_binary_feedback)

    def _handle_binary_feedback(self, data: bytes):
        """
        Process binary feedback from the gateway.
        We look for our specific payloads or generic status updates.
        """
        if len(data) < 28:
            return

        # 1. Simple check: Does the incoming data match our Open or Close hex exactly?
        # (This handles the case where the gateway echoes back our command)
        
        # We need to be careful with the sequence number (offset 16) when comparing
        # Let's compare parts before and after the sequence number byte
        def matches_template(template_hex: str, received_data: bytes) -> bool:
            try:
                temp_bin = self._client.format_payload(template_hex)
                # Compare skiping the sequence number at byte 16
                return temp_bin[:16] == received_data[:16] and temp_bin[17:] == received_data[17:]
            except Exception:
                return False

        if matches_template(self._payload_open, data):
            self._is_closed = False
            _LOGGER.debug("%s: Feedback confirms state is OPEN", self._name)
        elif matches_template(self._payload_close, data):
            self._is_closed = True
            _LOGGER.debug("%s: Feedback confirms state is CLOSED", self._name)
        
        self.schedule_update_ha_state()

    @property
    def is_closed(self):
        """Return True if the cover is closed. None means unknown."""
        return self._is_closed

    @property
    def supported_features(self):
        """Flag supported features."""
        features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
        if self._payload_stop:
            features |= CoverEntityFeature.STOP
        return features

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    def open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.info("Opening cover %s", self._name)
        self._is_closed = False # Optimistic
        self._client.send_command(self._payload_open)
        self.schedule_update_ha_state()

    def close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.info("Closing cover %s", self._name)
        self._is_closed = True # Optimistic
        self._client.send_command(self._payload_close)
        self.schedule_update_ha_state()

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        if not self._payload_stop:
            return
        _LOGGER.info("Stopping cover %s", self._name)
        self._client.send_command(self._payload_stop)
        # We don't know the state after a stop
        self._is_closed = None 
        self.schedule_update_ha_state()
