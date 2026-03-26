import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_BOX_MAC,
    CONF_SHUTTERS,
    CONF_NAME,
    CONF_PAYLOAD_OPEN,
    CONF_PAYLOAD_CLOSE,
    CONF_PAYLOAD_STOP,
)

class NeocontrolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neocontrol."""

    VERSION = 1

    def __init__(self):
        """Initialize the flow."""
        self.data = {}
        self.shutters = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step (Gateway MAC)."""
        errors = {}
        entries = self.hass.config_entries.async_entries(DOMAIN)
        
        if user_input is not None:
            # 1. Did the user select an existing gateway from the dropdown?
            existing_gateway = user_input.get("existing_gateway", "new")
            if existing_gateway != "new":
                return self.async_abort(
                    reason="already_configured", 
                    description_placeholders={"mac": existing_gateway}
                )

            # 2. Process a new MAC address
            mac_input = user_input.get(CONF_BOX_MAC)
            if not mac_input:
                errors[CONF_BOX_MAC] = "no_mac"
            else:
                mac = mac_input.replace(":", "").replace("-", "").upper()
                if len(mac) != 12:
                    errors[CONF_BOX_MAC] = "invalid_mac"
                else:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    self.data[CONF_BOX_MAC] = mac
                    return await self.async_step_shutter()

        # Build schema
        fields = {}
        if entries:
            # If we have existing entries, show a dropdown
            existing_macs = {e.unique_id: e.unique_id for e in entries if e.unique_id}
            existing_macs["new"] = "Add a New Gateway..."
            fields[vol.Optional("existing_gateway", default="new")] = vol.In(existing_macs)
        
        # MAC is optional in the schema but we validate it manually if existing_gateway == "new"
        fields[vol.Optional(CONF_BOX_MAC)] = str
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(fields),
            errors=errors,
        )

    async def async_step_shutter(self, user_input=None):
        """Handle adding shutters."""
        errors = {}
        if user_input is not None:
            # Add the current shutter to the list
            shutter = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_PAYLOAD_OPEN: user_input[CONF_PAYLOAD_OPEN],
                CONF_PAYLOAD_CLOSE: user_input[CONF_PAYLOAD_CLOSE],
                CONF_PAYLOAD_STOP: user_input.get(CONF_PAYLOAD_STOP, ""),
            }
            self.shutters.append(shutter)
            
            # After adding, ask if they want to add another or finish
            return await self.async_step_add_another()

        return self.async_show_form(
            step_id="shutter",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_PAYLOAD_OPEN): str,
                vol.Required(CONF_PAYLOAD_CLOSE): str,
                vol.Optional(CONF_PAYLOAD_STOP): str,
            }),
            description_placeholders={
                "count": str(len(self.shutters))
            },
            errors=errors,
        )

    async def async_step_add_another(self, user_input=None):
        """Step to ask if we should add another shutter."""
        if user_input is not None:
            if user_input["add_another"]:
                return await self.async_step_shutter()
            
            # Finalize
            self.data[CONF_SHUTTERS] = self.shutters
            return self.async_create_entry(
                title=f"Neocontrol ({self.data[CONF_BOX_MAC]})",
                data=self.data
            )

        return self.async_show_form(
            step_id="add_another",
            data_schema=vol.Schema({
                vol.Required("add_another", default=False): bool,
            }),
            description_placeholders={
                "count": str(len(self.shutters))
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NeocontrolOptionsFlowHandler(config_entry)

class NeocontrolOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options (adding/removing shutters later)."""

    def __init__(self, config_entry):
        """Initialize."""
        self.config_entry = config_entry
        self.data = dict(config_entry.data)
        self.shutters = list(self.data.get(CONF_SHUTTERS, []))

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Main options menu."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["add_shutter", "remove_shutter", "finish"]
        )

    async def async_step_add_shutter(self, user_input=None):
        """Add a new shutter."""
        if user_input is not None:
            shutter = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_PAYLOAD_OPEN: user_input[CONF_PAYLOAD_OPEN],
                CONF_PAYLOAD_CLOSE: user_input[CONF_PAYLOAD_CLOSE],
                CONF_PAYLOAD_STOP: user_input.get(CONF_PAYLOAD_STOP, ""),
            }
            self.shutters.append(shutter)
            return await self.async_step_user()

        return self.async_show_form(
            step_id="add_shutter",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_PAYLOAD_OPEN): str,
                vol.Required(CONF_PAYLOAD_CLOSE): str,
                vol.Optional(CONF_PAYLOAD_STOP): str,
            }),
        )

    async def async_step_remove_shutter(self, user_input=None):
        """Remove a shutter."""
        if user_input is not None:
            # Simple removal logic
            name_to_remove = user_input["name"]
            self.shutters = [s for s in self.shutters if s[CONF_NAME] != name_to_remove]
            return await self.async_step_user()

        shutter_names = [s[CONF_NAME] for s in self.shutters]
        return self.async_show_form(
            step_id="remove_shutter",
            data_schema=vol.Schema({
                vol.Required("name"): vol.In(shutter_names),
            }),
        )

    async def async_step_finish(self, user_input=None):
        """Save the options."""
        # Note: we update the ConfigEntry data directly
        self.data[CONF_SHUTTERS] = self.shutters
        return self.async_create_entry(title="", data=self.data)
