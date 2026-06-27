"""Constants for the Leviton VRCS4 / VRCZ4 (vrcx4) integration."""

from __future__ import annotations

DOMAIN = "vrcx4"
MANUFACTURER = "Leviton"

# Number of buttons / scene-controller groups on the device.
NUM_BUTTONS = 4

# Scene Activation sceneIds 1..8 = 4 buttons x 2 directions (see scene.py).
NUM_SCENES = 8

# VRCS4 needs SCC 1..8 written to emit identified scenes for the off direction;
# VRCZ4 emits 1..8 natively and only has 4 SCC slots (writing 5..8 errors).
PRODUCT_TYPE_VRCS4 = 0x0802
SCENE_CONFIG_PRODUCT_TYPES = {PRODUCT_TYPE_VRCS4}

# Command classes we drive (decimal, as zwave-js-server expects).
CC_ASSOCIATION = 0x85  # 133 - group membership (direct association)
CC_SCENE_ACTIVATION = 0x2B  # 43 - button press notifications
CC_SCENE_CONTROLLER_CONFIGURATION = 0x2D  # 45 - per-group sceneId (setup)
CC_SCENE_ACTUATOR_CONFIGURATION = 0x2C  # 44 - per-load scene->level (direct loads)
CC_MANUFACTURER_PROPRIETARY = 0x91  # 145 - LED control

# Entity domains whose "on" state should light a button's LED.
LED_STATE_DOMAINS = {"switch", "light", "fan", "input_boolean"}

# HA event fired by the zwave_js integration for stateless notifications.
ZWAVE_JS_VALUE_NOTIFICATION = "zwave_js_value_notification"

# The controller repeats each press ~4x within <0.5s; collapse to one logical
# press if the same sceneId arrives again inside this window.
SCENE_DEDUP_SECONDS = 2.0

# --- config / options keys ---
CONF_CONTROLLER_DEVICE_ID = "controller_device_id"
CONF_BUTTONS = "buttons"
CONF_TARGETS = "targets"  # HA entity_ids the hub toggles on press
CONF_ON_COLOR = "on_color"  # LED color when the button's load is on (green/amber)
CONF_OFF_COLOR = "off_color"  # LED color when off (off/red locator)
CONF_DIRECT_DEVICES = "direct_devices"  # z-wave device_ids associated for direct control

DEFAULT_ON_COLOR = "green"
DEFAULT_OFF_COLOR = "off"
