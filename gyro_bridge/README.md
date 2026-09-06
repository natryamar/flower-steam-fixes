# Flower raw virtual PS4 Steam Input bridge

This optional, reversible, unofficial bridge adapts Steam Input controllers to
the native ScePad path used by the Steam release of **Flower**. It exposes a
Flower-specific raw virtual PS4 controller surface. The action names represent
PS4 controls directly rather than semantic gameplay commands.

Component/installer `0.4.5` is included in bundle `1.2.0` (`v1.2.0`). The DLL and
action manifest remain the byte-identical native `0.4.4` artifacts with unchanged
exact sizes and hashes.
Existing native validation is not a new gameplay or Windows pass for this bundle.

Adapter mode is designed for Steam Deck, DualShock 4, DualSense, Steam
Controller, Switch controllers, and other devices exposed by Steam Input. A
physical motion sensor is needed only for motion steering. Informal gameplay has
exercised gyro with one real 8BitDo controller; other devices are expected
interoperability targets, not hardware-certified combinations. See
[`SUPPORT.md`](../SUPPORT.md).

Supported Flower Steam build: `4354278` (App ID `966330`). Compatibility is
byte-exact; see [Exact files and hashes](#exact-files-and-hashes).

## Quick start

Download `flower-steam-fixes-1.2.0.zip` and `SHA256SUMS`, verify the ZIP, and
extract the whole bundle. The root user guide is
[`GYRO_BRIDGE.md`](../GYRO_BRIDGE.md).

Close Flower. From the extracted bundle or repository root on SteamOS/Linux,
double-click [`INSTALL_GYRO_BRIDGE_LINUX.sh`](../INSTALL_GYRO_BRIDGE_LINUX.sh).
The equivalent direct command is:

```sh
python3 gyro_bridge/install_gyro_bridge.py install
```

On Windows, the root launchers are
[`INSTALL_GYRO_BRIDGE_WINDOWS.cmd`](../INSTALL_GYRO_BRIDGE_WINDOWS.cmd) and
[`REVERT_GYRO_BRIDGE_WINDOWS.cmd`](../REVERT_GYRO_BRIDGE_WINDOWS.cmd). For direct
PowerShell commands, use `py -3` in place of `python3` with Python 3.10 or newer.
Native Windows is not yet a validated support target. Never bypass an
`unsupported`, `unsafe`, backup, or artifact refusal.

After a successful install, fully exit and restart Steam, explicitly select or
create a **Flower Virtual PS4 Controller** layout, and follow
[Restart Steam and select a layout](#restart-steam-and-select-a-layout). The
installer does not create or select an account-owned layout.

To remove the bridge safely, close Flower and double-click
[`REVERT_GYRO_BRIDGE_LINUX.sh`](../REVERT_GYRO_BRIDGE_LINUX.sh), or run:

```sh
python3 gyro_bridge/install_gyro_bridge.py restore
```

Both action commands perform their own full preflight and final verification.
`status` and `--dry-run` remain optional inspection tools. See
[`docs/TROUBLESHOOTING.md`](../docs/TROUBLESHOOTING.md) for recovery states.

## Status and invariants

The production source has one native backend with these invariants:

- No XInput hook, Xbox-state synthesis, or XInput fallback clock.
- No USB-device identification or controller-specific calibration.
- One dedicated worker owns every legacy `SteamController005` call. Motion is
  transported only through the named `flower_ps4/tilt` action.
- `scePadReadState` returns either one complete Steam-owned `ScePadData` value or
  the complete result from the original DLL. Providers are never blended field
  by field.
- Steam-owned slots route Flower's native ScePad vibration and lightbar requests
  asynchronously on the worker. Original-owned slots retain original output
  behavior.
- The worker polls every 16 ms while a native slot is open and every 100 ms while
  idle. A state older than 250 ms loses Steam ownership and falls back wholesale
  to the original provider.
- Runtime storage is fixed-size. The per-frame path uses fixed arrays, short SRW
  lock sections, and no dynamic or per-frame allocation. No lock needed by a
  Flower-facing wrapper is held across a Steam call.

The deterministic LLVM-MinGW/Proton smoke matrix exercises complete-state raw
control delivery, two-slot isolation, exact-index-before-fallback assignment,
whole-provider fallback, ±45° roll/pitch conversion, independent axis clamping,
reconnect epochs, native outputs, close-time output cancellation, a deliberately
blocked `RunFrame`, and recovery without making an XInput or raw-motion call.

Real Steam client, gameplay, controller, rumble, lightbar, and hotplug testing is
still required before claiming hardware certification.

## Raw virtual PS4 action surface

Action set: `flower_ps4` (Steam UI: **Flower Virtual PS4 Controller**).

### Analog actions

| ID | Steam UI label | Native ScePad mapping |
|---|---|---|
| `left_stick` | **Left Stick** | Left stick X/Y bytes |
| `right_stick` | **Right Stick** | Right stick X/Y bytes |
| `tilt` | **Controller Tilt** | Normalized ±45° roll/pitch → unit ScePad gravity vector |

### Digital actions

| ID | Steam UI label | Native ScePad mapping |
|---|---|---|
| `dpad_up` | **D-Pad Up** | D-pad up (`0x00000010`) |
| `dpad_right` | **D-Pad Right** | D-pad right (`0x00000020`) |
| `dpad_down` | **D-Pad Down** | D-pad down (`0x00000040`) |
| `dpad_left` | **D-Pad Left** | D-pad left (`0x00000080`) |
| `square` | **Square** | Square (`0x00008000`) |
| `cross` | **Cross** | Cross (`0x00004000`) |
| `circle` | **Circle** | Circle (`0x00002000`) |
| `triangle` | **Triangle** | Triangle (`0x00001000`) |
| `l1` | **L1** | L1 (`0x00000400`) |
| `r1` | **R1** | R1 (`0x00000800`) |
| `l2` | **L2** | Digital L2 (`0x00000100`) |
| `r2` | **R2** | Digital R2 (`0x00000200`) |
| `options` | **Options (Start)** | Options (`0x00000008`) |
| `touchpad_click` | **Touchpad Click (Select)** | Touchpad click (`0x00100000`) |

`l2` and `r2` are deliberately digital actions. The synthetic state's analog
trigger bytes remain neutral. Do not rename IDs, change their case or type, or
move them to another action set; Steam layouts refer to the exact strings.

See [`docs/STEAM_INPUT_ACTIONS.md`](../docs/STEAM_INPUT_ACTIONS.md) for the stable
layout contract.

## Direct DS4 versus adapter mode

These are separate operating paths:

### Direct DS4

```text
Steam Input disabled → original libScePad → Flower
```

A direct DualShock 4 can use Flower's shipped native path without the adapter or
a Steam action layout. Restoring the bridge returns the installation to this
byte-verified original path.

### Steam Input adapter

```text
Steam Input enabled → flower_ps4 named actions → proxy → Flower ScePad
```

The user explicitly chooses a Steam layout that maps a physical controller to
the raw PS4 action surface. The proxy converts all active controls into a
complete native state. If no raw action is active, the controller disconnects,
or the last worker sample becomes stale, the proxy delegates the complete read
to `libScePad_original.dll`.

The adapter does not merge Steam sticks with original buttons, original motion
with Steam buttons, or any other combination of providers.

## Flower steering behavior

Flower requires no special native-controller enable toggle. The `PadDualShock`
value in `Documents/Flower/Flower.cfg` only chooses how Flower steers from the
ScePad state:

| Value | Steering behavior |
|---|---|
| `Off` | Do not steer from the ScePad steering inputs |
| `AnalogueLeft` | Steer from `left_stick` |
| `AnalogueRight` | Steer from `right_stick` |
| `TiltControl` | Steer from acceleration generated by the named `tilt` action |

Use `TiltControl` only for motion steering. It is not required to make the
controller native, to use face buttons, or to use ordinary stick steering. The
same selector applies whether the state comes from a direct DS4 or adapter mode.
Change `Flower.cfg` only while Flower is closed.

## How the proxy works

The installer manages two local files:

1. Flower's `libScePad.dll`, with the verified original preserved beside it as
   `libScePad_original.dll`.
2. `<Steam root>/controller_config/game_actions_966330.vdf`, the local
   In-Game Actions schema for App ID `966330`.

At runtime:

1. Flower opens its normal ScePad users.
2. The proxy starts one process-lifetime worker outside `DllMain`.
3. The worker acquires `SteamController005`, enumerates controller handles,
   activates `flower_ps4`, and reads all 17 named actions.
4. It builds and atomically publishes a complete 0x78-byte `ScePadData` snapshot
   for each owned slot.
5. Flower-facing reads only copy a fresh snapshot under a short SRW lock; they do
   not call or wait for Steam.
6. Unavailable, inactive, disconnected, or 250 ms stale Steam state invalidates
   ownership and forwards the entire read to the original library.
7. Flower's native vibration and RGB requests are queued to the worker for
   Steam-owned slots; original-owned slots are forwarded unchanged.

Only the six ScePad functions imported by this Flower build need local wrappers.
All remaining names and ordinals are unchanged forwarders. Detailed design is in
[`docs/NATIVE_SCEPAD_ARCHITECTURE.md`](../docs/NATIVE_SCEPAD_ARCHITECTURE.md).

## Explicit, reversible installation

The project must not modify Steam controller profiles automatically. In
particular, the installer does not create, import, publish, select, edit, or
delete Personal, Community, Official, or Recommended layouts. It only manages
the exact local action-schema pathname after an explicit user command. Layout
selection remains an explicit account-owner action in Steam's UI.

Close Flower first. From the repository root:

```sh
python3 gyro_bridge/install_gyro_bridge.py install
```

On Windows PowerShell, run the same commands with `py -3` instead of
`python3` (Python 3.10 or newer). Native Windows remains unverified; reports must not be generalized
into confirmed support.

For nonstandard locations:

```sh
python3 gyro_bridge/install_gyro_bridge.py install --game-dir "/path/to/steamapps/common/Flower" --steam-dir "/path/to/Steam"
```

Installation is fail-closed and reversible:

- The user must invoke `install`; there is no automatic deployment.
- Flower's executable, original ScePad library, Steam API, proxy artifact, and
  action file must match exact size and SHA-256 allowlists.
- Before replacement, the installer creates a no-clobber
  `libScePad_original.dll`, syncs it, and verifies it against the exact original
  hash.
- Unknown, linked, independently modified, or concurrently changing files are
  refused.
- Each managed file uses a verified temporary copy and atomic replacement, with
  final target and backup hashes checked afterward.
- The two-file install is coordinated: if the second step fails, the exact prior
  managed manifest state and verified original DLL are restored when safe; an
  unknown concurrent manifest is never overwritten.
- Restore removes the managed action file before reinstating the verified
  original DLL, so an interrupted restore leaves the proxy fail-open. Unknown
  files and account-owned profiles are never deleted.

Per-file atomic replacement and coordinated rollback are not an all-or-nothing
transaction. An error, interruption, or unsuccessful rollback can leave partial
state; preserve verified backups and inspect `status` before retrying.

Python 3.10 or newer is required. No third-party Python packages are needed.


## Restart Steam and select a layout

After a compatible action file is installed or updated, fully exit and restart
Steam so it reloads cached action metadata. Then explicitly create, import, or
select a layout for **Flower Virtual PS4 Controller** and map the physical
controls one-to-one.

For motion steering, set Steam's **Gyro Behavior** to **Controller Tilt**. That
creates a `gyro_to_joystick_deflection` source targeting `flower_ps4/tilt`; use
this exact contract:

- Activation: **Always On**.
- **Use Relative Pitch**: Off.
- **Use Relative Roll**: Off.
- **World Tilt Offset** / neutral angle: start at 0°, then set it to the actual
  angle at which the controller is comfortably held.
- Response curve: Linear.
- Minimum/maximum deflection angle: 0° / 45°.
- Minimum/maximum joystick output: 0% / 100%.
- **Lock at Edges**: Off.
- **Drag Center Point**: Off.
- Horizontal and vertical inversion: Off initially; change only after a physical
  four-direction test.

With both relative options off, Steam measures roll and pitch against Earth's
horizon. The bridge independently clamps the two signed action axes, converts
them to ±45° angles, and reconstructs a unit gravity vector. Set
`PadDualShock="TiltControl"` in Flower for this motion case.

Steam's two deadzone/ramp handles have different meanings:

- The **left** handle is the no-output boundary and beginning of the ramp. Raise
  only this handle slightly (often 2–5% is enough) to hide stationary sensor
  noise or residual drift.
- The **right** handle is the end of the ramp and beginning of maximum output.
  Set it so Steam reaches full action output at about 45° of physical tilt. If
  the UI expresses this against a 90° range, 45° is 50%; do not blindly move the
  right handle to 100%.

Gyro calibration happens upstream of this layout and therefore also applies to
**Controller Tilt**. First run Steam's manual calibration under **Settings →
Controller → Calibration & Advanced Settings → Gyro Calibration** with the
controller motionless on a stable surface. Enable background auto-calibration
only if manual calibration and a small no-output boundary are insufficient;
auto-calibration can misclassify very slow intentional tilt as drift on some
controller/Steam combinations.

A stick-only layout does not need `tilt`. Choose `AnalogueLeft` or
`AnalogueRight` to match the bound steering stick. Bind every raw control that
you expect Flower to receive; inactive or unbound controls are neutral while the
Steam provider owns the slot.

Without Flower's Steamworks publisher access, the project cannot publish or
auto-select an Official/Recommended layout. A user may explicitly select a
compatible Personal or Community layout.

## Debugging

Temporarily launch Flower with:

```text
FLOWER_INPUT_DEBUG=1 %command%
```

The proxy writes `flower_input_bridge.log` beside its DLL. Expected startup
messages include:

```text
FlowerInput: native ScePad Steam worker started
FlowerInput: acquired SteamController005 on worker
FlowerInput: resolved flower_ps4 action set and 17 actions
FlowerInput: Steam actions now own a native ScePad slot
```

If the first three messages appear but ownership never activates, Steam has not
selected a compatible `flower_ps4` layout or none of its raw actions is active.
If ownership activates and later expires, inspect Steam/controller connectivity;
the 250 ms watchdog intentionally returns reads to the original provider.

## Restore

Close Flower, then run:

```sh
python3 gyro_bridge/install_gyro_bridge.py restore
```

Restore puts the verified original ScePad DLL back into service and removes only
an exact project-managed local action file. Restart Steam after managed
action-file removal.

Restore does not rewrite `Flower.cfg` and must not alter account-owned Steam
controller profiles. Change the steering selector or profile selection yourself
if desired.

## Exact files and hashes

### Exact Flower compatibility targets

| File | Bytes | SHA-256 |
|---|---:|---|
| `Flower.exe` | 20,867,456 | `649b7b64db42146314ac0a0e55d5faf03194eba21ca9c791706ce827570d3aca` |
| Original `libScePad.dll` / verified `libScePad_original.dll` | 128,512 | `7d9a71a8a51bd6e81b6fb7835fea2c20e4f8f9e331ff26dd8ac09692ceb33de8` |
| `steam_api64.dll` | 242,976 | `38f6a1dd1e738e142160322638dae7b88dabcc30eea3f15c58eb08c5341f9b29` |

### Current installer-managed `0.4.4` artifacts

Component/installer `0.4.5` continues to manage these unchanged native `0.4.4`
artifacts. The installer version bump does not change their identity or hashes.

| File | Bytes | SHA-256 |
|---|---:|---|
| `gyro_bridge/dist/libScePad.dll` | 84,992 | `adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c` |
| `gyro_bridge/steam_input/game_actions_966330.vdf` | 2,438 | `8d3f5ab9b5a321ab3f6162935a8810642b08c307780a6356d75c102e8ce64b13` |

### Installer-managed historical artifacts

Installer `0.4.5` recognizes these exact prior generations for safe upgrade or
restore handling:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Historical `0.4.3` raw-motion bridge | 84,480 | `e7a77b24116b2756b4bcbf6f2a4b54ffc28c55003782824f9eba7c7e70082d44` |
| Historical `0.4.2` component-tilt bridge | 83,968 | `e34d78779b26aa2ff2f65f499aea8ee0966310731e0ab73cc055c8a69ff329b3` |
| Historical `0.4.1` inverted-X bridge | 84,480 | `9c5dcb1e482ecdf41660f39a474d5fef0b7fab0220f6fa04d3ab359e9ac07487` |
| Historical v0.1 bridge | 76,800 | `59042f843f49e02df0ad216b861cbdf8d99164c50ee371f2a2984fb86d64d027` |
| Historical four-action bridge | 82,944 | `4fafb0690c11320942a42e8a43e0c73ba88c32167f34f40553b976b300e33e90` |
| Historical XInput-cache candidate | 82,944 | `b3fc113dcbe8ddd494ad63c51f89418659eb1b9e3ff5e1a54121591e594204f6` |
| Historical semantic native bridge | 80,896 | `b9306428ac889f175a73b057b36f271898a301088c44ccb07cd6c085188cae51` |
| Historical four-action file | 860 | `2dce857f62c7d163f46d425cbb6bee01bfa523ae4d29663641b1040900dbf89a` |
| Historical semantic action file | 1,120 | `54b331f130e23654f7233eb19f5a7397e749d4f19089e39b2209ff5435c71623` |

Never relax these checks to force an installation. Only an intentional artifact
or compatibility change may update an allowlist, with matching tests and exact
artifact verification. Installer-only or bundle-only version bumps must preserve
unchanged native fingerprints.

## Build and test

`build.py` expects `x86_64-w64-mingw32-clang++`. Set `FLOWER_LLVM_MINGW` or
extract the pinned LLVM-MinGW `20260616` toolchain under `re-temp/toolchain/`.
The exact archive URL, SHA-256, compiler identity, and release process are in
[`RELEASING.md`](../RELEASING.md).

```sh
python3 gyro_bridge/build.py --verify-release
python3 gyro_bridge/test.py
python3 gyro_bridge/build.py --verify-release
python3 -m unittest discover -s tests -v
```

`--verify-release` requires the pinned Clang identity and exact production DLL
hash. Every bundle release includes the DLL and requires pinned verification and
the isolated Proton smoke matrix, even when native artifacts are unchanged. Run
`--verify-release` again after the smoke matrix to restore and verify the release
artifact. The default build remains available for development after intentional
source changes.

`gyro_bridge/test.py` uses only a dedicated prefix under
`re-temp/prefixes/native-scepad-smoke`. It must never be pointed at Flower's real
Proton prefix.

The test DLLs and executable are independently written and generated under the
ignored `re-temp/` directory. Proprietary game binaries are not part of the test
fixture or repository.

## Distribution and legal note

The proxy, installer, action schema, tests, and documentation are independently
written. Do not distribute Flower's executable, original DLL, Steam API DLL,
audio, banks, extracted media, or reverse-engineering databases. Users must
provide their own legitimate Steam installation.

This bridge does not bypass Steam or DRM. It is unofficial and is not affiliated
with or endorsed by thatgamecompany, Annapurna Interactive, Sony, Valve, or the
PC port's developers or publishers. Product and API names are used only to
identify interoperability targets. Project-authored work is MIT licensed;
binary distributions must also include
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) and its referenced license
texts.
