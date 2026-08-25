#!/usr/bin/env python3
"""Install or restore the Flower native ScePad Steam Input bridge.

The installer supports only the verified Steam build and a byte-exact bridge
artifact built from this repository. It does not contain or download game files.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

APP_ID = 966330
SUPPORTED_BUILD_ID = 4354278
SCRIPT_VERSION = "0.4.4"
TARGET_NAME = "libScePad.dll"
BACKUP_NAME = "libScePad_original.dll"
FLOWER_EXE_NAME = "Flower.exe"
STEAM_API_NAME = "steam_api64.dll"
ACTION_MANIFEST_NAME = "game_actions_966330.vdf"


class BridgeError(RuntimeError):
    """Raised when bridge installation or restoration would be unsafe."""


@dataclass(frozen=True)
class FileSignature:
    size: int
    sha256: str


@dataclass(frozen=True)
class BridgeSpec:
    original: FileSignature
    bridge: FileSignature
    flower_exe: FileSignature
    steam_api: FileSignature
    historical_bridges: tuple[FileSignature, ...] = ()


@dataclass(frozen=True)
class ActionManifestSpec:
    manifest: FileSignature
    historical_manifests: tuple[FileSignature, ...] = ()


SUPPORTED_SPEC = BridgeSpec(
    original=FileSignature(
        size=128_512,
        sha256="7d9a71a8a51bd6e81b6fb7835fea2c20e4f8f9e331ff26dd8ac09692ceb33de8",
    ),
    bridge=FileSignature(
        size=84_992,
        sha256="adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c",
    ),
    flower_exe=FileSignature(
        size=20_867_456,
        sha256="649b7b64db42146314ac0a0e55d5faf03194eba21ca9c791706ce827570d3aca",
    ),
    steam_api=FileSignature(
        size=242_976,
        sha256="38f6a1dd1e738e142160322638dae7b88dabcc30eea3f15c58eb08c5341f9b29",
    ),
    historical_bridges=(
        FileSignature(
            size=84_480,
            sha256="e7a77b24116b2756b4bcbf6f2a4b54ffc28c55003782824f9eba7c7e70082d44",
        ),
        FileSignature(
            size=83_968,
            sha256="e34d78779b26aa2ff2f65f499aea8ee0966310731e0ab73cc055c8a69ff329b3",
        ),
        FileSignature(
            size=84_480,
            sha256="9c5dcb1e482ecdf41660f39a474d5fef0b7fab0220f6fa04d3ab359e9ac07487",
        ),
        FileSignature(
            size=76_800,
            sha256="59042f843f49e02df0ad216b861cbdf8d99164c50ee371f2a2984fb86d64d027",
        ),
        FileSignature(
            size=82_944,
            sha256="4fafb0690c11320942a42e8a43e0c73ba88c32167f34f40553b976b300e33e90",
        ),
        FileSignature(
            size=82_944,
            sha256="b3fc113dcbe8ddd494ad63c51f89418659eb1b9e3ff5e1a54121591e594204f6",
        ),
        FileSignature(
            size=80_896,
            sha256="b9306428ac889f175a73b057b36f271898a301088c44ccb07cd6c085188cae51",
        ),
    ),
)

SUPPORTED_MANIFEST_SPEC = ActionManifestSpec(
    manifest=FileSignature(
        size=2_438,
        sha256="8d3f5ab9b5a321ab3f6162935a8810642b08c307780a6356d75c102e8ce64b13",
    ),
    historical_manifests=(
        FileSignature(
            size=860,
            sha256="2dce857f62c7d163f46d425cbb6bee01bfa523ae4d29663641b1040900dbf89a",
        ),
        FileSignature(
            size=1_120,
            sha256="54b331f130e23654f7233eb19f5a7397e749d4f19089e39b2209ff5435c71623",
        ),
    ),
)


@dataclass(frozen=True)
class FileInspection:
    state: str
    sha256: str
    size: int


@dataclass(frozen=True)
class OperationResult:
    changed: bool
    state: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_exists_without_following(path: Path) -> bool:
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return False
    return True


def inspect_file(
    path: Path,
    signatures: Mapping[str, FileSignature],
) -> FileInspection:
    try:
        before = path.lstat()
    except FileNotFoundError:
        return FileInspection("missing", "", 0)

    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        return FileInspection("unsafe", "", before.st_size)

    digest = sha256_file(path)
    try:
        after = path.lstat()
    except FileNotFoundError:
        return FileInspection("changed-during-read", digest, before.st_size)

    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    )
    if identity_before != identity_after or not stat.S_ISREG(after.st_mode):
        return FileInspection("changed-during-read", digest, after.st_size)

    for state, signature in signatures.items():
        if after.st_size == signature.size and digest == signature.sha256:
            return FileInspection(state, digest, after.st_size)
    return FileInspection("unsupported", digest, after.st_size)


def inspect_target(
    target: Path,
    spec: BridgeSpec = SUPPORTED_SPEC,
) -> FileInspection:
    signatures: dict[str, FileSignature] = {
        "original": spec.original,
        "bridge": spec.bridge,
    }
    for index, signature in enumerate(spec.historical_bridges):
        signatures[f"historical-bridge-{index}"] = signature
    inspection = inspect_file(target, signatures)
    if inspection.state.startswith("historical-bridge-"):
        return FileInspection("historical-bridge", inspection.sha256, inspection.size)
    return inspection


def inspect_action_manifest(
    path: Path,
    spec: ActionManifestSpec = SUPPORTED_MANIFEST_SPEC,
) -> FileInspection:
    signatures: dict[str, FileSignature] = {"manifest": spec.manifest}
    for index, signature in enumerate(spec.historical_manifests):
        signatures[f"historical-manifest-{index}"] = signature
    inspection = inspect_file(path, signatures)
    if inspection.state.startswith("historical-manifest-"):
        return FileInspection(
            "historical-manifest",
            inspection.sha256,
            inspection.size,
        )
    return inspection


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _copy_to_sibling_temp(source: Path, destination: Path) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        _ = shutil.copy2(source, temporary)
        _fsync_file(temporary)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _replace_atomically(temporary: Path, destination: Path) -> None:
    os.replace(temporary, destination)
    _fsync_directory(destination.parent)


def _require_disk_space(
    target: Path,
    spec: BridgeSpec,
    *,
    needs_backup: bool,
    restoring: bool,
) -> None:
    temporary_size = spec.original.size if restoring else spec.bridge.size
    backup_size = spec.original.size if needs_backup else 0
    required = temporary_size + backup_size + 1024 * 1024
    available = shutil.disk_usage(target.parent).free
    if available < required:
        raise BridgeError(
            f"Not enough free space in {target.parent}: need about {required} bytes, "
            + f"found {available}"
        )


def _require_supported_file(
    path: Path,
    signature: FileSignature,
    description: str,
) -> None:
    inspection = inspect_file(path, {"supported": signature})
    if inspection.state != "supported":
        raise BridgeError(
            f"Unsupported or unsafe {description}.\n"
            + f"Path: {path}\n"
            + f"State: {inspection.state}\n"
            + f"Size: {inspection.size}\n"
            + f"SHA-256: {inspection.sha256 or '<unavailable>'}\n"
            + f"Supported SHA-256: {signature.sha256}"
        )


def _require_supported_game(game_dir: Path, spec: BridgeSpec) -> None:
    _require_supported_file(
        game_dir / FLOWER_EXE_NAME,
        spec.flower_exe,
        FLOWER_EXE_NAME,
    )
    _require_supported_file(
        game_dir / STEAM_API_NAME,
        spec.steam_api,
        STEAM_API_NAME,
    )


def _create_original_backup_no_clobber(
    target: Path,
    backup: Path,
    spec: BridgeSpec,
) -> None:
    source_mode = stat.S_IMODE(target.lstat().st_mode)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    created = False
    try:
        descriptor = os.open(backup, flags, source_mode)
        created = True
        with os.fdopen(descriptor, "wb") as destination, target.open("rb") as source:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        shutil.copystat(target, backup, follow_symlinks=False)
        _fsync_file(backup)
        _fsync_directory(backup.parent)

        backup_state = inspect_file(backup, {"original": spec.original})
        if backup_state.state != "original":
            raise BridgeError("New original ScePad backup failed verification")
    except FileExistsError:
        existing = inspect_file(backup, {"original": spec.original})
        if existing.state != "original":
            raise BridgeError(
                "Backup appeared concurrently and is not the verified original: "
                + os.fspath(backup)
            )
    except Exception:
        if created:
            backup.unlink(missing_ok=True)
            _fsync_directory(backup.parent)
        raise


def _ensure_original_backup(
    target: Path,
    backup: Path,
    spec: BridgeSpec,
    dry_run: bool,
) -> None:
    inspection = inspect_file(backup, {"original": spec.original})
    if inspection.state == "original":
        return
    if inspection.state != "missing":
        raise BridgeError(
            "Existing ScePad backup is not a safe, verified original.\n"
            + f"Path: {backup}\n"
            + f"State: {inspection.state}\n"
            + f"SHA-256: {inspection.sha256 or '<unavailable>'}"
        )
    if dry_run:
        return

    _create_original_backup_no_clobber(target, backup, spec)
    final_state = inspect_file(backup, {"original": spec.original})
    if final_state.state != "original":
        raise BridgeError("Backup verification failed before installation")


def install_bridge(
    game_dir: Path,
    artifact: Path,
    spec: BridgeSpec = SUPPORTED_SPEC,
    *,
    dry_run: bool = False,
) -> OperationResult:
    target = game_dir / TARGET_NAME
    backup = game_dir / BACKUP_NAME

    _require_supported_game(game_dir, spec)
    artifact_state = inspect_file(artifact, {"bridge": spec.bridge})
    if artifact_state.state != "bridge":
        raise BridgeError(
            "The bridge artifact is missing, unsafe, or does not match this installer.\n"
            + f"Path: {artifact}\n"
            + f"State: {artifact_state.state}\n"
            + f"SHA-256: {artifact_state.sha256 or '<unavailable>'}\n"
            + f"Expected SHA-256: {spec.bridge.sha256}"
        )

    target_state = inspect_target(target, spec)
    if target_state.state == "missing":
        raise BridgeError(f"Flower ScePad DLL was not found: {target}")
    if target_state.state == "bridge":
        backup_state = inspect_file(backup, {"original": spec.original})
        if backup_state.state != "original":
            raise BridgeError(
                "The bridge is active, but its verified original backup is missing "
                + "or unsafe. Refusing to report a reversible installation."
            )
        return OperationResult(False, "already-installed")

    upgrading = target_state.state == "historical-bridge"
    if target_state.state not in ("original", "historical-bridge"):
        raise BridgeError(
            "Refusing to replace an unsupported or independently modified ScePad DLL.\n"
            + f"Path: {target}\n"
            + f"Size: {target_state.size}\n"
            + f"SHA-256: {target_state.sha256}\n"
            + f"Supported original SHA-256: {spec.original.sha256}"
        )

    backup_before = inspect_file(backup, {"original": spec.original})
    allowed_backup_states = ("original",) if upgrading else ("missing", "original")
    if backup_before.state not in allowed_backup_states:
        raise BridgeError(
            f"Refusing unsafe backup state {backup_before.state} at {backup}"
        )
    _require_disk_space(
        target,
        spec,
        needs_backup=backup_before.state == "missing",
        restoring=False,
    )
    if not upgrading:
        _ensure_original_backup(target, backup, spec, dry_run)
    if dry_run:
        return OperationResult(
            False,
            "dry-run-upgradable" if upgrading else "dry-run-installable",
        )

    temporary = _copy_to_sibling_temp(artifact, target)
    try:
        temporary_state = inspect_file(temporary, {"bridge": spec.bridge})
        if temporary_state.state != "bridge":
            raise BridgeError(
                "Temporary bridge copy failed verification; Flower was left untouched."
            )

        _require_supported_game(game_dir, spec)
        target_before_replace = inspect_target(target, spec)
        backup_before_replace = inspect_file(backup, {"original": spec.original})
        artifact_before_replace = inspect_file(artifact, {"bridge": spec.bridge})
        expected_target_state = (
            "historical-bridge" if upgrading else "original"
        )
        if target_before_replace.state != expected_target_state:
            raise BridgeError(
                "Active ScePad DLL changed during installation; refusing replacement."
            )
        if backup_before_replace.state != "original":
            raise BridgeError(
                "Original ScePad backup changed during installation; refusing replacement."
            )
        if artifact_before_replace.state != "bridge":
            raise BridgeError(
                "Bridge artifact changed during installation; refusing replacement."
            )
        _replace_atomically(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    final_target = inspect_target(target, spec)
    final_backup = inspect_file(backup, {"original": spec.original})
    if final_target.state != "bridge":
        raise BridgeError("Final bridge verification failed after atomic replacement")
    if final_backup.state != "original":
        raise BridgeError("Original backup failed verification after installation")
    return OperationResult(True, "upgraded" if upgrading else "installed")


def restore_bridge(
    game_dir: Path,
    spec: BridgeSpec = SUPPORTED_SPEC,
    *,
    dry_run: bool = False,
) -> OperationResult:
    target = game_dir / TARGET_NAME
    backup = game_dir / BACKUP_NAME
    target_state = inspect_target(target, spec)

    if target_state.state == "missing":
        raise BridgeError(f"Flower ScePad DLL was not found: {target}")
    if target_state.state == "original":
        return OperationResult(False, "already-original")
    if target_state.state not in ("bridge", "historical-bridge"):
        raise BridgeError(
            "Refusing to overwrite an unsupported or independently modified ScePad DLL.\n"
            + f"Path: {target}\n"
            + f"SHA-256: {target_state.sha256 or '<unavailable>'}"
        )

    backup_state = inspect_file(backup, {"original": spec.original})
    if backup_state.state != "original":
        raise BridgeError(
            "A verified original ScePad backup is required for restoration.\n"
            + f"Expected backup: {backup}\n"
            + f"Backup state: {backup_state.state}\n"
            + f"Backup SHA-256: {backup_state.sha256 or '<unavailable>'}"
        )
    _require_disk_space(
        target,
        spec,
        needs_backup=False,
        restoring=True,
    )
    if dry_run:
        return OperationResult(False, "dry-run-restorable")

    temporary = _copy_to_sibling_temp(backup, target)
    try:
        temporary_state = inspect_file(temporary, {"original": spec.original})
        if temporary_state.state != "original":
            raise BridgeError("Backup copy failed verification before restoration")

        target_before_replace = inspect_target(target, spec)
        backup_before_replace = inspect_file(backup, {"original": spec.original})
        if target_before_replace.state not in ("bridge", "historical-bridge"):
            raise BridgeError(
                "Active ScePad DLL changed during restoration; refusing replacement."
            )
        if backup_before_replace.state != "original":
            raise BridgeError(
                "Original ScePad backup changed during restoration; refusing replacement."
            )
        _replace_atomically(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    final_target = inspect_target(target, spec)
    final_backup = inspect_file(backup, {"original": spec.original})
    if final_target.state != "original":
        raise BridgeError("Final verification failed after restoration")
    if final_backup.state != "original":
        raise BridgeError("Original backup failed verification after restoration")
    return OperationResult(True, "restored")


def _require_manifest_directory(directory: Path, dry_run: bool) -> None:
    try:
        inspection = directory.lstat()
    except FileNotFoundError:
        if not dry_run:
            directory.mkdir(parents=False)
            _fsync_directory(directory.parent)
        return
    if not stat.S_ISDIR(inspection.st_mode):
        raise BridgeError(
            f"Steam controller_config path is not a real directory: {directory}"
        )


def install_action_manifest(
    steam_dir: Path,
    artifact: Path,
    spec: ActionManifestSpec = SUPPORTED_MANIFEST_SPEC,
    *,
    dry_run: bool = False,
) -> OperationResult:
    target = steam_dir / "controller_config" / ACTION_MANIFEST_NAME
    artifact_state = inspect_file(artifact, {"manifest": spec.manifest})
    if artifact_state.state != "manifest":
        raise BridgeError(
            "The Steam Input action manifest artifact is missing, unsafe, or "
            + "does not match this installer.\n"
            + f"Path: {artifact}\n"
            + f"State: {artifact_state.state}\n"
            + f"SHA-256: {artifact_state.sha256 or '<unavailable>'}\n"
            + f"Expected SHA-256: {spec.manifest.sha256}"
        )

    target_state = inspect_action_manifest(target, spec)
    if target_state.state == "manifest":
        return OperationResult(False, "manifest-already-installed")
    if target_state.state not in ("missing", "historical-manifest"):
        raise BridgeError(
            "Refusing to overwrite an unknown Steam Input action manifest.\n"
            + f"Path: {target}\n"
            + f"State: {target_state.state}\n"
            + f"SHA-256: {target_state.sha256 or '<unavailable>'}"
        )

    _require_manifest_directory(target.parent, dry_run)
    if dry_run:
        return OperationResult(
            False,
            "dry-run-manifest-upgradable"
            if target_state.state == "historical-manifest"
            else "dry-run-manifest-installable",
        )

    temporary = _copy_to_sibling_temp(artifact, target)
    try:
        temporary_state = inspect_file(temporary, {"manifest": spec.manifest})
        if temporary_state.state != "manifest":
            raise BridgeError("Temporary action manifest failed verification")
        target_before_replace = inspect_action_manifest(target, spec)
        if target_before_replace.state != target_state.state:
            raise BridgeError(
                "Steam Input action manifest changed during installation; "
                + "refusing replacement."
            )
        _replace_atomically(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    final_state = inspect_action_manifest(target, spec)
    if final_state.state != "manifest":
        raise BridgeError("Final action manifest verification failed")
    return OperationResult(
        True,
        "manifest-upgraded"
        if target_state.state == "historical-manifest"
        else "manifest-installed",
    )


def restore_action_manifest(
    steam_dir: Path,
    spec: ActionManifestSpec = SUPPORTED_MANIFEST_SPEC,
    *,
    dry_run: bool = False,
) -> OperationResult:
    target = steam_dir / "controller_config" / ACTION_MANIFEST_NAME
    target_state = inspect_action_manifest(target, spec)
    if target_state.state == "missing":
        return OperationResult(False, "manifest-already-absent")
    if target_state.state not in ("manifest", "historical-manifest"):
        return OperationResult(False, "manifest-unmanaged")
    if dry_run:
        return OperationResult(False, "dry-run-manifest-restorable")

    before_delete = inspect_action_manifest(target, spec)
    if before_delete.state != target_state.state:
        raise BridgeError(
            "Steam Input action manifest changed during restoration; refusing deletion."
        )
    target.unlink()
    _fsync_directory(target.parent)
    if inspect_action_manifest(target, spec).state != "missing":
        raise BridgeError("Action manifest still exists after restoration")
    return OperationResult(True, "manifest-removed")


def _describe_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


@dataclass(frozen=True)
class _ManifestSnapshot:
    state: str
    data: bytes | None
    sha256: str
    mode: int | None


def _snapshot_managed_manifest(
    target: Path,
    spec: ActionManifestSpec,
) -> _ManifestSnapshot:
    try:
        before = target.lstat()
    except FileNotFoundError:
        return _ManifestSnapshot("missing", None, "", None)

    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise BridgeError(
            f"Refusing to snapshot an unsafe Steam Input action manifest: {target}"
        )

    try:
        data = target.read_bytes()
        after = target.lstat()
    except FileNotFoundError as error:
        raise BridgeError(
            "Steam Input action manifest changed while it was being snapshotted"
        ) from error

    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    )
    if identity_before != identity_after or not stat.S_ISREG(after.st_mode):
        raise BridgeError(
            "Steam Input action manifest changed while it was being snapshotted"
        )

    digest = hashlib.sha256(data).hexdigest()
    if len(data) == spec.manifest.size and digest == spec.manifest.sha256:
        state = "manifest"
    elif any(
        len(data) == signature.size and digest == signature.sha256
        for signature in spec.historical_manifests
    ):
        state = "historical-manifest"
    else:
        raise BridgeError(
            "Refusing to snapshot an unknown Steam Input action manifest.\n"
            + f"Path: {target}\n"
            + f"SHA-256: {digest}"
        )

    return _ManifestSnapshot(
        state,
        data,
        digest,
        stat.S_IMODE(before.st_mode),
    )


def _manifest_matches_snapshot(
    target: Path,
    snapshot: _ManifestSnapshot,
    spec: ActionManifestSpec,
) -> bool:
    inspection = inspect_action_manifest(target, spec)
    if snapshot.state == "missing":
        return inspection.state == "missing"
    return (
        inspection.state == snapshot.state
        and inspection.sha256 == snapshot.sha256
        and snapshot.data is not None
        and inspection.size == len(snapshot.data)
    )


def _write_manifest_snapshot_temp(
    target: Path,
    snapshot: _ManifestSnapshot,
) -> Path:
    if snapshot.data is None:
        raise BridgeError("A missing manifest snapshot has no bytes to restore")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=target.name + ".rollback.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            _ = handle.write(snapshot.data)
            handle.flush()
            os.fsync(handle.fileno())
        if snapshot.mode is not None:
            os.chmod(temporary, snapshot.mode)
        _fsync_file(temporary)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _restore_manifest_snapshot(
    target: Path,
    snapshot: _ManifestSnapshot,
    spec: ActionManifestSpec,
) -> None:
    if _manifest_matches_snapshot(target, snapshot, spec):
        return

    current = inspect_action_manifest(target, spec)
    if current.state != "manifest":
        raise BridgeError(
            "Steam Input action manifest is no longer the current managed "
            + "manifest; refusing to overwrite a concurrent change.\n"
            + f"Path: {target}\n"
            + f"State: {current.state}\n"
            + f"SHA-256: {current.sha256 or '<unavailable>'}"
        )

    if snapshot.state == "missing":
        before_delete = inspect_action_manifest(target, spec)
        if before_delete.state != "manifest":
            raise BridgeError(
                "Steam Input action manifest changed during coordinated rollback; "
                + "refusing deletion."
            )
        target.unlink()
        _fsync_directory(target.parent)
    else:
        temporary = _write_manifest_snapshot_temp(target, snapshot)
        try:
            temporary_state = inspect_file(
                temporary,
                {
                    "snapshot": FileSignature(
                        len(snapshot.data or b""),
                        snapshot.sha256,
                    )
                },
            )
            if temporary_state.state != "snapshot":
                raise BridgeError(
                    "Temporary action manifest rollback copy failed verification"
                )
            before_replace = inspect_action_manifest(target, spec)
            if before_replace.state != "manifest":
                raise BridgeError(
                    "Steam Input action manifest changed during coordinated "
                    + "rollback; refusing replacement."
                )
            _replace_atomically(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    if not _manifest_matches_snapshot(target, snapshot, spec):
        raise BridgeError(
            "Action manifest did not match its exact pre-install state after rollback"
        )


def _restore_verified_original(game_dir: Path, spec: BridgeSpec) -> None:
    _ = restore_bridge(game_dir, spec)
    rollback_state = inspect_target(game_dir / TARGET_NAME, spec)
    if rollback_state.state != "original":
        raise BridgeError(
            "Bridge rollback did not leave a verified original ScePad DLL"
        )


def install_bridge_and_manifest(
    game_dir: Path,
    artifact: Path,
    steam_dir: Path,
    manifest_artifact: Path,
    spec: BridgeSpec = SUPPORTED_SPEC,
    manifest_spec: ActionManifestSpec = SUPPORTED_MANIFEST_SPEC,
    *,
    dry_run: bool = False,
) -> tuple[OperationResult, OperationResult]:
    """Install both managed files while keeping failures in a safe state."""
    bridge_preflight = install_bridge(game_dir, artifact, spec, dry_run=True)
    manifest_preflight = install_action_manifest(
        steam_dir,
        manifest_artifact,
        manifest_spec,
        dry_run=True,
    )
    if dry_run:
        return bridge_preflight, manifest_preflight

    manifest_target = steam_dir / "controller_config" / ACTION_MANIFEST_NAME
    bridge_before = inspect_target(game_dir / TARGET_NAME, spec)
    try:
        bridge_result = install_bridge(game_dir, artifact, spec)
    except BaseException as primary_error:
        try:
            bridge_after = inspect_target(game_dir / TARGET_NAME, spec)
        except BaseException as inspection_error:
            raise BridgeError(
                "Bridge installation failed, and its post-failure state could not "
                + "be inspected.\n"
                + f"Primary error: {_describe_error(primary_error)}\n"
                + f"Inspection error: {_describe_error(inspection_error)}"
            ) from inspection_error

        if bridge_before.state != "bridge" and bridge_after.state == "bridge":
            try:
                _restore_verified_original(game_dir, spec)
            except BaseException as rollback_error:
                raise BridgeError(
                    "Bridge installation failed after activating the bridge, and "
                    + "rollback to the verified original also failed.\n"
                    + f"Primary error: {_describe_error(primary_error)}\n"
                    + f"Rollback error: {_describe_error(rollback_error)}"
                ) from rollback_error
            if isinstance(primary_error, Exception):
                raise BridgeError(
                    "Bridge installation failed after activating the bridge. "
                    + "The bridge was rolled back to the verified original.\n"
                    + f"Primary error: {_describe_error(primary_error)}"
                ) from primary_error
        raise

    try:
        manifest_snapshot = _snapshot_managed_manifest(
            manifest_target,
            manifest_spec,
        )
    except BaseException as primary_error:
        if bridge_result.changed:
            try:
                _restore_verified_original(game_dir, spec)
            except BaseException as rollback_error:
                raise BridgeError(
                    "The bridge was installed, the action manifest could not be "
                    + "safely snapshotted, and bridge rollback also failed.\n"
                    + f"Primary error: {_describe_error(primary_error)}\n"
                    + f"Rollback error: {_describe_error(rollback_error)}"
                ) from rollback_error
            if isinstance(primary_error, Exception):
                raise BridgeError(
                    "The bridge was installed, but the action manifest could not be "
                    + "safely snapshotted. The bridge was rolled back to the "
                    + "verified original.\n"
                    + f"Primary error: {_describe_error(primary_error)}"
                ) from primary_error
        raise

    try:
        manifest_result = install_action_manifest(
            steam_dir,
            manifest_artifact,
            manifest_spec,
        )
    except BaseException as primary_error:
        rollback_errors: list[tuple[str, BaseException]] = []
        try:
            _restore_manifest_snapshot(
                manifest_target,
                manifest_snapshot,
                manifest_spec,
            )
        except (
            Exception,  # noqa: BLE001 - retain every rollback failure.
            KeyboardInterrupt,
            SystemExit,
            GeneratorExit,
        ) as rollback_error:
            rollback_errors.append(("Manifest rollback error", rollback_error))

        if bridge_result.changed:
            try:
                _restore_verified_original(game_dir, spec)
            except (
                Exception,  # noqa: BLE001 - preserve rollback diagnostics.
                KeyboardInterrupt,
                SystemExit,
                GeneratorExit,
            ) as rollback_error:
                rollback_errors.append(("Bridge rollback error", rollback_error))

        if rollback_errors:
            rollback_details = "\n".join(
                f"{label}: {_describe_error(error)}"
                for label, error in rollback_errors
            )
            raise BridgeError(
                "Action manifest installation failed, and coordinated rollback "
                + "did not complete.\n"
                + f"Primary error: {_describe_error(primary_error)}\n"
                + rollback_details
            ) from rollback_errors[-1][1]

        if isinstance(primary_error, Exception):
            recovery = "The prior managed manifest state was restored"
            if bridge_result.changed:
                recovery += ", and the bridge was rolled back to the verified original"
            raise BridgeError(
                "Action manifest installation failed. "
                + recovery
                + ".\n"
                + f"Primary error: {_describe_error(primary_error)}"
            ) from primary_error
        raise

    return bridge_result, manifest_result


def restore_bridge_and_manifest(
    game_dir: Path,
    steam_dir: Path,
    spec: BridgeSpec = SUPPORTED_SPEC,
    manifest_spec: ActionManifestSpec = SUPPORTED_MANIFEST_SPEC,
    *,
    dry_run: bool = False,
) -> tuple[OperationResult, OperationResult]:
    """Remove the manifest before restoring the bridge to remain fail-open."""
    bridge_preflight = restore_bridge(game_dir, spec, dry_run=True)
    manifest_preflight = restore_action_manifest(
        steam_dir,
        manifest_spec,
        dry_run=True,
    )
    if dry_run:
        return bridge_preflight, manifest_preflight

    manifest_result = restore_action_manifest(steam_dir, manifest_spec)
    bridge_result = restore_bridge(game_dir, spec)
    return bridge_result, manifest_result


def _absolute_without_resolving(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _unique_paths(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[Path] = set()
    for path in paths:
        normalized = _absolute_without_resolving(path)
        if normalized not in seen:
            seen.add(normalized)
            yield normalized


def _automatic_game_roots() -> Iterable[Path]:
    script_directory = Path(__file__).resolve().parent
    home = Path.home()
    roots = [
        Path.cwd(),
        script_directory,
        script_directory.parent,
        home / ".local/share/Steam/steamapps/common/Flower",
        home / ".steam/steam/steamapps/common/Flower",
        home / ".var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/Flower",
    ]
    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        base = os.environ.get(variable)
        if base:
            roots.append(Path(base) / "Steam/steamapps/common/Flower")
    yield from _unique_paths(roots)


def _automatic_steam_roots() -> Iterable[Path]:
    home = Path.home()
    roots = [
        home / ".local/share/Steam",
        home / ".steam/steam",
        home / ".var/app/com.valvesoftware.Steam/data/Steam",
    ]
    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        base = os.environ.get(variable)
        if base:
            roots.append(Path(base) / "Steam")
    yield from _unique_paths(roots)


def resolve_game_directory(game_dir: Path | None) -> Path:
    if game_dir is not None:
        supplied = _absolute_without_resolving(game_dir)
        if supplied.name.casefold() == TARGET_NAME.casefold():
            supplied = supplied.parent
        target = supplied / TARGET_NAME
        if _path_exists_without_following(target):
            return supplied
        raise BridgeError(
            f"Could not find {TARGET_NAME} under the supplied path: {supplied}"
        )

    for root in _automatic_game_roots():
        if _path_exists_without_following(root / TARGET_NAME):
            return root
    raise BridgeError(
        "Flower was not found automatically. Pass --game-dir /path/to/Flower."
    )


def resolve_steam_directory(steam_dir: Path | None) -> Path:
    if steam_dir is not None:
        supplied = _absolute_without_resolving(steam_dir)
        if (supplied / "steamapps").is_dir():
            return supplied
        raise BridgeError(
            f"The supplied Steam directory has no steamapps folder: {supplied}"
        )

    for root in _automatic_steam_roots():
        if (root / "steamapps").is_dir():
            return root
    raise BridgeError(
        "Steam was not found automatically. Pass --steam-dir /path/to/Steam."
    )


def resolve_bridge_artifact(bridge: Path | None) -> Path:
    if bridge is not None:
        return _absolute_without_resolving(bridge)
    return Path(__file__).resolve().parent / "dist" / TARGET_NAME


def resolve_manifest_artifact(manifest: Path | None) -> Path:
    if manifest is not None:
        return _absolute_without_resolving(manifest)
    return (
        Path(__file__).resolve().parent
        / "steam_input"
        / ACTION_MANIFEST_NAME
    )


def _overall_state(target: FileInspection, backup: FileInspection) -> str:
    if target.state == "bridge" and backup.state == "original":
        return "installed"
    if target.state == "bridge":
        return "bridge-active-without-verified-backup"
    if target.state == "historical-bridge" and backup.state == "original":
        return "upgrade-available"
    if target.state == "historical-bridge":
        return "historical-bridge-without-verified-backup"
    if target.state == "original":
        return "original"
    return target.state


def print_status(
    game_dir: Path,
    artifact: Path,
    steam_dir: Path,
    manifest_artifact: Path,
    spec: BridgeSpec = SUPPORTED_SPEC,
    manifest_spec: ActionManifestSpec = SUPPORTED_MANIFEST_SPEC,
) -> None:
    target = game_dir / TARGET_NAME
    backup = game_dir / BACKUP_NAME
    target_state = inspect_target(target, spec)
    backup_state = inspect_file(backup, {"original": spec.original})
    artifact_state = inspect_file(artifact, {"bridge": spec.bridge})
    executable_state = inspect_file(
        game_dir / FLOWER_EXE_NAME,
        {"supported": spec.flower_exe},
    )
    steam_state = inspect_file(
        game_dir / STEAM_API_NAME,
        {"supported": spec.steam_api},
    )
    manifest_target = steam_dir / "controller_config" / ACTION_MANIFEST_NAME
    manifest_state = inspect_action_manifest(manifest_target, manifest_spec)
    manifest_artifact_state = inspect_file(
        manifest_artifact,
        {"manifest": manifest_spec.manifest},
    )

    print(f"Flower Steam App: {APP_ID}")
    print(f"Supported build ID: {SUPPORTED_BUILD_ID}")
    print(f"Game directory: {game_dir}")
    print(f"Overall state: {_overall_state(target_state, backup_state)}")
    print(f"Active DLL: {target}")
    print(f"Active DLL state: {target_state.state}")
    print(f"Active DLL SHA-256: {target_state.sha256 or '<missing>'}")
    print(f"Original backup: {backup}")
    print(f"Original backup state: {backup_state.state}")
    print(f"Bridge artifact: {artifact}")
    print(f"Bridge artifact state: {artifact_state.state}")
    print(f"{FLOWER_EXE_NAME} state: {executable_state.state}")
    print(f"{STEAM_API_NAME} state: {steam_state.state}")
    print(f"Steam directory: {steam_dir}")
    print(f"Action manifest: {manifest_target}")
    print(f"Action manifest state: {manifest_state.state}")
    print(f"Action manifest artifact: {manifest_artifact}")
    print(f"Action manifest artifact state: {manifest_artifact_state.state}")


class _Arguments(Protocol):
    command: str
    game_dir: Path | None
    steam_dir: Path | None
    bridge: Path | None
    manifest: Path | None
    dry_run: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Adapt named Steam Input actions to Flower's native ScePad path "
            "with verified original-library fallback."
        )
    )
    _ = parser.add_argument(
        "command",
        nargs="?",
        choices=("status", "install", "restore"),
        default="status",
    )
    _ = parser.add_argument(
        "--game-dir",
        type=Path,
        help="Flower installation directory or its libScePad.dll file",
    )
    _ = parser.add_argument(
        "--steam-dir",
        type=Path,
        help="Steam installation root containing the steamapps directory",
    )
    _ = parser.add_argument(
        "--bridge",
        type=Path,
        help="bridge DLL artifact; defaults to gyro_bridge/dist/libScePad.dll",
    )
    _ = parser.add_argument(
        "--manifest",
        type=Path,
        help="Steam Input IGA artifact; defaults to the bundled App ID manifest",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="verify all preconditions without writing or replacing files",
    )
    _ = parser.add_argument("--version", action="version", version=SCRIPT_VERSION)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = cast(_Arguments, cast(object, build_parser().parse_args(argv)))
    try:
        game_dir = resolve_game_directory(args.game_dir)
        steam_dir = resolve_steam_directory(args.steam_dir)
        artifact = resolve_bridge_artifact(args.bridge)
        manifest_artifact = resolve_manifest_artifact(args.manifest)
        if args.command == "status":
            print_status(game_dir, artifact, steam_dir, manifest_artifact)
            return 0

        if args.command == "install":
            bridge_result, manifest_result = install_bridge_and_manifest(
                game_dir,
                artifact,
                steam_dir,
                manifest_artifact,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                print_status(game_dir, artifact, steam_dir, manifest_artifact)
                print(
                    "Dry run passed for the bridge and action manifest; "
                    + "no files were written or replaced."
                )
                print(f"Bridge preflight: {bridge_result.state}")
                print(f"Manifest preflight: {manifest_result.state}")
                return 0

            print_status(game_dir, artifact, steam_dir, manifest_artifact)
            print(f"Bridge result: {bridge_result.state}")
            print(f"Action manifest result: {manifest_result.state}")
            print(
                "Installation complete. Fully exit and restart Steam before "
                + "creating or applying a named-action controller layout."
            )
            return 0

        bridge_result, manifest_result = restore_bridge_and_manifest(
            game_dir,
            steam_dir,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print_status(game_dir, artifact, steam_dir, manifest_artifact)
            print(
                "Dry run passed for bridge restoration and managed-manifest "
                + "removal; no files were changed."
            )
            print(f"Bridge preflight: {bridge_result.state}")
            print(f"Manifest preflight: {manifest_result.state}")
            return 0

        print_status(game_dir, artifact, steam_dir, manifest_artifact)
        print(f"Bridge result: {bridge_result.state}")
        print(f"Action manifest result: {manifest_result.state}")
        if manifest_result.changed:
            print("Fully exit and restart Steam to clear the removed action manifest.")
        return 0
    except (OSError, BridgeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
