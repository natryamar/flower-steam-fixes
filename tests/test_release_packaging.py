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
BUNDLE_ARCHIVE = "flower-steam-fixes-1.2.0.zip"
EXPECTED_SOURCE_MEMBERS = {
    BUNDLE_ARCHIVE: (
        ("GYRO_BRIDGE.md", "GYRO_BRIDGE.md"),
        ("HAY_BALE_FIX.md", "HAY_BALE_FIX.md"),
        ("INSTALL_GYRO_BRIDGE_LINUX.sh", "INSTALL_GYRO_BRIDGE_LINUX.sh"),
        ("INSTALL_GYRO_BRIDGE_WINDOWS.cmd", "INSTALL_GYRO_BRIDGE_WINDOWS.cmd"),
        ("INSTALL_HAY_BALE_LINUX.sh", "INSTALL_HAY_BALE_LINUX.sh"),
        ("INSTALL_HAY_BALE_WINDOWS.cmd", "INSTALL_HAY_BALE_WINDOWS.cmd"),
        ("LICENSE", "LICENSE"),
        ("README.md", "BUNDLE_README.md"),
        ("REVERT_GYRO_BRIDGE_LINUX.sh", "REVERT_GYRO_BRIDGE_LINUX.sh"),
        ("REVERT_GYRO_BRIDGE_WINDOWS.cmd", "REVERT_GYRO_BRIDGE_WINDOWS.cmd"),
        ("REVERT_HAY_BALE_LINUX.sh", "REVERT_HAY_BALE_LINUX.sh"),
        ("REVERT_HAY_BALE_WINDOWS.cmd", "REVERT_HAY_BALE_WINDOWS.cmd"),
        ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        ("flower_haybale_fix.py", "flower_haybale_fix.py"),
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
    # Commit current inputs to an isolated fixture so tests cover uncommitted edits
    # without weakening the production builder's clean-checkout/Git-object policy.
    for relative_path in sorted(source_paths):
        data = (PROJECT_ROOT / relative_path).read_bytes()
        destination = project_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = destination.write_bytes(data)

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
    guide: str,
) -> None:
    members = set(archive.namelist())
    readme = archive.read(guide).decode("utf-8")
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
        assert_manifest(self, output, (BUNDLE_ARCHIVE,))

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
                self.assertNotIn("BUNDLE_README.md", archive.namelist())

    def test_component_only_requests_are_refused(self) -> None:
        for component in ("hay-bale", "bridge"):
            with (
                self.subTest(component=component),
                self.assertRaisesRegex(
                    build_release.ReleasePolicyError, "unknown release component"
                ),
            ):
                _ = build_release.build_releases(
                    self.output_path(f"release-{component}"),
                    component=component,
                    project_root=self.repository,
                )

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
        for name in (BUNDLE_ARCHIVE, "SHA256SUMS"):
            with self.subTest(path=name):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_zip_metadata_is_reproducible(self) -> None:
        output = self.output_path("metadata")
        _ = build_release.build_releases(
            output,
            component="all",
            project_root=self.repository,
        )
        with zipfile.ZipFile(output / BUNDLE_ARCHIVE) as archive:
            for info in archive.infolist():
                self.assertEqual(info.date_time, build_release.FIXED_ZIP_TIMESTAMP)
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.create_version, 20)
                self.assertEqual(info.extract_version, 20)
                self.assertEqual(info.flag_bits, 0)
                self.assertEqual(info.internal_attr, 0)
                expected_mode = (
                    stat.S_IFREG | 0o755
                    if info.filename.endswith(".sh")
                    else stat.S_IFREG | 0o644
                )
                self.assertEqual(info.external_attr >> 16, expected_mode)
                self.assertEqual(info.extra, b"")
                self.assertEqual(info.comment, b"")

    def test_readme_links_and_documented_commands_are_closed(self) -> None:
        output = self.output_path("closure")
        _ = build_release.build_releases(
            output,
            component="all",
            project_root=self.repository,
        )
        with zipfile.ZipFile(output / BUNDLE_ARCHIVE) as archive:
            for guide in ("README.md", "HAY_BALE_FIX.md", "GYRO_BRIDGE.md"):
                with self.subTest(guide=guide):
                    assert_archive_closure(self, archive, guide)

    @unittest.skipUnless(os.name == "posix", "Linux launchers need a POSIX shell")
    def test_extracted_launchers_find_the_bundled_installers(self) -> None:
        output = self.output_path("launcher-release")
        _ = build_release.build_releases(output, project_root=self.repository)
        extracted = self.root / "extracted bundle with spaces"
        with zipfile.ZipFile(output / BUNDLE_ARCHIVE) as archive:
            archive.extractall(extracted)
            launchers = [
                info for info in archive.infolist() if info.filename.endswith(".sh")
            ]
        environment = os.environ.copy()
        environment["FLOWER_FIX_IN_TERMINAL"] = "1"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        for info in launchers:
            with self.subTest(launcher=info.filename):
                launcher = extracted / info.filename
                # zipfile.extractall does not restore Unix permission metadata.
                launcher.chmod(stat.S_IMODE(info.external_attr >> 16))
                result = subprocess.run(
                    [os.fspath(launcher), "--help"],
                    cwd=self.root,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIn("--game-dir", result.stdout)
                self.assertIn("Press Enter to close...", result.stdout)

    def test_bundle_version_matches_project_metadata(self) -> None:
        metadata = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(f'version = "{build_release.BUNDLE_VERSION}"', metadata)
        self.assertEqual(build_release.BUNDLE_RELEASE.archive_name, BUNDLE_ARCHIVE)

    def test_no_forbidden_proprietary_file_classes_are_packaged(self) -> None:
        allowed_dll = "gyro_bridge/dist/libScePad.dll"
        forbidden_basenames = {
            "flower.exe",
            "libscepad_original.dll",
            "steam_api.dll",
            "steam_api64.dll",
        }
        for member in expected_members(BUNDLE_ARCHIVE):
            with self.subTest(member=member):
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
            ref="release-candidate",
            project_root=self.repository,
        )
        assert_manifest(self, output, (BUNDLE_ARCHIVE,))


class ReleasePolicyTests(CommittedRepositoryTestCase):
    def test_staged_changes_are_refused(self) -> None:
        _ = (self.repository / "LICENSE").write_text("staged replacement\n")
        _ = run_git(self.repository, "add", "--", "LICENSE")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "staged changes"):
            _ = build_release.build_releases(
                self.output_path("staged"),
                project_root=self.repository,
            )

    def test_unstaged_changes_are_refused(self) -> None:
        _ = (self.repository / "LICENSE").write_text("unstaged replacement\n")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "unstaged changes"):
            _ = build_release.build_releases(
                self.output_path("unstaged"),
                project_root=self.repository,
            )

    def test_untracked_files_are_refused(self) -> None:
        _ = (self.repository / "untracked.txt").write_text("not committed\n")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "untracked files"):
            _ = build_release.build_releases(
                self.output_path("untracked"),
                project_root=self.repository,
            )

    def test_repository_without_commit_is_refused(self) -> None:
        repository = self.root / "no-commit"
        repository.mkdir()
        _ = run_git(repository, "init", "--quiet")
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "no HEAD commit"):
            _ = build_release.build_releases(
                self.output_path("no-commit-output"),
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
                project_root=self.repository,
            )
        self.assertEqual((output / "old.zip").read_bytes(), b"stale")

    def test_existing_empty_external_output_is_accepted(self) -> None:
        output = self.output_path("empty-output")
        output.mkdir()
        _ = build_release.build_releases(
            output,
            project_root=self.repository,
        )
        assert_manifest(self, output, (BUNDLE_ARCHIVE,))

    def test_output_inside_repository_is_refused(self) -> None:
        with self.assertRaisesRegex(build_release.ReleasePolicyError, "external"):
            _ = build_release.build_releases(
                self.repository / "release-output",
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

    def test_cli_requires_only_an_output_directory(self) -> None:
        no_arguments = self.run_cli()
        self.assertEqual(no_arguments.returncode, 2)
        self.assertIn("--output-dir", no_arguments.stderr)

        output = self.output_path("default-bundle")
        result = self.run_cli("--output-dir", os.fspath(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_manifest(self, output, (BUNDLE_ARCHIVE,))

    def test_cli_legacy_all_selector_still_builds_bundle(self) -> None:
        output = self.output_path("legacy-selector")
        result = self.run_cli(
            "--output-dir",
            os.fspath(output),
            "--component",
            "all",
            "--ref",
            "HEAD",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        assert_manifest(self, output, (BUNDLE_ARCHIVE,))

    def test_cli_refuses_component_only_selectors(self) -> None:
        for component in ("hay-bale", "bridge"):
            with self.subTest(component=component):
                output = self.output_path(f"unsupported-{component}")
                result = self.run_cli(
                    "--output-dir", os.fspath(output), "--component", component
                )
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())

    def test_cli_refuses_repository_internal_output(self) -> None:
        result = self.run_cli(
            "--output-dir",
            os.fspath(self.repository / "release-output"),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("external", result.stderr)


if __name__ == "__main__":
    _ = unittest.main()
