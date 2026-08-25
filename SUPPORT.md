# Support

Flower Steam fixes is an unofficial, volunteer-maintained project. Support is
best-effort and limited to the exact compatibility target below.

## Supported scope

| Item | Current version | Support boundary |
|---|---:|---|
| Umbrella project | `1.1.0` | Current repository state |
| Hay-bale sound fix | `1.0.0` | Exact supported sound bank only |
| Native ScePad Steam Input bridge | `0.4.4` | Exact supported game files and bundled artifacts only |

The only supported game target is the Steam release of **Flower**, App ID
`966330`, build `4354278`. The installers intentionally refuse unknown,
modified, linked, or concurrently changing files. Historical bridge signatures
may be recognized for safe upgrade or restore; that does not make those releases
supported.

## Validation status

- The hay-bale fix is gameplay-confirmed on build `4354278` under
  SteamOS/Proton: all five nighttime activations use appropriate hay sounds and
  the unrelated landing sting is gone.
- Bridge `0.4.4` has a deterministic native smoke matrix using LLVM-MinGW,
  independent fake Steam/ScePad DLLs, and an isolated Proton prefix.
- Informal real-device gameplay testing has exercised bridge gyro input with an
  8BitDo controller.
- The bridge does **not** have broad controller, rumble, lightbar, hotplug,
  Steam-client, or hardware certification. A successful test on one device does
  not establish support for every Steam Input controller.
- Native Windows execution has not been verified.

## Before requesting help

1. Read [`README.md`](README.md) and
   [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).
2. Close Flower. Do not run an installer while Steam is updating or verifying
   the game.
3. Run the applicable status command:

   ```sh
   python3 flower_haybale_fix.py status
   python3 gyro_bridge/install_gyro_bridge.py status
   ```

4. Before any install or restore, run the same operation with `--dry-run`.
   Never bypass a hash check or replace a backup just to make a refusal go away.

For nonstandard libraries, pass `--game-dir`; the bridge may also need
`--steam-dir`. See the troubleshooting guide for exact examples and safe restore
steps.

## Getting help

For reproducible, non-security problems, open a
[bug report](https://github.com/natryamar/flower-steam-fixes/issues/new?template=bug_report.yml).
Include:

- the affected component and version;
- Flower App ID/build ID;
- operating system, Steam channel, and Proton version when applicable;
- controller model/connection, Steam Input mode, selected layout, and
  `PadDualShock` value for bridge input problems;
- exact reproduction steps and expected/actual behavior; and
- redacted status output plus only the few relevant error/debug lines.

Do **not** upload Flower executables, DLLs, banks, audio, extracted game data,
Steam controller profiles, full logs, or a game-directory archive. Redact
absolute paths, Steam/account identifiers, and controller/device identifiers.
Public SHA-256 values already printed by the tools may remain visible.

Report suspected vulnerabilities privately as described in
[`SECURITY.md`](SECURITY.md), not in a public issue.

## Out of scope

Support cannot provide copyrighted game files, publish or auto-select a Steam
layout, make an unsupported build pass the allowlist, or guarantee compatibility
with a particular controller or native Windows. Questions about Steam accounts,
Steam client defects, Proton itself, or the base game may need to go to their
respective support channels.
