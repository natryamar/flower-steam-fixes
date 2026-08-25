# Third-party notices

This notice applies to binary distributions containing the independently built
`gyro_bridge/dist/libScePad.dll`. The project's own source and documentation are
licensed under the repository's `LICENSE` file.

## Pinned binary provenance

The production DLL with SHA-256
`adca347f5f51c88907e0915b7920436a0dae96aa6ca621ece807bcd96b648f6c` is
reproduced with the following toolchain:

- llvm-mingw release: `20260616`
- Archive: `llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz`
- Archive URL:
  <https://github.com/mstorsjo/llvm-mingw/releases/download/20260616/llvm-mingw-20260616-ucrt-ubuntu-22.04-x86_64.tar.xz>
- Archive SHA-256:
  `534b92e067b22a6b4441f48ae9240a3341b17825d04d577eab0cf85c44b4deda`
- Compiler: Clang `22.1.8`, LLVM revision
  `ca7933e47d3a3451d81e72ac174dcb5aa28b59d1`
- Target: `x86_64-w64-windows-gnu` using the UCRT configuration

The toolchain archive and compiler/linker executables are build inputs and are
not bundled in a project release.

## Portions incorporated into the project DLL

### LLVM Project runtime portions

Clang and LLD produce the DLL. The link uses LLVM runtime archives, including
`compiler-rt` builtins, and can embed only the runtime objects needed by this
DLL. LLVM `libc++` and `libunwind` are also link inputs; any selected portions
are covered by the same LLVM Project notices. Clang and LLD themselves are not
part of the distributed DLL.

LLVM Project material is provided under the Apache License 2.0 with LLVM
Exceptions, with legacy notices where applicable. The exact license text copied
from the pinned toolchain's `LICENSE.TXT` is in [`licenses/LLVM.txt`](licenses/LLVM.txt)
(SHA-256
`8d85c1057d742e597985c7d4e6320b015a9139385cff4cbae06ffc0ebe89afee`).

### MinGW-w64 runtime portions

The DLL statically links required MinGW-w64 CRT startup and runtime portions and
uses MinGW-w64 Windows import libraries. These portions come from the exact
MinGW-w64 content carried by the pinned llvm-mingw archive.

The complete runtime notices copied from the pinned toolchain's
`x86_64-w64-mingw32/share/mingw32/COPYING.MinGW-w64-runtime.txt` are in
[`licenses/MINGW-W64-RUNTIME.txt`](licenses/MINGW-W64-RUNTIME.txt) (SHA-256
`1db8da07b436c68833c0673ffee3d9fcb2526047f3820b81661865dfedc79a1f`).
Those notices include the terms for the MinGW-w64 runtime and identified
third-party runtime portions.

Any binary package containing `libScePad.dll` must include this notice and both
license files above.

## Dynamically supplied Windows libraries

The production DLL's PE import table names the following libraries:

- `api-ms-win-crt-string-l1-1-0.dll`
- `api-ms-win-crt-runtime-l1-1-0.dll`
- `api-ms-win-crt-math-l1-1-0.dll`
- `api-ms-win-crt-private-l1-1-0.dll`
- `api-ms-win-crt-stdio-l1-1-0.dll`
- `api-ms-win-crt-heap-l1-1-0.dll`
- `KERNEL32.dll`

These UCRT API-set and Windows system libraries are dynamically supplied by the
user's Windows installation or compatible runtime environment. They are not
copied into, statically embedded in, or redistributed with the project release.

## Valve, Sony, and Flower/game binaries

The distributed project `libScePad.dll` is an independently implemented bridge;
it is not a copy or modification of Flower's original library. At runtime it can
load the user's sibling `libScePad_original.dll` and Flower's `steam_api64.dll`
for compatibility and fallback behavior. Those files must come from the user's
legitimate game installation and are not bundled by this project.

In particular, project releases contain:

- no Valve or Steamworks binary;
- no Sony binary or SDK; and
- no original Flower executable or DLL, or any other game binary or asset.

API and product names are used only to describe interoperability. This project
is unofficial and is not endorsed by or affiliated with Valve, Sony,
thatgamecompany, Annapurna Interactive, or the game's developers or publishers.
