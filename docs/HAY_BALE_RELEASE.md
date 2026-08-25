# Flower hay-bale sound fix

- **Component version:** `1.0.0`
- **Supported game:** Flower on Steam, App ID `966330`, build `4354278`
- **Requirement:** Python `3.10` or newer; no third-party Python packages

This unofficial, reversible fix corrects one nighttime hay-bale activation that
plays an unrelated landing sting. It changes three bytes in the exact supported
`Data/Sounds/Level4_A.bnk`, reusing a valid hay transformation sound already in
the installation. It does not include, download, or reconstruct game audio.

The archive contains the [installer source](flower_haybale_fix.py) and the
project's [MIT License](LICENSE).

## Safety first

- Close Flower before status-changing operations.
- Let Steam finish or pause updates and file verification before running the
  script.
- Run `status`, then `install --dry-run` or `restore --dry-run`, before any write.
- Never bypass an `unsupported`, `unsafe`, changed-file, or backup refusal.
- Never replace the verified backup with a downloaded or borrowed game file.

The script accepts only exact hashes, refuses linked or concurrently changing
files, creates a verified no-clobber original backup, prepares a synced temporary
copy, and uses atomic replacement.

## Steam Deck / Linux

Extract the archive, open a terminal in its root, and check before installing:

```sh
python3 flower_haybale_fix.py status
python3 flower_haybale_fix.py install --dry-run
python3 flower_haybale_fix.py install
python3 flower_haybale_fix.py status
```

For a nonstandard Steam library, add the Flower directory explicitly:

```sh
python3 flower_haybale_fix.py status \
  --game-dir "/path/to/steamapps/common/Flower"
```

Safe restore:

```sh
python3 flower_haybale_fix.py restore --dry-run
python3 flower_haybale_fix.py restore
python3 flower_haybale_fix.py status
```

## Windows

Native Windows use has not been verified. The script provides a Windows command
path for careful testing; this is not a Windows support certification.

Extract the archive, close Flower, open PowerShell in the archive root, and run:

```powershell
py -3.10 .\flower_haybale_fix.py status
py -3.10 .\flower_haybale_fix.py install --dry-run
py -3.10 .\flower_haybale_fix.py install
py -3.10 .\flower_haybale_fix.py status
```

For a nonstandard library:

```powershell
py -3.10 .\flower_haybale_fix.py status `
  --game-dir "D:\SteamLibrary\steamapps\common\Flower"
```

Safe restore:

```powershell
py -3.10 .\flower_haybale_fix.py restore --dry-run
py -3.10 .\flower_haybale_fix.py restore
py -3.10 .\flower_haybale_fix.py status
```

## Status and safe recovery

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

Version `1.0.0` is gameplay-confirmed on build `4354278` under SteamOS/Proton:
all five nighttime hay-bale activations play appropriate hay transformation
sounds and the unrelated landing sting is gone. Native Windows gameplay remains
unverified. This project is unofficial and unaffiliated with the game's owners,
developers, or publishers.

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
