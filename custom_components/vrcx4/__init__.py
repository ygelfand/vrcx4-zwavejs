"""Leviton VRCS4 / VRCZ4 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BUTTONS,
    CONF_CONTROLLER_DEVICE_ID,
    CONF_DIRECT_NODES,
    CONF_ON_COLOR,
    CONF_TARGETS,
    DOMAIN,
)
from .coordinator import ButtonConfig, VRCx4Controller
from .led import LedColor

type VRCx4ConfigEntry = ConfigEntry[VRCx4Controller]


def _buttons_from_options(options: dict) -> dict[int, ButtonConfig]:
    buttons: dict[int, ButtonConfig] = {}
    for key, raw in (options.get(CONF_BUTTONS) or {}).items():
        buttons[int(key)] = ButtonConfig(
            targets=list(raw.get(CONF_TARGETS, [])),
            on_color=LedColor[raw.get(CONF_ON_COLOR, "GREEN").upper()],
            direct_nodes=list(raw.get(CONF_DIRECT_NODES, [])),
        )
    return buttons


async def async_setup_entry(hass: HomeAssistant, entry: VRCx4ConfigEntry) -> bool:
    controller = VRCx4Controller(
        hass,
        device_id=entry.data[CONF_CONTROLLER_DEVICE_ID],
        buttons=_buttons_from_options(entry.options),
    )
    await controller.async_setup()
    entry.runtime_data = controller
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VRCx4ConfigEntry) -> bool:
    await entry.runtime_data.async_unload()
    return True


async def _async_reload(hass: HomeAssistant, entry: VRCx4ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
