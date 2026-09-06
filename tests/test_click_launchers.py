from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LINUX_LAUNCHERS = (
    (
        "INSTALL_HAY_BALE_LINUX.sh",
        "flower_haybale_fix.py",
        "install",
    ),
    (
        "REVERT_HAY_BALE_LINUX.sh",
        "flower_haybale_fix.py",
        "restore",
    ),
    (
        "INSTALL_GYRO_BRIDGE_LINUX.sh",
        "gyro_bridge/install_gyro_bridge.py",
        "install",
    ),
    (
        "REVERT_GYRO_BRIDGE_LINUX.sh",
        "gyro_bridge/install_gyro_bridge.py",
        "restore",
    ),
)
WINDOWS_LAUNCHERS = (
    (
        "INSTALL_HAY_BALE_WINDOWS.cmd",
        r"flower_haybale_fix.py",
        "install",
    ),
    (
        "REVERT_HAY_BALE_WINDOWS.cmd",
        r"flower_haybale_fix.py",
        "restore",
    ),
    (
        "INSTALL_GYRO_BRIDGE_WINDOWS.cmd",
        r"gyro_bridge\install_gyro_bridge.py",
        "install",
    ),
    (
        "REVERT_GYRO_BRIDGE_WINDOWS.cmd",
        r"gyro_bridge\install_gyro_bridge.py",
        "restore",
    ),
)


@unittest.skipUnless(os.name == "posix", "Linux launchers require a POSIX shell")
class LinuxClickLauncherTests(unittest.TestCase):
    temporary_path: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    bundle_root: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    working_directory: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    bin_directory: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    capture: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    terminal_capture: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    arguments: list[str]  # pyright: ignore[reportUninitializedInstanceVariable]

    # `typing.override` is only available in Python 3.12 and newer.
    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.temporary_path = Path(temporary_directory.name).resolve()
        self.bundle_root = self.temporary_path / "unpacked files" / "Flower Fix bundle"
        self.working_directory = self.temporary_path / "unrelated working directory"
        self.bin_directory = self.temporary_path / "fake commands"
        self.capture = self.temporary_path / "invocation.bin"
        self.terminal_capture = self.temporary_path / "terminal invocation.bin"
        game_directory = self.temporary_path / "Steam Library" / "Flower game"
        self.arguments = ["--game-dir", os.fspath(game_directory), "--dry-run"]
        for directory in (
            self.bundle_root,
            self.working_directory,
            self.bin_directory,
            game_directory,
        ):
            directory.mkdir(parents=True)

        # An isolated PATH prevents both real Python and real terminals from running.
        for command in ("dirname", "basename"):
            executable = shutil.which(command)
            if executable is None:
                self.fail(f"The POSIX launcher tests require {command}")
            (self.bin_directory / command).symlink_to(executable)
        fake_python = self.bin_directory / "python3"
        _ = fake_python.write_text(
            """#!/bin/sh
printf '%s\\0' "$PWD" "$@" >> "$FLOWER_FIX_CAPTURE"
exit "$FLOWER_FIX_FAKE_EXIT"
""",
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        (self.bin_directory / "python").symlink_to(fake_python)
        for relative_path, installer, _operation in LINUX_LAUNCHERS:
            _ = shutil.copy2(PROJECT_ROOT / relative_path, self.bundle_root / relative_path)
            installer_path = self.bundle_root / installer
            installer_path.parent.mkdir(parents=True, exist_ok=True)
            _ = installer_path.write_text(
                "raise AssertionError('Only the fake Python should be invoked')\n",
                encoding="utf-8",
            )

    def launcher_environment(self, exit_code: int = 0) -> dict[str, str]:
        environment = os.environ.copy()
        environment["PATH"] = os.fspath(self.bin_directory)
        environment["FLOWER_FIX_CAPTURE"] = os.fspath(self.capture)
        environment["FLOWER_FIX_TERMINAL_CAPTURE"] = os.fspath(self.terminal_capture)
        environment["FLOWER_FIX_FAKE_EXIT"] = str(exit_code)
        environment["FLOWER_FIX_IN_TERMINAL"] = "1"
        return environment

    def run_launcher(
        self,
        relative_path: str,
        arguments: list[str],
        *,
        exit_code: int = 0,
        cwd: Path | None = None,
        in_terminal: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        self.capture.unlink(missing_ok=True)
        self.terminal_capture.unlink(missing_ok=True)
        environment = self.launcher_environment(exit_code)
        if not in_terminal:
            _ = environment.pop("FLOWER_FIX_IN_TERMINAL")
        return subprocess.run(
            [os.fspath(self.bundle_root / relative_path), *arguments],
            cwd=cwd if cwd is not None else self.working_directory,
            env=environment,
            check=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def read_capture(self, path: Path) -> list[str]:
        self.assertTrue(path.is_file(), f"Expected command invocation in {path}")
        fields = path.read_bytes().split(b"\0")
        self.assertEqual(fields[-1], b"", "Capture must end with a NUL delimiter")
        return [os.fsdecode(field) for field in fields[:-1]]

    def assert_delegation(
        self, installer: str, operation: str, arguments: list[str]
    ) -> None:
        invocation = self.read_capture(self.capture)
        self.assertEqual(invocation[0], os.fspath(self.bundle_root))
        self.assertEqual(invocation[1:], [installer, operation, *arguments])

    def test_linux_launchers_are_executable_and_valid_shell(self) -> None:
        for relative_path, _installer, _operation in LINUX_LAUNCHERS:
            with self.subTest(path=relative_path):
                launcher = self.bundle_root / relative_path
                self.assertTrue(launcher.stat().st_mode & stat.S_IXUSR)
                syntax = subprocess.run(
                    ["sh", "-n", os.fspath(launcher)],
                    check=False,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_linux_launchers_delegate_from_root_regardless_of_working_directory(
        self,
    ) -> None:
        for relative_path, installer, operation in LINUX_LAUNCHERS:
            for cwd in (self.bundle_root, self.working_directory):
                with self.subTest(path=relative_path, cwd=cwd):
                    result = self.run_launcher(relative_path, self.arguments, cwd=cwd)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assert_delegation(installer, operation, self.arguments)
                    self.assertIn("Press Enter to close", result.stdout)

    def test_linux_launchers_preserve_installer_failure_status(self) -> None:
        for relative_path, installer, operation in LINUX_LAUNCHERS:
            with self.subTest(path=relative_path):
                result = self.run_launcher(relative_path, self.arguments, exit_code=7)
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assert_delegation(installer, operation, self.arguments)
                self.assertIn("Press Enter to close", result.stdout)

    def test_linux_launchers_fail_closed_without_sibling_installer(self) -> None:
        for relative_path, installer, _operation in LINUX_LAUNCHERS:
            with self.subTest(path=relative_path):
                (self.bundle_root / installer).unlink(missing_ok=True)
                # Both ancestor levels and the caller's cwd contain tempting decoys.
                for directory in (
                    self.bundle_root.parent,
                    self.bundle_root.parent.parent,
                    self.working_directory,
                ):
                    decoy = directory / installer
                    decoy.parent.mkdir(parents=True, exist_ok=True)
                    _ = decoy.write_text(
                        "raise AssertionError('An out-of-bundle installer must not run')\n",
                        encoding="utf-8",
                    )
                result = self.run_launcher(relative_path, self.arguments)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("ERROR: Incomplete bundle.", result.stderr)
                self.assertIn("Extract the entire ZIP", result.stderr)
                self.assertIn("Press Enter to close", result.stdout)
                self.assertFalse(self.capture.exists(), "Python must not be invoked")
                self.assertFalse(self.terminal_capture.exists())

    def test_linux_terminal_relaunch_preserves_arguments_and_exit_status(self) -> None:
        for terminal, separator in (("konsole", "-e"), ("gnome-terminal", "--")):
            fake_terminal = self.bin_directory / terminal
            _ = fake_terminal.write_text(
                """#!/bin/sh
printf '%s\\0' "$@" >> "$FLOWER_FIX_TERMINAL_CAPTURE"
[ "${FLOWER_FIX_IN_TERMINAL:-0}" = "1" ] || exit 99
shift
exec "$@"
""",
                encoding="utf-8",
            )
            fake_terminal.chmod(0o755)
            try:
                for relative_path, installer, operation in LINUX_LAUNCHERS:
                    with self.subTest(terminal=terminal, path=relative_path):
                        result = self.run_launcher(
                            relative_path,
                            self.arguments,
                            exit_code=7,
                            in_terminal=False,
                        )
                        self.assertEqual(result.returncode, 7, result.stderr)
                        self.assertEqual(
                            self.read_capture(self.terminal_capture),
                            [
                                separator,
                                os.fspath(self.bundle_root / relative_path),
                                *self.arguments,
                            ],
                        )
                        self.assert_delegation(installer, operation, self.arguments)
                        self.assertIn("Press Enter to close", result.stdout)
            finally:
                fake_terminal.unlink()


class WindowsClickLauncherTests(unittest.TestCase):
    def test_windows_launchers_delegate_and_keep_the_window_open(self) -> None:
        for relative_path, installer, operation in WINDOWS_LAUNCHERS:
            with self.subTest(path=relative_path):
                text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                lines = text.splitlines()
                command = f"{installer} {operation} %*"
                for python_command in (f"py -3 {command}", f"python {command}"):
                    self.assertIn(python_command, lines)
                    self.assertEqual(
                        lines[lines.index(python_command) + 1],
                        'set "flower_fix_exit=%errorlevel%"',
                    )
                self.assertIn(":finish", lines)
                finish = lines[lines.index(":finish") + 1 :]
                self.assertIn("pause", finish)
                self.assertIn("exit /b %flower_fix_exit%", finish)
                self.assertLess(
                    finish.index("pause"), finish.index("exit /b %flower_fix_exit%")
                )

    def test_windows_launchers_fail_closed_without_parent_directory_fallback(
        self,
    ) -> None:
        for relative_path, installer, _operation in WINDOWS_LAUNCHERS:
            with self.subTest(path=relative_path):
                text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                self.assertIn(":run", lines)
                self.assertEqual(
                    lines[: lines.index(":run")],
                    [
                        "@echo off",
                        "setlocal",
                        'pushd "%~dp0" >nul 2>nul',
                        "if errorlevel 1 goto directory_error",
                        f'if exist "{installer}" goto run',
                        (
                            "echo ERROR: Incomplete bundle. Extract the entire ZIP "
                            "before running this launcher. 1>&2"
                        ),
                        'set "flower_fix_exit=2"',
                        "goto finish",
                    ],
                )
                self.assertNotIn("../", text.replace("\\", "/"))
                self.assertEqual(lines[lines.index(":finish") + 1], "popd")
                self.assertEqual(
                    lines[lines.index(":directory_error") + 1 :],
                    [
                        "echo ERROR: Could not open the bundle folder. "
                        + "Extract the ZIP to a local folder and try again. 1>&2",
                        "echo.",
                        "pause",
                        "exit /b 2",
                    ],
                )


if __name__ == "__main__":
    _ = unittest.main()
