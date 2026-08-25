#!/usr/bin/env python3
"""Audit tracked Git objects for public-release privacy and artifact policy."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PINNED_BINARY_PATH = "gyro_bridge/dist/libScePad.dll"
PINNED_BINARY_SIZE = 84_992
PINNED_BINARY_SHA256 = (
    "adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c"
)
PINNED_BINARY_MISMATCH_REASON = "allowed DLL does not match pinned artifact"
PINNED_BINARY_PUBLIC_BUILD_PREFIX = (
    b"/" + b"home/" + b"runner/work/llvm-mingw/llvm-mingw"
)
ALLOWED_BINARY_PATHS = frozenset({PINNED_BINARY_PATH})
FORBIDDEN_BASENAMES = frozenset(
    {
        "flower.exe",
        "libscepad_original.dll",
        "steam_api.dll",
        "steam_api64.dll",
    }
)
FORBIDDEN_SUFFIXES = frozenset(
    {
        ".bank",
        ".bnk",
        ".dmp",
        ".dump",
        ".exe",
        ".gpr",
        ".ogg",
        ".pdb",
        ".pssg",
        ".rdb",
        ".rep",
        ".streams",
        ".wav",
        ".wem",
        ".xvag",
    }
)
FORBIDDEN_HISTORY_PATHS = frozenset({"docs/HANDOFF_NATIVE_TILT.md"})

ASCII_PRINTABLE_STRINGS = re.compile(rb"[\x09\x0a\x0d\x20-\x7e]{4,}")
UTF16_LE_PRINTABLE_STRINGS = re.compile(rb"(?:[\x09\x0a\x0d\x20-\x7e]\x00){4,}")
UTF16_BE_PRINTABLE_STRINGS = re.compile(rb"(?:\x00[\x09\x0a\x0d\x20-\x7e]){4,}")

TEXT_RULES = (
    (
        "absolute user home path",
        re.compile(rb"/(?:home/|Users/)(?![<]|path/to/)[A-Za-z0-9._-]+/"),
    ),
    (
        "absolute Windows user home path",
        re.compile(
            rb"\b[A-Za-z]:\\Users\\(?![<])[^\\\r\n]+(?:\\|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "account-scoped Steam userdata path",
        re.compile(rb"(?:^|[/\\])userdata[/\\][0-9]{6,}(?:[/\\]|$)"),
    ),
    (
        "account-scoped Steam controller-config path",
        re.compile(rb"Steam Controller Configs[/\\][0-9]{6,}(?:[/\\]|$)"),
    ),
    (
        "embedded URL credentials",
        re.compile(rb"https?://[^/\s:@]+:[^@\s/]+@", re.IGNORECASE),
    ),
    (
        "private key material",
        re.compile(rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    ),
    (
        "GitHub access token",
        re.compile(rb"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "AWS access key",
        re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    ),
)


@dataclass(frozen=True, order=True)
class Finding:
    location: str
    reason: str


def run_git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", os.fspath(root), *arguments],
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {message}")
    return completed.stdout


def validate_path(path: str, *, historical: bool) -> list[str]:
    reasons: list[str] = []
    pure_path = PurePosixPath(path)
    if not path or pure_path.is_absolute() or ".." in pure_path.parts:
        reasons.append("unsafe repository path")
        return reasons

    normalized = path.casefold()
    basename = pure_path.name.casefold()
    suffix = pure_path.suffix.casefold()
    if historical and path in FORBIDDEN_HISTORY_PATHS:
        reasons.append("known private handoff path remains reachable")
    if basename in FORBIDDEN_BASENAMES:
        reasons.append("proprietary or user-supplied binary name")
    if suffix == ".dll" and path not in ALLOWED_BINARY_PATHS:
        reasons.append("unapproved DLL")
    elif suffix in FORBIDDEN_SUFFIXES:
        reasons.append(f"forbidden file class {suffix}")
    if normalized.startswith("re-temp/") or "/re-temp/" in normalized:
        reasons.append("temporary workspace content")
    if "controller profile" in normalized or normalized.endswith("_gyro.vdf"):
        reasons.append("controller profile or calibration data")
    return reasons


def iter_printable_strings(data: bytes):
    for match in ASCII_PRINTABLE_STRINGS.finditer(data):
        yield match.group()
    for match in UTF16_LE_PRINTABLE_STRINGS.finditer(data):
        yield match.group()[::2]
    for match in UTF16_BE_PRINTABLE_STRINGS.finditer(data):
        yield match.group()[1::2]


def scan_text(path: str, data: bytes) -> list[str]:
    matched_rules: set[str] = set()
    for printable_string in iter_printable_strings(data):
        if path == PINNED_BINARY_PATH:
            printable_string = printable_string.replace(
                PINNED_BINARY_PUBLIC_BUILD_PREFIX,
                b"",
            )
        for name, pattern in TEXT_RULES:
            if name not in matched_rules and pattern.search(printable_string):
                matched_rules.add(name)
    return [name for name, _pattern in TEXT_RULES if name in matched_rules]


def validate_blob(path: str, data: bytes) -> list[str]:
    if path != PINNED_BINARY_PATH:
        return []
    if len(data) != PINNED_BINARY_SIZE:
        return [PINNED_BINARY_MISMATCH_REASON]
    if hashlib.sha256(data).hexdigest() != PINNED_BINARY_SHA256:
        return [PINNED_BINARY_MISMATCH_REASON]
    return []


def audit_index(root: Path) -> set[Finding]:
    findings: set[Finding] = set()
    output = run_git(root, "ls-files", "-z")
    paths = [item.decode("utf-8") for item in output.split(b"\0") if item]
    for path in paths:
        for reason in validate_path(path, historical=False):
            findings.add(Finding(path, reason))
        data = run_git(root, "cat-file", "blob", f":{path}")
        for reason in validate_blob(path, data):
            findings.add(Finding(path, reason))
        for reason in scan_text(path, data):
            findings.add(Finding(path, reason))
    return findings


def object_message(data: bytes) -> bytes:
    _headers, separator, message = data.partition(b"\n\n")
    return message if separator else b""


def audit_annotated_tag_messages(
    root: Path,
    tag_object_ids: tuple[bytes, ...] | None = None,
) -> set[Finding]:
    findings: set[Finding] = set()
    pending: list[bytes] = []
    if tag_object_ids is None:
        ref_output = run_git(
            root,
            "for-each-ref",
            "--format=%(objecttype) %(objectname)",
        )
        for raw_line in ref_output.splitlines():
            object_type, separator, object_id = raw_line.partition(b" ")
            if not separator:
                raise RuntimeError("malformed for-each-ref output")
            if object_type == b"tag":
                pending.append(object_id)
    else:
        pending.extend(tag_object_ids)

    seen: set[bytes] = set()
    while pending:
        object_id = pending.pop()
        if object_id in seen:
            continue
        seen.add(object_id)
        object_id_text = object_id.decode("ascii")
        data = run_git(root, "cat-file", "tag", object_id_text)
        headers, _separator, _message = data.partition(b"\n\n")
        header_values: dict[bytes, bytes] = {}
        for raw_header in headers.splitlines():
            name, separator, value = raw_header.partition(b" ")
            if separator and name in {b"object", b"type"}:
                header_values[name] = value
        if header_values.get(b"type") == b"tag" and b"object" in header_values:
            pending.append(header_values[b"object"])

        location = f"annotated tag {object_id_text[:12]}"
        for reason in scan_text(location, object_message(data)):
            findings.add(Finding(location, reason))
    return findings


def resolve_history_refs(
    root: Path,
    refs: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[bytes, ...]]:
    commit_ids: list[str] = []
    tag_object_ids: list[bytes] = []
    for ref in refs:
        object_id = run_git(
            root,
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{ref}^{{object}}",
        ).strip()
        commit_id = run_git(
            root,
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{ref}^{{commit}}",
        ).strip()
        if not re.fullmatch(rb"[0-9a-f]{40,64}", object_id):
            raise RuntimeError("git returned a malformed object ID")
        if not re.fullmatch(rb"[0-9a-f]{40,64}", commit_id):
            raise RuntimeError("git returned a malformed commit ID")

        object_id_text = object_id.decode("ascii")
        object_type = run_git(root, "cat-file", "-t", object_id_text).strip()
        if object_type == b"tag":
            tag_object_ids.append(object_id)
        commit_ids.append(commit_id.decode("ascii"))

    return tuple(commit_ids), tuple(tag_object_ids)


def audit_history(
    root: Path,
    refs: tuple[str, ...] | None = None,
) -> set[Finding]:
    findings: set[Finding] = set()
    selected_refs = tuple(refs or ())
    if selected_refs:
        commit_ids, tag_object_ids = resolve_history_refs(root, selected_refs)
        commit_output = run_git(root, "rev-list", *commit_ids)
    else:
        tag_object_ids = None
        commit_output = run_git(root, "rev-list", "--all")
    seen_entries: set[tuple[bytes, bytes]] = set()
    blob_text_reasons: dict[bytes, tuple[str, ...]] = {}
    pinned_binary_reasons: dict[bytes, tuple[str, ...]] = {}

    for raw_commit_id in commit_output.splitlines():
        commit_id = raw_commit_id.decode("ascii")
        commit_data = run_git(root, "cat-file", "commit", commit_id)
        commit_location = f"commit {commit_id[:12]}"
        for reason in scan_text(commit_location, object_message(commit_data)):
            findings.add(Finding(commit_location, reason))

        tree_output = run_git(root, "ls-tree", "-r", "-z", commit_id)
        for raw_entry in tree_output.split(b"\0"):
            if not raw_entry:
                continue
            metadata, separator, raw_path = raw_entry.partition(b"\t")
            metadata_parts = metadata.split()
            if not separator or len(metadata_parts) != 3:
                raise RuntimeError("malformed ls-tree output")
            _mode, object_type, object_id = metadata_parts
            entry_key = (object_id, raw_path)
            if entry_key in seen_entries:
                continue
            seen_entries.add(entry_key)

            path = raw_path.decode("utf-8", errors="replace")
            object_id_text = object_id.decode("ascii")
            location = f"{object_id_text[:12]}:{path}"
            for reason in validate_path(path, historical=True):
                findings.add(Finding(location, reason))
            if object_type != b"blob":
                continue

            data: bytes | None = None
            if object_id not in blob_text_reasons:
                data = run_git(root, "cat-file", "blob", object_id_text)
                blob_text_reasons[object_id] = tuple(scan_text(path, data))
            for reason in blob_text_reasons[object_id]:
                findings.add(Finding(location, reason))

            if path == PINNED_BINARY_PATH:
                if object_id not in pinned_binary_reasons:
                    if data is None:
                        data = run_git(root, "cat-file", "blob", object_id_text)
                    pinned_binary_reasons[object_id] = tuple(validate_blob(path, data))
                for reason in pinned_binary_reasons[object_id]:
                    findings.add(Finding(location, reason))

    findings.update(audit_annotated_tag_messages(root, tag_object_ids))
    return findings


class AuditArguments(argparse.Namespace):
    root: Path = PROJECT_ROOT
    history: bool = False
    refs: list[str] | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Git repository to audit (default: repository containing this script)",
    )
    _ = parser.add_argument(
        "--history",
        action="store_true",
        help="also inspect commit history (all local refs by default)",
    )
    _ = parser.add_argument(
        "--ref",
        action="append",
        dest="refs",
        metavar="REF",
        help="history ref to inspect; repeatable and requires --history",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = AuditArguments()
    parser = build_parser()
    _ = parser.parse_args(argv, namespace=args)
    if args.refs and not args.history:
        parser.error("--ref requires --history")
    root = args.root.resolve()
    try:
        findings = audit_index(root)
        if args.history:
            findings.update(audit_history(root, refs=tuple(args.refs or ())))
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"Public audit could not complete: {error}", file=sys.stderr)
        return 2

    if findings:
        print("Public audit failed; matched values are intentionally redacted:")
        for finding in sorted(findings):
            print(f"- {finding.location}: {finding.reason}")
        return 1

    if args.history and args.refs:
        scope = "tracked index and selected reachable history"
    elif args.history:
        scope = "tracked index and reachable history"
    else:
        scope = "tracked index"
    print(f"Public audit passed: {scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
