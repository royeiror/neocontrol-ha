import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_BOX_MAC,
    CONF_SHUTTERS,
    CONF_PAYLOAD_OPEN,
    CONF_PAYLOAD_CLOSE,
    CONF_PAYLOAD_STOP,
)
from .client import NeocontrolClient

_LOGGER = logging.getLogger(__name__)

# Define how our configuration.yaml should look
SHUTTER_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_PAYLOAD_OPEN): cv.string,
    vol.Required(CONF_PAYLOAD_CLOSE): cv.string,
    vol.Optional(CONF_PAYLOAD_STOP, default=""): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_BOX_MAC): cv.string,
        vol.Required(CONF_SHUTTERS): vol.All(cv.ensure_list, [SHUTTER_SCHEMA]),
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Neocontrol integration from configuration.yaml (legacy)."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "import"}, data=conf
        )
    )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up Neocontrol from a config entry (UI)."""
    box_mac = entry.data[CONF_BOX_MAC]
    shutters = entry.data[CONF_SHUTTERS]

    _LOGGER.info("Setting up Neocontrol entry for Gateway MAC: %s", box_mac)

    # Instantiate the client and connect
    client = NeocontrolClient(box_mac)
    
    try:
        # We use hass.async_add_executor_job because the client might do blocking I/O 
        await hass.async_add_executor_job(client.connect)
    except Exception as err:
        _LOGGER.error("Failed to connect to Somfy/Neocontrol cloud: %s", err)
        return False

    # Store client in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "shutters": shutters,
    }

    # Load the platforms (cover)
    await hass.config_entries.async_forward_entry_setups(entry, ["cover"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["cover"])
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        client = data["client"]
        await hass.async_add_executor_job(client.disconnect)

    return unload_ok
