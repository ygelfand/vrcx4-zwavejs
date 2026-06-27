"""Config and options flow for vrcx4."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    CONF_BUTTONS,
    CONF_CONTROLLER_DEVICE_ID,
    CONF_DIRECT_DEVICES,
    CONF_OFF_COLOR,
    CONF_ON_COLOR,
    CONF_TARGETS,
    DEFAULT_OFF_COLOR,
    DEFAULT_ON_COLOR,
    DOMAIN,
    NUM_BUTTONS,
)

ON_COLORS = ["green", "amber"]
OFF_COLORS = ["off", "red"]

_ON_COLOR_SELECTOR = SelectSelector(
    SelectSelectorConfig(options=ON_COLORS, translation_key="on_color")
)
_OFF_COLOR_SELECTOR = SelectSelector(
    SelectSelectorConfig(options=OFF_COLORS, translation_key="off_color")
)
_TARGETS_SELECTOR = EntitySelector(EntitySelectorConfig(multiple=True))
_DIRECT_SELECTOR = DeviceSelector(
    DeviceSelectorConfig(integration="zwave_js", multiple=True)
)


class VRCx4ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick the controller's z-wave device; per-button config lives in options."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            device_id = user_input[CONF_CONTROLLER_DEVICE_ID]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            device = dr.async_get(self.hass).async_get(device_id)
            return self.async_create_entry(
                title=device.name_by_user or device.name or "VRCS4",
                data={CONF_CONTROLLER_DEVICE_ID: device_id},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_CONTROLLER_DEVICE_ID): DeviceSelector(
                    DeviceSelectorConfig(integration="zwave_js")
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return VRCx4OptionsFlow()


class VRCx4OptionsFlow(OptionsFlow):
    """One form: per-button targets + on-color."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            buttons = {}
            for b in range(1, NUM_BUTTONS + 1):
                sec = user_input.get(f"button_{b}", {})
                buttons[str(b)] = {
                    CONF_TARGETS: sec.get("targets", []),
                    CONF_DIRECT_DEVICES: sec.get("direct", []),
                    CONF_ON_COLOR: sec.get("on_color", DEFAULT_ON_COLOR),
                    CONF_OFF_COLOR: sec.get("off_color", DEFAULT_OFF_COLOR),
                }
            return self.async_create_entry(data={CONF_BUTTONS: buttons})

        current = self.config_entry.options.get(CONF_BUTTONS, {})
        fields: dict = {}
        for b in range(1, NUM_BUTTONS + 1):
            saved = current.get(str(b), {})
            fields[vol.Required(f"button_{b}")] = section(
                vol.Schema(
                    {
                        vol.Optional("targets", default=saved.get(CONF_TARGETS, [])): _TARGETS_SELECTOR,
                        vol.Optional("direct", default=saved.get(CONF_DIRECT_DEVICES, [])): _DIRECT_SELECTOR,
                        vol.Optional("on_color", default=saved.get(CONF_ON_COLOR, DEFAULT_ON_COLOR)): _ON_COLOR_SELECTOR,
                        vol.Optional("off_color", default=saved.get(CONF_OFF_COLOR, DEFAULT_OFF_COLOR)): _OFF_COLOR_SELECTOR,
                    }
                ),
                {"collapsed": True},
            )
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
