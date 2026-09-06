# Changelog

Notable project changes are recorded here. The umbrella version and the two
component versions are independent.

## 1.2.0 - 2026-09-06

Umbrella/bundle `1.2.0` (`v1.2.0`) includes hay-bale installer `1.0.1` and
bridge component/installer `0.4.5`. Publication remains subject to the gates in
[`RELEASING.md`](RELEASING.md).

### Added

- Public support, security, contribution, troubleshooting, issue, and pull
  request guidance.
- A deterministic combined release bundle, `flower-steam-fixes-1.2.0.zip`, built
  from an explicit Git-object allowlist, with `SHA256SUMS` and proprietary-file
  rejection. These are the only two uploaded assets; neither component needs a
  separate archive.
- Pinned LLVM-MinGW release verification, binary provenance, and complete LLVM
  and MinGW-w64 runtime notices.
- CI coverage for Python 3.10/3.13, pinned Ruff, unit tests, and release policy.
- LF line-ending enforcement for byte-exact Steam action manifests.
- An ignored, cross-target `compile_commands.json` generator so clangd/Zed can
  analyze the Windows bridge with the pinned LLVM-MinGW headers.
- Clearly named Linux and Windows install/revert launchers for both fixes at the
  repository and bundle roots.
- A transparent AI-assisted development disclosure and an optional Monero
  donation section with a maintainer-supplied address.

### Changed

- Reworked the top-level and bridge documentation around safe public downloads,
  quick start, validation limits, gyro calibration, neutral angle, and the
  correct no-output/ramp deadzone semantics.
- Consolidated both independently selectable fixes into one GitHub download and
  simplified install/restore results with one-click launcher quick starts; direct
  commands, `status`, and `--dry-run` remain available.
- Moved the guides to root `BUNDLE_README.md`, `HAY_BALE_FIX.md`, and
  `GYRO_BRIDGE.md`. Packaging preserves root paths, except `BUNDLE_README.md` is
  aliased to the bundle's `README.md`.
- Updated the installer versions without changing the native bridge DLL or action
  manifest: both remain `0.4.4` artifacts with unchanged exact sizes and hashes.

### Validation boundary

- The bundle/installer updates do not record new gameplay or native Windows
  validation. The dated validation entries below remain historical.
- Every bundle release includes the native DLL and requires pinned bridge
  verification and the isolated Proton smoke matrix, even when artifacts are
  unchanged. Manual release-review and downloaded-asset gates still apply.

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
