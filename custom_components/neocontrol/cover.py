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

    @property
    def is_closed(self):
        """Return True if the cover is closed. None means unknown (always allow commands)."""
        return None

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
        self._client.send_command(self._payload_open)
        self.schedule_update_ha_state()

    def close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.info("Closing cover %s", self._name)
        self._client.send_command(self._payload_close)
        self.schedule_update_ha_state()

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        if not self._payload_stop:
            return
        _LOGGER.info("Stopping cover %s", self._name)
        self._client.send_command(self._payload_stop)
