#!/usr/bin/env python3
"""Build the deterministic, policy-checked public release bundle."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
REGULAR_FILE_MODE = stat.S_IFREG | 0o644
EXECUTABLE_FILE_MODE = stat.S_IFREG | 0o755

BUNDLE_VERSION = "1.2.0"
# Preserve --component all for older automation, but refuse component-only requests.
COMPONENTS = ("all",)


class ReleasePolicyError(RuntimeError):
    """Raised when a release would violate the public packaging policy."""


@dataclass(frozen=True)
class ReleaseMember:
    archive_path: str
    source_path: str


@dataclass(frozen=True)
class ReleaseSpec:
    component: str
    slug: str
    version: str
    members: tuple[ReleaseMember, ...]

    @property
    def archive_name(self) -> str:
        return f"{self.slug}-{self.version}.zip"


@dataclass(frozen=True)
class PinnedFile:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class BuiltArchive:
    path: Path
    sha256: str


BUNDLE_RELEASE = ReleaseSpec(
    component="all",
    slug="flower-steam-fixes",
    version=BUNDLE_VERSION,
    members=(
        ReleaseMember("GYRO_BRIDGE.md", "GYRO_BRIDGE.md"),
        ReleaseMember("HAY_BALE_FIX.md", "HAY_BALE_FIX.md"),
        ReleaseMember("INSTALL_GYRO_BRIDGE_LINUX.sh", "INSTALL_GYRO_BRIDGE_LINUX.sh"),
        ReleaseMember("INSTALL_GYRO_BRIDGE_WINDOWS.cmd", "INSTALL_GYRO_BRIDGE_WINDOWS.cmd"),
        ReleaseMember("INSTALL_HAY_BALE_LINUX.sh", "INSTALL_HAY_BALE_LINUX.sh"),
        ReleaseMember("INSTALL_HAY_BALE_WINDOWS.cmd", "INSTALL_HAY_BALE_WINDOWS.cmd"),
        ReleaseMember("LICENSE", "LICENSE"),
        ReleaseMember("README.md", "BUNDLE_README.md"),
        ReleaseMember("REVERT_GYRO_BRIDGE_LINUX.sh", "REVERT_GYRO_BRIDGE_LINUX.sh"),
        ReleaseMember("REVERT_GYRO_BRIDGE_WINDOWS.cmd", "REVERT_GYRO_BRIDGE_WINDOWS.cmd"),
        ReleaseMember("REVERT_HAY_BALE_LINUX.sh", "REVERT_HAY_BALE_LINUX.sh"),
        ReleaseMember("REVERT_HAY_BALE_WINDOWS.cmd", "REVERT_HAY_BALE_WINDOWS.cmd"),
        ReleaseMember("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        ReleaseMember("flower_haybale_fix.py", "flower_haybale_fix.py"),
        ReleaseMember("gyro_bridge/build.py", "gyro_bridge/build.py"),
        ReleaseMember(
            "gyro_bridge/dist/libScePad.dll",
            "gyro_bridge/dist/libScePad.dll",
        ),
        ReleaseMember(
            "gyro_bridge/install_gyro_bridge.py",
            "gyro_bridge/install_gyro_bridge.py",
        ),
        ReleaseMember(
            "gyro_bridge/src/flower_scepad_bridge.cpp",
            "gyro_bridge/src/flower_scepad_bridge.cpp",
        ),
        ReleaseMember(
            "gyro_bridge/src/libScePad.def",
            "gyro_bridge/src/libScePad.def",
        ),
        ReleaseMember(
            "gyro_bridge/steam_input/game_actions_966330.vdf",
            "gyro_bridge/steam_input/game_actions_966330.vdf",
        ),
        ReleaseMember("licenses/LLVM.txt", "licenses/LLVM.txt"),
        ReleaseMember(
            "licenses/MINGW-W64-RUNTIME.txt",
            "licenses/MINGW-W64-RUNTIME.txt",
        ),
    ),
)
RELEASES = (BUNDLE_RELEASE,)

PINNED_RELEASE_INPUTS = (
    PinnedFile(
        path="gyro_bridge/dist/libScePad.dll",
        size=84_992,
        sha256="adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c",
    ),
    PinnedFile(
        path="gyro_bridge/steam_input/game_actions_966330.vdf",
        size=2_438,
        sha256="8d3f5ab9b5a321ab3f6162935a8810642b08c307780a6356d75c102e8ce64b13",
    ),
)

ALLOWED_BINARY_SOURCE_FILES = frozenset(
    {
        "gyro_bridge/dist/libScePad.dll",
    }
)
ALLOWED_BINARY_ARCHIVE_FILES = ALLOWED_BINARY_SOURCE_FILES
ALLOWED_TEXT_SUFFIXES = frozenset(
    {
        ".cmd",
        ".cpp",
        ".def",
        ".md",
        ".py",
        ".sh",
        ".txt",
        ".vdf",
    }
)
FORBIDDEN_SUFFIXES = frozenset(
    {
        ".bank",
        ".bnk",
        ".dll",
        ".dylib",
        ".exe",
        ".ilk",
        ".lib",
        ".pck",
        ".pdb",
        ".rdb",
        ".so",
        ".streams",
        ".wem",
        ".xvag",
    }
)
FORBIDDEN_BASENAMES = frozenset(
    {
        "flower.exe",
        "libscepad_original.dll",
        "steam_api.dll",
        "steam_api64.dll",
    }
)


def _validate_relative_path(path: str) -> PurePosixPath:
    pure_path = PurePosixPath(path)
    if (
        not path
        or pure_path.is_absolute()
        or pure_path.as_posix() != path
        or "\\" in path
        or ":" in path
        or any(ord(character) < 32 for character in path)
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise ReleasePolicyError(f"unsafe release path: {path!r}")
    return pure_path


def _validate_public_file(
    path: str,
    *,
    allowed_binary_files: frozenset[str],
    label: str,
) -> None:
    pure_path = _validate_relative_path(path)
    if path in allowed_binary_files:
        return

    basename = pure_path.name.casefold()
    suffix = pure_path.suffix.casefold()
    if basename in FORBIDDEN_BASENAMES or suffix in FORBIDDEN_SUFFIXES:
        raise ReleasePolicyError(f"disallowed {label}: {path}")
    if pure_path.name == "LICENSE":
        return
    if suffix not in ALLOWED_TEXT_SUFFIXES:
        raise ReleasePolicyError(f"disallowed {label} file class: {path}")


def _validate_release_specs() -> None:
    archive_names = tuple(release.archive_name for release in RELEASES)
    components = tuple(release.component for release in RELEASES)
    if archive_names != tuple(sorted(archive_names)):
        raise ReleasePolicyError("release specifications must be explicitly sorted")
    if len(archive_names) != len(set(archive_names)):
        raise ReleasePolicyError("duplicate release archive name")
    if len(components) != len(set(components)):
        raise ReleasePolicyError("duplicate release component")

    for release in RELEASES:
        archive_paths = tuple(member.archive_path for member in release.members)
        if archive_paths != tuple(sorted(archive_paths)):
            raise ReleasePolicyError(
                f"{release.archive_name} member allowlist must be explicitly sorted"
            )
        if len(archive_paths) != len(set(archive_paths)):
            raise ReleasePolicyError(
                f"{release.archive_name} member allowlist contains duplicates"
            )
        for member in release.members:
            _validate_public_file(
                member.source_path,
                allowed_binary_files=ALLOWED_BINARY_SOURCE_FILES,
                label="release source",
            )
            _validate_public_file(
                member.archive_path,
                allowed_binary_files=ALLOWED_BINARY_ARCHIVE_FILES,
                label="archive member",
            )


def _run_git(
    project_root: Path,
    arguments: Sequence[str],
    *,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", os.fspath(project_root), *arguments]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
        )
    except FileNotFoundError as error:
        raise ReleasePolicyError("Git is required to build a release") from error

    if completed.returncode not in allowed_returncodes:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        if len(detail) > 800:
            detail = detail[-800:]
        message = f"Git command failed ({' '.join(arguments)})"
        if detail:
            message += f": {detail}"
        raise ReleasePolicyError(message)
    return completed


def _validate_repository_root(project_root: Path) -> Path:
    project_root = project_root.resolve()
    if not project_root.is_dir():
        raise ReleasePolicyError(f"project root is not a directory: {project_root}")
    result = _run_git(project_root, ("rev-parse", "--show-toplevel"))
    reported_root = Path(os.fsdecode(result.stdout).strip()).resolve()
    if reported_root != project_root:
        raise ReleasePolicyError(
            f"expected Git repository root {reported_root}, got {project_root}"
        )
    return project_root


def _resolve_commit(project_root: Path, ref: str) -> str | None:
    if (
        not ref
        or ref.startswith("-")
        or any(ord(character) < 32 for character in ref)
    ):
        raise ReleasePolicyError(f"unsafe Git ref: {ref!r}")
    result = _run_git(
        project_root,
        ("rev-parse", "--verify", f"{ref}^{{commit}}"),
        allowed_returncodes=(0, 1, 128),
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.decode("ascii", errors="strict").strip()
    if not commit or any(character not in "0123456789abcdef" for character in commit):
        raise ReleasePolicyError(f"Git returned an invalid commit ID for {ref!r}")
    return commit


def _require_clean_repository(project_root: Path, head_commit: str) -> None:
    staged = _run_git(
        project_root,
        (
            "diff",
            "--cached",
            "--quiet",
            "--no-ext-diff",
            head_commit,
            "--",
        ),
        allowed_returncodes=(0, 1),
    )
    if staged.returncode == 1:
        raise ReleasePolicyError("staged changes are not allowed for a release")

    unstaged = _run_git(
        project_root,
        ("diff", "--quiet", "--no-ext-diff", "--"),
        allowed_returncodes=(0, 1),
    )
    if unstaged.returncode == 1:
        raise ReleasePolicyError("unstaged changes are not allowed for a release")

    untracked = _run_git(
        project_root,
        ("ls-files", "--others", "--exclude-standard", "-z"),
    )
    if untracked.stdout:
        first_path = os.fsdecode(untracked.stdout.split(b"\0", 1)[0])
        raise ReleasePolicyError(
            f"untracked files are not allowed for a release: {first_path}"
        )


def resolve_release_commit(
    project_root: Path,
    ref: str = "HEAD",
) -> tuple[Path, str]:
    """Resolve a clean release ref and require it to identify current HEAD."""
    project_root = _validate_repository_root(project_root)
    head_commit = _resolve_commit(project_root, "HEAD")
    if head_commit is None:
        raise ReleasePolicyError("release repository has no HEAD commit")
    resolved_commit = _resolve_commit(project_root, ref)
    if resolved_commit is None:
        raise ReleasePolicyError(f"release ref does not resolve to a commit: {ref}")
    if resolved_commit != head_commit:
        raise ReleasePolicyError(
            f"release ref {ref!r} resolves to {resolved_commit}, not HEAD {head_commit}"
        )
    _require_clean_repository(project_root, head_commit)
    return project_root, resolved_commit


def _committed_blob_ids(
    project_root: Path,
    commit: str,
    source_paths: tuple[str, ...],
) -> dict[str, str]:
    result = _run_git(
        project_root,
        ("ls-tree", "-z", "--full-tree", commit, "--", *source_paths),
    )
    entries: dict[str, str] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, encoded_path = record.split(b"\t", 1)
            encoded_mode, encoded_type, encoded_object_id = metadata.split(b" ", 2)
        except ValueError as error:
            raise ReleasePolicyError("Git returned an invalid tree record") from error
        path = os.fsdecode(encoded_path)
        mode = os.fsdecode(encoded_mode)
        object_type = os.fsdecode(encoded_type)
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise ReleasePolicyError(
                f"release source is not a regular committed file: {path}"
            )
        entries[path] = os.fsdecode(encoded_object_id)

    for path in source_paths:
        if path not in entries:
            raise ReleasePolicyError(f"release source is missing from commit: {path}")
    return entries


def load_committed_files(
    project_root: Path,
    commit: str,
    source_paths: tuple[str, ...],
) -> dict[str, bytes]:
    """Load immutable allowlisted blobs from one resolved Git commit."""
    for path in source_paths:
        _validate_public_file(
            path,
            allowed_binary_files=ALLOWED_BINARY_SOURCE_FILES,
            label="release source",
        )
    object_ids = _committed_blob_ids(project_root, commit, source_paths)
    return {
        path: _run_git(project_root, ("cat-file", "blob", object_ids[path])).stdout
        for path in source_paths
    }


def _validate_pinned_inputs(committed_files: dict[str, bytes]) -> None:
    for pinned in PINNED_RELEASE_INPUTS:
        data = committed_files.get(pinned.path)
        if data is None:
            continue
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != pinned.size or digest != pinned.sha256:
            detail = (
                f"release fingerprint mismatch for {pinned.path}: expected "
                f"{pinned.size} bytes/{pinned.sha256}, got {len(data)} "
                f"bytes/{digest}"
            )
            raise ReleasePolicyError(detail)


def _select_releases(component: str) -> tuple[ReleaseSpec, ...]:
    if component not in COMPONENTS:
        raise ReleasePolicyError(f"unknown release component: {component}")
    return RELEASES


def _release_members(
    release: ReleaseSpec,
    committed_files: dict[str, bytes],
) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (member.archive_path, committed_files[member.source_path])
        for member in release.members
    )


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.flag_bits = 0
    info.internal_attr = 0
    mode = (
        EXECUTABLE_FILE_MODE
        if PurePosixPath(path).suffix.casefold() == ".sh"
        else REGULAR_FILE_MODE
    )
    info.external_attr = mode << 16
    info.extra = b""
    info.comment = b""
    return info


def _build_zip(members: tuple[tuple[str, bytes], ...]) -> bytes:
    with tempfile.SpooledTemporaryFile(mode="w+b") as buffer:
        with zipfile.ZipFile(
            buffer,
            mode="w",
            compression=zipfile.ZIP_STORED,
            allowZip64=True,
            strict_timestamps=True,
        ) as archive:
            archive.comment = b""
            for path, data in members:
                archive.writestr(_zip_info(path), data)
        _ = buffer.seek(0)
        return buffer.read()


def _prepare_output_directory(project_root: Path, output_dir: Path) -> Path:
    output_dir = output_dir.expanduser()
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    resolved_output = output_dir.resolve(strict=False)
    resolved_root = project_root.resolve()
    if resolved_output == resolved_root or resolved_output.is_relative_to(resolved_root):
        raise ReleasePolicyError(
            f"release output directory must be external to the repository: {output_dir}"
        )

    try:
        if output_dir.exists() or output_dir.is_symlink():
            output_mode = output_dir.lstat().st_mode
            if not stat.S_ISDIR(output_mode) or output_dir.is_symlink():
                raise ReleasePolicyError(
                    f"release output path is not a regular directory: {output_dir}"
                )
            stale_entry = next(output_dir.iterdir(), None)
            if stale_entry is not None:
                raise ReleasePolicyError(
                    f"release output directory contains stale entries: {stale_entry.name}"
                )
        else:
            output_dir.mkdir(parents=True)
    except ReleasePolicyError:
        raise
    except OSError as error:
        raise ReleasePolicyError(
            f"cannot prepare release output directory {output_dir}: {error}"
        ) from error
    return output_dir


def build_releases(
    output_dir: Path,
    *,
    component: str = "all",
    ref: str = "HEAD",
    project_root: Path = PROJECT_ROOT,
) -> tuple[BuiltArchive, ...]:
    """Build the public bundle ZIP and its matching SHA-256 manifest."""
    _validate_release_specs()
    selected_releases = _select_releases(component)
    project_root, commit = resolve_release_commit(project_root, ref)
    source_paths = tuple(
        sorted(
            {
                member.source_path
                for release in selected_releases
                for member in release.members
            }
        )
    )
    committed_files = load_committed_files(project_root, commit, source_paths)
    _validate_pinned_inputs(committed_files)

    archive_data = tuple(
        (
            release.archive_name,
            _build_zip(_release_members(release, committed_files)),
        )
        for release in selected_releases
    )
    sums = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, data in archive_data
    ).encode("ascii")

    output_dir = _prepare_output_directory(project_root, output_dir)
    output_names = tuple(name for name, _ in archive_data) + ("SHA256SUMS",)
    with tempfile.TemporaryDirectory(
        prefix=".flower-release-",
        dir=output_dir,
    ) as staging_name:
        staging_dir = Path(staging_name)
        for name, data in (*archive_data, ("SHA256SUMS", sums)):
            staged_path = staging_dir / name
            _ = staged_path.write_bytes(data)
            staged_path.chmod(0o644)
        unexpected_entries = tuple(
            path for path in output_dir.iterdir() if path != staging_dir
        )
        if unexpected_entries:
            names = ", ".join(path.name for path in unexpected_entries)
            raise ReleasePolicyError(
                f"release output directory changed during build: {names}"
            )
        for name in output_names:
            os.replace(staging_dir / name, output_dir / name)

    return tuple(
        BuiltArchive(
            path=output_dir / name,
            sha256=hashlib.sha256(data).hexdigest(),
        )
        for name, data in archive_data
    )


@dataclass(frozen=True)
class CommandLineOptions:
    output_dir: Path
    component: str
    ref: str


def _parse_args(arguments: Sequence[str] | None) -> CommandLineOptions:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new or empty output directory outside the repository",
    )
    _ = parser.add_argument(
        "--component",
        choices=COMPONENTS,
        default="all",
        help=argparse.SUPPRESS,
    )
    _ = parser.add_argument(
        "--ref",
        default="HEAD",
        help="Git commit/ref to package; it must resolve to current HEAD",
    )
    options = parser.parse_args(arguments)
    output_dir = cast(object, options.output_dir)
    component = cast(object, options.component)
    ref = cast(object, options.ref)
    if not isinstance(output_dir, Path):
        raise ReleasePolicyError("--output-dir must be a filesystem path")
    if not isinstance(component, str) or not isinstance(ref, str):
        raise ReleasePolicyError("invalid command-line release selection")
    return CommandLineOptions(output_dir, component, ref)


def main(arguments: Sequence[str] | None = None) -> int:
    options = _parse_args(arguments)
    try:
        built = build_releases(
            options.output_dir,
            component=options.component,
            ref=options.ref,
        )
    except (OSError, ReleasePolicyError) as error:
        print(f"release build refused: {error}", file=sys.stderr)
        return 1

    for archive in built:
        print(f"{archive.sha256}  {archive.path}")
    print(f"Wrote {built[0].path.parent / 'SHA256SUMS'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
