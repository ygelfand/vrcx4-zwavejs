"""Scene Activation decoding for the VRCS4 / VRCZ4.

sceneId 1..4 = buttons 1..4 "on" press, 5..8 = buttons 1..4 "off" press.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import NUM_BUTTONS


@dataclass(frozen=True)
class ButtonPress:
    button: int  # 1..4
    is_on: bool


def decode_scene(scene_id: int) -> ButtonPress | None:
    """Map a Scene Activation sceneId to a button press, or None if out of range."""
    if not 1 <= scene_id <= 2 * NUM_BUTTONS:
        return None
    button = ((scene_id - 1) % NUM_BUTTONS) + 1
    return ButtonPress(button=button, is_on=scene_id <= NUM_BUTTONS)


class SceneDeduper:
    """Collapse the controller's repeated sends of the same press."""

    def __init__(self, window_seconds: float) -> None:
        self._window = window_seconds
        self._last_scene: int | None = None
        self._last_time: float = 0.0

    def is_repeat(self, scene_id: int, now: float) -> bool:
        repeat = self._last_scene == scene_id and (now - self._last_time) < self._window
        self._last_scene = scene_id
        self._last_time = now
        return repeat
