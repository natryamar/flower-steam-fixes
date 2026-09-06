# Troubleshooting

These instructions apply to umbrella/bundle `1.2.0` (`v1.2.0`), hay-bale
installer `1.0.1`, and native ScePad bridge component/installer `0.4.5`, targeting
only Flower Steam build `4354278` (App ID `966330`). The bridge DLL and action
manifest remain unchanged native `0.4.4` artifacts with the same exact sizes and
hashes. Unknown builds are intentionally unsupported.

## Safety rules

1. Close Flower before `install` or `restore` and before editing `Flower.cfg`.
2. Do not run a project tool while Steam is updating or verifying Flower.
3. `install` and `restore` perform their own full preflight and final
   verification. Use `status` or `--dry-run` only for read-only diagnosis or an
   optional preview.
4. Do not delete, rename, replace, or download a substitute for a verified
   backup. Do not bypass a hash check.
5. If a file changes during inspection, stop every updater, verifier, editor, and
   copy operation touching it, then retry from `status`.
6. Never use someone else's game file. Steam's own **Verify integrity of game
   files** is the supported fallback when local verified restoration is
   impossible.

For a nonstandard Steam library, add `--game-dir "/path/to/Flower"`. The bridge
may also need `--steam-dir "/path/to/Steam"`.

## What fail-closed means

The installers identify files by exact size and SHA-256. A refusal is a safety
result, not a prompt to force installation. On an unknown, unsafe, or changing
state they stop rather than intentionally overwrite a managed target.

Common inspection states are:

| State | Meaning | Safe next step |
|---|---|---|
| `original` | Exact supported original | A verified install may proceed |
| `patched` / `bridge` | Exact current managed file | Confirm the verified original backup exists |
| `historical-bridge` | Exact recognized prior managed bridge | Current installer may safely upgrade or restore it |
| `missing` | Path or file was not found | Check the explicit directory and Steam library |
| `unsupported` | Size/hash is unknown | Do not force; check the build, mods, and Steam update state |
| `unsafe` | Not a single regular file, such as a symlink or hard-linked file | Restore a normal Steam-managed file; do not relink it |
| `changed-during-read` | Another process changed the file while it was hashed | Stop concurrent activity and retry |

Low disk space, a mismatched bundled artifact, a corrupt/missing backup, or a
file changing just before replacement also causes a refusal. Temporary copies
are verified before atomic replacement and final targets are verified afterward.

These are per-file safeguards, not an all-or-nothing transaction. An error or
interruption can occur after a backup or managed file has changed, and bridge
rollback can proceed only when safe. Partial state can remain. Preserve verified
backups, read the error, and run the applicable `status` command before retrying;
follow the recovery steps below rather than forcing an operation.

## Hay-bale sound fix

### Check status

```sh
python3 flower_haybale_fix.py status
```

A healthy installed state is:

- `State: patched`; and
- `Backup state: original` for
  `Data/Sounds/Level4_A.bnk.flower-haybale-fix.original`.

`State: patched` without an `original` backup is deliberately not considered a
safe, reversible installation. Both install and restore refuse to invent or
replace that backup.

### Safe restore

```sh
python3 flower_haybale_fix.py restore
```

The restore accepts only the exact patched bank plus the exact verified original
backup. It copies and verifies the backup to a sibling temporary file, checks
both files again, atomically activates the original, and verifies the result.
The backup remains in place.

If restore reports a missing/corrupt backup or an unsupported target, do not
manually copy a `.bnk` file over it. Stop the script, use Steam's **Verify
integrity of game files**, wait for verification to finish, and then rerun
`status`. Verification can restore the official bank and may also replace other
modified game files. Never run verification concurrently with this tool.

### The patch installs but the sound seems wrong

Confirm all of the following:

- Steam reports build `4354278` for App `966330`;
- the status is `patched` with an `original` backup;
- the nighttime level's five separate hay-bale activations were tested; and
- Steam did not update or verify the bank after installation.

The fix intentionally reuses one valid hay transformation sound because only
four distinct recordings are present. It does not add missing audio.

## Native ScePad Steam Input bridge

### Check status and preconditions

```sh
python3 gyro_bridge/install_gyro_bridge.py status
```

A healthy installed state reports:

- `Overall state: installed`;
- `Active DLL state: bridge`;
- `Original backup state: original`;
- `Bridge artifact state: bridge`;
- `Flower.exe state: supported`;
- `steam_api64.dll state: supported`;
- `Action manifest state: manifest`; and
- `Action manifest artifact state: manifest`.

Other important overall states:

| Overall state | Meaning | Action |
|---|---|---|
| `original` | Official ScePad DLL is active | A verified install may proceed |
| `upgrade-available` | Recognized historical bridge plus verified backup | Current install or restore may proceed |
| `bridge-active-without-verified-backup` | Current bridge is active but safe restore is unavailable | Do not reinstall or fabricate a backup; use the recovery steps below |
| `historical-bridge-without-verified-backup` | Prior managed bridge is active without a verified backup | Do not upgrade; use the recovery steps below |
| `unsupported`, `unsafe`, `changed-during-read`, or `missing` | Active DLL cannot be managed safely | Stop and identify the file/build/concurrency problem |

An unknown action manifest is never overwritten or deleted. A historical exact
manifest may be upgraded or removed; a missing manifest is harmless to restore.
Account-owned controller profiles are outside the installer and remain untouched.

### Safe restore

Close Flower, then run:

```sh
python3 gyro_bridge/install_gyro_bridge.py restore
```

For nonstandard paths:

```sh
python3 gyro_bridge/install_gyro_bridge.py restore --game-dir "/path/to/steamapps/common/Flower" --steam-dir "/path/to/Steam"
```

Restore preflights both managed locations. It removes only an exact current or
historical project-managed action manifest, then atomically reinstates only the
verified `libScePad_original.dll`. This order is intentional: if restore is
interrupted after manifest removal, the still-active proxy has no named actions
to own and delegates complete reads to the original provider. It never blends
partial Steam and original state.

After a managed manifest is removed, fully exit and restart Steam. Restore does
not change `Flower.cfg` or any selected Personal, Community, Official, or
Recommended controller layout.

If `Flower.exe` or `steam_api64.dll` changed after installation, a verified
managed bridge can still be restored; compatibility checks are required for
install, not used to trap a user in an installation. If the active DLL is unknown
or the verified original backup is missing/corrupt:

1. Do not rename the unknown DLL or create a replacement backup.
2. Finish the failed tool operation and keep only redacted text of its output.
3. Use Steam's **Verify integrity of game files** and wait for completion.
4. Rerun bridge `status`.
5. If the official DLL is now `original`, run bridge `restore` again so an exact
   managed local action manifest can be removed.

The restore command preserves an unknown action manifest. Never manually delete
one unless you independently know it is yours and understand its purpose.

### Controller is not detected in adapter mode

The two controller paths are different:

- Direct DualShock 4: Steam Input disabled → original `libScePad` → Flower.
- Adapter mode: Steam Input enabled → `flower_ps4` named actions → bridge →
  Flower ScePad.

For adapter mode:

1. Confirm bridge status is healthy.
2. Fully exit and restart Steam after installing/updating the action manifest.
3. Enable Steam Input and explicitly select or create a layout for **Flower
   Virtual PS4 Controller**.
4. Bind the raw controls you expect to use. The project cannot publish or
   auto-select an Official/Recommended layout.
5. Remember that no active raw action means the bridge intentionally delegates
   the complete read to the original provider.

### Buttons work but steering does not

`PadDualShock` in `Documents/Flower/Flower.cfg` chooses steering behavior; it is
not a general native-controller enable switch. Edit it only while Flower is
closed:

- `AnalogueLeft` for `left_stick`;
- `AnalogueRight` for `right_stick`; or
- `TiltControl` only for motion steering from `tilt`.

For gyro, set Steam **Gyro Behavior** to **Controller Tilt**, target
`flower_ps4/tilt`, use gravity-relative roll/pitch, a linear 0°–45° range, and
start with horizontal/vertical inversion off. Correct signs only after a real
four-direction test. See
[`STEAM_INPUT_ACTIONS.md`](STEAM_INPUT_ACTIONS.md) for the complete layout
contract.

If level steering slowly drifts while the controller is stationary:

1. Run Steam's controller-level manual gyro calibration with the controller
   motionless on a stable surface.
2. Confirm the neutral angle matches the angle at which the controller is
   actually held.
3. Raise only Steam's left/no-output boundary slightly; it is the start of the
   ramp. The right handle is the end of the ramp/start of maximum output and
   should still reach full action output at roughly 45° (often 50% on a 90°
   display).
4. Use background auto-calibration only if manual calibration and a small
   no-output boundary are insufficient. It can misclassify very slow intentional
   tilt as drift on some controller/Steam combinations.

The bridge itself performs a stateless X/Y-to-gravity conversion and cannot
accumulate orientation drift.

### Input activates, then drops back

A Steam sample older than 250 ms deliberately loses ownership and the whole slot
returns to the original provider. Check controller connectivity, the selected
layout, and Steam client health. To capture a small diagnostic excerpt, launch
with:

```text
FLOWER_INPUT_DEBUG=1 %command%
```

The bridge writes `flower_input_bridge.log` beside its DLL. Look for worker
startup, `SteamController005` acquisition, resolution of `flower_ps4` plus 17
actions, and slot ownership. Do not upload the log file. Paste only the few
relevant lines after redacting absolute paths and account/device identifiers.
Disable the debug launch option after diagnosis.

## Validation limits

Recorded hay-bale gameplay validation is for `1.0.0` under SteamOS/Proton.
Bridge `0.4.4` has deterministic native smoke coverage under Proton and prior
informal real gameplay testing of gyro with an 8BitDo controller. These records
do not establish a new gameplay pass for bundle `1.2.0` or its updated installers,
nor broad controller, rumble, lightbar, hotplug, or Steam-client certification.
Native Windows remains unverified; reports are useful, but Windows behavior
should not be described as confirmed support.

If the steps above do not resolve a non-security problem, open the repository's
bug report form. Do not upload proprietary game files, controller profiles, full
logs, or directory archives. Follow [`SECURITY.md`](../SECURITY.md) for private
vulnerability reports.
