from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools import audit_public_tree


class PublicAuditUnitTests(unittest.TestCase):
    def test_path_policy_allows_only_the_project_dll(self) -> None:
        self.assertEqual(
            audit_public_tree.validate_path(
                "gyro_bridge/dist/libScePad.dll", historical=False
            ),
            [],
        )
        self.assertIn(
            "unapproved DLL",
            audit_public_tree.validate_path("steam_api64.dll", historical=False),
        )
        self.assertIn(
            "forbidden file class .bnk",
            audit_public_tree.validate_path("fixtures/Level4_A.bnk", historical=False),
        )

    def test_text_policy_detects_private_values_without_returning_them(self) -> None:
        home_path = b"/" + b"home/" + b"example/Projects/fix"
        controller_path = (
            b"Steam Controller " + b"Configs/" + b"123456789/config/file.vdf"
        )
        reasons = audit_public_tree.scan_text(
            "note.md",
            b"workspace: " + home_path + b"\nprofile: " + controller_path + b"\n",
        )
        self.assertEqual(
            reasons,
            [
                "absolute user home path",
                "account-scoped Steam controller-config path",
            ],
        )

    def test_runner_exception_is_limited_to_the_pinned_dll_prefix(self) -> None:
        runner_path = (
            b"/" + b"home/" + b"runner/work/llvm-mingw/llvm-mingw/build"
        )
        self.assertEqual(
            audit_public_tree.scan_text(
                audit_public_tree.PINNED_BINARY_PATH,
                runner_path,
            ),
            [],
        )
        self.assertIn(
            "absolute user home path",
            audit_public_tree.scan_text("build.log", runner_path),
        )

    def test_text_policy_detects_windows_user_home_paths(self) -> None:
        windows_path = b"C:" + b"\\Users\\" + b"example\\Documents\\private.txt"
        self.assertEqual(
            audit_public_tree.scan_text("note.md", windows_path),
            ["absolute Windows user home path"],
        )

    def test_ref_requires_history(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            _ = audit_public_tree.main(["--ref", "HEAD"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--ref requires --history", stderr.getvalue())


class PublicAuditRepositoryTests(unittest.TestCase):
    def create_repository(self) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        self.run_git(root, "init", "--quiet")
        self.run_git(root, "config", "user.name", "Public Audit Test")
        self.run_git(root, "config", "user.email", "test@example.invalid")
        return root

    def run_git(self, root: Path, *arguments: str) -> None:
        _ = subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=True,
            capture_output=True,
        )

    def write(self, root: Path, relative_path: str, contents: str | bytes) -> None:
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, str):
            _ = destination.write_text(contents, encoding="utf-8")
        else:
            _ = destination.write_bytes(contents)

    def commit(self, root: Path, message: str) -> None:
        self.run_git(root, "add", "--all")
        self.run_git(root, "commit", "--quiet", "-m", message)

    def private_home_path(self) -> str:
        return "/" + "home/" + "example/Projects/fix"

    def pinned_dll(self) -> bytes:
        return (
            audit_public_tree.PROJECT_ROOT / audit_public_tree.PINNED_BINARY_PATH
        ).read_bytes()

    def test_safe_current_fixture_passes(self) -> None:
        root = self.create_repository()
        self.write(root, "README.md", "safe public fixture\n")
        self.write(root, audit_public_tree.PINNED_BINARY_PATH, self.pinned_dll())
        self.run_git(root, "add", "--all")

        self.assertEqual(audit_public_tree.audit_index(root), set())

    def test_forbidden_renamed_path_with_same_blob_fails_history(self) -> None:
        root = self.create_repository()
        self.write(root, "safe.txt", "unchanged blob\n")
        self.commit(root, "safe name")
        self.run_git(root, "mv", "safe.txt", "payload.exe")
        self.commit(root, "forbidden name")
        self.run_git(root, "mv", "payload.exe", "safe.txt")
        self.commit(root, "restore safe name")

        self.assertEqual(audit_public_tree.audit_index(root), set())
        findings = audit_public_tree.audit_history(root)
        self.assertTrue(
            any(
                finding.location.endswith(":payload.exe")
                and finding.reason == "forbidden file class .exe"
                for finding in findings
            )
        )

    def test_sensitive_commit_message_fails_without_printing_value(self) -> None:
        root = self.create_repository()
        private_path = self.private_home_path()
        self.write(root, "README.md", "safe\n")
        self.commit(root, f"built from {private_path}")

        findings = audit_public_tree.audit_history(root)
        self.assertTrue(
            any(
                finding.location.startswith("commit ")
                and finding.reason == "absolute user home path"
                for finding in findings
            )
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = audit_public_tree.main(["--root", str(root), "--history"])
        self.assertEqual(exit_code, 1)
        self.assertNotIn(private_path, stdout.getvalue())
        self.assertNotIn(private_path, stderr.getvalue())

    def test_sensitive_annotated_tag_message_fails(self) -> None:
        root = self.create_repository()
        private_path = self.private_home_path()
        self.write(root, "README.md", "safe\n")
        self.commit(root, "safe")
        self.run_git(root, "tag", "-a", "v1.0", "-m", f"built from {private_path}")

        all_findings = audit_public_tree.audit_history(root)
        selected_findings = audit_public_tree.audit_history(root, refs=("v1.0",))
        for findings in (all_findings, selected_findings):
            self.assertTrue(
                any(
                    finding.location.startswith("annotated tag ")
                    and finding.reason == "absolute user home path"
                    for finding in findings
                )
            )

    def test_selected_history_ignores_unrelated_refs(self) -> None:
        root = self.create_repository()
        private_path = self.private_home_path()
        self.write(root, "README.md", "safe public history\n")
        self.commit(root, "safe")
        self.run_git(root, "branch", "safe-branch")
        self.run_git(root, "switch", "--quiet", "-c", "private-branch")
        self.write(root, "private-note.txt", f"workspace {private_path}\n")
        self.commit(root, f"private build from {private_path}")
        self.run_git(
            root,
            "tag",
            "-a",
            "private-tag",
            "-m",
            f"private tag from {private_path}",
        )

        all_findings = audit_public_tree.audit_history(root)
        self.assertTrue(
            any(
                finding.reason == "absolute user home path"
                for finding in all_findings
            )
        )
        self.assertTrue(
            any(
                finding.location.startswith("annotated tag ")
                for finding in all_findings
            )
        )
        self.assertEqual(
            audit_public_tree.audit_history(root, refs=("safe-branch",)),
            set(),
        )

    def test_binary_printable_sensitive_path_fails(self) -> None:
        root = self.create_repository()
        private_path = self.private_home_path().encode("ascii")
        binary_data = b"\x00\xffdiagnostic: " + private_path + b"\x00\x01"
        self.write(root, "artifact.bin", binary_data)
        self.commit(root, "binary fixture")

        index_reasons = {
            finding.reason for finding in audit_public_tree.audit_index(root)
        }
        history_reasons = {
            finding.reason for finding in audit_public_tree.audit_history(root)
        }
        self.assertIn("absolute user home path", index_reasons)
        self.assertIn("absolute user home path", history_reasons)

    def test_stale_dll_generation_fails_index_and_history(self) -> None:
        root = self.create_repository()
        pinned_dll = self.pinned_dll()
        stale_dll = bytearray(pinned_dll)
        stale_dll[-1] ^= 1
        self.write(root, audit_public_tree.PINNED_BINARY_PATH, bytes(stale_dll))
        self.commit(root, "stale DLL")

        current_reasons = {
            finding.reason for finding in audit_public_tree.audit_index(root)
        }
        self.assertIn(audit_public_tree.PINNED_BINARY_MISMATCH_REASON, current_reasons)

        self.write(root, audit_public_tree.PINNED_BINARY_PATH, pinned_dll)
        self.commit(root, "restore pinned DLL")
        self.assertEqual(audit_public_tree.audit_index(root), set())
        history_reasons = {
            finding.reason for finding in audit_public_tree.audit_history(root)
        }
        self.assertIn(audit_public_tree.PINNED_BINARY_MISMATCH_REASON, history_reasons)

    def test_deleted_private_handoff_remains_a_history_failure(self) -> None:
        root = self.create_repository()
        self.write(root, "README.md", "safe\n")
        self.commit(root, "safe")
        self.assertEqual(audit_public_tree.audit_index(root), set())

        private_path = self.private_home_path()
        self.write(
            root,
            "docs/HANDOFF_NATIVE_TILT.md",
            f"workspace {private_path}\n",
        )
        self.commit(root, "private note")
        self.run_git(root, "rm", "--quiet", "docs/HANDOFF_NATIVE_TILT.md")
        self.commit(root, "delete note")

        self.assertEqual(audit_public_tree.audit_index(root), set())
        reasons = {finding.reason for finding in audit_public_tree.audit_history(root)}
        self.assertIn("known private handoff path remains reachable", reasons)
        self.assertIn("absolute user home path", reasons)


if __name__ == "__main__":
    _ = unittest.main()
