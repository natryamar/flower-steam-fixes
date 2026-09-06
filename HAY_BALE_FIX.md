# Flower hay-bale sound fix

- **Component / installer version:** `1.0.1`
- **Supported game:** Flower on Steam, App ID `966330`, build `4354278`
- **Requirement:** Python `3.10` or newer; no third-party Python packages

This unofficial, reversible fix corrects one nighttime hay-bale activation that
plays an unrelated landing sting. It changes three bytes in the exact supported
`Data/Sounds/Level4_A.bnk`, reusing a valid hay transformation sound already in
the installation. It does not include, download, or reconstruct game audio.

This component is included in the unified `flower-steam-fixes-1.2.0.zip` bundle
(`v1.2.0`), not in a separate component archive. The bundle
contains the [installer source](flower_haybale_fix.py) and the project's
[MIT License](LICENSE).

## Safety first

- Close Flower before status-changing operations.
- Let Steam finish or pause updates and file verification before running the
  script.
- `install` and `restore` perform their own full preflight and final verification;
  `status` and `--dry-run` are optional inspection tools.
- Never bypass an `unsupported`, `unsafe`, changed-file, or backup refusal.
- Never replace the verified backup with a downloaded or borrowed game file.

The script accepts only exact hashes, refuses linked or concurrently changing
files, creates a verified no-clobber original backup, prepares a synced temporary
copy, and uses atomic replacement. These per-file safeguards do not guarantee
that an error or interruption leaves no partial state. Preserve the verified
backup and inspect `status` before retrying.

## Steam Deck / Linux

Extract the bundle and double-click
[INSTALL_HAY_BALE_LINUX.sh](INSTALL_HAY_BALE_LINUX.sh). If your file manager asks
what to do, choose **Run** or **Execute in Terminal**. The
launcher opens a terminal, runs the same verified installer, and waits so you can
read the result.

To undo the fix, double-click
[REVERT_HAY_BALE_LINUX.sh](REVERT_HAY_BALE_LINUX.sh). If an extractor removed
executable permission, restore it once with:

```sh
chmod +x INSTALL_HAY_BALE_LINUX.sh REVERT_HAY_BALE_LINUX.sh
```

The direct commands remain available, including for a nonstandard Steam library:

```sh
python3 flower_haybale_fix.py install
python3 flower_haybale_fix.py install --game-dir "/path/to/steamapps/common/Flower"
python3 flower_haybale_fix.py restore
```

## Windows

Native Windows use has not been verified. The launchers provide a Windows path
for careful testing; this is not a Windows support certification.

Extract the bundle and double-click
[INSTALL_HAY_BALE_WINDOWS.cmd](INSTALL_HAY_BALE_WINDOWS.cmd). To undo the fix,
double-click [REVERT_HAY_BALE_WINDOWS.cmd](REVERT_HAY_BALE_WINDOWS.cmd). Each
window stays open so you can read the result.

The direct PowerShell commands remain available, including for a nonstandard
library:

```powershell
py -3 .\flower_haybale_fix.py install
py -3 .\flower_haybale_fix.py install --game-dir "D:\SteamLibrary\steamapps\common\Flower"
py -3 .\flower_haybale_fix.py restore
```

## Status and safe recovery

A successful action verifies the final state before printing its result. Use
`status` when you want a read-only inspection, or append `--dry-run` for an
optional preview.

A healthy uninstalled bank reports `State: original`. A healthy installed fix
reports both:

- `State: patched`
- `Backup state: original`

The verified backup remains at:

```text
Data/Sounds/Level4_A.bnk.flower-haybale-fix.original
```

`patched` without an `original` backup is intentionally not treated as a safe,
reversible installation. `missing`, `unsupported`, `unsafe`, or
`changed-during-read` means the script will stop instead of overwriting the
file. Check the game path, supported build, mods, links, and concurrent Steam
activity; do not force the operation.

Restore accepts only the exact patched bank and exact verified backup. If that
safe local restore is unavailable, stop the script and use Steam's **Verify
integrity of game files**. Wait for verification to finish before running
`status` again. Steam verification can replace other modified game files and
must never run concurrently with this script.

## Exact supported bank

| State | Bytes | SHA-256 |
|---|---:|---|
| Original | 46,780,694 | `17e112eeed5f40baa14b9e1838c9373d3d3a84f394c1bef6a371599dcdc65728` |
| Patched | 46,780,694 | `c61b23587a8edd69b2201d918e8ee5a401f4f34ef272daa35b614f1d1f9c4012` |

These fingerprints apply only to Steam build `4354278`. A different hash is not
permission to add it to the allowlist.

## Validation limits

Recorded gameplay validation is for version `1.0.0` on build `4354278` under
SteamOS/Proton: all five nighttime hay-bale activations play appropriate hay
transformation sounds and the unrelated landing sting is gone. Those results
are historical, not a new gameplay pass for installer `1.0.1` or bundle `1.2.0`.
Native Windows gameplay remains unverified. This project is unofficial and
unaffiliated with the game's owners, developers, or publishers.

## Privacy and support

Do not upload or redistribute `Flower.exe`, DLLs, `.bnk` files, audio, extracted
assets, a game-directory archive, controller profiles, or full logs. Status
output contains local paths; redact absolute paths plus any Steam/account or
device identifiers before sharing a minimal text excerpt.

Repository-only guidance:

- [Support](https://github.com/natryamar/flower-steam-fixes/blob/main/SUPPORT.md)
- [Private security reporting](https://github.com/natryamar/flower-steam-fixes/blob/main/SECURITY.md)
- [Troubleshooting and safe recovery](https://github.com/natryamar/flower-steam-fixes/blob/main/docs/TROUBLESHOOTING.md)
- [Changelog](https://github.com/natryamar/flower-steam-fixes/blob/main/CHANGELOG.md)
