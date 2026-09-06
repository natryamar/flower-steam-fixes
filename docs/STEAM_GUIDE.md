# Steam guide update

Existing guide: <https://steamcommunity.com/sharedfiles/filedetails/?id=3789842457>

## Saved copy — not part of the Steam guide

The guide body below is the user's edited text for release `v1.2.0`, saved as
provided. The title and description are retained from the previous draft.
Saving this file does not update the live Steam guide. Markdown headings and
backtick fences are not part of the text to paste into Steam.

## Guide title

```text
Unofficial Flower Steam Fixes — Audio + Native Steam Input
```

## Guide description

```text
I vibe-coded two independent, reversible fixes for Flower: a Level 4 hay-bale audio correction and native Steam Input controls with optional gyro steering. Download one ZIP, then click the install or revert script for the fix you want. Python 3.10+ required.
```

## Guide body

```bbcode
I vibe-coded some fixes for Flower.

This project contains two independent, reversible fixes:
[list]
[*][b]Hay-bale audio fix:[/b] Replaces an unrelated sound effect from one hay-bale activation in Level 4 with a suitable sound already present in the game.
[*][b]Steam Input bridge:[/b] Provides native PS4-style controls and optional gyro steering through Steam Input.
[/list]

No original game files are included—you need your own legitimate Steam copy. This project is unofficial and is not affiliated with the game's developers or publishers.


[h1]Download[/h1]
[url=https://github.com/natryamar/flower-steam-fixes/releases/tag/v1.2.0]Flower Steam Fixes — Release v1.2.0[/url]

For bundle 1.2.0, download:
[list]
[*][url=https://github.com/natryamar/flower-steam-fixes/releases/download/v1.2.0/flower-steam-fixes-1.2.0.zip]flower-steam-fixes-1.2.0.zip[/url] — both fixes, the ready-built bridge, instructions, and all Linux/Windows launchers.
[/list]

[h2]Before installing[/h2]
[list]
[*]Python 3.10 or newer is required and is not included. If needed, install it from [url=https://www.python.org/downloads/]python.org[/url].
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
With Python 3.10+ installed, open the extracted folder and double-click:
[list]
[*][b]INSTALL_HAY_BALE_WINDOWS.cmd[/b] — install the hay-bale audio fix.
[*][b]INSTALL_GYRO_BRIDGE_WINDOWS.cmd[/b] — install the Steam Input and gyro bridge.
[/list]

[h2]What you will see[/h2]
A successful installation prints:
[code]Success.[/code]
The window stays open so you can read the result. On Linux, press Enter to close it; on Windows, follow the “Press any key” prompt.

[b]Audio fix:[/b] No controller setup is needed.
[b]Steam Input bridge:[/b] Continue to the next section. Installing the files does not configure or select your Steam Input layout for you.

[h1]After installing the bridge[/h1]
[list]
[*]Fully exit and restart Steam.
[*]Enable Steam Input for Flower.
[*]Create or select a layout for [b]Flower Virtual PS4 Controller[/b].
[*]Bind your sticks, D-pad, face buttons, shoulders, and menu buttons to the matching actions.
[/list]

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

If verified local restoration is unavailable, Steam's [b]Verify integrity of game files[/b] can restore official game files. Stop the installer before verification and wait for Steam to finish. Verification can also replace other modified game files.

[h1]Source code[/h1]
[url=https://github.com/natryamar/flower-steam-fixes]Source code, full instructions, and troubleshooting[/url]

[h1]Optional support[/h1]
This project is free and open source. If it helped you and you would like to say thanks—or help pay for my ChatGPT subscription—you can optionally donate XMR:
[code]87dpgD3rcSY59Uja8wL7dW68eGEe8L7zdgUdauwgTnPcMMX4k1N6VYMAYgwtnrT4e5chGDYaBoT1LXrSQF1VXDMANNWZGWB[/code]
```
