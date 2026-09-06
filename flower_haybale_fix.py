#!/usr/bin/env python3
"""Install or restore the Flower Level 4 hay-bale activation sound fix.

This script intentionally supports only the verified Steam bank build. It does
not contain or download any game assets.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

APP_ID = 966330
SUPPORTED_BUILD_ID = 4354278
TARGET_RELATIVE_PATH = Path("Data") / "Sounds" / "Level4_A.bnk"
BACKUP_SUFFIX = ".flower-haybale-fix.original"
SCRIPT_VERSION = "1.0.1"


class PatchError(RuntimeError):
    """Raised when applying or restoring the patch would be unsafe."""


@dataclass(frozen=True)
class PatchSpec:
    file_size: int
    offset: int
    original_bytes: bytes
    patched_bytes: bytes
    original_sha256: str
    patched_sha256: str

    def __post_init__(self) -> None:
        if len(self.original_bytes) != len(self.patched_bytes):
            raise ValueError("Patch must not change the target file size")
        if self.offset < 0 or self.offset + len(self.original_bytes) > self.file_size:
            raise ValueError("Patch range is outside the target file")


LEVEL4_PATCH = PatchSpec(
    file_size=46_780_694,
    offset=0x1E18,
    original_bytes=bytes.fromhex("50 64 01 2D"),
    patched_bytes=bytes.fromhex("1C 65 01 01"),
    original_sha256="17e112eeed5f40baa14b9e1838c9373d3d3a84f394c1bef6a371599dcdc65728",
    patched_sha256="c61b23587a8edd69b2201d918e8ee5a401f4f34ef272daa35b614f1d1f9c4012",
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


def inspect_file(path: Path, spec: PatchSpec = LEVEL4_PATCH) -> FileInspection:
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

    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or not stat.S_ISREG(after.st_mode):
        return FileInspection("changed-during-read", digest, after.st_size)

    size = after.st_size
    if size == spec.file_size and digest == spec.original_sha256:
        state = "original"
    elif size == spec.file_size and digest == spec.patched_sha256:
        state = "patched"
    else:
        state = "unsupported"
    return FileInspection(state, digest, size)


def _read_patch_site(path: Path, spec: PatchSpec) -> bytes:
    with path.open("rb") as handle:
        _ = handle.seek(spec.offset)
        return handle.read(len(spec.original_bytes))


def _require_patch_site(path: Path, expected: bytes, spec: PatchSpec) -> None:
    actual = _read_patch_site(path, spec)
    if actual != expected:
        raise PatchError(
            f"Patch-site verification failed at 0x{spec.offset:X}: "
            + f"expected {expected.hex(' ')}, found {actual.hex(' ')}"
        )


def backup_path_for(target: Path) -> Path:
    return target.with_name(target.name + BACKUP_SUFFIX)


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
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=destination.parent,
    )
    os.close(file_descriptor)
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


def _require_disk_space(target: Path, spec: PatchSpec, *, needs_backup: bool) -> None:
    required = spec.file_size * (2 if needs_backup else 1) + 1024 * 1024
    available = shutil.disk_usage(target.parent).free
    if available < required:
        raise PatchError(
            f"Not enough free space in {target.parent}: need about {required} bytes, "
            + f"found {available}"
        )


def _create_original_backup_no_clobber(
    target: Path,
    backup: Path,
    spec: PatchSpec,
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

        backup_state = inspect_file(backup, spec)
        if backup_state.state != "original":
            raise PatchError("New backup failed full-file verification")
    except FileExistsError:
        existing = inspect_file(backup, spec)
        if existing.state != "original":
            raise PatchError(
                f"Backup appeared concurrently and is not a verified original: {backup}"
            )
    except Exception:
        if created:
            backup.unlink(missing_ok=True)
            _fsync_directory(backup.parent)
        raise


def _ensure_original_backup(target: Path, spec: PatchSpec, dry_run: bool) -> Path:
    backup = backup_path_for(target)
    backup_state = inspect_file(backup, spec)
    if backup_state.state == "original":
        return backup
    if backup_state.state != "missing":
        raise PatchError(
            f"Existing backup is not a safe, supported original file: {backup}\n"
            + f"State: {backup_state.state}\n"
            + f"SHA-256: {backup_state.sha256 or '<unavailable>'}"
        )
    if dry_run:
        return backup

    _create_original_backup_no_clobber(target, backup, spec)
    final_backup_state = inspect_file(backup, spec)
    if final_backup_state.state != "original":
        raise PatchError("Backup verification failed before installation")
    return backup


def install_patch(
    target: Path,
    spec: PatchSpec = LEVEL4_PATCH,
    *,
    dry_run: bool = False,
) -> OperationResult:
    inspection = inspect_file(target, spec)
    if inspection.state == "missing":
        raise PatchError(f"Target bank was not found: {target}")
    if inspection.state == "patched":
        _require_patch_site(target, spec.patched_bytes, spec)
        backup_state = inspect_file(backup_path_for(target), spec)
        if backup_state.state != "original":
            raise PatchError(
                "The bank is patched, but its verified original backup is missing or "
                + "unsafe. Refusing to report a reversible installation."
            )
        return OperationResult(False, "already-patched")
    if inspection.state != "original":
        raise PatchError(
            "Refusing to patch an unsupported or modified bank.\n"
            + f"Path: {target}\n"
            + f"Size: {inspection.size}\n"
            + f"SHA-256: {inspection.sha256}\n"
            + f"Supported original SHA-256: {spec.original_sha256}"
        )

    _require_patch_site(target, spec.original_bytes, spec)
    backup_before = inspect_file(backup_path_for(target), spec)
    if backup_before.state not in ("missing", "original"):
        raise PatchError(
            f"Refusing unsafe backup state: {backup_before.state} "
            + f"at {backup_path_for(target)}"
        )
    _require_disk_space(target, spec, needs_backup=backup_before.state == "missing")
    backup = _ensure_original_backup(target, spec, dry_run)
    if dry_run:
        return OperationResult(False, "dry-run-installable")

    temporary = _copy_to_sibling_temp(target, target)
    try:
        with temporary.open("r+b") as handle:
            _ = handle.seek(spec.offset)
            current = handle.read(len(spec.original_bytes))
            if current != spec.original_bytes:
                raise PatchError("Temporary copy changed before patching")
            _ = handle.seek(spec.offset)
            _ = handle.write(spec.patched_bytes)
            handle.flush()
            os.fsync(handle.fileno())

        patched_state = inspect_file(temporary, spec)
        if patched_state.state != "patched":
            raise PatchError(
                "Patched-file verification failed; original file was left untouched.\n"
                + f"Temporary SHA-256: {patched_state.sha256}"
            )

        target_before_replace = inspect_file(target, spec)
        backup_before_replace = inspect_file(backup, spec)
        if target_before_replace.state != "original":
            raise PatchError(
                "Target changed while preparing the patch; refusing to replace it."
            )
        if backup_before_replace.state != "original":
            raise PatchError(
                "Backup changed while preparing the patch; refusing to continue."
            )
        _require_patch_site(target, spec.original_bytes, spec)
        _replace_atomically(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    final_state = inspect_file(target, spec)
    final_backup_state = inspect_file(backup, spec)
    if final_state.state != "patched":
        raise PatchError("Final verification failed after atomic replacement")
    if final_backup_state.state != "original":
        raise PatchError("Original backup failed verification after installation")
    return OperationResult(True, "patched")


def restore_patch(
    target: Path,
    spec: PatchSpec = LEVEL4_PATCH,
    *,
    dry_run: bool = False,
) -> OperationResult:
    inspection = inspect_file(target, spec)
    if inspection.state == "missing":
        raise PatchError(f"Target bank was not found: {target}")
    if inspection.state == "original":
        _require_patch_site(target, spec.original_bytes, spec)
        return OperationResult(False, "already-original")
    if inspection.state != "patched":
        raise PatchError(
            "Refusing to overwrite an unsupported or independently modified bank.\n"
            + f"Path: {target}\nSHA-256: {inspection.sha256}"
        )

    _require_patch_site(target, spec.patched_bytes, spec)
    backup = backup_path_for(target)
    backup_state = inspect_file(backup, spec)
    if backup_state.state != "original":
        raise PatchError(
            "A verified original backup is required for restoration.\n"
            + f"Expected backup: {backup}\n"
            + f"Backup SHA-256: {backup_state.sha256 or '<missing>'}"
        )
    _require_disk_space(target, spec, needs_backup=False)
    if dry_run:
        return OperationResult(False, "dry-run-restorable")

    temporary = _copy_to_sibling_temp(backup, target)
    try:
        restored_state = inspect_file(temporary, spec)
        if restored_state.state != "original":
            raise PatchError("Backup copy failed verification before restoration")

        target_before_replace = inspect_file(target, spec)
        backup_before_replace = inspect_file(backup, spec)
        if target_before_replace.state != "patched":
            raise PatchError(
                "Target changed while preparing restoration; refusing to replace it."
            )
        if backup_before_replace.state != "original":
            raise PatchError(
                "Backup changed while preparing restoration; refusing to continue."
            )
        _require_patch_site(target, spec.patched_bytes, spec)
        _replace_atomically(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    final_state = inspect_file(target, spec)
    final_backup_state = inspect_file(backup, spec)
    if final_state.state != "original":
        raise PatchError("Final verification failed after restoration")
    if final_backup_state.state != "original":
        raise PatchError("Backup failed verification after restoration")
    return OperationResult(True, "restored")


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
        home / ".local/share/Steam/steamapps/common/Flower",
        home / ".steam/steam/steamapps/common/Flower",
        home / ".var/app/com.valvesoftware.Steam/data/Steam/steamapps/common/Flower",
    ]

    for variable in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        base = os.environ.get(variable)
        if base:
            roots.append(Path(base) / "Steam/steamapps/common/Flower")
    yield from _unique_paths(roots)


def resolve_target(game_dir: Path | None) -> Path:
    if game_dir is not None:
        supplied = _absolute_without_resolving(game_dir)
        if (
            supplied.name.casefold() == "level4_a.bnk"
            and _path_exists_without_following(supplied)
        ):
            return supplied
        target = supplied / TARGET_RELATIVE_PATH
        if _path_exists_without_following(target):
            return target
        raise PatchError(
            f"Could not find {TARGET_RELATIVE_PATH} under the supplied path: {supplied}"
        )

    for root in _automatic_game_roots():
        target = root / TARGET_RELATIVE_PATH
        if _path_exists_without_following(target):
            return target
    raise PatchError(
        "Flower was not found automatically. Copy this script into the Flower game "
        + "directory or pass --game-dir /path/to/Flower."
    )


def print_status(target: Path, spec: PatchSpec = LEVEL4_PATCH) -> None:
    inspection = inspect_file(target, spec)
    backup = backup_path_for(target)
    backup_inspection = inspect_file(backup, spec)
    print(f"Flower Steam App: {APP_ID}")
    print(f"Supported build ID: {SUPPORTED_BUILD_ID}")
    print(f"Target: {target}")
    print(f"State: {inspection.state}")
    print(f"Size: {inspection.size}")
    print(f"SHA-256: {inspection.sha256 or '<missing>'}")
    print(f"Backup: {backup}")
    print(f"Backup state: {backup_inspection.state}")


class _Arguments(Protocol):
    command: str
    game_dir: Path | None
    dry_run: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fix the unrelated landing sting played by one Level 4 hay-bale "
            "activation in the Steam version of Flower."
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
        help="Flower installation directory or the Level4_A.bnk file itself",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="check target content, backup state, and free space without writing files",
    )
    _ = parser.add_argument("--version", action="version", version=SCRIPT_VERSION)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = cast(_Arguments, cast(object, build_parser().parse_args(argv)))
    try:
        target = resolve_target(args.game_dir)
        if args.command == "status":
            print_status(target)
            return 0
        if args.command == "install":
            _ = install_patch(target, dry_run=args.dry_run)
            print("Dry run successful; no changes made." if args.dry_run else "Success.")
            return 0

        _ = restore_patch(target, dry_run=args.dry_run)
        print(
            "Dry run successful; no changes made."
            if args.dry_run
            else "Fix reverted."
        )
        return 0
    except (OSError, PatchError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
