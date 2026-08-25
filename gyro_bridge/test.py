#!/usr/bin/env python3
"""Build and run the isolated native-ScePad bridge smoke test under Proton."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
TEST_ROOT = ROOT / "tests"
STAGE = PROJECT_ROOT / "re-temp" / "native-scepad-smoke"
PREFIX = PROJECT_ROOT / "re-temp" / "prefixes" / "native-scepad-smoke"
BRIDGE = ROOT / "dist" / "libScePad.dll"
EXPECTED_STEAM_API_SIZE = 242_976
TOOLCHAIN_NAME = "llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64"


def find_compiler() -> Path:
    override = os.environ.get("FLOWER_LLVM_MINGW")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates.append(
        PROJECT_ROOT
        / "re-temp"
        / "toolchain"
        / TOOLCHAIN_NAME
        / "bin"
        / "x86_64-w64-mingw32-clang++"
    )
    discovered = shutil.which("x86_64-w64-mingw32-clang++")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        if candidate.is_file():
            # LLVM-MinGW's shared wrapper infers the target from argv[0], so do
            # not resolve the target-prefixed compiler symlink.
            return Path(os.path.abspath(candidate))
    raise SystemExit(
        "x86_64-w64-mingw32-clang++ was not found. Set FLOWER_LLVM_MINGW or "
        + "extract the documented toolchain under re-temp/toolchain."
    )


def find_proton() -> Path:
    override = os.environ.get("FLOWER_PROTON")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    steam = Path.home() / ".local" / "share" / "Steam"
    candidates.extend(
        (
            steam / "steamapps" / "common" / "Proton - Experimental" / "proton",
            steam / "steamapps" / "common" / "Proton 10.0" / "proton",
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit("Proton was not found. Set FLOWER_PROTON to its launcher path.")


def compile_windows(
    compiler: Path,
    source: Path,
    output: Path,
    *,
    definition: Path | None = None,
    shared: bool = False,
) -> None:
    command = [
        os.fspath(compiler),
        "-std=c++20",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-Werror",
        "-fno-exceptions",
        "-fno-rtti",
    ]
    if shared:
        command.append("-shared")
    command.extend(("-Wl,--no-insert-timestamp", os.fspath(source)))
    if definition is not None:
        command.append(os.fspath(definition))
    command.extend(("-o", os.fspath(output)))
    print("Building:", " ".join(command))
    _ = subprocess.run(command, check=True)


def pad_fake_steam_api(path: Path) -> None:
    size = path.stat().st_size
    if size > EXPECTED_STEAM_API_SIZE:
        raise SystemExit(
            f"Fake steam_api64.dll is unexpectedly large: {size} bytes"
        )
    with path.open("ab") as handle:
        _ = handle.write(b"\0" * (EXPECTED_STEAM_API_SIZE - size))


def verify_bridge_surface() -> None:
    objdump = shutil.which("objdump")
    if objdump is None:
        raise SystemExit("objdump is required to verify bridge exports")
    result = subprocess.run(
        [objdump, "-p", os.fspath(BRIDGE)],
        check=True,
        capture_output=True,
        text=True,
    )
    expected = {
        "scePadClose": 1,
        "scePadGetControllerInformation": 2,
        "scePadGetHandle": 3,
        "scePadGetJackState": 4,
        "scePadGetParticularMode": 5,
        "scePadInit": 6,
        "scePadIsSupportedAudioFunction": 7,
        "scePadOpen": 8,
        "scePadRead": 9,
        "scePadReadState": 10,
        "scePadResetLightBar": 11,
        "scePadResetOrientation": 12,
        "scePadSetAngularVelocityDeadbandState": 13,
        "scePadSetAudioOutPath": 14,
        "scePadSetLightBar": 15,
        "scePadSetMotionSensorState": 16,
        "scePadSetParticularMode": 17,
        "scePadSetTiltCorrectionState": 18,
        "scePadSetVibration": 19,
        "scePadSetVolumeGain": 20,
    }
    marker = "[Ordinal/Name Pointer] Table"
    if marker not in result.stdout:
        raise SystemExit("Bridge export verification found no name table")
    name_table = result.stdout.split(marker, 1)[1]
    actual: dict[str, int] = {}
    for line in name_table.splitlines():
        match = re.search(r"\+base\[\s*(\d+)\].*\s(scePad\w+)$", line)
        if match:
            actual[match.group(2)] = int(match.group(1))
    if actual != expected:
        raise SystemExit(
            f"Bridge name/ordinal verification failed: expected {expected}, got {actual}"
        )

    binary = BRIDGE.read_bytes()
    if b"XInputGetState" in binary or b"XInputSetState" in binary:
        raise SystemExit("Bridge unexpectedly contains an XInput hook dependency")
    if b"GetMotionData" in binary:
        raise SystemExit("Bridge unexpectedly contains a raw-motion dependency")


def main() -> int:
    compiler = find_compiler()
    proton = find_proton()

    _ = subprocess.run(
        [sys.executable, os.fspath(ROOT / "build.py")],
        check=True,
    )
    verify_bridge_surface()

    shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True)
    fake_steam = STAGE / "steam_api64.dll"
    fake_original = STAGE / "libScePad_original.dll"
    smoke = STAGE / "native_scepad_smoke.exe"

    compile_windows(
        compiler,
        TEST_ROOT / "fake_steam_api.cpp",
        fake_steam,
        shared=True,
    )
    pad_fake_steam_api(fake_steam)
    compile_windows(
        compiler,
        TEST_ROOT / "fake_scepad.cpp",
        fake_original,
        definition=TEST_ROOT / "fake_scepad.def",
        shared=True,
    )
    compile_windows(
        compiler,
        TEST_ROOT / "native_scepad_smoke.cpp",
        smoke,
    )
    _ = shutil.copy2(BRIDGE, STAGE / BRIDGE.name)

    if not PREFIX.resolve().is_relative_to((PROJECT_ROOT / "re-temp").resolve()):
        raise SystemExit("Refusing to use a Proton prefix outside project re-temp")
    shutil.rmtree(PREFIX, ignore_errors=True)
    PREFIX.mkdir(parents=True)

    steam_root = Path.home() / ".local" / "share" / "Steam"
    environment = os.environ.copy()
    environment.update(
        {
            "STEAM_COMPAT_DATA_PATH": os.fspath(PREFIX),
            "STEAM_COMPAT_CLIENT_INSTALL_PATH": os.fspath(steam_root),
            "WINEDEBUG": "-all",
        }
    )
    command = [os.fspath(proton), "run", os.fspath(smoke)]
    print("Running:", " ".join(command))
    completed = subprocess.run(
        command,
        cwd=STAGE,
        env=environment,
        text=True,
        timeout=60,
        check=False,
    )

    result_path = STAGE / "native_scepad_smoke_result.txt"
    if result_path.is_file():
        print(result_path.read_text(encoding="utf-8", errors="replace"))
    if completed.returncode != 0:
        raise SystemExit(
            f"Native ScePad smoke failed with exit code {completed.returncode}"
        )
    print("Native ScePad smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
