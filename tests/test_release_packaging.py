from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath
from typing import cast
from urllib.parse import unquote, urlsplit

from tools import build_release

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HAY_BALE_ARCHIVE = "flower-hay-bale-fix-1.0.0.zip"
BRIDGE_ARCHIVE = "flower-native-scepad-bridge-0.4.4.zip"
EXPECTED_SOURCE_MEMBERS = {
    HAY_BALE_ARCHIVE: (
        ("LICENSE", "LICENSE"),
        ("README.md", "docs/HAY_BALE_RELEASE.md"),
        ("flower_haybale_fix.py", "flower_haybale_fix.py"),
    ),
    BRIDGE_ARCHIVE: (
        ("LICENSE", "LICENSE"),
        ("README.md", "docs/BRIDGE_RELEASE.md"),
        ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        ("gyro_bridge/build.py", "gyro_bridge/build.py"),
        ("gyro_bridge/dist/libScePad.dll", "gyro_bridge/dist/libScePad.dll"),
        (
            "gyro_bridge/install_gyro_bridge.py",
            "gyro_bridge/install_gyro_bridge.py",
        ),
        (
            "gyro_bridge/src/flower_scepad_bridge.cpp",
            "gyro_bridge/src/flower_scepad_bridge.cpp",
        ),
        ("gyro_bridge/src/libScePad.def", "gyro_bridge/src/libScePad.def"),
        (
            "gyro_bridge/steam_input/game_actions_966330.vdf",
            "gyro_bridge/steam_input/game_actions_966330.vdf",
        ),
        ("licenses/LLVM.txt", "licenses/LLVM.txt"),
        (
            "licenses/MINGW-W64-RUNTIME.txt",
            "licenses/MINGW-W64-RUNTIME.txt",
        ),
    ),
}
FORBIDDEN_PROPRIETARY_SUFFIXES = {
    ".bank",
    ".bnk",
    ".dll",
    ".exe",
    ".pck",
    ".pdb",
    ".rdb",
    ".streams",
    ".wem",
    ".xvag",
}
MARKDOWN_LINK: re.Pattern[str] = re.compile(r"!?\[[^\]]*\]\(([^)\n]+)\)")
COMMAND_BLOCK: re.Pattern[str] = re.compile(
    r"```(?:bash|console|powershell|pwsh|sh|shell)\s*\n(.*?)```",
    flags=re.IGNORECASE | re.DOTALL,
)
PYTHON_SCRIPT: re.Pattern[str] = re.compile(
    r"(?<![A-Za-z0-9_.\\/-])((?:\.?[\\/])?[A-Za-z0-9_.-]+(?:[\\/][A-Za-z0-9_.-]+)*\.py)\b"
)

FALLBACK_HAY_README = b"""# Flower hay-bale sound fix 1.0.0

See the [project license](LICENSE).

```sh
python3 flower_haybale_fix.py status
python3 flower_haybale_fix.py install --dry-run
```
"""
FALLBACK_BRIDGE_README = b"""# Flower native ScePad bridge 0.4.4

See the [project license](LICENSE),
[third-party notices](THIRD_PARTY_NOTICES.md),
[LLVM terms](licenses/LLVM.txt), and
[MinGW-w64 runtime terms](licenses/MINGW-W64-RUNTIME.txt).
The [installer](gyro_bridge/install_gyro_bridge.py),
[build script](gyro_bridge/build.py),
[native source](gyro_bridge/src/flower_scepad_bridge.cpp), and
[action manifest](gyro_bridge/steam_input/game_actions_966330.vdf) are included.

```sh
python3 gyro_bridge/install_gyro_bridge.py status
python3 gyro_bridge/install_gyro_bridge.py install --dry-run
python3 gyro_bridge/build.py
```
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_git(
    project_root: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", os.fspath(project_root), *arguments],
        check=check,
        capture_output=True,
    )


def commit_blob(project_root: Path, path: str, ref: str = "HEAD") -> bytes:
    return run_git(project_root, "show", f"{ref}:{path}").stdout


def project_head_blob(path: str) -> bytes | None:
    result = run_git(PROJECT_ROOT, "show", f"HEAD:{path}", check=False)
    return result.stdout if result.returncode == 0 else None


def commit_all(project_root: Path, message: str) -> str:
    _ = run_git(project_root, "add", "--", ".")
    _ = run_git(
        project_root,
        "-c",
        "user.name=Release Packaging Tests",
        "-c",
        "user.email=release-tests@example.invalid",
        "commit",
        "--quiet",
        "-m",
        message,
    )
    return run_git(project_root, "rev-parse", "HEAD").stdout.decode("ascii").strip()


def create_committed_repository(project_root: Path) -> str:
    project_root.mkdir()
    _ = run_git(project_root, "init", "--quiet")
    source_paths = {
        source_path
        for mappings in EXPECTED_SOURCE_MEMBERS.values()
        for _archive_path, source_path in mappings
    }
    fallback_docs = {
        "docs/HAY_BALE_RELEASE.md": FALLBACK_HAY_README,
        "docs/BRIDGE_RELEASE.md": FALLBACK_BRIDGE_README,
    }
    for relative_path in sorted(source_paths):
        data = project_head_blob(relative_path)
        working_source = PROJECT_ROOT / relative_path
        if (
            data is None
            and relative_path in fallback_docs
            and working_source.is_file()
        ):
            data = working_source.read_bytes()
        if data is None:
            data = fallback_docs.get(
                relative_path,
                f"fixture for {relative_path}\n".encode(),
            )
        destination = project_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = destination.write_bytes(data)

    for pinned_path in (
        "gyro_bridge/dist/libScePad.dll",
        "gyro_bridge/steam_input/game_actions_966330.vdf",
    ):
        if project_head_blob(pinned_path) is None:
            raise AssertionError(f"project HEAD is missing pinned fixture {pinned_path}")

    tool_destination = project_root / "tools" / "build_release.py"
    tool_destination.parent.mkdir(parents=True, exist_ok=True)
    _ = tool_destination.write_bytes(
        (PROJECT_ROOT / "tools" / "build_release.py").read_bytes()
    )
    tool_destination.chmod(0o755)
    return commit_all(project_root, "release fixture")


def expected_members(archive_name: str) -> tuple[str, ...]:
    return tuple(path for path, _source in EXPECTED_SOURCE_MEMBERS[archive_name])


def assert_manifest(
    testcase: unittest.TestCase,
    output_dir: Path,
    archive_names: tuple[str, ...],
) -> None:
    testcase.assertEqual(
        {path.name for path in output_dir.iterdir()},
        {*archive_names, "SHA256SUMS"},
    )
    expected_lines = [
        f"{sha256((output_dir / name).read_bytes())}  {name}"
        for name in archive_names
    ]
    sums = (output_dir / "SHA256SUMS").read_bytes()
    testcase.assertTrue(sums.endswith(b"\n"))
    testcase.assertEqual(sums.decode("ascii").splitlines(), expected_lines)


def relative_markdown_targets(readme: str) -> tuple[str, ...]:
    targets: list[str] = []
    raw_destinations = cast(list[str], MARKDOWN_LINK.findall(readme))
    for raw_destination in raw_destinations:
        destination = raw_destination.strip()
        if destination.startswith("<") and ">" in destination:
            destination = destination[1:destination.index(">")]
        else:
            destination = destination.split(maxsplit=1)[0]
        parsed = urlsplit(destination)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        decoded_path = unquote(parsed.path)
        candidate = PurePosixPath(decoded_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            targets.append(decoded_path)
        else:
            targets.append(candidate.as_posix())
    return tuple(targets)


def documented_python_targets(readme: str) -> tuple[str, ...]:
    targets: list[str] = []
    blocks = cast(list[str], COMMAND_BLOCK.findall(readme))
    for block in blocks:
        matches = cast(list[str], PYTHON_SCRIPT.findall(block))
        for match in matches:
            normalized = match.replace("\\", "/").removeprefix("./")
            targets.append(normalized)
    return tuple(targets)


def assert_archive_closure(
    testcase: unittest.TestCase,
    archive: zipfile.ZipFile,
) -> None:
    members = set(archive.namelist())
    readme = archive.read("README.md").decode("utf-8")
    links = relative_markdown_targets(readme)
    testcase.assertTrue(links, "README must contain relative Markdown links")
    for target in links:
        testcase.assertIn(target, members, f"README link is not packaged: {target}")

    commands = documented_python_targets(readme)
    testcase.assertTrue(commands, "README must document a Python command")
    for target in commands:
        testcase.assertIn(
            target,
            members,
            f"documented Python command target is not packaged: {target}",
        )


class CommittedRepositoryTestCase(unittest.TestCase):
    temporary_directory: tempfile.TemporaryDirectory[str]  # pyright: ignore[reportUninitializedInstanceVariable]
    root: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    repository: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    head_commit: str  # pyright: ignore[reportUninitializedInstanceVariable]

    # `typing.override` is only available in Python 3.12 and newer.
    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.repository = self.root / "repository"
        self.head_commit = create_committed_repository(self.repository)
        self.assertEqual(run_git(self.repository, "status", "--porcelain").stdout, b"")

    def output_path(self, name: str) -> Path:
        return self.root / name


class ReleaseArchiveTests(CommittedRepositoryTestCase):
    def test_exact_members_aliases_and_committed_bytes(self) -> None:
        output = self.output_path("all-release")
        _ = build_release.build_releases(
            output,
            component="all",
            project_root=self.repository,
        )
        assert_manifest(self, output, (HAY_BALE_ARCHIVE, BRIDGE_ARCHIVE))

        for archive_name, mappings in EXPECTED_SOURCE_MEMBERS.items():
            with (
                self.subTest(archive=archive_name),
                zipfile.ZipFile(output / archive_name) as archive,
            ):
                self.assertEqual(tuple(archive.namelist()), expected_members(archive_name))
                self.assertEqual(archive.comment, b"")
                for archive_path, source_path in mappings:
                    self.assertEqual(
                        archive.read(archive_path),
                        commit_blob(self.repository, source_path, self.head_commit),
                    )
                self.assertNotIn("docs/HAY_BALE_RELEASE.md", archive.namelist())
                self.assertNotIn("docs/BRIDGE_RELEASE.md", archive.namelist())

    def test_per_component_archives_and_manifests(self) -> None:
        cases = (
            ("hay-bale", (HAY_BALE_ARCHIVE,)),
            ("bridge", (BRIDGE_ARCHIVE,)),
            ("all", (HAY_BALE_ARCHIVE, BRIDGE_ARCHIVE)),
        )
        for component, archive_names in cases:
            with self.subTest(component=component):
                output = self.output_path(f"release-{component}")
                _ = build_release.build_releases(
                    output,
                    component=component,
                    project_root=self.repository,
                )
                assert_manifest(self, output, archive_names)

    def test_archive_bytes_are_deterministic(self) -> None:
        first = self.output_path("first")
        second = self.output_path("second")
        _ = build_release.build_releases(
            first,
            component="all",
            ref=self.head_commit,
            project_root=self.repository,
        )
        _ = build_release.build_releases(
            second,
            component="all",
            ref="HEAD",
            project_root=self.repository,
        )
        for name in (HAY_BALE_ARCHIVE, BRIDGE_ARCHIVE, "SHA256SUMS"):
            with self.subTest(path=name):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_zip_metadata_is_reproducible(self) -> None:
        output = self.output_path("metadata")
        _ = build_release.build_releases(
            output,
            component="all",
            project_root=self.repository,
        )
        for archive_name in (HAY_BALE_ARCHIVE, BRIDGE_ARCHIVE):
            with zipfile.ZipFile(output / archive_name) as archive:
                for info in archive.infolist():
                    self.assertEqual(info.date_time, build_release.FIXED_ZIP_TIMESTAMP)
                    self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                    self.assertEqual(info.create_system, 3)
                    self.assertEqual(info.create_version, 20)
                    self.assertEqual(info.extract_version, 20)
                    self.assertEqual(info.flag_bits, 0)
                    self.assertEqual(info.internal_attr, 0)
                    self.assertEqual(info.external_attr >> 16, stat.S_IFREG | 0o644)
                    self.assertEqual(info.extra, b"")
                    self.assertEqual(info.comment, b"")

    def test_readme_links_and_documented_commands_are_closed(self) -> None:
        output = self.output_path("closure")
        _ = build_release.build_releases(
            output,
            component="all",
            project_root=self.repository,
        )
        for archive_name in (HAY_BALE_ARCHIVE, BRIDGE_ARCHIVE):
            with (
                self.subTest(archive=archive_name),
                zipfile.ZipFile(output / archive_name) as archive,
            ):
                assert_archive_closure(self, archive)

    def test_no_forbidden_proprietary_file_classes_are_packaged(self) -> None:
        allowed_dll = "gyro_bridge/dist/libScePad.dll"
        forbidden_basenames = {
            "flower.exe",
            "libscepad_original.dll",
            "steam_api.dll",
            "steam_api64.dll",
        }
        for archive_name in (HAY_BALE_ARCHIVE, BRIDGE_ARCHIVE):
            for member in expected_members(archive_name):
                with self.subTest(archive=archive_name, member=member):
                    path = PurePosixPath(member)
                    self.assertNotIn(path.name.casefold(), forbidden_basenames)
                    suffix = path.suffix.casefold()
                    if suffix == ".dll":
                        self.assertEqual(member, allowed_dll)
                    else:
                        self.assertNotIn(suffix, FORBIDDEN_PROPRIETARY_SUFFIXES)

    def test_explicit_tag_resolving_to_head_is_accepted(self) -> None:
        _ = run_git(self.repository, "tag", "release-candidate")
        output = self.output_path("tagged")
        _ = build_release.build_releases(
            output,
            component="hay-bale",
            ref="release-candidate",
            project_root=self.repository,
        )
        assert_manifest(self, output, (HAY_BALE_ARCHIVE,))


class ReleasePolicyTests(CommittedRepositoryTestCase):
    def test_staged_changes_are_refused(self) -> None:
        _ = (self.repository / "LICENSE").write_text("staged replacement\n")
        _ = run_git(self.repository, "add", "--", "LICENSE")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "staged changes"):
            _ = build_release.build_releases(
                self.output_path("staged"),
                component="hay-bale",
                project_root=self.repository,
            )

    def test_unstaged_changes_are_refused(self) -> None:
        _ = (self.repository / "LICENSE").write_text("unstaged replacement\n")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "unstaged changes"):
            _ = build_release.build_releases(
                self.output_path("unstaged"),
                component="hay-bale",
                project_root=self.repository,
            )

    def test_untracked_files_are_refused(self) -> None:
        _ = (self.repository / "untracked.txt").write_text("not committed\n")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "untracked files"):
            _ = build_release.build_releases(
                self.output_path("untracked"),
                component="hay-bale",
                project_root=self.repository,
            )

    def test_repository_without_commit_is_refused(self) -> None:
        repository = self.root / "no-commit"
        repository.mkdir()
        _ = run_git(repository, "init", "--quiet")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "no HEAD commit"):
            _ = build_release.build_releases(
                self.output_path("no-commit-output"),
                component="hay-bale",
                project_root=repository,
            )

    def test_ref_not_resolving_to_head_is_refused(self) -> None:
        old_commit = self.head_commit
        _ = (self.repository / "history.txt").write_text("second commit\n")
        new_commit = commit_all(self.repository, "advance HEAD")
        self.assertNotEqual(old_commit, new_commit)
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "not HEAD"):
            _ = build_release.build_releases(
                self.output_path("old-ref"),
                component="hay-bale",
                ref=old_commit,
                project_root=self.repository,
            )

    def test_stale_output_entries_are_refused(self) -> None:
        output = self.output_path("stale-output")
        output.mkdir()
        _ = (output / "old.zip").write_bytes(b"stale")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "stale entries"):
            _ = build_release.build_releases(
                output,
                component="hay-bale",
                project_root=self.repository,
            )
        self.assertEqual((output / "old.zip").read_bytes(), b"stale")

    def test_existing_empty_external_output_is_accepted(self) -> None:
        output = self.output_path("empty-output")
        output.mkdir()
        _ = build_release.build_releases(
            output,
            component="hay-bale",
            project_root=self.repository,
        )
        assert_manifest(self, output, (HAY_BALE_ARCHIVE,))

    def test_output_inside_repository_is_refused(self) -> None:
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "external"):
            _ = build_release.build_releases(
                self.repository / "release-output",
                component="hay-bale",
                project_root=self.repository,
            )

    def test_modified_committed_bridge_artifact_is_refused(self) -> None:
        artifact = self.repository / "gyro_bridge" / "dist" / "libScePad.dll"
        _ = artifact.write_bytes(artifact.read_bytes() + b"tampered")
        _ = commit_all(self.repository, "tamper bridge")
        with self.assertRaisesRegex(
            build_release.ReleasePolicyError,
            "release fingerprint mismatch",
        ):
            _ = build_release.build_releases(
                self.output_path("tampered-bridge"),
                component="bridge",
                project_root=self.repository,
            )


class ReleaseCliTests(CommittedRepositoryTestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                os.fspath(self.repository / "tools" / "build_release.py"),
                *arguments,
            ],
            cwd=self.repository,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_requires_output_directory_and_component(self) -> None:
        no_arguments = self.run_cli()
        self.assertEqual(no_arguments.returncode, 2)
        self.assertIn("--output-dir", no_arguments.stderr)
        self.assertIn("--component", no_arguments.stderr)

        missing_component = self.run_cli(
            "--output-dir",
            os.fspath(self.output_path("missing-component")),
        )
        self.assertEqual(missing_component.returncode, 2)
        self.assertIn("--component", missing_component.stderr)

    def test_cli_builds_only_selected_component(self) -> None:
        output = self.output_path("cli-bridge")
        result = self.run_cli(
            "--output-dir",
            os.fspath(output),
            "--component",
            "bridge",
            "--ref",
            "HEAD",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_manifest(self, output, (BRIDGE_ARCHIVE,))

    def test_cli_refuses_repository_internal_output(self) -> None:
        result = self.run_cli(
            "--output-dir",
            os.fspath(self.repository / "release-output"),
            "--component",
            "hay-bale",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("external", result.stderr)


if __name__ == "__main__":
    _ = unittest.main()
