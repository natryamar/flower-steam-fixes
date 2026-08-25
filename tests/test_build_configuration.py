from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import cast

from gyro_bridge import build


class BuildConfigurationTests(unittest.TestCase):
    def test_compile_commands_use_the_cross_target_and_pinned_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            compiler = root / "toolchain" / "bin" / "x86_64-w64-mingw32-clang++"
            destination = root / "compile_commands.json"
            with redirect_stdout(io.StringIO()):
                build.write_compile_commands(compiler, destination)

            database = cast(
                list[dict[str, object]],
                json.loads(destination.read_text(encoding="utf-8")),
            )
            self.assertEqual(len(database), 1)
            entry = database[0]
            self.assertEqual(entry["directory"], str(build.PROJECT_ROOT))
            self.assertEqual(entry["file"], str(build.SOURCE))

            arguments = cast(list[str], entry["arguments"])
            self.assertEqual(arguments[0], str(compiler))
            self.assertIn("--target=x86_64-w64-windows-gnu", arguments)
            self.assertIn("-std=c++20", arguments)
            self.assertIn("-fsyntax-only", arguments)
            self.assertIn(
                str(
                    root
                    / "toolchain"
                    / "x86_64-w64-mingw32"
                    / "include"
                    / "c++"
                    / "v1"
                ),
                arguments,
            )
            self.assertIn(
                str(root / "toolchain" / "x86_64-w64-mingw32" / "include"),
                arguments,
            )
            self.assertIn(
                str(root / "toolchain" / "lib" / "clang" / "22" / "include"),
                arguments,
            )

    def test_compile_database_and_release_modes_are_mutually_exclusive(self) -> None:
        with (
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            _ = build.build_parser().parse_args(
                ["--verify-release", "--write-compile-commands"]
            )
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    _ = unittest.main()
