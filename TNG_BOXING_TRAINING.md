# TNG Boxing Game training modes

The game remains admin-only under `/#/tng-boxing-game`. No member access, game APIs, external AI services or account data changes are introduced.

- **Combination Lab** preserves the existing numbered sequences, custom combinations and timing windows.
- **Heavy Bag** scores contact at the punch's impact time. Straight punches reach farther than hooks and uppercuts; stepping inside matters.
- **Defense & Counters** telegraphs jabs, hooks, crosses and body shots. Successful defense opens a limited counter window. Slipping a hook and high-guarding a body shot do not count as correct defenses.
- **Footwork** calls working range, outside range and left/right pivots. The player must reach and briefly hold each position.
- **Sparring** adds partner attacks, a changing guard, distance pressure and simulated round condition for both boxers.

Punches consume stamina and require startup/recovery. Rapid repeated inputs cannot create extra contacts. Rest restores stamina. Training difficulty changes the telegraph and attack cadence. Round length and player stance remain configurable. The 3D arena adds a swinging heavy bag, positional movement, torso/guard changes, incoming attack cues and hit reactions. It is a training game, not a physical technique assessment.

Keyboard: 1–6 punches; A/D or left/right arrows slip; S/down rolls; Space/up high guard. In the simulation modes W steps in, Z steps out, Q/E pivot, and C guards the body. Standard controllers retain existing punch/defense controls and add right-stick footwork and left-stick click for body guard. On-screen controls work too. Controller edge logic is unit-tested; physical controller hardware was not available for verification.

P/Start pauses; Escape, tab hiding and browser blur pause automatically. Resume shifts attack, impact and round timers together, without granting recovery during the pause. Full screen and low-motion controls remain available; reduced-motion preferences disable animations. Sessions stay on this screen.

Validation covers impact timing, recovery/spam rejection, range, stamina, defense selection, counter windows, footwork goals, pause, round expiry, controller edges and existing combination behavior. Browser checks exercise keyboard play through all new modes, mobile layout and scene switching.

## 3D arena and phone controls

The default arena now uses WebGL 2 and a bundled CC0-derived rigged human model, with gloves, boots and athlete kits. Ring geometry, ropes, lighting, shadows, audience silhouettes and branded boards are rendered in 3D. Fighter guard, punches, slips, rolls, body guard and stance use a simplified skeleton with two-bone limb IK. This is a browser 3D beta rather than a motion-captured console simulation.

Ringside, Broadcast and Corner cameras are available; drag the ring to orbit. Auto, Battery saver, Balanced and High detail settings limit pixel ratio and frame rate. Auto uses the lighter pipeline on coarse-pointer phones, without the expensive reflection/shadow passes. Richer settings retain environmental reflections and soft shadows. Context/asset failures pause play and offer Reload arena; unmount disposes canvas, GPU resources and handlers.

Phone touch mode is selected automatically on narrow/coarse-pointer devices, and can also be toggled manually. A left pad handles movement/pivots (or defense in Combination Lab); right buttons provide punches and defense. Guard/body guard support holding. Multiple pointer capture, release, cancellation and pause clear held controls. Controls remain inside the arena in portrait and landscape. Full screen uses the browser API where available and a full-window overlay fallback otherwise; Exit restores page scrolling. Keyboard and standard controller play remain available. Sound is opt-in and uses local Web Audio for short impact/bell cues; it requires no microphone or external service.

The game remains admin-only. The 3D model is not a likeness of a saved fighter, and no customer/member records or gameplay results are sent to external providers. Source credits, licenses and rebuild commands are in `public/game/assets/ATTRIBUTION.md`.

## Browser ringside presentation update

The browser game remains the active implementation; no Unity installation, download, or AI credits are required. A fight-director camera tracks the action with a five-second manual orbit override, alongside the three fixed presets. The ring has darker spectator rows, illuminated ribbons and a larger canvas logo. Pro trunks and gym-vest kits are selectable. A broadcast score strip shows both corners' condition, stamina, round time and points. Contact can produce small sweat droplets and restrained camera movement; Effects off omits those effects. Sound remains opt-in, with synthesized bell partials, filtered glove noise and separate guard impacts.

Punch presentation now loads, reaches contact at the simulation's startup time, and returns to guard with separate straight/hook/uppercut paths. Opponent punches have per-attack identities and follow through after the game resolves contact, so repeating the same move animates again. Render frames interpolate between simulation snapshots so punch motion does not step at the UI refresh rate. Pause shifts the presentation timeline together with the simulation. Punches can follow a movement input immediately for two-thumb play; recovery still rejects repeat punches. A floating-point tolerance prevents stepping exactly to a punch's near-range boundary from incorrectly missing.

This is an original browser boxing prototype, not Fight Night or a claim of equivalent production quality. Character art, motion capture and physical-device profiling remain separate development work. All 79 frontend unit tests pass; software-rendered Chromium checks cover desktop scene loading and phone multi-touch, guard cancellation, pause, fullscreen fallback, portrait and landscape. Physical phone/controller performance has not been verified.
