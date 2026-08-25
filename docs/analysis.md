# Flower Level 4 hay-bale sound analysis

This document records metadata and hashes, not copyrighted game code or audio.

## Affected build

- Steam app: `966330`
- Steam build ID: `4354278`
- `Flower.exe` SHA-256: `649b7b64db42146314ac0a0e55d5faf03194eba21ca9c791706ce827570d3aca`
- Original `Data/Sounds/Level4_A.bnk` SHA-256: `17e112eeed5f40baa14b9e1838c9373d3d3a84f394c1bef6a371599dcdc65728`
- `Data/Sounds/Level7_A.bnk` SHA-256: `274f93ee47b00dc621389409a55a16f5e159631ad2a6de61a1f3fe13e2ab5ccb`
- `Data/Sounds/LvlSfxLevel7_A.bnk.streams` SHA-256: `9bc961ca1409b570ba166b6486a0781888e2aea6f8555d48f1c6ee4888251608`

## Finding

The five Level 4 hay-bale completion triggers are correctly wired to five
`HayBailDone` emitters at the corresponding hay-bale coordinates. The defect is
inside the `HayBailDone` event in `Level4_A.bnk`.

The event uses a deterministic five-choice round-robin controller. Its choices
resolve to:

1. The streamed landing sting `20081018_landing_c_24.mp3`
2. Resident audio block 236
3. Resident audio block 237
4. Resident audio block 238
5. Resident audio block 239

The first entry is unrelated to the hay-bale sequence. The four resident entries
are used only by `HayBailDone`.

Level 7 contains a one-sample `HayBailDone` event. Its manifest identifies that
sample as `Level4-HayBale-Transform5-Rev2-Angles`, and its audio block is
byte-identical to Level 4 resident block 239. This independently verifies that
the resident entries are hay-bale transformation recordings and that the last
entry is Transform 5.

The installed game contains no standalone `Level4-HayBale-Transform*` files and
no separately addressable fifth resident hay sample. Restoring five distinct
recordings would therefore require obtaining the missing source from a lawful,
independent source and rebuilding or extending the bank.

## Confirmed fix

The conservative fix replaces only the bad stream grain reference with a
duplicate of the adjacent known-good resident hay grain reference.

- Patch offset: `0x1E18`
- Original 32-bit value: `0x2D016450`
- Patched 32-bit value: `0x0101651C`
- Original bytes: `50 64 01 2D`
- Patched bytes: `1C 65 01 01`
- Patched bank SHA-256: `c61b23587a8edd69b2201d918e8ee5a401f4f34ef272daa35b614f1d1f9c4012`

This changes the cycle from:

```text
landing sting, hay A, hay B, hay C, hay D
```

to:

```text
hay A, hay A, hay B, hay C, hay D
```

It does not change file size, audio payloads, Lua scripts, executable code, DRM,
or Steam integration.

## Gameplay validation

The patched bank was tested in the nighttime level on Steam build `4354278`
under SteamOS/Proton. All five hay-bale activations played appropriate
transformation sounds, and the unrelated landing sting no longer played.

## Relevant SBlk metadata

- Outer metadata offset: `0x20`
- SBlk version: `12`
- `HayBailDone` name record: `0x198D0`
- `HayBailDone` event record: `0x4F0`
- Round-robin grain list: `0x1E10`
- Bad stream grain reference: `0x1E18`
- First valid resident grain reference: `0x1E20`

The read-only inspector is available at `tools/sblk_inspect.py`.

## Reproduction

Inspect the two event definitions:

```sh
python3 tools/sblk_inspect.py "/path/to/Flower/Data/Sounds/Level4_A.bnk" --event HayBailDone --audio-neighbors 12
python3 tools/sblk_inspect.py "/path/to/Flower/Data/Sounds/Level7_A.bnk" --event HayBailDone --audio-neighbors 10
```

Level 4 block 239 is at file offset `0x1DA92A0`, size `0x3B5A0`.
Level 7's only `HayBailDone` block is at file offset `0x1123E20`, also size
`0x3B5A0`. Both blocks have SHA-256:

```text
d378eb681003e25882cf99d1dd63b25825d72c2df6d19a61acf44f85aa0b7db7
```

The Level 7 stream manifest contains only one hay dependency:
`Level4-HayBale-Transform5-Rev2-Angles.xvag`. No installed file under
`Data/Sounds/Streams` matches `*Hay*`, `*Bale*`, or `*Bail*`.
