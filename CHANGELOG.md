# Changelog

Notable project changes are recorded here. The umbrella version and the two
component versions are independent.

## Unreleased

### Added

- Public support, security, contribution, troubleshooting, issue, and pull
  request guidance.
- Deterministic component release archives built from explicit Git-object
  allowlists, with `SHA256SUMS` and proprietary-file rejection.
- Pinned LLVM-MinGW release verification, binary provenance, and complete LLVM
  and MinGW-w64 runtime notices.
- CI coverage for Python 3.10/3.13, pinned Ruff, unit tests, and release policy.
- LF line-ending enforcement for byte-exact Steam action manifests.
- An ignored, cross-target `compile_commands.json` generator so clangd/Zed can
  analyze the Windows bridge with the pinned LLVM-MinGW headers.
- A transparent AI-assisted development disclosure and an optional Monero
  donation section with a maintainer-supplied address placeholder.

### Changed

- Reworked the top-level and bridge documentation around safe public downloads,
  quick start, validation limits, gyro calibration, neutral angle, and the
  correct no-output/ramp deadzone semantics.

## 1.1.0 - 2026-08-24

### Added

- Native ScePad Steam Input bridge `0.4.4` for the exact Flower Steam build
  `4354278` (App ID `966330`).
- Stable `flower_ps4` raw virtual PS4 action surface with two sticks, 14 digital
  controls, and gravity-relative `tilt` steering.
- Explicit, coordinated bridge/action-manifest installation and safe restore,
  with historical managed signatures recognized for upgrade or cleanup.
- Deterministic LLVM-MinGW/Proton native smoke coverage using independent fake
  Steam and ScePad providers.

### Changed

- Renamed the umbrella package to `flower-steam-fixes` and replaced earlier
  experimental tilt-hook designs with complete native ScePad snapshots from a
  dedicated Steam worker.
- Made unavailable, disconnected, inactive, or stale Steam state fall back to
  the complete original provider instead of mixing fields.

### Validation boundary

- Informal gameplay testing exercised gyro with a real 8BitDo controller.
- The native smoke matrix and that real-device check do not constitute broad
  hardware, Steam-client, rumble, lightbar, or hotplug certification.
- Native Windows execution remains unverified.

## 1.0.0 - 2026-08-15

### Added

- Gameplay-confirmed hay-bale sound fix `1.0.0` for Steam build `4354278`.
- Exact-hash gating, verified no-clobber backup, dry-run, atomic install,
  idempotent status, and verified restore for `Level4_A.bnk`.

### Validation

- Confirmed under SteamOS/Proton that all five nighttime hay-bale activations
  play appropriate transformation sounds and the unrelated landing sting is
  removed.
- The fix duplicates one present, valid hay sound because the fifth distinct
  recording is absent from the Steam installation; no proprietary audio is
  distributed.
