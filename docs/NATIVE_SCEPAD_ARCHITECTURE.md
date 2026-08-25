# Native ScePad Steam Input architecture

## Goal

Adapt any explicitly configured Steam Input controller to the raw PS4-shaped
ScePad surface consumed by Flower. The adapter uses Flower-specific named
transport actions for remappable controls, including a two-axis absolute tilt
action; it does not reduce the controller to semantic gameplay commands.

```text
physical controller
  → user-selected Steam layout
  → flower_ps4 named actions
     analog: left_stick, right_stick, tilt
     digital: dpad_up/right/down/left, square/cross/circle/triangle,
              l1/r1/l2/r2, options, touchpad_click
  → dedicated SteamController005 worker
  → complete synthetic ScePadData snapshot
  → Flower native ScePad controls
```

The Steam labels for the final two controls are exactly `Options (Start)` and
`Touchpad Click (Select)`.

The proxy does not emulate an Xbox controller, hook XInput, poll raw
`GetMotionData`, identify USB devices, or apply controller-specific calibration.

## Two intentionally separate controller paths

### Direct DualShock 4

```text
Steam Input disabled → original libScePad → Flower
```

This is Flower's shipped native path. It requires neither a Steam action layout
nor a bridge-specific native-controller toggle.

### Steam Input adapter

```text
Steam Input enabled → flower_ps4 named actions → proxy → Flower ScePad
```

The user explicitly selects a layout that binds a Steam Input device to the raw
virtual PS4 surface. If the proxy cannot provide a complete fresh Steam-owned
state, it forwards the complete call to the original library. The architecture
never splices the two paths together field by field.

## Why a local action schema is required

Steam cannot infer Flower's closed-source ScePad data surface. The project
therefore defines a local In-Game Actions file for App ID `966330`. Its named
actions are stable transport slots for raw PS4 controls, not game verbs. The
file gives Steam exact IDs and player-facing labels; it does not create bindings
or publish a controller layout.

The project must not automatically create, import, select, modify, or delete a
Steam controller profile. Without Flower's Steamworks publisher access it also
cannot publish or auto-select an Official/Recommended layout. Every compatible
Personal or Community layout is selected explicitly by the user.

## Flower's imported ScePad surface

The supported Flower build imports six ScePad functions:

| Function | Proxy behavior |
|---|---|
| `scePadInit` | Forwarded unchanged. |
| `scePadOpen` | Forwarded; the returned handle is associated with native slot `user_id - 1`, and the worker starts lazily. |
| `scePadClose` | Forwarded; mapping and pending Steam output are cleared. |
| `scePadReadState` | Returns one complete fresh Steam-owned state or forwards the entire call to the original DLL. |
| `scePadSetVibration` | Queues native vibration for a fresh Steam-owned slot; otherwise forwards unchanged. |
| `scePadSetLightBar` | Queues native LED color for a fresh Steam-owned slot; otherwise forwards unchanged. |

All other exported names and ordinals remain direct forwarders to
`libScePad_original.dll`.

## Raw virtual PS4 state mapping

The action set is `flower_ps4`. A Steam-owned state is a complete,
zero-initialized 0x78-byte `ScePadData` value:

| Raw action | Published field or bit |
|---|---|
| `left_stick` | Left stick X/Y bytes |
| `right_stick` | Right stick X/Y bytes |
| `tilt` | Normalized ±45° roll/pitch converted to ScePad acceleration X/Y/Z |
| `dpad_up` | `0x00000010` |
| `dpad_right` | `0x00000020` |
| `dpad_down` | `0x00000040` |
| `dpad_left` | `0x00000080` |
| `square` | `0x00008000` |
| `cross` | `0x00004000` |
| `circle` | `0x00002000` |
| `triangle` | `0x00001000` |
| `l1` | `0x00000400` |
| `r1` | `0x00000800` |
| `l2` | Digital L2 bit `0x00000100` |
| `r2` | Digital R2 bit `0x00000200` |
| `options` | Options bit `0x00000008`; label `Options (Start)` |
| `touchpad_click` | Touchpad-click bit `0x00100000`; label `Touchpad Click (Select)` |

`l2` and `r2` are digital actions; the two analog trigger bytes remain neutral.
Touch coordinates, angular velocity, extension data, and unrelated/reserved
fields remain neutral. Orientation is identity. Connection count and timestamp
metadata are generated coherently for each ownership epoch.

Inactive individual actions are neutral. Once at least one raw action reports
active, this complete value owns the slot. If no action is active, action
handles are unavailable, the controller disappears, or the sample becomes
stale, ownership is invalidated and the original `scePadReadState` call is used
wholesale.

## Whole-provider ownership

A slot is never assembled from mixed original and Steam fields. In particular,
the proxy does not combine:

- Steam sticks with original buttons.
- Steam buttons with original motion.
- Original triggers with Steam face buttons.
- A stale Steam snapshot with fresh original fields.

A fresh Steam snapshot owns the entire slot. Otherwise the original provider
owns the entire read. Native output routing follows the same ownership decision.
This all-or-nothing boundary is both the fallback policy and a defense against
internally inconsistent controller frames.

## Flower steering selector

Flower requires no special native-controller toggle. `PadDualShock` only selects
which ScePad steering source Flower consumes:

| Value | Steering behavior |
|---|---|
| `Off` | No ScePad steering source |
| `AnalogueLeft` | Consume the native left stick |
| `AnalogueRight` | Consume the native right stick |
| `TiltControl` | Consume native acceleration for motion steering |

`TiltControl` is required only for motion steering. It is not needed to enable
the ScePad controller, receive buttons, use direct DS4 input, or steer with a
stick. This game-side selector applies equally to direct DS4 and adapter states.

## Motion contract

The `tilt` action is the authoritative motion source. Steam must expose it through
**Gyro Behavior → Controller Tilt** with this fixed contract:

- Always On activation.
- **Use Relative Pitch** and **Use Relative Roll** off, so both axes are measured
  against Earth's horizon.
- Linear response; 0°/45° minimum/maximum deflection.
- 0%/100% minimum/maximum output.
- 0° World Tilt Offset initially, then adjusted to the user's actual holding angle.
- **Lock at Edges** and **Drag Center Point** off.
- Horizontal/vertical inversion off initially and adjusted only after a physical
  axis test.
- Left deadzone handle used only as the no-output boundary; right handle set so
  full action output is reached at approximately 45° (50% when shown against a
  90° range).

Controller-level Steam gyro calibration occurs before this contract. The bridge
adds no device-specific calibration or temporal integration.

Level must report `{0, 0}`. The two signed action axes are independent normalized
angles, not acceleration components. For sample `{x, y}`:

```text
roll  = clamp(x, -1, 1) * pi/4
pitch = clamp(y, -1, 1) * pi/4

acceleration = {
    sin(roll) * cos(pitch),
    cos(roll) * cos(pitch),
    sin(pitch)
}
```

This is a unit vector with positive Y at level. It preserves valid diagonal input
such as `{1, 1}` instead of radially shrinking it. Positive Steam X maps to
positive ScePad X and positive Steam Y maps to positive ScePad Z; device-specific
sign correction belongs in Steam's inversion controls.

Flower's `TiltControl` consumer reads acceleration X/Y/Z. It does not require the
orientation quaternion or angular velocity for steering, so synthetic orientation
remains identity and angular velocity remains zero. The proxy has no raw-motion
path, device branches, profile offsets, or hidden sensitivity scaling.

## Dedicated worker and performance boundary

Only the dedicated worker thread calls `SteamController005`:

1. Wait 16 ms while at least one native ScePad slot is open, or 100 ms while
   idle. Output requests can wake it sooner.
2. Call `RunFrame` once for that worker generation.
3. Enumerate up to 16 connected Steam controller handles into fixed arrays.
4. Preserve stable handle-to-open-ScePad-slot assignments.
5. Resolve and activate `flower_ps4`, then read all three analog and fourteen
   digital actions into fixed local values.
6. Convert the current named `tilt` angles and build complete local `ScePadData`
   snapshots for up to four native slots.
7. Publish each snapshot in one short SRW-lock section.
8. Drain up to sixteen fixed vibration/lightbar requests.

There is no heap or per-frame allocation in this loop. Runtime slots, connected
handles, samples, assignments, and output requests all use bounded fixed arrays.
Each output carries a slot/native-handle/Steam-handle ownership generation and is
revalidated before each external output call. Deduplication and enqueue happen
inside the same short state epoch, using the single nested lock order
`state → output`; the worker releases the output lock before checking state.
No lock needed by a Flower-facing wrapper is held while Steam code executes.

Flower-facing ScePad wrappers never call Steam and never wait for the worker. A
Steam call may block its dedicated worker, but after 250 ms the last published
state fails the freshness check and Flower's read immediately uses the complete
original-provider result. The proxy pins itself for the process lifetime after
starting the worker and does not wait for that worker from `DllMain`, avoiding a
loader-lock shutdown dependency.

## Native outputs

Flower supplies two 8-bit vibration values. For Steam-owned slots they are
converted to 16-bit amplitudes with `value * 257`, deduplicated, and queued to
`SteamController005::TriggerVibration` on the worker.

Flower's three-byte RGB lightbar request is deduplicated and queued to
`SetLEDColor` when that legacy export is available. Output support is optional
and never gates input. Original-owned slots forward vibration and lightbar calls
to the original ScePad library unchanged.

Ownership loss, disconnect, close, or stale state queues zero vibration for the
previous Steam handle.

## Slot mapping

Flower opens native users 1 through 4 with index zero, so `user_id - 1` is the
authoritative native slot. Steam handles retain their assignments while
connected. A new handle first prefers Steam's gamepad index when it identifies a
free open slot, then uses the lowest free open native slot. Surviving handles are
never compacted after another controller disconnects.

## Explicit installation and rollback safety

Installation is never automatic. An explicit installer command must:

1. Verify the exact supported `Flower.exe`, original `libScePad.dll`, and
   `steam_api64.dll` size/hash tuple.
2. Verify the exact proxy and local action-file artifacts.
3. Create `libScePad_original.dll` without clobbering any existing path, sync it,
   and verify it against the exact original hash.
4. Recheck source, target, artifact, and backup immediately before each verified
   atomic replacement.
5. If the second install step fails, restore the exact prior managed manifest
   state and verified original DLL when neither path changed concurrently.
6. Refuse unknown, linked, modified, or concurrently changing files.

Restore is equally explicit. It reinstates only the verified original ScePad DLL
and removes only an exact project-managed action file. It does not rewrite
`Flower.cfg` and must not alter account-owned Steam profiles.

### Exact compatibility fingerprints

| File | Bytes | SHA-256 |
|---|---:|---|
| `Flower.exe` | 20,867,456 | `649b7b64db42146314ac0a0e55d5faf03194eba21ca9c791706ce827570d3aca` |
| Original `libScePad.dll` / verified backup | 128,512 | `7d9a71a8a51bd6e81b6fb7835fea2c20e4f8f9e331ff26dd8ac09692ceb33de8` |
| `steam_api64.dll` | 242,976 | `38f6a1dd1e738e142160322638dae7b88dabcc30eea3f15c58eb08c5341f9b29` |
| Current `0.4.4` angle-tilt proxy artifact | 84,992 | `adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c` |
| Current `0.4.4` raw-surface action file | 2,438 | `8d3f5ab9b5a321ab3f6162935a8810642b08c307780a6356d75c102e8ce64b13` |

Installer `0.4.4` allowlists those exact current artifacts. Prior semantic and
experimental managed generations remain historical signatures so upgrade and
restore operations can identify them safely. The complete historical table is in
[`gyro_bridge/README.md`](../gyro_bridge/README.md).

## Validation boundary

`python3 gyro_bridge/test.py` builds the proxy and independent fake Steam/ScePad
DLLs, creates a dedicated Proton prefix under `re-temp/`, and exercises:

- Resolution of `flower_ps4` plus all 17 exact action IDs.
- Native raw button, dual-stick, and tilt delivery without any XInput call.
- Complete-state ownership with no original-field blending.
- Full original-provider fallback when actions are inactive or stale.
- Two-slot isolation, reconnect ownership epochs, and exact-index priority even
  when an unindexed controller is enumerated first.
- Fixed ±45° roll/pitch conversion, independent angle clamping, diagonal input,
  and the resulting unit gravity vector.
- Inactive-action neutralization, including neutral analog trigger bytes.
- Native vibration/lightbar routing, output deduplication, and close-time
  cancellation of a copied stale lightbar request with eventual zero vibration.
- Bounded ScePad reads and outputs while `RunFrame` blocks for 600 ms.
- Recovery after the 250 ms stale watchdog invalidates worker ownership.
- No raw-motion or XInput-hook dependency.
- Exact export-name and ordinal surface.

This deterministic matrix is necessary but is not a substitute for real Steam
client, controller, gameplay, rumble, lightbar, and hotplug testing. The
remaining platform risk is whether Flower's shipped legacy
`SteamController005` behaves consistently from one background owner on every
supported Steam/Proton combination. Whole-provider stale fallback contains a
blocked call but cannot remove an external Steam defect.

## Historical lesson

Earlier experiments called Steam from `scePadReadState`, used XInput polling as
the native state's clock, or mixed partial provider state. They produced
reconnect hangs, black screens, stale partial input, and controller-slot errors.
Those implementations remain only in Git history or ignored local redesign
backups, not in the active architecture or test plan.
