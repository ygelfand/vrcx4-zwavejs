"""Runtime controller: LED output, scene-event input, load mirroring."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.zwave_js.helpers import async_get_node_from_device_id
from homeassistant.const import STATE_ON
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from zwave_js_server.const import CommandClass

from .const import (
    CC_ASSOCIATION,
    CC_MANUFACTURER_PROPRIETARY,
    CC_SCENE_ACTIVATION,
    CC_SCENE_CONTROLLER_CONFIGURATION,
    LED_STATE_DOMAINS,
    NUM_BUTTONS,
    NUM_SCENES,
    SCENE_CONFIG_PRODUCT_TYPES,
    SCENE_DEDUP_SECONDS,
    ZWAVE_JS_VALUE_NOTIFICATION,
)
from .led import LedColor, invoke_cc_api_args, pack_light_byte
from .scene import SceneDeduper, decode_scene

_LOGGER = logging.getLogger(__name__)


@dataclass
class ButtonConfig:
    """Per-button configuration."""

    targets: list[str] = field(default_factory=list)  # hub toggles these on press
    on_color: LedColor = LedColor.GREEN
    off_color: LedColor = LedColor.OFF
    direct_device_ids: list[str] = field(default_factory=list)  # associated z-wave devices


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
        # entity_ids whose state lights each button's LED (targets + direct loads)
        self._led_entities: dict[int, list[str]] = {}

    @property
    def node_id(self) -> int:
        return self._node.node_id

    async def async_setup(self) -> None:
        self._node = async_get_node_from_device_id(self.hass, self.device_id)

        await self._async_apply_scene_controller_config()
        await self._async_apply_associations()
        self._resolve_led_entities()

        self._unsubs.append(
            self.hass.bus.async_listen(
                ZWAVE_JS_VALUE_NOTIFICATION, self._handle_value_notification
            )
        )
        watched = sorted({e for ents in self._led_entities.values() for e in ents})
        if watched:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, watched, self._handle_target_state_change
                )
            )
        await self.async_refresh_leds()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    async def _async_apply_scene_controller_config(self) -> None:
        """Map each group to its sceneId so every press emits an identified scene."""
        if self._node.product_type not in SCENE_CONFIG_PRODUCT_TYPES:
            _LOGGER.debug(
                "vrcx4: node %s emits scenes natively; skipping SCC setup", self.node_id
            )
            return
        for scene_id in range(1, NUM_SCENES + 1):
            await self._node.async_invoke_cc_api(
                CommandClass(CC_SCENE_CONTROLLER_CONFIGURATION), "set", scene_id, scene_id
            )

    async def _async_apply_associations(self) -> None:
        """Ensure the hub is in every button group (so presses reach HA), plus
        any configured direct z-wave loads."""
        hub_id = self._node.client.driver.controller.own_node_id
        for button in range(1, NUM_BUTTONS + 1):
            node_ids = [hub_id]
            cfg = self.buttons.get(button)
            if cfg:
                node_ids += [n for d in cfg.direct_device_ids if (n := self._device_node_id(d))]
            await self._node.async_invoke_cc_api(
                CommandClass(CC_ASSOCIATION), "addNodeIds", button, *node_ids
            )

    def _device_node_id(self, device_id: str) -> int | None:
        try:
            return async_get_node_from_device_id(self.hass, device_id).node_id
        except (ValueError, KeyError):
            _LOGGER.warning("vrcx4: %s is not a z-wave node; skipping", device_id)
            return None

    def _resolve_led_entities(self) -> None:
        ent_reg = er.async_get(self.hass)
        for button, cfg in self.buttons.items():
            entities = list(cfg.targets)
            for device_id in cfg.direct_device_ids:
                for entry in er.async_entries_for_device(ent_reg, device_id):
                    if entry.domain in LED_STATE_DOMAINS:
                        entities.append(entry.entity_id)
            self._led_entities[button] = entities

    # --- input: button presses ---

    @callback
    def _handle_value_notification(self, event: Event) -> None:
        data = event.data
        if data.get("device_id") != self.device_id:
            return
        if (
            data.get("command_class") != CC_SCENE_ACTIVATION
            or data.get("property") != "sceneId"
        ):
            return
        scene_id = data.get("value")
        if not isinstance(scene_id, int):
            return
        if self._deduper.is_repeat(scene_id, self.hass.loop.time()):
            return
        press = decode_scene(scene_id)
        if press is None:
            return
        self.hass.async_create_task(self._async_handle_press(press.button, press.is_on))

    async def _async_handle_press(self, button: int, is_on: bool) -> None:
        cfg = self.buttons.get(button)
        if cfg is None:
            return
        # Hub-handled targets only; direct z-wave loads acted on their own.
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
                (state := self.hass.states.get(e)) is not None and state.state == STATE_ON
                for e in self._led_entities.get(button, [])
            )
            colors[button - 1] = cfg.on_color if on else cfg.off_color
        await self.async_set_leds(colors)

    async def async_set_leds(self, colors: list[LedColor]) -> None:
        light = pack_light_byte(colors)
        await self._node.async_invoke_cc_api(
            CommandClass(CC_MANUFACTURER_PROPRIETARY),
            "sendData",
            *invoke_cc_api_args(self.node_id, light),
        )
