# Contributing

Contributions are welcome when they keep the fixes narrow, reversible, and safe
for users who provide their own legitimate Steam installation of Flower.

## Project boundaries

The current project contains:

- umbrella project `1.1.0`;
- hay-bale fix `1.0.0`; and
- native ScePad Steam Input bridge `0.4.4`.

Compatibility is byte-exact for Steam build `4354278` (App ID `966330`). Do not
relax an allowlist, add a force flag, or treat a new hash as compatible without a
separately justified and tested release update.

Keep these safety properties intact:

- install and restore remain explicit, hash-gated, atomic, and reversible;
- verified original backups are never silently replaced;
- unknown, linked, or concurrently changing files are refused;
- Steam controller profiles are never created, selected, edited, or deleted;
- Steam-owned and original ScePad fields are never blended; and
- unavailable or stale Steam state returns the complete read to the original
  provider.

## Prohibited content

Do not commit, attach to a pull request, or place in a test fixture:

- `Flower.exe`, original game DLLs, `steam_api64.dll`, banks, audio, extracted
  media, or any other proprietary game asset;
- Personal, Community, Official, or Recommended Steam controller profiles;
- logs, including `flower_input_bridge.log`, or crash dumps;
- real Proton prefixes, account data, controller/device identifiers, or reverse-
  engineering databases; or
- archives containing any of the above.

Tests must use synthetic files and independently written fake DLLs. Local
builds, temporary toolchains, generated test binaries, prefixes, profiles, and
logs belong only under ignored `re-temp/` and must remain local.

## Development setup

Python `3.10` or newer is required; the Python tools use only the standard
library. Native bridge work additionally needs `x86_64-w64-mingw32-clang++`
from LLVM-MinGW and Proton. Set `FLOWER_LLVM_MINGW` or place the documented
local toolchain under `re-temp/toolchain/`. `FLOWER_PROTON` may point to a Proton
launcher.

Never point bridge tests at Flower's real Proton prefix. The test runner accepts
only its dedicated ignored prefix under
`re-temp/prefixes/native-scepad-smoke`.

After installing the pinned cross-toolchain, generate correct local clangd/Zed
metadata with:

```sh
python3 gyro_bridge/build.py --write-compile-commands
```

The ignored `compile_commands.json` contains machine-local absolute paths. Never
commit or include it in an archive. Without it, a Linux editor may parse the
Windows source as a native Linux translation unit and report cascading errors
starting with `windows.h` not found.

## Current tests

The repository currently has these test suites and entry points:

| Suite or check | Command | Coverage |
|---|---|---|
| `tests/test_flower_haybale_fix.py` | `python3 -m unittest discover -s tests -v` | Hay-bale install/restore, dry-run, backup verification, idempotency, unknown-file and link refusal |
| `tests/test_gyro_bridge_installer.py` | `python3 -m unittest discover -s tests -v` | Bridge/action-manifest install, upgrade, rollback, restore, exact signatures, races/links, and preservation of unmanaged files |
| `tests/test_release_packaging.py` | `python3 -m unittest discover -s tests -v` | Explicit archive allowlists, Git-object provenance, deterministic ZIPs/checksums, and proprietary-file rejection |
| Native editor configuration | `python3 gyro_bridge/build.py --write-compile-commands` | Generates ignored local clangd metadata using the real Windows cross-target and headers |
| Native bridge release build | `python3 gyro_bridge/build.py --verify-release` | Requires the pinned LLVM-MinGW identity and reproduces the exact production DLL hash |
| `gyro_bridge/tests/native_scepad_smoke.cpp` | `python3 gyro_bridge/test.py` | Deterministic fake Steam/ScePad matrix under an isolated Proton prefix, including raw controls, two slots, whole-provider fallback, tilt conversion, native outputs, blocked calls, recovery, and export surface |
| Public tree/history audit | `python3 tools/audit_public_tree.py --history` | Rejects prohibited tracked artifacts, known private handoff history, user paths/account-scoped data, and common credential forms without printing matches |
| Public release packaging | `python3 tools/build_release.py --component all --ref HEAD --output-dir /tmp/flower-releases` | From a clean checkout, builds component archives from explicit commit-object allowlists and emits `SHA256SUMS` |
| Python lint | `python3 -m ruff check .` | Runs the pinned CI lint policy; CI installs Ruff `0.11.13` |

`gyro_bridge/test.py` rebuilds the bridge before running the native smoke test.
Run every check relevant to the files changed and report the exact commands and
results in the pull request. If a native prerequisite is unavailable, say so;
do not describe an unrun check as passing.

Automated native smoke coverage is not hardware certification. Informal gameplay
has exercised gyro with a real 8BitDo controller, but broad controller, rumble,
lightbar, hotplug, and Steam-client combinations remain uncertified. Native
Windows execution is currently unverified. Manual reports must name their exact
platform and scope without generalizing beyond what was tested.

## Making a change

1. Open an issue first for compatibility expansion, action-ID changes, installer
   safety changes, or native architecture changes.
2. Keep the patch focused and follow the existing Python/C++ style.
3. Add or update synthetic tests for behavior changes.
4. Update the relevant README, architecture/action contract, troubleshooting,
   and changelog text when public behavior or compatibility changes.
5. Inspect the diff for generated files, proprietary content, profiles, logs,
   absolute paths, and account/device IDs.
6. Open a pull request using the repository template.

For a newly observed game build, report only file sizes, hashes, and behavior.
Do not submit the files themselves. A compatibility change requires deliberate
source updates, regenerated artifacts where applicable, installer tests, native
smoke validation, and clearly bounded manual validation.

Potential vulnerabilities must be reported through the private process in
[`SECURITY.md`](SECURITY.md), not discussed first in a public issue.

Contributions are submitted under this repository's MIT License.
