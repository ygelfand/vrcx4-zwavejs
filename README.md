# Leviton VRCS4 / VRCZ4 for Home Assistant

A custom integration for the Leviton **VRCS4** (4-button scene controller) and
**VRCZ4** (4-zone controller) over Z-Wave JS:

- Button presses drive Home Assistant (toggle target entities, trigger automations).
- Native control of the proprietary button **LEDs** (green / amber / red / off).
- LEDs automatically mirror the state of each button's loads.
- Optional **direct Z-Wave association** so a button drives a load peer-to-peer
  (instant, works even if HA is down) while HA keeps the LED in sync.

## Requirements

- The **Z-Wave JS** integration set up in Home Assistant.
- Your VRCS4 / VRCZ4 controllers included into the Z-Wave network.

## Installation (HACS)

1. In HACS, open the **⋮** menu (top right) → **Custom repositories**.
2. Add the repository URL `https://github.com/ygelfand/vrcx4-zwavejs` and choose
   category **Integration**, then **Add**.
3. Search HACS for **Leviton VRCS4 / VRCZ4** and **Download** it.
4. **Restart** Home Assistant.

## Setup

1. **Settings → Devices & Services → Add Integration** → search
   **Leviton VRCS4 / VRCZ4**.
2. Pick the controller's Z-Wave device. (Add the integration once per controller.)
3. Open the integration's **Configure** dialog and set, per button:
   - **Targets** — entities the hub toggles on press.
   - **On color** — LED color when the load is on (green or amber).
   - **Off color** — LED when off (dark, or red as a locator).
   - **Direct Z-Wave devices** — optional load(s) to associate for peer-to-peer
     control.

## Note for the VRCZ4

The VRCZ4 isn't in the Z-Wave JS device database, so Z-Wave JS only exposes 4 of
its 8 scene-controller groups — which leaves the "off" buttons inoperable. Drop
[`device-config/leviton-vrcz4.json`](device-config/leviton-vrcz4.json) into your
Z-Wave JS **`deviceConfigPriorityDir`**, restart Z-Wave JS, and re-interview the
controller. (The VRCS4 is already in the embedded database and needs nothing.)
