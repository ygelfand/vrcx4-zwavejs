"""Runtime controller: LED output, scene-event input, load mirroring."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.zwave_js.helpers import async_get_node_from_device_id
from homeassistant.const import STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CC_MANUFACTURER_PROPRIETARY,
    CC_SCENE_ACTIVATION,
    CC_SCENE_CONTROLLER_CONFIGURATION,
    NUM_BUTTONS,
    NUM_SCENES,
    SCENE_DEDUP_SECONDS,
    ZWAVE_JS_VALUE_NOTIFICATION,
)
from .led import LedColor, invoke_cc_api_args, pack_light_byte
from .scene import SceneDeduper, decode_scene

_LOGGER = logging.getLogger(__name__)


@dataclass
class ButtonConfig:
    """Per-button configuration."""

    targets: list[str] = field(default_factory=list)  # HA entity_ids
    on_color: LedColor = LedColor.GREEN
    direct_nodes: list[int] = field(default_factory=list)  # z-wave node ids


class VRCx4Controller:
    """One physical VRCS4 / VRCZ4 controller."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        buttons: dict[int, ButtonConfig],
    ) -> None:
        self.hass = hass
        self.device_id = device_id
        self.buttons = buttons
        self._node = None
        self._deduper = SceneDeduper(SCENE_DEDUP_SECONDS)
        self._unsubs: list = []
        # Current per-button color; index 0 == button 1.
        self._colors: list[LedColor] = [LedColor.OFF] * NUM_BUTTONS

    @property
    def node_id(self) -> int:
        return self._node.node_id

    async def async_setup(self) -> None:
        self._node = async_get_node_from_device_id(self.hass, self.device_id)

        await self._async_apply_scene_controller_config()

        self._unsubs.append(
            self.hass.bus.async_listen(
                ZWAVE_JS_VALUE_NOTIFICATION, self._handle_value_notification
            )
        )
        targets = [t for cfg in self.buttons.values() for t in cfg.targets]
        if targets:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, targets, self._handle_target_state_change
                )
            )
        await self.async_refresh_leds()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    async def _async_apply_scene_controller_config(self) -> None:
        """Map each group to its sceneId so every press emits an identified scene."""
        for scene_id in range(1, NUM_SCENES + 1):
            await self._node.async_invoke_cc_api(
                CC_SCENE_CONTROLLER_CONFIGURATION, "set", scene_id, scene_id
            )

    # --- input: button presses ---

    @callback
    def _handle_value_notification(self, event: Event) -> None:
        data = event.data
        if data.get("device_id") != self.device_id:
            return
        if data.get("command_class") != CC_SCENE_ACTIVATION or data.get("property") != "sceneId":
            return
        scene_id = data.get("value")
        if not isinstance(scene_id, int):
            return
        now = self.hass.loop.time()
        if self._deduper.is_repeat(scene_id, now):
            return
        press = decode_scene(scene_id)
        if press is None:
            return
        self.hass.async_create_task(self._async_handle_press(press.button, press.is_on))

    async def _async_handle_press(self, button: int, is_on: bool) -> None:
        cfg = self.buttons.get(button)
        if cfg is None:
            return
        # Hub-handled targets: drive them. (Direct z-wave loads handle themselves.)
        service = "turn_on" if is_on else "turn_off"
        for entity_id in cfg.targets:
            domain = entity_id.split(".", 1)[0]
            await self.hass.services.async_call(
                domain, service, {"entity_id": entity_id}, blocking=False
            )

    # --- output: LED mirroring ---

    @callback
    def _handle_target_state_change(self, event: Event) -> None:
        self.hass.async_create_task(self.async_refresh_leds())

    async def async_refresh_leds(self) -> None:
        colors = [LedColor.OFF] * NUM_BUTTONS
        for button, cfg in self.buttons.items():
            on = any(
                (state := self.hass.states.get(t)) is not None and state.state == STATE_ON
                for t in cfg.targets
            )
            colors[button - 1] = cfg.on_color if on else LedColor.OFF
        await self.async_set_leds(colors)

    async def async_set_leds(self, colors: list[LedColor]) -> None:
        self._colors = colors
        light = pack_light_byte(colors)
        await self._node.async_invoke_cc_api(
            CC_MANUFACTURER_PROPRIETARY,
            "sendData",
            *invoke_cc_api_args(self.node_id, light),
        )
