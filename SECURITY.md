# Security Policy

## Supported versions

Security fixes are considered for the current public source only:

| Item | Supported version | Compatibility target |
|---|---:|---|
| Umbrella project | `1.1.0` | Current repository state |
| Hay-bale sound fix | `1.0.0` | Steam build `4354278`, App `966330` |
| Native ScePad bridge | `0.4.4` | Steam build `4354278`, App `966330` |

Historical bridge artifacts are recognized only so the current installer can
upgrade or restore them safely. Unknown game builds and locally modified
artifacts are outside the supported compatibility boundary.

## Report a vulnerability privately

Use GitHub's
[private vulnerability reporting](https://github.com/natryamar/flower-steam-fixes/security/advisories/new)
to open a private security advisory. Do not disclose a suspected vulnerability,
proof of concept, or exploit details in a public issue or pull request.

A useful report contains:

- affected component and version;
- security impact and who or what is at risk;
- minimal, repeatable steps using synthetic data where possible;
- expected and observed behavior;
- relevant status/state names and public hashes; and
- a suggested mitigation, if known.

## Protect game and user data

Never upload or attach proprietary game files. This includes `Flower.exe`,
shipped DLLs, `steam_api64.dll`, `.bnk` files, audio, extracted assets, or an
archive of the Flower directory. A legitimate local installation may be needed
to reproduce a report, but its files must remain local.

Also do not submit Steam controller profiles, credentials, tokens, reverse-
engineering databases, crash dumps, or full logs. Paste only the minimum relevant
text and redact:

- absolute home, Steam-library, and game paths;
- Steam/account names or IDs;
- controller serials, Bluetooth addresses, USB IDs, and other device IDs; and
- unrelated environment variables or process information.

The installers' published SHA-256 compatibility values are not secrets and do
not need redaction.

## Security-relevant scope

Examples include unsafe file replacement or rollback, allowlist bypass,
symlink/hardlink or race handling, unintended profile/data modification,
memory-safety defects in the native bridge, and a failure to return wholly to
the original provider when Steam-owned state becomes unavailable or stale.
Ordinary controller-layout or compatibility problems belong in a bug report
unless they create a security impact.

Do not weaken exact-hash checks or use real proprietary files as a test fixture.
Security reproductions should use the repository's synthetic Python fixtures or
independent fake native DLLs.

## If an installation may be unsafe

Close Flower, stop running project tools, and do not retry installation or edit
the verified backup. Run `status`, then a `restore --dry-run` only if doing so is
safe. Follow [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) for the supported
restore and Steam verification paths. Preserve only redacted text needed for the
private report.

The project will coordinate remediation and disclosure in the private advisory.
No public disclosure timeline is promised before the issue has been assessed and
a safe fix or mitigation is available.
