# TNGOS Godot amateur boxing prototype

Open `TNGAmateur/project.godot` using Godot 4.6.3 Standard. Beginner setup, controls, checkpoint tests and export limitations are in [START_HERE.md](TNGAmateur/START_HERE.md).

The current TNGOS browser game is retained. This source prototype is first-person, keyboard-first (arrow movement and punches 1–6), has health/stamina for both boxers, an opponent, three-round fights/rests, prototype scorecards, pause/restart and optional touchscreen controls. The desktop HUD hides combat commands by default. Each model checkpoint was run successfully before UI integration; actual scene/UI and key-event checks were then run. It was also rendered in Godot using a private software-OpenGL display and inspected visually.

`build_download.py` packages the source project reproducibly into the frontend's static downloads. Run after the Godot checkpoint tests; the `.godot` cache, editor state and exports are excluded. Platform-specific EXE/Web/APK export templates are not installed here. A Godot PCK resource build is available separately and has been run with the installed engine.

Downloads after the frontend deployment:

- Source ZIP: https://tngos.tngboxinggym.com/downloads/TNGOS-Godot-Amateur-Prototype.zip
- Godot game resource pack (requires Godot): https://tngos.tngboxinggym.com/downloads/TNGOS-Amateur-Boxing.pck
- File sizes/checksums: https://tngos.tngboxinggym.com/downloads/tngos-godot-manifest.json
