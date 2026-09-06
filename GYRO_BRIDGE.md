# Flower native ScePad Steam Input bridge

- **Component / installer version:** `0.4.5`
- **Supported game:** Flower on Steam, App ID `966330`, build `4354278`
- **Requirement:** Python `3.10` or newer; no third-party Python packages

This optional, reversible, unofficial bridge maps a user-selected Steam Input
layout to Flower's native PS4-shaped ScePad path. It provides two sticks, D-pad,
face/shoulder/menu controls, native output routing, and gravity-relative tilt
steering without an XInput hook or raw-motion hook.

This component is included in the unified `flower-steam-fixes-1.2.0.zip` bundle
(`v1.2.0`), not in a separate component archive. Keep the extracted bundle layout
intact. It contains:

- the [installer](gyro_bridge/install_gyro_bridge.py);
- the exact [bridge DLL](gyro_bridge/dist/libScePad.dll) and
  [Steam action manifest](gyro_bridge/steam_input/game_actions_966330.vdf); and
- reproducible build inputs: [build.py](gyro_bridge/build.py),
  [native source](gyro_bridge/src/flower_scepad_bridge.cpp), and
  [export definition](gyro_bridge/src/libScePad.def).

The bundled DLL is prebuilt; installation does not require a compiler.
Component/installer `0.4.5` retains the byte-identical native DLL and action
manifest built for `0.4.4`. Their native identity, exact sizes, and hashes are
unchanged; the installer version does not imply a new native build.

## Safety first

- Close Flower before install, restore, or editing `Flower.cfg`.
- Do not run the installer while Steam is updating or verifying Flower.
- `install` and `restore` perform their own full preflight and final verification;
  `status` and `--dry-run` are optional inspection tools.
- Never bypass an `unsupported`, `unsafe`, changed-file, backup, or artifact
  refusal.
- Do not replace `libScePad_original.dll` manually or use someone else's game
  files.

Installation is byte-exact and fail-closed. It verifies `Flower.exe`, the
original ScePad DLL, `steam_api64.dll`, the bundled bridge, and the bundled action
manifest; creates and verifies a no-clobber original backup; atomically replaces
managed files; and coordinates rollback when safe if the second install step
fails. Unknown files and account-owned Steam controller layouts are never
overwritten or deleted.

Per-file atomic replacement is not an all-or-nothing transaction. An error,
interruption, or unsuccessful rollback can leave partial state; preserve verified
backups and inspect `status` before retrying.

## Steam Deck / Linux

Extract the bundle and double-click
[INSTALL_GYRO_BRIDGE_LINUX.sh](INSTALL_GYRO_BRIDGE_LINUX.sh). If your file manager
asks what to do, choose **Run** or **Execute in Terminal**. The
launcher opens a terminal, runs the same verified installer, and waits so you can
read the result.

To undo the fix, double-click
[REVERT_GYRO_BRIDGE_LINUX.sh](REVERT_GYRO_BRIDGE_LINUX.sh). If an extractor
removed executable permission, restore it once with:

```sh
chmod +x INSTALL_GYRO_BRIDGE_LINUX.sh REVERT_GYRO_BRIDGE_LINUX.sh
```

The direct commands remain available, including for nonstandard locations:

```sh
python3 gyro_bridge/install_gyro_bridge.py install
python3 gyro_bridge/install_gyro_bridge.py install --game-dir "/path/to/steamapps/common/Flower" --steam-dir "/path/to/Steam"
python3 gyro_bridge/install_gyro_bridge.py restore
```

## Windows

Native Windows execution is unverified. The launchers are provided for careful
review and testing, not as Windows certification.

Extract the bundle and double-click
[INSTALL_GYRO_BRIDGE_WINDOWS.cmd](INSTALL_GYRO_BRIDGE_WINDOWS.cmd). To undo the
fix, double-click [REVERT_GYRO_BRIDGE_WINDOWS.cmd](REVERT_GYRO_BRIDGE_WINDOWS.cmd).
Each window stays open so you can read the result.

The direct PowerShell commands remain available, including for nonstandard
locations:

```powershell
py -3 .\gyro_bridge\install_gyro_bridge.py install
py -3 .\gyro_bridge\install_gyro_bridge.py install --game-dir "D:\SteamLibrary\steamapps\common\Flower" --steam-dir "C:\Program Files (x86)\Steam"
py -3 .\gyro_bridge\install_gyro_bridge.py restore
```

## Read status safely

A healthy installation reports:

- `Overall state: installed`
- `Active DLL state: bridge`
- `Original backup state: original`
- `Bridge artifact state: bridge`
- `Flower.exe state: supported`
- `steam_api64.dll state: supported`
- `Action manifest state: manifest`
- `Action manifest artifact state: manifest`

`original` is a healthy uninstalled state. `upgrade-available` is an exact
recognized historical bridge with a verified backup. A state ending in
`without-verified-backup`, or an `unsupported`, `unsafe`, `changed-during-read`,
or `missing` state, is a stop condition—not a reason to force installation.

Restore removes only an exact project-managed action manifest before atomically
reactivating the verified original ScePad DLL. That order is deliberate: if
restore is interrupted after manifest removal, the proxy has no named actions to
own and delegates complete reads to the original provider. Restore leaves
`Flower.cfg` and Personal, Community, Official, and Recommended layouts alone.
Fully exit and restart Steam after a managed manifest is removed.

If the active DLL or backup cannot be restored safely, do not fabricate a backup.
Stop the installer, use Steam's **Verify integrity of game files**, wait for it to
finish, and then run `restore` again so an exact managed manifest can be removed.
The command rechecks both managed locations; an unknown manifest is preserved.

## Restart Steam and create/select a layout

After install:

1. Fully exit and restart Steam so it reloads
   `game_actions_966330.vdf`.
2. Enable Steam Input for adapter mode.
3. Explicitly select, import, or create a layout for **Flower Virtual PS4
   Controller** and bind each physical control to the matching raw PS4 action.
   The installer cannot publish or auto-select an Official/Recommended layout.
4. For stick steering, bind `left_stick` or `right_stick` and select the matching
   `PadDualShock` value (`AnalogueLeft` or `AnalogueRight`) while Flower is
   closed.
5. For motion steering, use the exact setup below and set
   `PadDualShock="TiltControl"` in `Documents/Flower/Flower.cfg` while Flower is
   closed.

A direct DualShock 4 path is separate: Steam Input disabled → original ScePad →
Flower. Adapter mode is Steam Input enabled → named actions → bridge → Flower.

## Exact gyro setup

Set Steam **Gyro Behavior** to **Controller Tilt**, targeting
`flower_ps4/tilt`:

- Activation: **Always On**.
- **Use Relative Pitch**: Off.
- **Use Relative Roll**: Off.
- **World Tilt Offset** / neutral angle: start at 0°, then set it to the real,
  comfortable holding angle so the held controller produces neutral output.
- Response curve: Linear.
- Minimum/maximum deflection angle: 0° / 45°.
- Minimum/maximum output: 0% / 100%.
- **Lock at Edges**: Off.
- **Drag Center Point**: Off.
- Horizontal/vertical inversion: Off initially; change a sign only after a real
  four-direction test.

Both relative axes must remain off: despite the UI wording, this makes Steam
measure roll and pitch against Earth's horizon. The bridge clamps each axis
independently to ±45° and reconstructs a unit gravity vector.

Steam's two deadzone/ramp handles are not interchangeable:

- The **left handle is the no-output boundary and start of the ramp**. Raise only
  it slightly to suppress stationary noise or residual drift; about 2–5% is often
  enough.
- The **right handle is the end of the ramp and start of maximum output**. Set it
  so full action output is reached at about 45° of physical tilt. If Steam shows
  the control against a 90° range, 45° is 50%; do not blindly set the right
  handle to 100%.

Calibrate before compensating in the layout. First run Steam's **manual gyro
calibration** with the controller motionless on a stable surface. Use background
auto-calibration only if manual calibration plus a small left/no-output boundary
is insufficient; auto-calibration can mistake very slow intentional tilt for
drift on some controller/Steam combinations.

## Exact compatibility and artifact hashes

### Game files required for installation

| File | Bytes | SHA-256 |
|---|---:|---|
| `Flower.exe` | 20,867,456 | `649b7b64db42146314ac0a0e55d5faf03194eba21ca9c791706ce827570d3aca` |
| Original `libScePad.dll` / verified `libScePad_original.dll` | 128,512 | `7d9a71a8a51bd6e81b6fb7835fea2c20e4f8f9e331ff26dd8ac09692ceb33de8` |
| `steam_api64.dll` | 242,976 | `38f6a1dd1e738e142160322638dae7b88dabcc30eea3f15c58eb08c5341f9b29` |

### Installer-managed `0.4.4` artifacts

Component/installer `0.4.5` manages these unchanged native `0.4.4` artifacts:

| Archive file | Bytes | SHA-256 |
|---|---:|---|
| `gyro_bridge/dist/libScePad.dll` | 84,992 | `adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c` |
| `gyro_bridge/steam_input/game_actions_966330.vdf` | 2,438 | `8d3f5ab9b5a321ab3f6162935a8810642b08c307780a6356d75c102e8ce64b13` |

Do not update or bypass these fingerprints to make an unknown build install.

## Validation limits

Existing validation of the `0.4.4` native artifacts includes a deterministic
LLVM-MinGW/Proton smoke matrix using independent fake Steam/ScePad providers.
It covers all 17 raw actions, two-slot
isolation, whole-provider fallback, ±45° conversion, reconnect ownership,
native output routing, blocked Steam calls, stale-state recovery, and export
surface without XInput or raw-motion dependencies.

Prior informal real gameplay exercised gyro with one 8BitDo controller. These
records do not claim fresh gameplay validation for component/installer `0.4.5`
or bundle `1.2.0`. This is not broad controller, Steam-client, rumble, lightbar,
hotplug, or hardware certification. Native Windows remains unverified. Treat
devices other than the one informally exercised as interoperability targets,
not certified hardware.

At runtime, unavailable, inactive, disconnected, or older-than-250-ms Steam
state loses ownership of the whole slot and delegates the complete read to the
original provider; Steam and original fields are never blended.

## Privacy and proprietary files

This archive contains an independently implemented bridge, not Flower, Valve,
Steamworks, or Sony binaries. Never upload or redistribute `Flower.exe`, the
original ScePad DLL, `steam_api64.dll`, game assets, controller profiles, a game
or Proton-prefix archive, reverse-engineering data, crash dumps, or full logs.
Redact absolute paths, Steam/account IDs, controller serials, Bluetooth
addresses, USB/device IDs, and unrelated environment data from minimal pasted
text. Do not upload `flower_input_bridge.log`; paste only necessary redacted
lines.

## License and notices

Project source and documentation are provided under the [MIT License](LICENSE).
The binary includes runtime portions built with the pinned llvm-mingw toolchain;
read [Third-party notices](THIRD_PARTY_NOTICES.md), the
[LLVM license text](licenses/LLVM.txt), and the
[MinGW-w64 runtime notices](licenses/MINGW-W64-RUNTIME.txt). Keep all notice and
license files with redistributed copies of the bridge DLL.

Repository-only guidance:

- [Support](https://github.com/natryamar/flower-steam-fixes/blob/main/SUPPORT.md)
- [Private security reporting](https://github.com/natryamar/flower-steam-fixes/blob/main/SECURITY.md)
- [Troubleshooting and safe recovery](https://github.com/natryamar/flower-steam-fixes/blob/main/docs/TROUBLESHOOTING.md)
- [Changelog](https://github.com/natryamar/flower-steam-fixes/blob/main/CHANGELOG.md)
