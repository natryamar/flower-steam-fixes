from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import gyro_bridge.install_gyro_bridge as installer
from gyro_bridge.install_gyro_bridge import (
    ACTION_MANIFEST_NAME,
    BACKUP_NAME,
    FLOWER_EXE_NAME,
    STEAM_API_NAME,
    SUPPORTED_MANIFEST_SPEC,
    SUPPORTED_SPEC,
    TARGET_NAME,
    ActionManifestSpec,
    BridgeError,
    BridgeSpec,
    FileSignature,
    OperationResult,
    inspect_action_manifest,
    inspect_target,
    install_action_manifest,
    install_bridge,
    install_bridge_and_manifest,
    resolve_game_directory,
    resolve_steam_directory,
    restore_action_manifest,
    restore_bridge,
    restore_bridge_and_manifest,
)


def signature(data: bytes) -> FileSignature:
    return FileSignature(len(data), hashlib.sha256(data).hexdigest())


class GyroBridgeInstallerTests(unittest.TestCase):
    temporary_directory: tempfile.TemporaryDirectory[str]  # pyright: ignore[reportUninitializedInstanceVariable]
    root: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    game: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    target: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    backup: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    artifact: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    executable: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    steam_api: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    steam_root: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    manifest: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    manifest_artifact: Path  # pyright: ignore[reportUninitializedInstanceVariable]
    original_data: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    bridge_data: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    executable_data: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    steam_api_data: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    manifest_data: bytes  # pyright: ignore[reportUninitializedInstanceVariable]
    spec: BridgeSpec  # pyright: ignore[reportUninitializedInstanceVariable]
    manifest_spec: ActionManifestSpec  # pyright: ignore[reportUninitializedInstanceVariable]

    # `typing.override` is only available in Python 3.12 and newer.
    def setUp(self) -> None:  # pyright: ignore[reportImplicitOverride]
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.game = self.root / "Flower"
        self.game.mkdir()
        bundle = self.root / "bundle"
        bundle.mkdir()
        self.steam_root = self.root / "Steam"
        (self.steam_root / "steamapps").mkdir(parents=True)

        self.target = self.game / TARGET_NAME
        self.backup = self.game / BACKUP_NAME
        self.artifact = bundle / TARGET_NAME
        self.executable = self.game / FLOWER_EXE_NAME
        self.steam_api = self.game / STEAM_API_NAME
        self.manifest = (
            self.steam_root / "controller_config" / ACTION_MANIFEST_NAME
        )
        self.manifest_artifact = bundle / ACTION_MANIFEST_NAME

        self.original_data = b"verified-original-scepad"
        self.bridge_data = b"independently-built-motion-bridge"
        self.executable_data = b"supported-flower-executable"
        self.steam_api_data = b"supported-steam-api"
        self.manifest_data = b'"In Game Actions" { "actions" { } }'
        self.spec = BridgeSpec(
            original=signature(self.original_data),
            bridge=signature(self.bridge_data),
            flower_exe=signature(self.executable_data),
            steam_api=signature(self.steam_api_data),
        )
        self.manifest_spec = ActionManifestSpec(
            manifest=signature(self.manifest_data)
        )

        _ = self.target.write_bytes(self.original_data)
        _ = self.artifact.write_bytes(self.bridge_data)
        _ = self.executable.write_bytes(self.executable_data)
        _ = self.steam_api.write_bytes(self.steam_api_data)
        _ = self.manifest_artifact.write_bytes(self.manifest_data)

    def test_install_is_backed_up_verified_and_idempotent(self) -> None:
        result = install_bridge(self.game, self.artifact, self.spec)
        self.assertTrue(result.changed)
        self.assertEqual(result.state, "installed")
        self.assertEqual(self.target.read_bytes(), self.bridge_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertEqual(inspect_target(self.target, self.spec).state, "bridge")

        repeated = install_bridge(self.game, self.artifact, self.spec)
        self.assertFalse(repeated.changed)
        self.assertEqual(repeated.state, "already-installed")
        self.assertEqual(self.backup.read_bytes(), self.original_data)

    def test_restore_uses_verified_backup_and_is_idempotent(self) -> None:
        _ = install_bridge(self.game, self.artifact, self.spec)
        result = restore_bridge(self.game, self.spec)
        self.assertTrue(result.changed)
        self.assertEqual(result.state, "restored")
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)

        repeated = restore_bridge(self.game, self.spec)
        self.assertFalse(repeated.changed)
        self.assertEqual(repeated.state, "already-original")

    def test_install_dry_run_writes_nothing(self) -> None:
        result = install_bridge(
            self.game,
            self.artifact,
            self.spec,
            dry_run=True,
        )
        self.assertFalse(result.changed)
        self.assertEqual(result.state, "dry-run-installable")
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertFalse(self.backup.exists())

    def test_restore_dry_run_writes_nothing(self) -> None:
        _ = install_bridge(self.game, self.artifact, self.spec)
        result = restore_bridge(self.game, self.spec, dry_run=True)
        self.assertFalse(result.changed)
        self.assertEqual(result.state, "dry-run-restorable")
        self.assertEqual(self.target.read_bytes(), self.bridge_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)

    def test_install_rejects_unsupported_executable(self) -> None:
        _ = self.executable.write_bytes(b"updated executable")
        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertFalse(self.backup.exists())

    def test_install_rejects_unsupported_steam_api(self) -> None:
        _ = self.steam_api.write_bytes(b"new wrapper generation")
        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertFalse(self.backup.exists())

    def test_install_rejects_unknown_target(self) -> None:
        _ = self.target.write_bytes(b"third-party proxy")
        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), b"third-party proxy")

    def test_install_rejects_wrong_bridge_artifact(self) -> None:
        _ = self.artifact.write_bytes(b"different build")
        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertFalse(self.backup.exists())

    def test_active_bridge_requires_verified_backup(self) -> None:
        _ = self.target.write_bytes(self.bridge_data)
        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.bridge_data)

    def test_corrupt_existing_backup_is_never_replaced(self) -> None:
        _ = self.backup.write_bytes(b"keep-this-unknown-file")
        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), b"keep-this-unknown-file")

    def test_restore_requires_verified_backup(self) -> None:
        _ = self.target.write_bytes(self.bridge_data)
        with self.assertRaises(BridgeError):
            _ = restore_bridge(self.game, self.spec)
        self.assertEqual(self.target.read_bytes(), self.bridge_data)

    def test_restore_remains_available_after_compatibility_files_change(self) -> None:
        _ = install_bridge(self.game, self.artifact, self.spec)
        _ = self.executable.write_bytes(b"updated executable")
        self.steam_api.unlink()

        result = restore_bridge(self.game, self.spec)
        self.assertTrue(result.changed)
        self.assertEqual(self.target.read_bytes(), self.original_data)

    def test_target_symlink_is_refused(self) -> None:
        real_target = self.root / "real-libScePad.dll"
        _ = real_target.write_bytes(self.original_data)
        self.target.unlink()
        try:
            self.target.symlink_to(real_target)
        except (NotImplementedError, OSError):
            self.skipTest("symlinks are not available")

        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(real_target.read_bytes(), self.original_data)

    def test_backup_symlink_is_refused(self) -> None:
        try:
            self.backup.symlink_to(self.target)
        except (NotImplementedError, OSError):
            self.skipTest("symlinks are not available")

        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original_data)

    def test_hardlinked_artifact_is_refused(self) -> None:
        second_name = self.artifact.with_name("bridge-copy.dll")
        try:
            os.link(self.artifact, second_name)
        except (NotImplementedError, OSError):
            self.skipTest("hardlinks are not available")

        with self.assertRaises(BridgeError):
            _ = install_bridge(self.game, self.artifact, self.spec)
        self.assertEqual(self.target.read_bytes(), self.original_data)

    def test_verified_historical_bridge_is_upgraded(self) -> None:
        historical_data = b"published-version-zero-one-bridge"
        upgrade_spec = BridgeSpec(
            original=self.spec.original,
            bridge=self.spec.bridge,
            flower_exe=self.spec.flower_exe,
            steam_api=self.spec.steam_api,
            historical_bridges=(signature(historical_data),),
        )
        _ = self.target.write_bytes(historical_data)
        _ = self.backup.write_bytes(self.original_data)

        dry_run = install_bridge(
            self.game,
            self.artifact,
            upgrade_spec,
            dry_run=True,
        )
        self.assertEqual(dry_run.state, "dry-run-upgradable")
        self.assertEqual(self.target.read_bytes(), historical_data)

        result = install_bridge(self.game, self.artifact, upgrade_spec)
        self.assertTrue(result.changed)
        self.assertEqual(result.state, "upgraded")
        self.assertEqual(self.target.read_bytes(), self.bridge_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)

    def test_historical_bridge_can_be_restored(self) -> None:
        historical_data = b"published-version-zero-one-bridge"
        upgrade_spec = BridgeSpec(
            original=self.spec.original,
            bridge=self.spec.bridge,
            flower_exe=self.spec.flower_exe,
            steam_api=self.spec.steam_api,
            historical_bridges=(signature(historical_data),),
        )
        _ = self.target.write_bytes(historical_data)
        _ = self.backup.write_bytes(self.original_data)

        result = restore_bridge(self.game, upgrade_spec)
        self.assertTrue(result.changed)
        self.assertEqual(self.target.read_bytes(), self.original_data)

    def test_action_manifest_install_restore_and_idempotency(self) -> None:
        result = install_action_manifest(
            self.steam_root,
            self.manifest_artifact,
            self.manifest_spec,
        )
        self.assertTrue(result.changed)
        self.assertEqual(result.state, "manifest-installed")
        self.assertEqual(self.manifest.read_bytes(), self.manifest_data)
        self.assertEqual(
            inspect_action_manifest(self.manifest, self.manifest_spec).state,
            "manifest",
        )

        repeated = install_action_manifest(
            self.steam_root,
            self.manifest_artifact,
            self.manifest_spec,
        )
        self.assertFalse(repeated.changed)
        self.assertEqual(repeated.state, "manifest-already-installed")

        restored = restore_action_manifest(self.steam_root, self.manifest_spec)
        self.assertTrue(restored.changed)
        self.assertEqual(restored.state, "manifest-removed")
        self.assertFalse(self.manifest.exists())

        repeated_restore = restore_action_manifest(
            self.steam_root,
            self.manifest_spec,
        )
        self.assertEqual(repeated_restore.state, "manifest-already-absent")

    def test_action_manifest_dry_run_creates_nothing(self) -> None:
        result = install_action_manifest(
            self.steam_root,
            self.manifest_artifact,
            self.manifest_spec,
            dry_run=True,
        )
        self.assertEqual(result.state, "dry-run-manifest-installable")
        self.assertFalse((self.steam_root / "controller_config").exists())

    def test_unknown_action_manifest_is_preserved(self) -> None:
        self.manifest.parent.mkdir()
        unknown = b"publisher-or-user-owned-manifest"
        _ = self.manifest.write_bytes(unknown)

        with self.assertRaises(BridgeError):
            _ = install_action_manifest(
                self.steam_root,
                self.manifest_artifact,
                self.manifest_spec,
            )
        restore_result = restore_action_manifest(
            self.steam_root,
            self.manifest_spec,
        )
        self.assertEqual(restore_result.state, "manifest-unmanaged")
        self.assertEqual(self.manifest.read_bytes(), unknown)

    def test_historical_action_manifest_is_upgraded(self) -> None:
        historical_data = b"older-managed-action-manifest"
        manifest_spec = ActionManifestSpec(
            manifest=self.manifest_spec.manifest,
            historical_manifests=(signature(historical_data),),
        )
        self.manifest.parent.mkdir()
        _ = self.manifest.write_bytes(historical_data)

        result = install_action_manifest(
            self.steam_root,
            self.manifest_artifact,
            manifest_spec,
        )
        self.assertEqual(result.state, "manifest-upgraded")
        self.assertEqual(self.manifest.read_bytes(), self.manifest_data)

    def test_coordinated_install_rolls_back_post_commit_bridge_failure(
        self,
    ) -> None:
        def install_bridge_then_fail(
            game_dir: Path,
            artifact: Path,
            spec: BridgeSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            result = install_bridge(
                game_dir,
                artifact,
                spec,
                dry_run=dry_run,
            )
            if dry_run:
                return result
            raise OSError("injected post-commit bridge failure")

        with (
            mock.patch.object(
                installer,
                "install_bridge",
                side_effect=install_bridge_then_fail,
            ),
            self.assertRaises(BridgeError) as raised,
        ):
            _ = install_bridge_and_manifest(
                self.game,
                self.artifact,
                self.steam_root,
                self.manifest_artifact,
                self.spec,
                self.manifest_spec,
            )

        message = str(raised.exception)
        self.assertIn(
            "Bridge installation failed after activating the bridge",
            message,
        )
        self.assertIn(
            "Primary error: OSError: injected post-commit bridge failure",
            message,
        )
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertFalse(self.manifest.exists())

    def test_coordinated_install_rolls_back_post_commit_manifest_interrupt(
        self,
    ) -> None:
        def install_manifest_then_interrupt(
            steam_dir: Path,
            artifact: Path,
            spec: ActionManifestSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            result = install_action_manifest(
                steam_dir,
                artifact,
                spec,
                dry_run=dry_run,
            )
            if dry_run:
                return result
            raise KeyboardInterrupt("injected post-commit manifest interrupt")

        with (
            mock.patch.object(
                installer,
                "install_action_manifest",
                side_effect=install_manifest_then_interrupt,
            ),
            self.assertRaises(KeyboardInterrupt) as raised,
        ):
            _ = install_bridge_and_manifest(
                self.game,
                self.artifact,
                self.steam_root,
                self.manifest_artifact,
                self.spec,
                self.manifest_spec,
            )

        self.assertEqual(
            str(raised.exception),
            "injected post-commit manifest interrupt",
        )
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertFalse(self.manifest.exists())

    def test_coordinated_install_restores_historical_manifest_after_commit(
        self,
    ) -> None:
        historical_data = b"exact-prior-managed-action-manifest"
        manifest_spec = ActionManifestSpec(
            manifest=self.manifest_spec.manifest,
            historical_manifests=(signature(historical_data),),
        )
        self.manifest.parent.mkdir()
        _ = self.manifest.write_bytes(historical_data)

        def install_manifest_then_fail(
            steam_dir: Path,
            artifact: Path,
            spec: ActionManifestSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            result = install_action_manifest(
                steam_dir,
                artifact,
                spec,
                dry_run=dry_run,
            )
            if dry_run:
                return result
            raise OSError("injected post-commit manifest upgrade failure")

        with (
            mock.patch.object(
                installer,
                "install_action_manifest",
                side_effect=install_manifest_then_fail,
            ),
            self.assertRaises(BridgeError) as raised,
        ):
            _ = install_bridge_and_manifest(
                self.game,
                self.artifact,
                self.steam_root,
                self.manifest_artifact,
                self.spec,
                manifest_spec,
            )

        self.assertIn(
            "prior managed manifest state was restored",
            str(raised.exception),
        )
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertEqual(self.manifest.read_bytes(), historical_data)
        self.assertEqual(
            inspect_action_manifest(self.manifest, manifest_spec).state,
            "historical-manifest",
        )

    def test_coordinated_install_preserves_concurrent_unknown_manifest(
        self,
    ) -> None:
        unknown = b"concurrently-replaced-unknown-manifest"

        def install_manifest_then_replace_with_unknown(
            steam_dir: Path,
            artifact: Path,
            spec: ActionManifestSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            result = install_action_manifest(
                steam_dir,
                artifact,
                spec,
                dry_run=dry_run,
            )
            if dry_run:
                return result
            _ = self.manifest.write_bytes(unknown)
            raise OSError("injected failure after concurrent manifest change")

        with (
            mock.patch.object(
                installer,
                "install_action_manifest",
                side_effect=install_manifest_then_replace_with_unknown,
            ),
            self.assertRaises(BridgeError) as raised,
        ):
            _ = install_bridge_and_manifest(
                self.game,
                self.artifact,
                self.steam_root,
                self.manifest_artifact,
                self.spec,
                self.manifest_spec,
            )

        message = str(raised.exception)
        self.assertIn("refusing to overwrite a concurrent change", message)
        self.assertEqual(self.manifest.read_bytes(), unknown)
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)

    def test_coordinated_install_rolls_back_after_manifest_failure(self) -> None:
        self.manifest.parent.mkdir()
        unrelated_game = self.game / "unrelated-game.bin"
        unrelated_steam = self.manifest.parent / "unrelated-steam.vdf"
        _ = unrelated_game.write_bytes(b"leave game file alone")
        _ = unrelated_steam.write_bytes(b"leave Steam file alone")

        def fail_manifest_install(
            steam_dir: Path,
            artifact: Path,
            spec: ActionManifestSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            if dry_run:
                return install_action_manifest(
                    steam_dir,
                    artifact,
                    spec,
                    dry_run=True,
                )
            raise OSError("injected manifest installation failure")

        with (
            mock.patch.object(
                installer,
                "install_action_manifest",
                side_effect=fail_manifest_install,
            ),
            self.assertRaises(BridgeError) as raised,
        ):
            _ = install_bridge_and_manifest(
                self.game,
                self.artifact,
                self.steam_root,
                self.manifest_artifact,
                self.spec,
                self.manifest_spec,
            )

        self.assertIn(
            "bridge was rolled back to the verified original",
            str(raised.exception),
        )
        self.assertIn(
            "Primary error: OSError: injected manifest installation failure",
            str(raised.exception),
        )
        self.assertEqual(self.target.read_bytes(), self.original_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(unrelated_game.read_bytes(), b"leave game file alone")
        self.assertEqual(unrelated_steam.read_bytes(), b"leave Steam file alone")
        self.assertEqual(
            {path.name for path in self.game.iterdir()},
            {
                TARGET_NAME,
                BACKUP_NAME,
                FLOWER_EXE_NAME,
                STEAM_API_NAME,
                unrelated_game.name,
            },
        )
        self.assertEqual(set(self.manifest.parent.iterdir()), {unrelated_steam})

    def test_coordinated_restore_removes_manifest_before_bridge_failure(
        self,
    ) -> None:
        _ = install_bridge_and_manifest(
            self.game,
            self.artifact,
            self.steam_root,
            self.manifest_artifact,
            self.spec,
            self.manifest_spec,
        )
        unrelated_game = self.game / "unrelated-game.bin"
        unrelated_steam = self.manifest.parent / "unrelated-steam.vdf"
        _ = unrelated_game.write_bytes(b"leave game file alone")
        _ = unrelated_steam.write_bytes(b"leave Steam file alone")

        def fail_bridge_restore(
            game_dir: Path,
            spec: BridgeSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            if dry_run:
                return restore_bridge(game_dir, spec, dry_run=True)
            raise OSError("injected bridge restoration failure")

        with (
            mock.patch.object(
                installer,
                "restore_bridge",
                side_effect=fail_bridge_restore,
            ),
            self.assertRaisesRegex(
                OSError,
                "injected bridge restoration failure",
            ),
        ):
            _ = restore_bridge_and_manifest(
                self.game,
                self.steam_root,
                self.spec,
                self.manifest_spec,
            )

        self.assertEqual(self.target.read_bytes(), self.bridge_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(unrelated_game.read_bytes(), b"leave game file alone")
        self.assertEqual(unrelated_steam.read_bytes(), b"leave Steam file alone")
        self.assertEqual(
            {path.name for path in self.game.iterdir()},
            {
                TARGET_NAME,
                BACKUP_NAME,
                FLOWER_EXE_NAME,
                STEAM_API_NAME,
                unrelated_game.name,
            },
        )
        self.assertEqual(set(self.manifest.parent.iterdir()), {unrelated_steam})

    def test_coordinated_install_reports_primary_and_rollback_failures(
        self,
    ) -> None:
        self.manifest.parent.mkdir()

        def fail_manifest_install(
            steam_dir: Path,
            artifact: Path,
            spec: ActionManifestSpec,
            *,
            dry_run: bool = False,
        ) -> OperationResult:
            if dry_run:
                return install_action_manifest(
                    steam_dir,
                    artifact,
                    spec,
                    dry_run=True,
                )
            raise OSError("injected manifest installation failure")

        def fail_bridge_rollback(
            _game_dir: Path,
            _spec: BridgeSpec,
        ) -> OperationResult:
            raise OSError("injected bridge rollback failure")

        with (
            mock.patch.object(
                installer,
                "install_action_manifest",
                side_effect=fail_manifest_install,
            ),
            mock.patch.object(
                installer,
                "restore_bridge",
                side_effect=fail_bridge_rollback,
            ),
            self.assertRaises(BridgeError) as raised,
        ):
            _ = install_bridge_and_manifest(
                self.game,
                self.artifact,
                self.steam_root,
                self.manifest_artifact,
                self.spec,
                self.manifest_spec,
            )

        message = str(raised.exception)
        self.assertIn(
            "Primary error: OSError: injected manifest installation failure",
            message,
        )
        self.assertIn(
            "Bridge rollback error: OSError: injected bridge rollback failure",
            message,
        )
        self.assertEqual(self.target.read_bytes(), self.bridge_data)
        self.assertEqual(self.backup.read_bytes(), self.original_data)
        self.assertFalse(self.manifest.exists())

    def test_explicit_path_resolution(self) -> None:
        self.assertEqual(resolve_game_directory(self.game), self.game)
        self.assertEqual(resolve_game_directory(self.target), self.game)
        self.assertEqual(resolve_steam_directory(self.steam_root), self.steam_root)


class BridgeReleaseTests(unittest.TestCase):
    project_root: Path = Path(__file__).resolve().parents[1]
    bridge: Path = project_root / "gyro_bridge" / "dist" / "libScePad.dll"
    manifest: Path = (
        project_root
        / "gyro_bridge"
        / "steam_input"
        / "game_actions_966330.vdf"
    )
    source: Path = (
        project_root
        / "gyro_bridge"
        / "src"
        / "flower_scepad_bridge.cpp"
    )

    def test_bundled_bridge_matches_installer_signature(self) -> None:
        self.assertEqual(self.bridge.stat().st_size, SUPPORTED_SPEC.bridge.size)
        self.assertEqual(
            hashlib.sha256(self.bridge.read_bytes()).hexdigest(),
            SUPPORTED_SPEC.bridge.sha256,
        )

    def test_previous_inverted_x_bridge_remains_managed(self) -> None:
        managed_signatures = {
            (signature.size, signature.sha256)
            for signature in SUPPORTED_SPEC.historical_bridges
        }
        self.assertIn(
            (
                84_480,
                "9c5dcb1e482ecdf41660f39a474d5fef0b7fab0220f6fa04d3ab359e9ac07487",
            ),
            managed_signatures,
        )

    def test_previous_raw_motion_bridge_remains_managed(self) -> None:
        managed_signatures = {
            (signature.size, signature.sha256)
            for signature in SUPPORTED_SPEC.historical_bridges
        }
        self.assertIn(
            (
                84_480,
                "e7a77b24116b2756b4bcbf6f2a4b54ffc28c55003782824f9eba7c7e70082d44",
            ),
            managed_signatures,
        )

    def test_previous_named_tilt_bridge_remains_managed(self) -> None:
        managed_signatures = {
            (signature.size, signature.sha256)
            for signature in SUPPORTED_SPEC.historical_bridges
        }
        self.assertIn(
            (
                83_968,
                "e34d78779b26aa2ff2f65f499aea8ee0966310731e0ab73cc055c8a69ff329b3",
            ),
            managed_signatures,
        )

    def test_bundled_manifest_matches_installer_signature(self) -> None:
        self.assertEqual(
            self.manifest.stat().st_size,
            SUPPORTED_MANIFEST_SPEC.manifest.size,
        )
        self.assertEqual(
            hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            SUPPORTED_MANIFEST_SPEC.manifest.sha256,
        )

    def test_native_source_uses_named_tilt_without_xinput_or_raw_motion(self) -> None:
        source = self.source.read_text(encoding="utf-8")
        self.assertNotIn("XInputGetState", source)
        self.assertNotIn("XInputSetState", source)
        self.assertNotIn("GetMotionData", source)
        self.assertIn("kTiltMaximumAngleRadians", source)

    def test_manifest_keeps_the_raw_virtual_ps4_action_ids(self) -> None:
        manifest = self.manifest.read_text(encoding="utf-8")
        analog_actions = ("left_stick", "right_stick", "tilt")
        digital_actions = (
            "dpad_up",
            "dpad_right",
            "dpad_down",
            "dpad_left",
            "square",
            "cross",
            "circle",
            "triangle",
            "l1",
            "r1",
            "l2",
            "r2",
            "options",
            "touchpad_click",
        )
        for action in (*analog_actions, *digital_actions):
            self.assertIn(f'"{action}"', manifest)
        self.assertIn('"Options (Start)"', manifest)
        self.assertIn('"Touchpad Click (Select)"', manifest)
        self.assertIn('"flower_ps4"', manifest)


if __name__ == "__main__":
    _ = unittest.main()
