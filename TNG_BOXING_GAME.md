# TNG Boxing Game — Combination Lab

Open Gym & Members → TNG Boxing Game or TNGTrainer → Boxing Game as an administrator. The game is currently admin-only. Staff, fighters, managers and members have no navigation, portal launcher or trainer entry for it.

Start round and click the ring to focus. Keyboard: 1 jab, 2 cross, 3 lead hook, 4 rear hook, 5 lead uppercut, 6 rear uppercut; A/left arrow and D/right arrow slip, S/down arrow rolls, space/up arrow blocks. P pauses/resumes, Escape pauses, F requests browser fullscreen. Exiting or changing applications automatically pauses. Fullscreen support depends on the browser.

Standard-mapped USB/Bluetooth controllers: A/Cross = 1, B/Circle = 2, X/Square = 3, Y/Triangle = 4, LB/L1 = 5, RB/R1 = 6. LT/L2 slips left; RT/R2 slips right. Left-stick and D-pad left/right also slip; D-pad down rolls and up blocks. Start/Options pauses/resumes. Press a face button after connecting so the browser exposes the controller, then start the round. Standard gamepad API mapping is required; nonstandard controllers retain keyboard controls. Physical controller hardware must still be checked on the target device.

The first drill is 1, slip, 5, 2, 3, 2. Either direction satisfies “slip”; directional slips require the specified direction. Four other drills and a custom combination editor support 2–16 moves. Orthodox/southpaw identifies lead/rear hands; configurable rounds are 1–3 minutes and between-move windows are 2.2, 1.4 or 0.85 seconds. There is no deadline before the first move of each combination.

Correct moves earn 100 points; a complete combination adds 250. Wrong moves or an expired timing window reset the sequence. Accuracy counts valid discrete button attempts; timed-out sequences separately count as misses. Held keys/buttons and unreleased sticks do not auto-complete moves. Simultaneous controller actions are ignored. Pause preserves round and combo time. Animation, input and timer listeners are disposed when the screen closes. No API calls, messages or billing changes; round scores are session-only. This scores input sequence and timing, not physical technique.

## Arena graphics
The lightweight vector arena includes shaded fighters/equipment, crowd silhouettes, overhead trusses and lighting, a perspective canvas, punch trails and one-shot impact particles. Effects on / Low motion controls ambient and strike effects. The browser reduced-motion preference disables decorative motion automatically. No image downloads or new paid graphics services are required. Admin-only access remains unchanged.
