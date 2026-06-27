"""LED frame encoding for the Leviton VRCS4 / VRCZ4 (Manufacturer Proprietary CC 0x91).

sendData(manufacturerId, data) prepends `91 00 1D`, so data is the rest:

    data = [0x0D, 0x01, 0xFF, light, 0x00, 0x00, 0x0A, checksum]
    light    = c1 + (c2 << 1) + (c3 << 2) + (c4 << 3)   # per-button color
    checksum = 0x96 ^ nodeId ^ light
"""

from __future__ import annotations

from enum import IntEnum

# Leviton manufacturer id (also the first sendData argument).
MANUFACTURER_ID = 0x001D

NUM_BUTTONS = 4

# Fixed bytes that bracket the light byte in the `data` payload.
_SUBHEADER = (0x0D, 0x01, 0xFF)
_TRAILER = (0x00, 0x00, 0x0A)
_CHECKSUM_SEED = 0x96


class LedColor(IntEnum):
    """Per-button LED color (pre-shift value used by `pack_light_byte`)."""

    OFF = 0x00
    GREEN = 0x01
    RED = 0x10
    AMBER = 0x11


def pack_light_byte(colors: list[LedColor] | list[int]) -> int:
    """Pack four per-button colors (button 1..4) into the light byte."""
    if len(colors) != NUM_BUTTONS:
        raise ValueError(f"expected {NUM_BUTTONS} colors, got {len(colors)}")
    light = 0
    for index, color in enumerate(colors):
        light += int(color) << index
    return light & 0xFF


def checksum(node_id: int, light: int) -> int:
    """Node-dependent XOR checksum: 0x96 ^ nodeId ^ light."""
    return (_CHECKSUM_SEED ^ node_id ^ light) & 0xFF


def build_send_data(node_id: int, light: int) -> list[int]:
    """The `data` byte array for ManufacturerProprietaryCC.sendData."""
    return [*_SUBHEADER, light & 0xFF, *_TRAILER, checksum(node_id, light)]


def invoke_cc_api_args(node_id: int, light: int) -> list:
    """Args for `node.async_invoke_cc_api(MANUFACTURER_PROPRIETARY, "sendData", *args)`.

    The byte array crosses the WS as a serialized Buffer. Encoding kept here so
    it's the one place to adjust if the live call needs a different shape.
    """
    data = build_send_data(node_id, light)
    return [MANUFACTURER_ID, {"type": "Buffer", "data": data}]


if __name__ == "__main__":
    assert pack_light_byte([LedColor.GREEN, LedColor.OFF, LedColor.OFF, LedColor.OFF]) == 0x01
    assert pack_light_byte([LedColor.GREEN] * 4) == 0x0F
    assert pack_light_byte([LedColor.AMBER] * 4) == 0xFF
    assert pack_light_byte([LedColor.RED] * 4) == 0xF0
    # node 3, button 1 green -> checksum 0x94 (what we sent on the bench)
    assert checksum(3, 0x01) == 0x94
    assert build_send_data(3, 0x01) == [0x0D, 0x01, 0xFF, 0x01, 0x00, 0x00, 0x0A, 0x94]
    print("led.py self-test OK")
