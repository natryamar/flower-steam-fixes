# Flower Steam fixes

Unofficial, reversible fixes for the Steam release of **Flower**. Users provide
their own legitimate game installation; this project contains no original game
executable, DLL, audio, bank, or other game asset.

> [!IMPORTANT]
> Both components support only Flower Steam build `4354278` (App ID `966330`).
> The installers deliberately refuse unknown or modified files. Never bypass an
> exact-hash, backup, or safety refusal.

## Choose the fix you need

The two components are independent. Install either one or both.

| Component | Version | What it fixes or enables | Validation |
|---|---:|---|---|
| [Hay-bale sound fix](#hay-bale-sound-fix) | `1.0.0` | Removes the unrelated landing sting from one nighttime hay-bale activation | Gameplay-confirmed on SteamOS/Proton |
| [Native ScePad Steam Input bridge](#native-scepad-steam-input-bridge) | `0.4.4` | Lets Steam Input controllers drive Flower's native PS4-style buttons, sticks, rumble/lightbar path, and tilt steering | Deterministic native smoke coverage plus informal real 8BitDo gyro gameplay testing; not broad hardware certification |

See [`SUPPORT.md`](SUPPORT.md) for the exact support and validation matrix.
Native Windows execution has not yet been verified.

## Download and verify

Use component archives from the repository's
[GitHub Releases](https://github.com/natryamar/flower-steam-fixes/releases) page
once a tagged release is published. Each public release must include
`SHA256SUMS`; verify it before running an installer. Do not redistribute an ad
hoc ZIP of a working directory or an untagged DLL from another source.

Developers and reviewers can build the same deterministic archives with:

```sh
python3 tools/build_release.py --component all --ref HEAD \
  --output-dir /path/to/new-empty-output
```

The packager reads an explicit allowlist from Git objects, excludes local
workspace files, and writes reproducible component ZIPs plus `SHA256SUMS`.
Release procedure and binary provenance are documented in
[`RELEASING.md`](RELEASING.md) and
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Safety before installation

- Python `3.10` or newer is required; the installers use only the standard
  library.
- Close Flower before installing, restoring, or editing `Flower.cfg`.
- Do not run an installer while Steam is updating or verifying Flower.
- Start with `status`, then run the intended write operation with `--dry-run`.
- Keep the downloaded archive layout intact. The bridge installer verifies the
  bundled DLL and action manifest beside its own source tree.
- Do not use someone else's game files or replace a verified backup manually.
- If a tool reports `unsupported`, `unsafe`, or a changed file, stop and follow
  [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

## Hay-bale sound fix

The Steam build contains an unrelated landing sting in one entry of the
nighttime hay-bale completion cycle. `flower_haybale_fix.py` changes three bytes
in the exact supported `Level4_A.bnk`, replacing that bad reference with a
present, valid hay transformation sound. It does not add or redistribute audio.

The script creates and verifies a no-clobber original backup, uses a synced
temporary file and atomic replacement, refuses linked or unknown files, detects
an installed fix, and restores only from the verified backup.

### Steam Deck / Linux

From the extracted release or repository root:

```sh
python3 flower_haybale_fix.py status
python3 flower_haybale_fix.py install --dry-run
python3 flower_haybale_fix.py install
python3 flower_haybale_fix.py status
```

For a nonstandard library, add:

```sh
--game-dir "/path/to/steamapps/common/Flower"
```

### Windows

Extract the release, open PowerShell in that directory, and run:

```powershell
py -3.10 flower_haybale_fix.py status
py -3.10 flower_haybale_fix.py install --dry-run
py -3.10 flower_haybale_fix.py install
py -3.10 flower_haybale_fix.py status
```

If automatic discovery does not find Flower, pass the full game directory with
`--game-dir`.

### Restore

```sh
python3 flower_haybale_fix.py restore --dry-run
python3 flower_haybale_fix.py restore
python3 flower_haybale_fix.py status
```

On Windows, replace `python3` with `py -3.10`. The verified backup remains at:

```text
Data/Sounds/Level4_A.bnk.flower-haybale-fix.original
```

Steam's **Verify integrity of game files** can restore the official bank when a
verified local restore is unavailable. Never run Steam verification concurrently
with this script.

### Supported bank hashes

| State | SHA-256 |
|---|---|
| Original | `17e112eeed5f40baa14b9e1838c9373d3d3a84f394c1bef6a371599dcdc65728` |
| Patched | `c61b23587a8edd69b2201d918e8ee5a401f4f34ef272daa35b614f1d1f9c4012` |

Technical audio findings are in [`docs/analysis.md`](docs/analysis.md).

## Native ScePad Steam Input bridge

`gyro_bridge/` is an advanced adapter from Steam Input's named actions to the
native ScePad path used by Flower. It exposes a raw virtual PS4-style surface:
two sticks, D-pad, face/shoulder/menu controls, and a gravity-relative `tilt`
action. It does not emulate XInput or poll Steam's raw motion API.

Installation preserves and verifies Flower's original `libScePad.dll`, installs
the exact project bridge and local action schema atomically, and coordinates
rollback if either managed step fails. It never creates, selects, edits, or
deletes an account-owned Steam controller layout.

### Install on Steam Deck / Linux

```sh
python3 gyro_bridge/install_gyro_bridge.py status
python3 gyro_bridge/install_gyro_bridge.py install --dry-run
python3 gyro_bridge/install_gyro_bridge.py install
python3 gyro_bridge/install_gyro_bridge.py status
```

For nonstandard locations, add `--game-dir "/path/to/Flower"` and
`--steam-dir "/path/to/Steam"`.

### Install on Windows

Extract the bridge release, close Flower, open PowerShell in the extracted
folder, and run:

```powershell
py -3.10 gyro_bridge/install_gyro_bridge.py status
py -3.10 gyro_bridge/install_gyro_bridge.py install --dry-run
py -3.10 gyro_bridge/install_gyro_bridge.py install
py -3.10 gyro_bridge/install_gyro_bridge.py status
```

Windows is documented for review and testing but is not yet a validated support
target.

### Configure Steam Input

After installation:

1. Fully exit and restart Steam so it reloads the local action schema.
2. Explicitly select or create a layout for **Flower Virtual PS4 Controller**.
3. Bind each physical control to the matching raw action.
4. For motion, set **Gyro Behavior** to **Controller Tilt**, keep both relative
   axes off, and follow the exact neutral-angle, calibration, deadzone, and ±45°
   setup in [`gyro_bridge/README.md`](gyro_bridge/README.md#restart-steam-and-select-a-layout).
5. With Flower closed, select the matching `PadDualShock` steering behavior in
   `Documents/Flower/Flower.cfg`: `AnalogueLeft`, `AnalogueRight`, or
   `TiltControl` for motion.

The project cannot publish or auto-select an Official/Recommended layout without
Flower's Steamworks publisher access. Layout selection remains an explicit user
action.

### Restore

```sh
python3 gyro_bridge/install_gyro_bridge.py restore --dry-run
python3 gyro_bridge/install_gyro_bridge.py restore
python3 gyro_bridge/install_gyro_bridge.py status
```

On Windows, replace `python3` with `py -3.10`. After a managed action manifest is
removed, fully exit and restart Steam. Restore leaves account-owned layouts and
`Flower.cfg` unchanged.

Full compatibility hashes, historical managed signatures, runtime design, and
validation details are in:

- [`gyro_bridge/README.md`](gyro_bridge/README.md)
- [`docs/STEAM_INPUT_ACTIONS.md`](docs/STEAM_INPUT_ACTIONS.md)
- [`docs/NATIVE_SCEPAD_ARCHITECTURE.md`](docs/NATIVE_SCEPAD_ARCHITECTURE.md)

## Development

The `[project]` table in `pyproject.toml` is repository metadata; these tools are
run directly and the repository is not currently distributed as a pip package.

```sh
python3 -m unittest discover -s tests -v
python3 gyro_bridge/build.py --write-compile-commands  # local clangd/Zed metadata
python3 gyro_bridge/build.py --verify-release
python3 gyro_bridge/test.py
python3 tools/build_release.py --component all --ref HEAD \
  --output-dir /tmp/flower-releases
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) before submitting changes. Temporary
toolchains, Proton prefixes, fake binaries, logs, controller profiles, and
reverse-engineering workspaces belong only under ignored `re-temp/`.

## Project policies

- [Support and validation](SUPPORT.md)
- [Troubleshooting and safe recovery](docs/TROUBLESHOOTING.md)
- [Security reporting](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Release process](RELEASING.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## AI-assisted development

This project was developed with extensive AI coding assistance—in other words,
it was openly **vibe coded**. The maintainer directed the behavior, tested the
fixes on the supported game build, reviewed the resulting changes, and added
repeatable safety, installer, native-smoke, privacy, and release checks.

AI assistance is not proof that software is correct. The source is provided so
others can inspect it, and compatibility remains deliberately limited to the
exact tested files. Review the code and the documented validation boundaries
before installing it; careful human review and reproducible bug reports are
welcome.

## Donations

If these fixes helped and you voluntarily want to support their maintenance,
you can donate Monero (XMR). Donations are optional and do not purchase support,
features, compatibility work, or faster responses.

**XMR address:**

```text
87dpgD3rcSY59Uja8wL7dW68eGEe8L7zdgUdauwgTnPcMMX4k1N6VYMAYgwtnrT4e5chGDYaBoT1LXrSQF1VXDMANNWZGWB
```

Before donating, verify the address in the canonical repository rather than a
reposted archive or screenshot.

## Distribution, trademarks, and legal note

Do not add or distribute Flower executables, original DLLs, Steam API DLLs,
banks, extracted audio, controller profiles, reverse-engineering workspaces, or
other proprietary material. Users must provide their own legitimate Steam
installation.

This project is unofficial and is not affiliated with or endorsed by
thatgamecompany, Annapurna Interactive, Sony, Valve, or the PC port's developers
or publishers. Flower, Steam, Steam Input, PlayStation, PS4, DualShock,
DualSense, and other names and marks belong to their respective owners and are
used only to identify interoperability targets. Laws and license terms vary;
this repository is not legal advice.

Project-authored source and documentation are licensed under the
[MIT License](LICENSE). Binary distributions also include the notices described
in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
