# Releasing

Releases are produced from immutable Git tags in a fresh checkout. Never package
from a developer's ordinary working directory.

## Independent component versions and tags

The repository contains two independently versioned deliverables:

| Component | Current version source | Tag format | Tag for this version |
|---|---|---|---|
| Hay-bale sound fix | `flower_haybale_fix.py` `SCRIPT_VERSION` (`1.0.0`) | `haybale-vMAJOR.MINOR.PATCH` | `haybale-v1.0.0` |
| Native ScePad gyro bridge | `gyro_bridge/install_gyro_bridge.py` `SCRIPT_VERSION` (`0.4.4`) | `gyro-bridge-vMAJOR.MINOR.PATCH` | `gyro-bridge-v0.4.4` |

These tag names are created only when those versions are released. The version
in `pyproject.toml` is repository/package metadata; it is not a substitute for
either component version. A commit may carry both component tags
when both are released, but one component must not be renumbered merely because
the other changed.

Before tagging:

1. Update the changed component's version and all matching documentation.
2. For a bridge change, rebuild the DLL, update the installer's exact size/hash
   allowlist, and update tests and documented artifact hashes together.
3. Review the complete diff and make the release commit.
4. Create an annotated, signed tag using the component's tag format. Tags are
   immutable; correct a release with a new version rather than moving a tag.

## Release roles and record

One named **release packager** owns each release build. Record the packager's
name or account in the release notes. The packager must perform the clean
checkout, toolchain verification, tests, package/source-archive creation,
checksum creation, and upload as one traceable release run; do not combine artifacts
built by different people or from different checkouts.

Retain a transcript containing:

- component version, signed tag, and full commit ID;
- release packager identity and build host/OS;
- llvm-mingw release, archive URL, and verified archive SHA-256;
- complete `clang --version` output;
- production DLL SHA-256 and PE import list;
- every required test command and result;
- final archive names and `SHA256SUMS`.

A second maintainer should compare the transcript and downloaded assets against
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
git clone --no-local <canonical-repository-url> flower-fix-release
cd flower-fix-release
git fetch --force --tags
git verify-tag <component-tag>
git checkout --detach <component-tag>
git status --porcelain=v1 --untracked-files=all
```

The final command must print nothing. Record `git rev-parse HEAD` and verify that
it is the reviewed release commit. Do not copy a DLL or any other payload from a
developer checkout into this clone.

## Pinned llvm-mingw toolchain

Bridge release builds use exactly:

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

Run all Python tests for every component release:

```sh
python3 -m unittest discover -s tests -v
```

For every bridge release, also run the pinned release build and the isolated
Proton smoke matrix. Record the Proton version/path used by the smoke test.
`gyro_bridge/test.py` invokes the default `build.py` interface, so this also
guards compatibility between the two scripts.

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
git diff --exit-code
git diff --cached --exit-code
git status --porcelain=v1 --untracked-files=all
```

Only ignored files under `re-temp/` may have been created. There must be no
tracked diff after the deterministic rebuild. Hardware/gameplay claims still
require the real Steam client, supported Flower build, and physical-controller
checks described in `gyro_bridge/README.md`; do not turn the isolated smoke test
into a hardware-certification claim.

## Release packaging

Each independently tagged release contains only its applicable component ZIP,
its deterministic tag-derived source ZIP, and a final `SHA256SUMS` covering
exactly those two archives. Never combine both components in one output
directory or checksum manifest.

Run the hardened packager from the clean, detached checkout used for validation:

```text
python3 tools/build_release.py --component hay-bale|bridge \
  --ref <verified-tag> --output-dir <new-external-empty-dir>
```

The literal `--ref` must be the verified component tag and must resolve to the
currently checked-out `HEAD`. The packager must refuse a different ref, a dirty
checkout (including staged, unstaged, or untracked changes), and an output path
inside the checkout. `<new-external-empty-dir>` must be outside the checkout and
must either not exist or be an empty real directory; never reuse a prior release
directory.

Run only the command for the component being released:

```sh
python3 tools/build_release.py \
  --component hay-bale \
  --ref haybale-v1.0.0 \
  --output-dir <new-external-empty-dir>
```

or:

```sh
python3 tools/build_release.py \
  --component bridge \
  --ref gyro-bridge-v0.4.4 \
  --output-dir <new-external-empty-dir>
```

The result is only `flower-hay-bale-fix-1.0.0.zip` for the hay-bale tag or only
`flower-native-scepad-bridge-0.4.4.zip` for the bridge tag, plus the packager's
initial one-archive `SHA256SUMS`. Do not rename or post-process the component ZIP.

### `flower-hay-bale-fix-1.0.0.zip` exact standalone members

| Tracked source | ZIP member |
|---|---|
| `LICENSE` | `LICENSE` |
| `docs/HAY_BALE_RELEASE.md` | `README.md` |
| `flower_haybale_fix.py` | `flower_haybale_fix.py` |

### `flower-native-scepad-bridge-0.4.4.zip` exact standalone members

| Tracked source | ZIP member |
|---|---|
| `LICENSE` | `LICENSE` |
| `docs/BRIDGE_RELEASE.md` | `README.md` |
| `THIRD_PARTY_NOTICES.md` | `THIRD_PARTY_NOTICES.md` |
| `gyro_bridge/build.py` | `gyro_bridge/build.py` |
| `gyro_bridge/dist/libScePad.dll` | `gyro_bridge/dist/libScePad.dll` |
| `gyro_bridge/install_gyro_bridge.py` | `gyro_bridge/install_gyro_bridge.py` |
| `gyro_bridge/src/flower_scepad_bridge.cpp` | `gyro_bridge/src/flower_scepad_bridge.cpp` |
| `gyro_bridge/src/libScePad.def` | `gyro_bridge/src/libScePad.def` |
| `gyro_bridge/steam_input/game_actions_966330.vdf` | `gyro_bridge/steam_input/game_actions_966330.vdf` |
| `licenses/LLVM.txt` | `licenses/LLVM.txt` |
| `licenses/MINGW-W64-RUNTIME.txt` | `licenses/MINGW-W64-RUNTIME.txt` |

Each component-specific release guide is deliberately aliased to the package
root as `README.md`. The bridge retains its repository-relative `gyro_bridge/`
layout because the installer resolves its bundled DLL and manifest from those
paths. Native source and build inputs preserve binary provenance.
`THIRD_PARTY_NOTICES.md` and both license files are tracked, byte-exact release
inputs. Every unlisted member is forbidden.

### Exact deterministic source archives

Create exactly one source archive from the same verified tag, directly from Git
objects and into the component's external output directory. For the hay-bale
release, run from the clean checkout:

```sh
git archive --format=zip \
  --prefix=flower-hay-bale-fix-1.0.0-source/ \
  --output="<new-external-empty-dir>/flower-hay-bale-fix-1.0.0-source.zip" \
  haybale-v1.0.0
```

For the bridge release, run:

```sh
git archive --format=zip \
  --prefix=flower-native-scepad-bridge-0.4.4-source/ \
  --output="<new-external-empty-dir>/flower-native-scepad-bridge-0.4.4-source.zip" \
  gyro-bridge-v0.4.4
```

The fixed top-level prefixes and filenames are part of the release contract. Do
not use a branch, raw commit argument, copied checkout, staging tree, file-browser
archive, or working-directory ZIP as the source archive.

### No working-directory archives

Never run `zip -r` on `.`, the repository root, or any developer working
directory. `tools/build_release.py` is the sole component-package builder, and
`git archive` with the exact verified tag is the sole source-package builder.
Both must write only to `<new-external-empty-dir>` outside the checkout. `.git`,
`re-temp`, the toolchain, caches, test binaries, logs, and every unlisted file
must remain outside the component ZIP.

## Checksums and publication

The exact source command adds a second ZIP after the packager writes its initial
manifest. From inside `<new-external-empty-dir>`, replace that manifest with the
component's final two-archive manifest and verify it.

For the hay-bale release:

```sh
sha256sum \
  flower-hay-bale-fix-1.0.0.zip \
  flower-hay-bale-fix-1.0.0-source.zip \
  > SHA256SUMS
sha256sum --check --strict SHA256SUMS
```

For the bridge release:

```sh
sha256sum \
  flower-native-scepad-bridge-0.4.4.zip \
  flower-native-scepad-bridge-0.4.4-source.zip \
  > SHA256SUMS
sha256sum --check --strict SHA256SUMS
```

The final output directory and release upload must contain exactly the applicable
component ZIP, its source ZIP, and this final `SHA256SUMS`; no archive or checksum
for the other component belongs in that independently tagged release.

Upload those three files to a draft release for the matching component tag.
Release notes must include the full commit ID, release packager, pinned toolchain
identity, production DLL hash (for a bridge release), validation results, and
any manual-test limitations.

Finally, download the three draft assets into a new empty directory and run
`sha256sum --check --strict SHA256SUMS` there. Inspect the component ZIP against
its exact standalone member table and inspect the source ZIP for the exact fixed
prefix and tag contents. Confirm that no Valve, Sony, Flower/game, toolchain,
test, or working-directory binary slipped into either archive. Publish only
after that independent downloaded-asset verification passes.
