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
from .client import NeocontrolClient

class NeocontrolConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neocontrol."""

    VERSION = 1

    def __init__(self):
        """Initialize the flow."""
        self.data = {}
        self.shutters = []

    async def async_step_user(self, user_input=None):
        """Initial choice: select existing gateway or add new."""
        entries = self.hass.config_entries.async_entries(DOMAIN)
        
        if not entries:
            # No existing gateways, go direct to new MAC entry
            return await self.async_step_new_gateway()

        if user_input is not None:
            gateway_id = user_input.get("gateway_id")
            if gateway_id == "new":
                return await self.async_step_new_gateway()
            
            # Use an existing gateway. gateway_id is the unique_id or entry_id
            entry = next((e for e in entries if e.entry_id == gateway_id or e.unique_id == gateway_id), None)
            if entry:
                self.data[CONF_BOX_MAC] = entry.data.get(CONF_BOX_MAC, entry.unique_id)
                await self.async_set_unique_id(self.data[CONF_BOX_MAC])
                return await self.async_step_shutter()

        # Build selection schema
        selection = {}
        for e in entries:
            # Fallback for label: unique_id -> data[mac] -> entry_id
            mac = e.unique_id or e.data.get(CONF_BOX_MAC) or e.entry_id
            selection[e.entry_id] = f"{e.title} ({mac})"
        
        selection["new"] = "Add a NEW Gateway..."
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("gateway_id", default="new"): vol.In(selection),
            }),
        )

    async def async_step_new_gateway(self, user_input=None):
        """Step to enter a new Gateway MAC."""
        errors = {}
        if user_input is not None:
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

        return self.async_show_form(
            step_id="new_gateway",
            data_schema=vol.Schema({
                vol.Required(CONF_BOX_MAC): str,
            }),
            errors=errors,
        )

    async def async_step_shutter(self, user_input=None):
        """Handle adding shutters."""
        errors = {}
        description_placeholders = {"test_result": ""}
        
        if user_input is not None:
            # Handle Test Action
            test_action = user_input.get("test_action", "save")
            if test_action != "save":
                mac = self.data[CONF_BOX_MAC]
                client = NeocontrolClient(mac)
                payload = ""
                if test_action == "test_open": payload = user_input[CONF_PAYLOAD_OPEN]
                elif test_action == "test_close": payload = user_input[CONF_PAYLOAD_CLOSE]
                elif test_action == "test_stop": payload = user_input.get(CONF_PAYLOAD_STOP, "")
                
                if payload:
                    client.send_command(payload)
                    description_placeholders["test_result"] = f"✅ Test command sent! Check your shutter."
                else:
                    description_placeholders["test_result"] = "⚠️ No payload entered for this action."
                
                return self.async_show_form(
                    step_id="shutter",
                    data_schema=self._get_shutter_schema(user_input),
                    description_placeholders=description_placeholders,
                    errors=errors,
                )

            # SAVE
            shutter = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_PAYLOAD_OPEN: user_input[CONF_PAYLOAD_OPEN],
                CONF_PAYLOAD_CLOSE: user_input[CONF_PAYLOAD_CLOSE],
                CONF_PAYLOAD_STOP: user_input.get(CONF_PAYLOAD_STOP, ""),
            }
            self.shutters.append(shutter)
            return await self.async_step_add_another()

        return self.async_show_form(
            step_id="shutter",
            data_schema=self._get_shutter_schema(),
            description_placeholders=description_placeholders,
            errors=errors,
        )

    def _get_shutter_schema(self, defaults=None):
        """Helper to build shutter schema with test actions."""
        if defaults is None: defaults = {}
        return vol.Schema({
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
            vol.Required(CONF_PAYLOAD_OPEN, default=defaults.get(CONF_PAYLOAD_OPEN, "")): str,
            vol.Required(CONF_PAYLOAD_CLOSE, default=defaults.get(CONF_PAYLOAD_CLOSE, "")): str,
            vol.Optional(CONF_PAYLOAD_STOP, default=defaults.get(CONF_PAYLOAD_STOP, "")): str,
            vol.Required("test_action", default="save"): vol.In({
                "save": "💾 CONFIRM and Save Shutter",
                "test_open": "🔼 TEST Open Command",
                "test_close": "🔽 TEST Close Command",
                "test_stop": "⏹️ TEST Stop Command",
            }),
        })

    async def async_step_add_another(self, user_input=None):
        """Step to ask if we should add another shutter."""
        if user_input is not None:
            if user_input["add_another"]:
                return await self.async_step_shutter()
            
            # Finalize: Check if we are UPDATING an existing entry or CREATING a new one
            mac = self.data[CONF_BOX_MAC]
            existing_entry = next(
                (e for e in self.hass.config_entries.async_entries(DOMAIN) if e.unique_id == mac), 
                None
            )
            
            if existing_entry:
                # UPDATE: Append new shutters to the existing list
                current_shutters = list(existing_entry.data.get(CONF_SHUTTERS, []))
                current_shutters.extend(self.shutters)
                
                new_data = dict(existing_entry.data)
                new_data[CONF_SHUTTERS] = current_shutters
                
                # Update and reload
                self.hass.config_entries.async_update_entry(existing_entry, data=new_data)
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")
            
            # CREATE NEW
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
        self._editing_index = None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Main options menu."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["add_shutter", "edit_shutter", "remove_shutter", "finish"]
        )

    async def async_step_add_shutter(self, user_input=None):
        """Add a new shutter."""
        description_placeholders = {"test_result": ""}
        if user_input is not None:
            test_action = user_input.get("test_action", "save")
            if test_action != "save":
                # Test logic
                mac = self.data[CONF_BOX_MAC]
                client = NeocontrolClient(mac)
                payload = user_input.get(CONF_PAYLOAD_OPEN if test_action == "test_open" else CONF_PAYLOAD_CLOSE)
                if test_action == "test_stop": payload = user_input.get(CONF_PAYLOAD_STOP)
                if payload:
                    client.send_command(payload)
                    description_placeholders["test_result"] = "✅ Test command sent!"
                return self.async_show_form(
                    step_id="add_shutter",
                    data_schema=self._get_shutter_schema(user_input),
                    description_placeholders=description_placeholders,
                )

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
            data_schema=self._get_shutter_schema(),
            description_placeholders=description_placeholders,
        )

    def _get_shutter_schema(self, defaults=None):
        """Helper to build shutter schema with test actions (Options Flow)."""
        if defaults is None: defaults = {}
        return vol.Schema({
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
            vol.Required(CONF_PAYLOAD_OPEN, default=defaults.get(CONF_PAYLOAD_OPEN, "")): str,
            vol.Required(CONF_PAYLOAD_CLOSE, default=defaults.get(CONF_PAYLOAD_CLOSE, "")): str,
            vol.Optional(CONF_PAYLOAD_STOP, default=defaults.get(CONF_PAYLOAD_STOP, "")): str,
            vol.Required("test_action", default="save"): vol.In({
                "save": "💾 CONFIRM and Save Shutter",
                "test_open": "🔼 TEST Open Command",
                "test_close": "🔽 TEST Close Command",
                "test_stop": "⏹️ TEST Stop Command",
            }),
        })

    async def async_step_edit_shutter(self, user_input=None):
        """Select a shutter to edit."""
        if user_input is not None:
            # Use index for safer lookup
            shutter_names = [s[CONF_NAME] for s in self.shutters]
            if user_input["name"] in shutter_names:
                self._editing_index = shutter_names.index(user_input["name"])
                return await self.async_step_edit_shutter_form()

        shutter_names = [s[CONF_NAME] for s in self.shutters]
        return self.async_show_form(
            step_id="edit_shutter",
            data_schema=vol.Schema({
                vol.Required("name"): vol.In(shutter_names),
            }),
        )

    async def async_step_edit_shutter_form(self, user_input=None):
        """Edit the selected shutter's details."""
        if self._editing_index is None or self._editing_index >= len(self.shutters):
            return await self.async_step_user()
            
        shutter = self.shutters[self._editing_index]
        description_placeholders = {"test_result": ""}
        
        if user_input is not None:
            test_action = user_input.get("test_action", "save")
            if test_action != "save":
                # Test logic
                mac = self.data[CONF_BOX_MAC]
                client = NeocontrolClient(mac)
                payload = user_input.get(CONF_PAYLOAD_OPEN if test_action == "test_open" else CONF_PAYLOAD_CLOSE)
                if test_action == "test_stop": payload = user_input.get(CONF_PAYLOAD_STOP)
                if payload:
                    client.send_command(payload)
                    description_placeholders["test_result"] = "✅ Test command sent!"
                return self.async_show_form(
                    step_id="edit_shutter_form",
                    data_schema=self._get_shutter_schema(user_input),
                    description_placeholders=description_placeholders,
                )

            # Update the shutter in the list
            self.shutters[self._editing_index] = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_PAYLOAD_OPEN: user_input[CONF_PAYLOAD_OPEN],
                CONF_PAYLOAD_CLOSE: user_input[CONF_PAYLOAD_CLOSE],
                CONF_PAYLOAD_STOP: user_input.get(CONF_PAYLOAD_STOP, ""),
            }
            return await self.async_step_user()

        return self.async_show_form(
            step_id="edit_shutter_form",
            data_schema=self._get_shutter_schema(shutter),
            description_placeholders=description_placeholders,
        )

    async def async_step_remove_shutter(self, user_input=None):
        """Remove a shutter."""
        if user_input is not None:
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
        """Save the options and reload the entry."""
        self.data[CONF_SHUTTERS] = self.shutters
        self.hass.config_entries.async_update_entry(self.config_entry, data=self.data)
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        return self.async_create_entry(title="", data={})
