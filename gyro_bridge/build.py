#!/usr/bin/env python3
"""Build the Flower native ScePad Steam Input bridge with llvm-mingw."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
OUTPUT = ROOT / "dist" / "libScePad.dll"
SOURCE = ROOT / "src" / "flower_scepad_bridge.cpp"
DEFINITION = ROOT / "src" / "libScePad.def"
COMPILE_COMMANDS = PROJECT_ROOT / "compile_commands.json"

TOOLCHAIN_RELEASE = "20260616"
TOOLCHAIN_NAME = f"llvm-mingw-{TOOLCHAIN_RELEASE}-ucrt-ubuntu-22.04-x86_64"
TOOLCHAIN_ARCHIVE = f"{TOOLCHAIN_NAME}.tar.xz"
TOOLCHAIN_URL = (
    "https://github.com/mstorsjo/llvm-mingw/releases/download/20260616/"
    "llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz"
)
TOOLCHAIN_SHA256 = (
    "534b92e067b22a6b4441f48ae9240a3341b17825d04d577eab0cf85c44b4deda"
)
CLANG_VERSION = "22.1.8"
LLVM_REVISION = "ca7933e47d3a3451d81e72ac174dcb5aa28b59d1"
LLVM_REPOSITORY = "https://github.com/llvm/llvm-project.git"
EXPECTED_CLANG_IDENTITY = (
    f"clang version {CLANG_VERSION} ({LLVM_REPOSITORY} {LLVM_REVISION})"
)
EXPECTED_TARGET = "x86_64-w64-windows-gnu"
EXPECTED_TARGET_LINE = f"Target: {EXPECTED_TARGET}"
PRODUCTION_DLL_SHA256 = (
    "adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_compiler() -> Path:
    environment = os.environ.get("FLOWER_LLVM_MINGW")
    candidates: list[Path] = []
    if environment:
        candidates.append(Path(environment).expanduser())
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
            # The shared wrapper infers its target from argv[0], so preserve the
            # target-prefixed symlink instead of resolving it to clang itself.
            return Path(os.path.abspath(candidate))
    raise SystemExit(
        "x86_64-w64-mingw32-clang++ was not found. Set FLOWER_LLVM_MINGW "
        + f"or extract {TOOLCHAIN_ARCHIVE} under re-temp/toolchain.\n"
        + f"Pinned archive: {TOOLCHAIN_URL}\n"
        + f"Archive SHA-256: {TOOLCHAIN_SHA256}"
    )


def verify_compiler_identity(compiler: Path) -> None:
    try:
        completed = subprocess.run(
            [os.fspath(compiler), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SystemExit(f"Could not query compiler identity: {error}") from error

    version_output = "\n".join(
        output for output in (completed.stdout, completed.stderr) if output
    ).strip()
    if completed.returncode != 0:
        raise SystemExit(
            "Compiler identity query failed with exit code "
            + f"{completed.returncode}:\n{version_output or '<no output>'}"
        )

    lines = {line.strip() for line in version_output.splitlines() if line.strip()}
    identity_lines = {line for line in lines if line.startswith("clang version ")}
    target_lines = {line for line in lines if line.startswith("Target: ")}
    if identity_lines != {EXPECTED_CLANG_IDENTITY} or target_lines != {
        EXPECTED_TARGET_LINE
    }:
        raise SystemExit(
            "Compiler identity verification failed.\n"
            + f"Expected: {EXPECTED_CLANG_IDENTITY}\n"
            + f"Expected: {EXPECTED_TARGET_LINE}\n"
            + "Reported:\n"
            + f"{version_output or '<no output>'}"
        )

    print(f"Verified compiler identity: {EXPECTED_CLANG_IDENTITY}")
    print(f"Verified compiler target: {EXPECTED_TARGET}")


def bridge_build_command(compiler: Path) -> list[str]:
    return [
        os.fspath(compiler),
        "-std=c++20",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-Werror",
        "-fno-exceptions",
        "-fno-rtti",
        "-shared",
        "-Wl,--no-insert-timestamp",
        os.fspath(SOURCE),
        os.fspath(DEFINITION),
        "-o",
        os.fspath(OUTPUT),
    ]


def build_bridge(compiler: Path) -> str:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    command = bridge_build_command(compiler)
    print("Building:", " ".join(command))
    _ = subprocess.run(command, check=True)
    output_sha256 = sha256_file(OUTPUT)
    print(f"Built {OUTPUT}")
    print(f"SHA-256: {output_sha256}")
    return output_sha256


def clangd_compile_command(compiler: Path) -> list[str]:
    toolchain_root = compiler.parent.parent
    target_root = toolchain_root / "x86_64-w64-mingw32"
    return [
        os.fspath(compiler),
        "--target=x86_64-w64-windows-gnu",
        "-std=c++20",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-Werror",
        "-fno-exceptions",
        "-fno-rtti",
        "-resource-dir",
        os.fspath(toolchain_root / "lib" / "clang" / "22"),
        "-isystem",
        os.fspath(target_root / "include" / "c++" / "v1"),
        "-isystem",
        os.fspath(toolchain_root / "lib" / "clang" / "22" / "include"),
        "-isystem",
        os.fspath(target_root / "include"),
        "-fsyntax-only",
        os.fspath(SOURCE),
    ]


def write_compile_commands(compiler: Path, destination: Path = COMPILE_COMMANDS) -> None:
    database = [
        {
            "directory": os.fspath(PROJECT_ROOT),
            "file": os.fspath(SOURCE),
            "arguments": clangd_compile_command(compiler),
        }
    ]
    _ = destination.write_text(
        json.dumps(database, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {destination}")
    print("This local file contains absolute paths and must remain untracked.")


def verify_release_hash(output_sha256: str) -> None:
    if output_sha256 != PRODUCTION_DLL_SHA256:
        raise SystemExit(
            "Release DLL SHA-256 verification failed.\n"
            + f"Expected: {PRODUCTION_DLL_SHA256}\n"
            + f"Actual:   {output_sha256}\n"
            + f"Artifact: {OUTPUT}"
        )
    print(f"Verified production DLL SHA-256: {PRODUCTION_DLL_SHA256}")


class BuildArguments(argparse.Namespace):
    verify_release: bool = False
    write_compile_commands: bool = False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    _ = mode.add_argument(
        "--verify-release",
        action="store_true",
        help=(
            "require the pinned clang identity and reproduce the current "
            "production DLL SHA-256"
        ),
    )
    _ = mode.add_argument(
        "--write-compile-commands",
        action="store_true",
        help=(
            "write an ignored local compile_commands.json for clangd/Zed "
            "using the discovered cross-compiler"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = BuildArguments()
    _ = build_parser().parse_args(argv, namespace=args)
    compiler = find_compiler()
    if args.write_compile_commands:
        write_compile_commands(compiler)
        return 0
    if args.verify_release:
        verify_compiler_identity(compiler)

    output_sha256 = build_bridge(compiler)
    if args.verify_release:
        verify_release_hash(output_sha256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
