# Releasing

Releases are produced from immutable Git tags in a fresh checkout. Never package
from a developer's ordinary working directory.

## Bundle and component versions

This procedure covers bundle `1.2.0` (tag `v1.2.0`), dated `2026-09-06`.
The release must provide one bundle containing both independently selectable
components:

| Item | Release version source | Version | Tag for this bundle |
|---|---|---:|---|
| Combined release bundle | `pyproject.toml` and `tools/build_release.py` `BUNDLE_VERSION` | `1.2.0` | `v1.2.0` |
| Hay-bale sound-fix installer | `flower_haybale_fix.py` `SCRIPT_VERSION` | `1.0.1` | Included in the bundle tag |
| Native ScePad gyro bridge component/installer | `gyro_bridge/install_gyro_bridge.py` `SCRIPT_VERSION` | `0.4.5` | Included in the bundle tag |

Component versions still describe their own compatibility and behavior, but new
GitHub releases use one umbrella `vMAJOR.MINOR.PATCH` tag and one ready-to-run
bundle. Historical component tags remain historical and must not be moved.

Bridge `0.4.5` is a component/installer version, not a new native build. This
bundle reuses the DLL and action manifest built for `0.4.4` byte-for-byte, with
the unchanged sizes and hashes documented in [`GYRO_BRIDGE.md`](GYRO_BRIDGE.md).
Do not relabel the native artifacts or change their expected hashes for an
installer-only version bump.

Before tagging:

1. Update the bundle version in `pyproject.toml`, `tools/build_release.py`, and all
   matching documentation. Update an individual component version when that
   component's behavior or compatibility changed.
2. For a native-runtime or action-schema change, rebuild or update the affected
   artifacts and review the exact size/hash allowlists, tests, and documented
   fingerprints together. Installer-only changes must preserve unchanged native
   artifacts; `0.4.5` retains the `0.4.4` fingerprints.
3. Review the complete diff and make the release commit.
4. Create the annotated, signed umbrella tag `v1.2.0`. Tags are immutable;
   correct a release with a new version rather than moving a tag.

## Release roles and record

One named **release packager** owns each release build. Record the packager's
name or account in the release notes. The packager must perform the clean
checkout, toolchain verification, tests, bundle creation, checksum verification,
and upload as one traceable release run; do not combine artifacts
built by different people or from different checkouts.

Retain a transcript containing:

- bundle and included component versions, signed tag, and full commit ID;
- release packager identity and build host/OS;
- llvm-mingw release, archive URL, and verified archive SHA-256;
- complete `clang --version` output;
- production DLL SHA-256 and PE import list;
- every required test command and result;
- final bundle name and `SHA256SUMS`.

A second maintainer must compare the transcript and downloaded assets against
the tag before the draft release is made public.

## First-public-release history sanitation gate

This gate is mandatory once, before any repository URL, tag, or release is made
public. It applies to the entire reachable Git history, not just the current
tree. `.gitignore`, deleting a file in a later commit, or omitting it from a ZIP
does not sanitize history.

The repository owner and release packager must inspect all reachable commits,
tags, trees, and blobs (and Git LFS objects, if LFS is ever used) for:

- Flower/game executables, DLLs, banks, audio, textures, or extracted assets;
- Valve, Steamworks, Sony, or other third-party SDKs and binaries;
- toolchain archives, Proton prefixes, controller profiles, reverse-engineering
  databases, dumps, logs, and generated test binaries;
- credentials, tokens, private URLs, personal data, or other secrets;
- oversized or unexpected binary blobs, including files later deleted or
  renamed.

Run the repository's redacting audit as one required check:

```sh
python3 tools/audit_public_tree.py --history
```

It must pass from a fresh full-history clone. It supplements rather than replaces
manual and specialist secret-scanning review.

Record an explicit `PASS` with the date, reviewed refs, tools/commands used, and
the two reviewers. If anything prohibited or sensitive is found, stop: remove
it from history with a reviewed history rewrite (or recreate the repository),
rotate every exposed secret, make a fresh clone, and repeat the full gate. Do
not publish first and attempt to sanitize afterward.

## Clean tagged checkout

After the release tag exists, the packager must use a new empty directory and a
fresh clone from the canonical repository, not a worktree containing local
builds:

```sh
git clone --no-local https://github.com/natryamar/flower-steam-fixes.git flower-fix-release
cd flower-fix-release
git fetch --force --tags
git verify-tag v1.2.0
git checkout --detach v1.2.0
git status --porcelain=v1 --untracked-files=all
```

The final command must print nothing. Record `git rev-parse HEAD` and verify that
it is the reviewed release commit. Do not copy a DLL or any other payload from a
developer checkout into this clone.

## Pinned llvm-mingw toolchain

Every bundle includes the bridge DLL and must verify it with this pinned
toolchain, even when the native artifacts are unchanged:

- release: `20260616`;
- archive: `llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz`;
- URL:
  <https://github.com/mstorsjo/llvm-mingw/releases/download/20260616/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz>;
- SHA-256:
  `534b92e067b22a6b4441f48ae9240a3341b17825d04d577eab0cf85c44b4deda`;
- Clang: `22.1.8`, LLVM revision
  `ca7933e47d3a3451d81e72ac174dcb5aa28b59d1`;
- target: `x86_64-w64-windows-gnu` with UCRT.

Download into the ignored `re-temp/` area, verify the archive before extraction,
and never add the archive or extracted toolchain to a release payload:

```sh
mkdir -p re-temp/toolchain
curl --fail --location \
  --output re-temp/toolchain/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz \
  https://github.com/mstorsjo/llvm-mingw/releases/download/20260616/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz
printf '%s  %s\n' \
  534b92e067b22a6b4441f48ae9240a3341b17825d04d577eab0cf85c44b4deda \
  re-temp/toolchain/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz \
  | sha256sum --check --strict
tar -xJf re-temp/toolchain/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz \
  -C re-temp/toolchain
```

Ensure `FLOWER_LLVM_MINGW` is unset. `python3 gyro_bridge/build.py
--verify-release` checks the exact Clang identity and target before compiling,
then requires the rebuilt production DLL to have SHA-256
`adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c`.
A compiler identity or binary hash mismatch is a release blocker; do not update
the expected hash merely to make the check pass.

Confirm that the distributed license texts are byte-for-byte copies from this
verified toolchain:

```sh
cmp licenses/LLVM.txt \
  re-temp/toolchain/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64/LICENSE.TXT
cmp licenses/MINGW-W64-RUNTIME.txt \
  re-temp/toolchain/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64/x86_64-w64-mingw32/share/mingw32/COPYING.MinGW-w64-runtime.txt
```

## Required validation

Run all Python tests for every bundle release:

```sh
python3 -m unittest discover -s tests -v
```

For every bundle release, also run the pinned bridge release build and the
isolated Proton smoke matrix. The bundle always includes the DLL, so these
checks are mandatory even for installer-only, launcher-only, or documentation-only
changes with unchanged native artifacts. Record the Proton version/path used by
the smoke test. `gyro_bridge/test.py` invokes the default `build.py` interface,
so this also guards compatibility between the two scripts.

```sh
python3 gyro_bridge/build.py --verify-release
python3 gyro_bridge/test.py
python3 gyro_bridge/build.py --verify-release
```

The last command restores and verifies the release artifact after the smoke
matrix. Then verify the export/import surface using the repository's existing
smoke checks and inspect the PE import list:

```sh
objdump -p gyro_bridge/dist/libScePad.dll | grep 'DLL Name'
sha256sum gyro_bridge/dist/libScePad.dll
git --no-pager diff --exit-code
git --no-pager diff --cached --exit-code
git status --porcelain=v1 --untracked-files=all
```

Only ignored files under `re-temp/` may have been created. There must be no
tracked diff after the deterministic rebuild. Hardware/gameplay claims still
require the real Steam client, supported Flower build, and physical-controller
checks described in [`gyro_bridge/README.md`](gyro_bridge/README.md); do not turn
the isolated smoke test into a hardware-certification claim. Record unrun checks
explicitly; prior validation does not establish a new gameplay or native Windows
pass for `v1.2.0`.

## Release packaging

Each umbrella-tagged GitHub release must have one intended user download:
`flower-steam-fixes-1.2.0.zip` for this release. The only additional uploaded asset is
`SHA256SUMS`. GitHub supplies its own automatically generated source archives;
do not build or upload another source ZIP that could be mistaken for the
ready-to-run bundle.

Run the hardened packager from the clean, detached checkout used for validation:

```sh
python3 tools/build_release.py \
  --ref v1.2.0 \
  --output-dir "<new-external-empty-dir>"
```

The literal `--ref` must be the verified umbrella tag and must resolve to the
currently checked-out `HEAD`. The packager must refuse a different ref, a dirty
checkout (including staged, unstaged, or untracked changes), and an output path
inside the checkout. Replace the quoted `<new-external-empty-dir>` placeholder
with a path outside the checkout. It must either not exist or be an empty real
directory; never reuse a prior release directory.

The result must be exactly `flower-steam-fixes-1.2.0.zip` and `SHA256SUMS`. Do not
rename or post-process the bundle.

### `flower-steam-fixes-1.2.0.zip` exact members

| Tracked source | ZIP member |
|---|---|
| `GYRO_BRIDGE.md` | `GYRO_BRIDGE.md` |
| `HAY_BALE_FIX.md` | `HAY_BALE_FIX.md` |
| `INSTALL_GYRO_BRIDGE_LINUX.sh` | `INSTALL_GYRO_BRIDGE_LINUX.sh` |
| `INSTALL_GYRO_BRIDGE_WINDOWS.cmd` | `INSTALL_GYRO_BRIDGE_WINDOWS.cmd` |
| `INSTALL_HAY_BALE_LINUX.sh` | `INSTALL_HAY_BALE_LINUX.sh` |
| `INSTALL_HAY_BALE_WINDOWS.cmd` | `INSTALL_HAY_BALE_WINDOWS.cmd` |
| `LICENSE` | `LICENSE` |
| `BUNDLE_README.md` | `README.md` |
| `REVERT_GYRO_BRIDGE_LINUX.sh` | `REVERT_GYRO_BRIDGE_LINUX.sh` |
| `REVERT_GYRO_BRIDGE_WINDOWS.cmd` | `REVERT_GYRO_BRIDGE_WINDOWS.cmd` |
| `REVERT_HAY_BALE_LINUX.sh` | `REVERT_HAY_BALE_LINUX.sh` |
| `REVERT_HAY_BALE_WINDOWS.cmd` | `REVERT_HAY_BALE_WINDOWS.cmd` |
| `THIRD_PARTY_NOTICES.md` | `THIRD_PARTY_NOTICES.md` |
| `flower_haybale_fix.py` | `flower_haybale_fix.py` |
| `gyro_bridge/build.py` | `gyro_bridge/build.py` |
| `gyro_bridge/dist/libScePad.dll` | `gyro_bridge/dist/libScePad.dll` |
| `gyro_bridge/install_gyro_bridge.py` | `gyro_bridge/install_gyro_bridge.py` |
| `gyro_bridge/src/flower_scepad_bridge.cpp` | `gyro_bridge/src/flower_scepad_bridge.cpp` |
| `gyro_bridge/src/libScePad.def` | `gyro_bridge/src/libScePad.def` |
| `gyro_bridge/steam_input/game_actions_966330.vdf` | `gyro_bridge/steam_input/game_actions_966330.vdf` |
| `licenses/LLVM.txt` | `licenses/LLVM.txt` |
| `licenses/MINGW-W64-RUNTIME.txt` | `licenses/MINGW-W64-RUNTIME.txt` |

All payloads keep their repository-relative paths; the sole alias is
`BUNDLE_README.md` to the ZIP's root `README.md`. The repository's top-level
`README.md` is not packaged. Component guides and launchers live at the root in
both the repository and bundle. Linux launchers carry mode `0755`; all other
text files carry mode `0644`. The bridge retains its repository-relative
`gyro_bridge/` layout because the installer resolves its DLL and manifest there.
Every unlisted member is forbidden.

### No working-directory archives

Never run `zip -r` on `.`, the repository root, or any developer working
directory. `tools/build_release.py` is the sole bundle builder and must write only
to `<new-external-empty-dir>` outside the checkout. `.git`, `re-temp`, the
toolchain, caches, test binaries, logs, and every unlisted file must remain
outside the bundle.

## Checksums and publication

The packager writes the final one-bundle checksum manifest. Verify it from inside
`<new-external-empty-dir>`:

```sh
sha256sum --check --strict SHA256SUMS
```

The final output directory and uploaded release assets must contain exactly:

- `flower-steam-fixes-1.2.0.zip`
- `SHA256SUMS`

Upload those two files to a draft release for the matching umbrella tag. In the
GitHub release notes, identify `flower-steam-fixes-1.2.0.zip` as the only
ready-to-run download and explain that GitHub's **Source code** links are not the
installer bundle.

Release notes must also include the full commit ID, release packager, pinned
toolchain identity, production DLL hash, validation results, and manual-test
limitations. Distinguish component/installer `0.4.5` from the unchanged `0.4.4`
native DLL/action manifest. Never claim gameplay or native Windows validation
that was not actually run.

Finally, download both uploaded assets into a new empty directory and run
`sha256sum --check --strict SHA256SUMS` there. Inspect the bundle against its exact
member table and confirm that no Valve, Sony, Flower/game, toolchain, test, or
working-directory binary slipped into it. Publish only after that independent
downloaded-asset verification and second-maintainer review pass. Passing CI or
packaging is not publication approval: no publishing workflow may bypass the
history-sanitation gate, release transcript, manual review, or downloaded-asset
verification.
