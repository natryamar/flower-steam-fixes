# Flower Steam fixes

- **Bundle version:** `1.2.0` (tag `v1.2.0`)
- **Supported game:** Flower on Steam, App ID `966330`, build `4354278`
- **Requirement:** Python `3.10` or newer; no third-party Python packages

The unified `v1.2.0` release provides one ready-to-run download,
`flower-steam-fixes-1.2.0.zip`, plus `SHA256SUMS`. The two unofficial, reversible
fixes are independent: install either one, both, or neither.

| Component | Component / installer version | Purpose | Detailed guide |
|---|---:|---|---|
| Hay-bale sound fix | `1.0.1` | Removes an unrelated landing sting from one nighttime hay-bale activation | [HAY_BALE_FIX.md](HAY_BALE_FIX.md) |
| Native ScePad Steam Input bridge | `0.4.5` | Enables native-style controls and tilt steering through a user-selected Steam Input layout | [GYRO_BRIDGE.md](GYRO_BRIDGE.md) |

Bridge component/installer `0.4.5` retains the unchanged native DLL and action
manifest built for `0.4.4`, with the same exact sizes and hashes. These installer
version updates do not imply newly run gameplay or native Windows validation;
see the component guides for the recorded validation limits.

## Before running anything

1. Verify the ZIP against `SHA256SUMS` from the same release.
2. Extract the entire ZIP. Do not run launchers from inside the archive preview.
3. Close Flower.
4. Let Steam finish any update or file verification.
5. Keep the extracted folders and files together.

Install and revert perform exact-hash preflight and final verification, use
atomic replacement for individual managed files, and preserve verified backups.
Bridge installation coordinates rollback when safe. These safeguards do not make
multi-step operations interruption-proof. The launchers only run the existing
Python installers; they do not bypass any safety check.

## Click the action you want

### Steam Deck / Linux

If the file manager asks what to do, choose **Run** or **Execute in Terminal**.
The launcher opens a terminal and keeps it visible so you can read the result.

| Action | Launcher |
|---|---|
| Install hay-bale sound fix | [INSTALL_HAY_BALE_LINUX.sh](INSTALL_HAY_BALE_LINUX.sh) |
| Revert hay-bale sound fix | [REVERT_HAY_BALE_LINUX.sh](REVERT_HAY_BALE_LINUX.sh) |
| Install native ScePad/gyro bridge | [INSTALL_GYRO_BRIDGE_LINUX.sh](INSTALL_GYRO_BRIDGE_LINUX.sh) |
| Revert native ScePad/gyro bridge | [REVERT_GYRO_BRIDGE_LINUX.sh](REVERT_GYRO_BRIDGE_LINUX.sh) |

The release preserves executable permissions. If an extractor removes them, run
this once from the extracted directory:

```sh
chmod +x *_LINUX.sh
```

### Windows

Native Windows execution has not yet been verified. These launchers are included
for careful testing, not as Windows support certification. Each command window
stays open so you can read the result.

| Action | Launcher |
|---|---|
| Install hay-bale sound fix | [INSTALL_HAY_BALE_WINDOWS.cmd](INSTALL_HAY_BALE_WINDOWS.cmd) |
| Revert hay-bale sound fix | [REVERT_HAY_BALE_WINDOWS.cmd](REVERT_HAY_BALE_WINDOWS.cmd) |
| Install native ScePad/gyro bridge | [INSTALL_GYRO_BRIDGE_WINDOWS.cmd](INSTALL_GYRO_BRIDGE_WINDOWS.cmd) |
| Revert native ScePad/gyro bridge | [REVERT_GYRO_BRIDGE_WINDOWS.cmd](REVERT_GYRO_BRIDGE_WINDOWS.cmd) |

## Result messages

A completed install prints:

```text
Success.
```

A completed revert prints:

```text
Fix reverted.
```

Errors remain descriptive, but an error, interruption, or unsuccessful rollback
can leave partial state. Keep verified backups, read the error, and run the
relevant installer's `status` command before retrying. Follow the safe-recovery
steps in [HAY_BALE_FIX.md](HAY_BALE_FIX.md#status-and-safe-recovery) or
[GYRO_BRIDGE.md](GYRO_BRIDGE.md#read-status-safely); never force past a refusal.

## Direct commands

The launchers are optional. The equivalent commands are:

```sh
python3 flower_haybale_fix.py install
python3 flower_haybale_fix.py restore
python3 gyro_bridge/install_gyro_bridge.py install
python3 gyro_bridge/install_gyro_bridge.py restore
```

For nonstandard Steam libraries, use the path options documented in the detailed
component guides.

## After installing the gyro bridge

Fully exit and restart Steam, then explicitly select or create a named-action
layout for **Flower Virtual PS4 Controller**. The project cannot publish or
select an Official/Recommended layout without publisher access. Follow the
controller and tilt setup in [GYRO_BRIDGE.md](GYRO_BRIDGE.md).

## Verification and legal notices

Verify the downloaded `flower-steam-fixes-1.2.0.zip` against the adjacent
`SHA256SUMS` from the same GitHub release before running it. Do not redistribute
an ad hoc working-directory ZIP.

The bundle contains no original Flower executable, DLL, bank, audio, controller
profile, or other game asset. Project source and documentation are under the
[MIT License](LICENSE). The independently implemented bridge includes runtime
portions covered by [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the
license texts under `licenses/`.

Repository guidance:

- [Support](https://github.com/natryamar/flower-steam-fixes/blob/main/SUPPORT.md)
- [Troubleshooting](https://github.com/natryamar/flower-steam-fixes/blob/main/docs/TROUBLESHOOTING.md)
- [Private security reporting](https://github.com/natryamar/flower-steam-fixes/security/advisories/new)
