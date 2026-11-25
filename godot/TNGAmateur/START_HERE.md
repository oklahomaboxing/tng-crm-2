# TNGOS Amateur Boxing — start here

A playable **Godot 4.6.3 Standard / GDScript** prototype. It is an original first-person training game, not a real boxing assessment or official USA Boxing scoring system. Three rounds are fixed; choose 2-minute rounds, 3-minute rounds, or quick practice (30-second rounds with 10-second rests). Regular formats have 60-second rests. Health reaching zero ends the match early as a training stoppage.

## Open and play — Windows beginner steps

1. Download the project ZIP and choose **Extract All** in Windows Downloads. Open the extracted folder containing this file and `project.godot`.
2. Download **Godot Standard for Windows** from https://godotengine.org/download/windows/ — use **4.6.3** to match the tested version. The Standard version uses GDScript; .NET/C# is unnecessary. Godot is free and needs no account or activation.
3. Extract Godot's ZIP and open the Godot application. In its project manager, choose **Import**, then select **`project.godot`**, and choose **Import & Edit**. Select the file, not just its folder. You do not use Unity Hub.
4. Let the fighter model import. Press **F5** (Run Project).
5. Choose **Quick practice** for your first test, then **START FIGHT**. Click the game window if the keys do not respond. Press **P** to pause; press **F8** to stop the game and return to the editor.

On Windows, this source project's import and keyboard behavior still need your device check. It has been imported, run, rendered and tested in Godot 4.6.3 on Linux using software OpenGL. Phone touch layout has been tested through the Godot interface, not on physical mobile hardware.

## Play without commands covering the screen

The desktop interface shows health, stamina, clock and a small menu. Combat buttons and the keyboard guide are hidden by default. Press **CONTROLS** to reveal the guide, then press it again to hide it.

| Key | Action |
| --- | --- |
| Arrow keys | Move forward/backward and circle left/right |
| 1 | Jab |
| 2 | Cross |
| 3 / 4 | Lead / rear hook |
| 5 / 6 | Lead / rear uppercut |
| Space | Hold guard; uses stamina |
| Q or E | Brief slip; time it against the incoming punch |
| P or Escape | Pause / resume |

WASD also moves. Lower your guard and stop punching briefly to recover stamina. Short punches need closer range. The partner walks into range, signals attacks, guards and attacks; there are no hidden real-person opponents or online accounts.

**TOUCH** reveals an optional movement pad and six punch/defense buttons. Touch controls also appear automatically when Godot reports a touchscreen. Multiple touches can move and punch together. **HIDE TOUCH** clears held inputs. A phone install or browser version requires a platform export; downloading this source ZIP does not install a phone app.

## Test one feature at a time

Do these checks in order. Stop if a check fails; use the first red message in Godot's **Debugger → Errors** when reporting it.

1. **Movement:** Start the fight. Use all four arrows. You should move inside the ropes and stay facing the partner. The ring boundary prevents walking out.
2. **Punches and stamina:** Press 1 once, then 2. Gloves should punch and return. Your gold stamina bar should drop and recover with rest. Repeated tapping cannot bypass punch recovery. Punching from too far away should miss.
3. **Health and defense:** Step into range. A clean punch should lower the partner's blue health bar. An undefended partner punch should lower your red health bar. Hold Space to guard, or time Q/E to slip. Guard consumes stamina; it is not unlimited protection.
4. **Three rounds:** Use Quick practice. At the bell, the fight enters a timed rest, then round 2, another rest, and round 3. Rest restores stamina and some health. The final screen lists each round's clean contacts and prototype 10/9 or 10/10 scores. If health reaches zero first, the fight stops early. This simplified score is **not official amateur judging**.
5. **Pause and restart:** Press P during a fight and during a rest. The clock and attack timing must freeze. Resume must preserve the remaining time. Restart returns to format selection with fresh match data.
6. **Clean UI and touch:** Combat commands should be absent on desktop. CONTROLS toggles help. TOUCH shows the pad/buttons. Try moving and punching together; release the pad and it should center. Hide touch again. Resize the window to portrait and landscape and check that buttons fit.

These six checkpoints have automated Godot checks too. From PowerShell in this project folder, set the path to your downloaded Godot program:

```powershell
$GodotEditor = 'C:\Your\Godot_v4.6.3-stable_win64.exe'
& $GodotEditor --headless --editor --path . --import --quit
& $GodotEditor --headless --path . --script res://tests/test_model.gd -- --stage=1
# Only continue after PASS stage 1:
& $GodotEditor --headless --path . --script res://tests/test_model.gd -- --stage=2
& $GodotEditor --headless --path . --script res://tests/test_model.gd -- --stage=3
& $GodotEditor --headless --path . --script res://tests/test_model.gd -- --stage=4
& $GodotEditor --headless --path . --script res://tests/test_ui.gd
& $GodotEditor --headless --path . --script res://tests/test_keyboard.gd
```

The model checks do not use a camera or graphics device. UI checks instantiate the actual game scene and check buttons, bars, multi-touch state, portrait/landscape bounds, result cards, help visibility and restart. Input checks send Godot arrow-key events and verify keys 1–6, pause and lost-focus handling.

## Where to change things

- `scripts/fight_model.gd`: health, stamina, punch costs, opponent and three-round state machine. Test this first before changing visuals.
- `scripts/main.gd`: ring, first-person camera, gloves, TNGOS branding, HUD and menus.
- `scripts/boxer_visual.gd`: licensed skinned opponent and procedural guard/punch poses.
- `scripts/touch_pad.gd`: optional joystick and touch release/reset behavior.
- `tests/`: checkpoint tests. The tests use short simulated rounds so you do not wait six or nine minutes.

To mute the simple synthesized bell/impact cues, select the main scene's TNGOSAmateur node in the editor and uncheck **Sound Enabled** in the Inspector. No external audio, microphone, AI subscription or API is used.

## Build and share later

The source project works with F5 without export templates. `export_presets.cfg` includes Windows and Web presets. To make a standalone Windows EXE or browser build, use **Project → Export → Manage Export Templates** and install the templates matching your Godot version, then export the selected preset. A Web build needs a WebGL 2-capable browser and HTTP hosting; a Windows executable should be tested on Windows before sharing. We have not built a Windows EXE, APK or Web/WASM release in this workspace: the platform export templates are not installed. The existing TNGOS browser game is separate and remains available.

A compiled **`.pck` game pack** was built and launched with Godot here. It is not an EXE: advanced users can run it using the matching Godot executable with `--main-pack TNGOSAmateur.pck`. Beginners should use the source project and F5 above.

All match data stays in memory and resets when the game closes. This prototype does not read or change TNGOS accounts, attendance, financial records or boxing records. The included generic opponent is derived from CC0 MakeHuman assets; licenses and source credits are in `assets/`.
