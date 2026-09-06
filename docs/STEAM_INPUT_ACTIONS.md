# Steam Input raw virtual PS4 action contract

The bridge defines one Flower-specific raw virtual PS4 action set. These exact
IDs are the transport contract between a user-selected Steam controller layout
and Flower's native ScePad proxy. They name PS4 controls, not semantic gameplay
commands.

## Stable schema

Action set: `flower_ps4` (Steam UI: **Flower Virtual PS4 Controller**).

### Analog actions

| ID | Type | Steam UI label | Native Flower mapping |
|---|---|---|---|
| `left_stick` | Analog | **Left Stick** | Native left stick X/Y |
| `right_stick` | Analog | **Right Stick** | Native right stick X/Y |
| `tilt` | Analog | **Controller Tilt** | Normalized ±45° roll/pitch → unit ScePad gravity vector |

### Digital actions

| ID | Type | Steam UI label | Native Flower mapping |
|---|---|---|---|
| `dpad_up` | Digital | **D-Pad Up** | D-pad up (`0x00000010`) |
| `dpad_right` | Digital | **D-Pad Right** | D-pad right (`0x00000020`) |
| `dpad_down` | Digital | **D-Pad Down** | D-pad down (`0x00000040`) |
| `dpad_left` | Digital | **D-Pad Left** | D-pad left (`0x00000080`) |
| `square` | Digital | **Square** | Square (`0x00008000`) |
| `cross` | Digital | **Cross** | Cross (`0x00004000`) |
| `circle` | Digital | **Circle** | Circle (`0x00002000`) |
| `triangle` | Digital | **Triangle** | Triangle (`0x00001000`) |
| `l1` | Digital | **L1** | L1 (`0x00000400`) |
| `r1` | Digital | **R1** | R1 (`0x00000800`) |
| `l2` | Digital | **L2** | Digital L2 (`0x00000100`) |
| `r2` | Digital | **R2** | Digital R2 (`0x00000200`) |
| `options` | Digital | **Options (Start)** | Options (`0x00000008`) |
| `touchpad_click` | Digital | **Touchpad Click (Select)** | Touchpad click (`0x00100000`) |

The labels `Options (Start)` and `Touchpad Click (Select)` are exact
compatibility labels. Do not reverse, abbreviate, or reinterpret them. Likewise,
do not rename an ID, change its case or type, or move it to another action set;
Steam layouts refer to these strings exactly.

`l2` and `r2` are digital in this contract. The proxy leaves the synthetic
state's analog trigger bytes neutral. Touch coordinates, angular velocity, and
extension data are also neutral. Motion steering is transported only through the
named `tilt` action; the proxy does not poll Steam's raw motion API.

Current action-file fingerprint:

```text
gyro_bridge/steam_input/game_actions_966330.vdf
2,438 bytes
SHA-256 8d3f5ab9b5a321ab3f6162935a8810642b08c307780a6356d75c102e8ce64b13
```

## Direct DS4 and adapter paths

Do not conflate native direct input with the Steam Input adapter:

- Direct DS4: `Steam Input disabled → original libScePad → Flower`.
- Adapter mode: `Steam Input enabled → flower_ps4 named actions → proxy → Flower ScePad`.

A direct DualShock 4 needs neither this action schema nor a special
native-controller switch. Adapter mode requires an explicitly selected layout
that maps a Steam Input device to the raw `flower_ps4` controls.

If the proxy is present but the action set is unavailable, all actions are
inactive, the Steam controller disconnects, or the sample exceeds the 250 ms
freshness window, `scePadReadState` falls back to the original provider for the
whole call. It never combines fields from the two paths.

## Flower steering selector

`PadDualShock` is not a controller-mode or native-controller enable toggle. It
only selects Flower's steering behavior:

| `PadDualShock` value | Flower steering source |
|---|---|
| `Off` | No ScePad steering source |
| `AnalogueLeft` | `left_stick` |
| `AnalogueRight` | `right_stick` |
| `TiltControl` | Acceleration generated from the named `tilt` action |

For stick steering, choose `AnalogueLeft` or `AnalogueRight` to match the
layout. `TiltControl` is required only for motion steering. It is not required
for buttons, direct DS4 support, adapter activation, or ordinary stick steering.

Change `Documents/Flower/Flower.cfg` only while Flower is closed. A motion setup,
for example, uses:

```xml
<Steer ... PadDualShock="TiltControl"/>
```

Under a usual SteamOS Proton installation that file is below:

```text
~/.local/share/Steam/steamapps/compatdata/966330/pfx/
  drive_c/users/steamuser/Documents/Flower/Flower.cfg
```

The action file and Steam layout do not change this game-side steering choice.

## Explicit Steam layout contract

Installing `game_actions_966330.vdf` only makes the raw schema and labels
available to Steam. It does not bind a controller and must not create, import,
publish, select, edit, or delete any Steam controller profile automatically.
Every Personal or Community layout remains account-owned and user-selected.

After a compatible schema installation, fully exit and restart Steam to reload
its cached metadata. Then explicitly create, import, or select a layout for
**Flower Virtual PS4 Controller**. A one-to-one PS4-style layout normally binds:

- Physical left stick/pad → `flower_ps4/left_stick`.
- Physical right stick/pad → `flower_ps4/right_stick`.
- D-pad directions → the four `flower_ps4/dpad_*` actions.
- Face buttons → `flower_ps4/square`, `cross`, `circle`, and `triangle`.
- Shoulder controls → `flower_ps4/l1`, `r1`, `l2`, and `r2`.
- Menu/start equivalent → `flower_ps4/options`, labeled `Options (Start)`.
- Back/select/touchpad-click equivalent → `flower_ps4/touchpad_click`, labeled
  `Touchpad Click (Select)`.

Bind every control that should reach Flower. An inactive or unbound field is
neutral while the Steam provider owns the slot.

### Motion steering

Set Steam's **Gyro Behavior** to **Controller Tilt**, targeting
`flower_ps4/tilt`, and configure:

- Activation: **Always On**.
- **Use Relative Pitch**: Off.
- **Use Relative Roll**: Off.
- **World Tilt Offset** / neutral angle: 0° initially, then adjusted to the user's actual comfortable holding angle.
- Response curve: Linear.
- Minimum/maximum deflection angle: 0° / 45°.
- Minimum/maximum joystick output: 0% / 100%.
- **Lock at Edges**: Off.
- **Drag Center Point**: Off.
- Horizontal/vertical inversion: Off initially.

Steam's internal keys call the relative toggles `use_gravity`, but its UI text is
inverse: with **Use Relative Pitch/Roll** off, output is measured against Earth's
horizon. The action must report `{0, 0}` while level. The bridge treats X as
normalized roll and Y as normalized pitch, clamps each independently to
`[-1, 1]`, maps them to ±45°, and computes a unit gravity vector. Do not use
Camera Style, gyro-as-mouse, a rate-based mapping, radial edge locking, or center
point dragging for this action.

In Steam's deadzone/ramp control, the left handle is the no-output boundary and
the right handle is the end of the ramp/start of maximum output. Raise only the
left handle enough to suppress stationary noise or drift. The right handle must
make the action reach full output at about 45°; when Steam displays a 90° range,
that commonly corresponds to 50%, not 100%.

Steam's controller-level manual or automatic gyro calibration is upstream of
this action and is compatible with it. Manual calibration and a small no-output
boundary should be tried before background auto-calibration, which can mistake
very slow intentional movement for drift on some devices.

Finally, select `PadDualShock="TiltControl"` in Flower. After the first physical
four-direction test, correct a sign only with Steam's horizontal/vertical
inversion controls; the bridge deliberately has no device-specific inversion.

A stick-only layout does not need an active `tilt` action and must not be told to
use `TiltControl`.

## Ownership and fallback

When at least one raw action reports active, the Steam provider owns the native
slot and publishes one complete zero-initialized state. Active values are
translated; inactive individual controls remain neutral.

When no raw action is active, the controller disconnects, action handles cannot
be resolved, or the worker's state is older than 250 ms, ownership is
invalidated. Flower's entire `scePadReadState` call is then forwarded to the
original ScePad provider. There is no original/Steam field blending.

The worker polls at 16 ms while native slots are open and at 100 ms while idle.
All `SteamController005` work stays on that dedicated thread; Flower-facing reads
use fixed state arrays, short SRW locks, and no per-frame allocation. Native
vibration and lightbar output follow the current whole-slot owner. The bridge
contains no XInput or raw `GetMotionData` dependency.

## Publisher and installation boundary

The local schema pathname is:

```text
<Steam root>/controller_config/game_actions_966330.vdf
```

It is Valve's local-development In-Game Actions mechanism. Without Flower's
Steamworks publisher access, this project cannot publish an Official or
Recommended layout, auto-select a layout for any controller family, or change
App ID controller settings through Steamworks.

Installation and restoration must remain explicit and reversible. Bridge
component/installer `0.4.5` in bundle `1.2.0` hash-gates every managed file,
preserves a verified `libScePad_original.dll`, and removes only an exact
project-managed schema on restore. The native proxy and action file remain the
unchanged `0.4.4` artifacts; the installer version does not change their exact
sizes or hashes. Exact game, current native-artifact, and historical managed
hashes are listed in [`gyro_bridge/README.md`](../gyro_bridge/README.md).
