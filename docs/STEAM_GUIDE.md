# Steam guide update

Existing guide: <https://steamcommunity.com/sharedfiles/filedetails/?id=3789842457>

## Publication note — not part of the Steam guide

This copy/paste text targets release `v1.2.0`, dated `2026-09-06`, and its click
launchers. This text does not update Steam; applying it in the Steam guide editor
is a separate manual action. Confirm release publication and downloaded-asset
verification before updating the live guide; see [`RELEASING.md`](../RELEASING.md).

The text below preserves the existing title, four section names, AI-development
disclosure, controller setup, and optional donation details. Each fenced block
is the content for the corresponding Steam editor field. The Markdown headings,
backtick fences, and this publication note are not part of the guide.

## Guide title

```text
Unofficial Flower Steam Fixes — Audio + Native Steam Input
```

## Guide description

```text
I vibe-coded two independent, reversible fixes for Flower: a Level 4 hay-bale audio correction and native Steam Input controls with optional gyro steering. Download one ZIP, then click the install or revert script for the fix you want. Python 3.10+ required.
```

## Section: What Is This?

```bbcode
I vibe-coded some fixes for Flower.

This project contains two independent, reversible fixes:
[list]
[*][b]Hay-bale audio fix:[/b] Replaces an unrelated sound effect from one hay-bale activation in Level 4 with a suitable sound already present in the game.
[*][b]Steam Input bridge:[/b] Provides native PS4-style controls and optional gyro steering through Steam Input.
[/list]

[b]One download, your choice.[/b] Both fixes are in the same ZIP. Install either one or both, and revert them independently whenever you want. Installing the audio fix does not install the controller bridge.

[b]Versions:[/b] Bundle 1.2.0 includes hay-bale installer 1.0.1 and bridge component/installer 0.4.5. The native bridge DLL and action manifest remain unchanged 0.4.4 artifacts with the same exact hashes.

[b]Supported game:[/b] Flower on Steam, App ID 966330, build 4354278. The installers deliberately refuse unknown or modified files.

Previous gameplay testing was on SteamOS/Proton; gyro testing included an 8BitDo controller. That is not broad controller certification, and the new launcher bundle does not imply a new gameplay validation pass. [b]Native Windows use is currently unverified.[/b]

No original game files are included—you need your own legitimate Steam copy. This project is unofficial and is not affiliated with the game's developers or publishers.
```

## Section: Download and Install

```bbcode
[h1]Download once[/h1]
[url=https://github.com/natryamar/flower-steam-fixes/releases/tag/v1.2.0]Flower Steam Fixes — Release v1.2.0[/url]

For bundle 1.2.0, download:
[list]
[*][url=https://github.com/natryamar/flower-steam-fixes/releases/download/v1.2.0/flower-steam-fixes-1.2.0.zip]flower-steam-fixes-1.2.0.zip[/url] — both fixes, the ready-built bridge, instructions, and all Linux/Windows launchers.
[*][url=https://github.com/natryamar/flower-steam-fixes/releases/download/v1.2.0/SHA256SUMS]SHA256SUMS[/url] — the checksum file from the same release.
[/list]

Do not choose GitHub's automatic “Source code” downloads for the click-to-run bundle. You do not need a compiler or a separate ZIP for each fix.

[h2]Before installing[/h2]
[list]
[*]Python 3.10 or newer is required and is not included. If needed, install it from [url=https://www.python.org/downloads/]python.org[/url].
[*]Verify the ZIP against SHA256SUMS before running anything; commands are provided below.
[*]Extract the entire ZIP into its own folder. Do not run scripts from inside an archive preview, and keep the extracted files and folders together.
[*]Close Flower and make sure Steam is not updating or verifying the game.
[/list]

[h1]Steam Deck / Linux[/h1]
On Steam Deck, switch to Desktop Mode first. Open the extracted folder and double-click the script for the fix you want:
[list]
[*][b]INSTALL_HAY_BALE_LINUX.sh[/b] — install the hay-bale audio fix.
[*][b]INSTALL_GYRO_BRIDGE_LINUX.sh[/b] — install the Steam Input and gyro bridge.
[/list]

Choose [b]Run[/b] or [b]Execute in Terminal[/b] if your file manager asks. If a script opens as text or is not executable, open its Properties → Permissions and enable execution, then choose the run option. The exact labels depend on your desktop.

[h1]Windows[/h1]
Native Windows execution is unverified. With Python 3.10+ installed, open the extracted folder and double-click:
[list]
[*][b]INSTALL_HAY_BALE_WINDOWS.cmd[/b] — install the hay-bale audio fix.
[*][b]INSTALL_GYRO_BRIDGE_WINDOWS.cmd[/b] — install the Steam Input and gyro bridge.
[/list]

[h2]What you will see[/h2]
A successful installation prints:
[code]Success.[/code]
The window stays open so you can read the result. On Linux, press Enter to close it; on Windows, follow the “Press any key” prompt.

The launchers run the same verified installers. File checks and verified backups are still required; a shorter message does not mean fewer safety checks. If an installer reports [b]unsupported[/b], [b]unsafe[/b], or another error, stop and read it—do not bypass the check.

[b]Audio fix:[/b] No controller setup is needed.
[b]Steam Input bridge:[/b] Continue to the next section. Installing the files does not configure or select your Steam Input layout for you.

For nonstandard Steam-library paths or terminal commands, see the included README.md, HAY_BALE_FIX.md, and GYRO_BRIDGE.md, or the [url=https://github.com/natryamar/flower-steam-fixes]GitHub documentation[/url].

[h2]Verify the download[/h2]
Put the ZIP and SHA256SUMS in the same folder.

On Linux, open a terminal in that folder and run:
[code]sha256sum --check --strict SHA256SUMS[/code]
It should report the bundle ZIP as OK. Do not run the bundle if verification fails.

On Windows, open PowerShell in that folder and run:
[code]Get-FileHash .\flower-steam-fixes-1.2.0.zip -Algorithm SHA256[/code]
Open SHA256SUMS in a text editor and compare the full hash with the entry for that ZIP. Letter case does not matter, but every hexadecimal digit must match.
```

## Section: Steam Input and Gyro Setup

```bbcode
[h1]After installing the bridge[/h1]
[list]
[*]Fully exit and restart Steam.
[*]Enable Steam Input for Flower.
[*]Create or select a layout for [b]Flower Virtual PS4 Controller[/b].
[*]Bind your sticks, D-pad, face buttons, shoulders, and menu buttons to the matching actions.
[/list]

The installer does not create, select, or overwrite your account-owned controller layouts. It cannot publish or automatically select an Official/Recommended layout without the game's publisher access.

[h1]Tell Flower which input should steer[/h1]
The bridge supplies native controller and tilt data, but Flower still uses its own [b]PadDualShock[/b] setting to choose stick or tilt steering. The installer leaves this setting unchanged.

With Flower closed, open [b]Flower.cfg[/b]. On Windows, its usual location is:
[code]%USERPROFILE%\Documents\Flower\Flower.cfg[/code]
If Windows redirects your Documents folder, look in that Documents folder instead.

On Steam Deck/Linux, the usual default-library Proton location is:
[code]~/.local/share/Steam/steamapps/compatdata/966330/pfx/drive_c/users/steamuser/Documents/Flower/Flower.cfg[/code]
If Flower is in another Steam library, look under that library's steamapps/compatdata/966330/pfx folder. If the file is missing, launch and close Flower once so the game can create it.

Find the existing PadDualShock setting and change its value. [b]Do not add a second duplicate setting.[/b]

For left-stick steering:
[code]PadDualShock="AnalogueLeft"[/code]
For right-stick steering:
[code]PadDualShock="AnalogueRight"[/code]
For gyro steering:
[code]PadDualShock="TiltControl"[/code]

[h1]Recommended gyro settings[/h1]
Set [b]Gyro Behavior[/b] to [b]Controller Tilt[/b], targeting the tilt action (flower_ps4/tilt):
[list]
[*]Activation: Always On.
[*]Use Relative Pitch: Off.
[*]Use Relative Roll: Off.
[*]Response curve: Linear.
[*]Minimum/maximum deflection: 0° / 45°.
[*]Minimum/maximum output: 0% / 100%.
[*]Lock at Edges: Off.
[*]Drag Center Point: Off.
[*]Horizontal/vertical inversion: Off initially; only change a sign after testing all four directions.
[/list]

[b]Keep both relative axes off.[/b] Start World Tilt Offset / neutral angle at 0°, then adjust it to your comfortable holding angle so holding the controller still produces neutral output.

Run Steam's manual gyro calibration with the controller motionless on a stable surface before adjusting deadzones.

Steam's two deadzone/ramp handles do different jobs:
[list]
[*][b]Left handle:[/b] The no-output boundary and start of the ramp. Raise it only slightly to suppress drift; about 2–5% is a starting point, not a universal setting.
[*][b]Right handle:[/b] The end of the ramp and start of full output. Set it so full output is reached at about 45° of physical tilt. If Steam shows a 90° range, 45° is 50%—do not blindly set this handle to 100%.
[/list]

Steam's “Controller Preferred” deadzone settings were not ideal with my 8BitDo controller, so manual adjustment may feel better. Controller and Steam-client combinations vary.
```

## Section: Restoration and Source Code

```bbcode
[h1]Revert only what you want[/h1]
Close Flower and make sure Steam is not updating or verifying it. Open the same extracted bundle folder.

[h2]Steam Deck / Linux[/h2]
[list]
[*][b]REVERT_HAY_BALE_LINUX.sh[/b] — revert the audio fix.
[*][b]REVERT_GYRO_BRIDGE_LINUX.sh[/b] — revert the controller bridge and remove its managed action manifest.
[/list]

[h2]Windows[/h2]
[list]
[*][b]REVERT_HAY_BALE_WINDOWS.cmd[/b] — revert the audio fix.
[*][b]REVERT_GYRO_BRIDGE_WINDOWS.cmd[/b] — revert the controller bridge and remove its managed action manifest.
[/list]

A successful revert prints:
[code]Fix reverted.[/code]

[b]Fully exit and restart Steam after reverting the bridge.[/b] Reverting either fix does not revert the other. Bridge restoration leaves Flower.cfg and your account-owned controller layouts unchanged.

[h2]If something goes wrong[/h2]
Read the error and stop rather than forcing a restore. Errors or interruptions can leave partial state, so keep the verified backups and follow the [url=https://github.com/natryamar/flower-steam-fixes/blob/main/docs/TROUBLESHOOTING.md]troubleshooting and safe-recovery instructions[/url].

For detailed read-only information, open a terminal in the extracted bundle folder and run the relevant status command:
[code]python3 flower_haybale_fix.py status
python3 gyro_bridge/install_gyro_bridge.py status[/code]
On Windows, use PowerShell and replace python3 with py -3.

If verified local restoration is unavailable, Steam's [b]Verify integrity of game files[/b] can restore official game files. Stop the installer before verification and wait for Steam to finish. Verification can also replace other modified game files. For the bridge, follow the recovery guide and retry restoration afterward if needed to remove its exact managed manifest.

When asking for help, share only the relevant error or redacted status text. Do not upload game files, controller profiles, or full logs; remove personal paths and account/device identifiers.

[h1]Source code[/h1]
[url=https://github.com/natryamar/flower-steam-fixes]Source code, full instructions, and troubleshooting[/url]

[h1]Optional support[/h1]
This project is free and open source. If it helped you and you would like to say thanks—or help pay for my AI subscription—you can optionally donate XMR:
[code]87dpgD3rcSY59Uja8wL7dW68eGEe8L7zdgUdauwgTnPcMMX4k1N6VYMAYgwtnrT4e5chGDYaBoT1LXrSQF1VXDMANNWZGWB[/code]
Before sending anything, verify the address against the canonical GitHub repository. Donations are optional and do not purchase support, features, or faster updates.
```
