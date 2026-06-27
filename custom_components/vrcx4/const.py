"""Constants for the Leviton VRCS4 / VRCZ4 (vrcx4) integration."""

from __future__ import annotations

DOMAIN = "vrcx4"
MANUFACTURER = "Leviton"

# Number of buttons / scene-controller groups on the device.
NUM_BUTTONS = 4

# Scene Activation sceneIds 1..8 = 4 buttons x 2 directions (see scene.py).
NUM_SCENES = 8

# Command classes we drive (decimal, as zwave-js-server expects).
CC_SCENE_ACTIVATION = 0x2B  # 43 - button press notifications
CC_SCENE_CONTROLLER_CONFIGURATION = 0x2D  # 45 - per-group sceneId (setup)
CC_SCENE_ACTUATOR_CONFIGURATION = 0x2C  # 44 - per-load scene->level (direct loads)
CC_MANUFACTURER_PROPRIETARY = 0x91  # 145 - LED control

# HA event fired by the zwave_js integration for stateless notifications.
ZWAVE_JS_VALUE_NOTIFICATION = "zwave_js_value_notification"

# The controller repeats each press ~4x within <0.5s; collapse to one logical
# press if the same sceneId arrives again inside this window.
SCENE_DEDUP_SECONDS = 2.0

# --- config / options keys ---
CONF_CONTROLLER_DEVICE_ID = "controller_device_id"
CONF_BUTTONS = "buttons"
CONF_TARGETS = "targets"  # list of HA entity_ids the button controls
CONF_ON_COLOR = "on_color"  # LED color shown when the button's load is on
CONF_DIRECT_NODES = "direct_nodes"  # z-wave node ids associated for direct control

DEFAULT_ON_COLOR = "green"
