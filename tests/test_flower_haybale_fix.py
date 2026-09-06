from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import flower_haybale_fix as installer
from flower_haybale_fix import (
    BACKUP_SUFFIX,
    PatchError,
    PatchSpec,
    backup_path_for,
    inspect_file,
    install_patch,
    resolve_target,
    restore_patch,
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FlowerHayBaleFixTests(unittest.TestCase):
    temporary_directory: tempfile.TemporaryDirectory[str]  # pyright: ignore[reportUninitializedInstanceVariable]
    game: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    target: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    original: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    patched: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    spec: PatchSpec  # pyright: ignore[reportUninitializedInstanceVariable]

    # `typing.override` is only available in Python 3.12 and newer.
    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.game = Path(self.temporary_directory.name) / "Flower"
        self.target = self.game / "Data" / "Sounds" / "Level4_A.bnk"
        self.target.parent.mkdir(parents=True)

        self.original = b"SBlk-test-before-OLD!-after"
        self.patched = b"SBlk-test-before-NEW!-after"
        self.spec = PatchSpec(
            file_size=len(self.original),
            offset=self.original.index(b"OLD!"),
            original_bytes=b"OLD!",
            patched_bytes=b"NEW!",
            original_sha256=digest(self.original),
            patched_sha256=digest(self.patched),
        )
        _ = self.target.write_bytes(self.original)

    def test_install_is_verified_backed_up_and_idempotent(self) -> None:
        result = install_patch(self.target, self.spec)
        self.assertTrue(result.changed)
        self.assertEqual(result.state, "patched")
        self.assertEqual(self.target.read_bytes(), self.patched)

        backup = backup_path_for(self.target)
        self.assertEqual(backup.name, self.target.name + BACKUP_SUFFIX)
        self.assertEqual(backup.read_bytes(), self.original)

        repeated = install_patch(self.target, self.spec)
        self.assertFalse(repeated.changed)
        self.assertEqual(repeated.state, "already-patched")
        self.assertEqual(backup.read_bytes(), self.original)

    def test_already_patched_requires_verified_backup(self) -> None:
        _ = self.target.write_bytes(self.patched)
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), self.patched)

    def test_already_patched_rejects_corrupt_backup(self) -> None:
        _ = self.target.write_bytes(self.patched)
        _ = backup_path_for(self.target).write_bytes(b"corrupt")
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), self.patched)

    def test_restore_requires_and_uses_verified_backup(self) -> None:
        _ = install_patch(self.target, self.spec)
        result = restore_patch(self.target, self.spec)
        self.assertTrue(result.changed)
        self.assertEqual(result.state, "restored")
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertEqual(inspect_file(self.target, self.spec).state, "original")

        repeated = restore_patch(self.target, self.spec)
        self.assertFalse(repeated.changed)
        self.assertEqual(repeated.state, "already-original")

    def test_dry_run_does_not_write_target_or_backup(self) -> None:
        result = install_patch(self.target, self.spec, dry_run=True)
        self.assertFalse(result.changed)
        self.assertEqual(result.state, "dry-run-installable")
        self.assertEqual(self.target.read_bytes(), self.original)
        self.assertFalse(backup_path_for(self.target).exists())

    def test_unknown_target_is_refused(self) -> None:
        _ = self.target.write_bytes(b"independently modified")
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)

    def test_same_sized_unknown_with_original_patch_site_is_refused(self) -> None:
        unknown = bytearray(self.original)
        unknown[-1] ^= 1
        self.assertEqual(
            unknown[self.spec.offset:self.spec.offset + len(self.spec.original_bytes)],
            self.spec.original_bytes,
        )
        _ = self.target.write_bytes(unknown)
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), unknown)

    def test_corrupt_existing_backup_is_refused(self) -> None:
        _ = backup_path_for(self.target).write_bytes(b"not the original")
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_existing_valid_backup_is_preserved(self) -> None:
        backup = backup_path_for(self.target)
        _ = backup.write_bytes(self.original)
        original_stat = backup.stat()
        _ = install_patch(self.target, self.spec)
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertEqual(backup.stat().st_ino, original_stat.st_ino)

    def test_backup_symlink_is_refused(self) -> None:
        backup = backup_path_for(self.target)
        try:
            backup.symlink_to(self.target)
        except (NotImplementedError, OSError):
            self.skipTest("symlinks are not available")
        self.assertEqual(inspect_file(backup, self.spec).state, "unsafe")
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_target_symlink_is_refused(self) -> None:
        real_target = Path(self.temporary_directory.name) / "real-Level4_A.bnk"
        _ = real_target.write_bytes(self.original)
        self.target.unlink()
        try:
            self.target.symlink_to(real_target)
        except (NotImplementedError, OSError):
            self.skipTest("symlinks are not available")
        self.assertEqual(inspect_file(self.target, self.spec).state, "unsafe")
        with self.assertRaises(PatchError):
            _ = install_patch(self.target, self.spec)
        self.assertEqual(real_target.read_bytes(), self.original)

    def test_restore_refuses_unknown_target(self) -> None:
        _ = backup_path_for(self.target).write_bytes(self.original)
        _ = self.target.write_bytes(b"different modification")
        with self.assertRaises(PatchError):
            _ = restore_patch(self.target, self.spec)

    def test_restore_without_backup_leaves_patched_target_untouched(self) -> None:
        _ = self.target.write_bytes(self.patched)
        with self.assertRaises(PatchError):
            _ = restore_patch(self.target, self.spec)
        self.assertEqual(self.target.read_bytes(), self.patched)

    def test_explicit_game_directory_resolution(self) -> None:
        self.assertEqual(resolve_target(self.game), self.target)
        self.assertEqual(resolve_target(self.target), self.target)

    def test_main_prints_concise_operation_results(self) -> None:
        cases = (
            (["install"], "install_patch", "Success.\n", False),
            (["restore"], "restore_patch", "Fix reverted.\n", False),
            (
                ["install", "--dry-run"],
                "install_patch",
                "Dry run successful; no changes made.\n",
                True,
            ),
            (
                ["restore", "--dry-run"],
                "restore_patch",
                "Dry run successful; no changes made.\n",
                True,
            ),
        )

        for argv, operation_name, expected_output, dry_run in cases:
            with self.subTest(argv=argv):
                output = io.StringIO()
                with (
                    mock.patch.object(
                        installer,
                        "resolve_target",
                        return_value=self.target,
                    ),
                    mock.patch.object(installer, operation_name) as operation,
                    redirect_stdout(output),
                ):
                    exit_code = installer.main(argv)

                self.assertEqual(exit_code, 0)
                self.assertEqual(output.getvalue(), expected_output)
                operation.assert_called_once_with(self.target, dry_run=dry_run)


if __name__ == "__main__":
    _ = unittest.main()
