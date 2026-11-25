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

## First-person default

First person is now the default camera. It follows the player's eye position and faces the training partner (or the bag's contact area). The player's full world mesh is hidden in this view; a separate camera-space glove/forearm model renders after the arena, with straight/hook/uppercut motion driven by the same action IDs, progress and impact timing. This keeps the lens clear of the player's head and prevents the full-body gloves from enveloping the camera. First-person spacing uses the training distance rather than the compressed broadcast staging. The full body is restored when choosing a broadcast/orbit view.

Orbit controls are disabled in first person; no pointer lock, camera permission, mouse-look requirement or new phone gesture is introduced. Existing movement, defensive controls, controller support and touch inputs remain the same. Portrait uses a wider vertical lens; near clipping is limited to 2.5 cm. Effects off uses a stable eye position and removes impact shake. Camera switching, phone portrait/landscape, multi-touch, pause and fullscreen fallback are checked in Chromium; 82 frontend tests pass, including first-person glove framing, guard return, handedness, body guard and frozen visual time. Physical device performance remains unverified.

## Godot amateur prototype (separate project)

`godot/TNGAmateur/project.godot` is a playable Godot 4.6.3 Standard/GDScript prototype with a first-person ring, licensed skinned partner, both fighters' health/stamina, punches 1–6, arrow/WASD movement, guard, slip and three-round training matches with rests and prototype scorecards. Desktop combat commands are hidden; Controls opens help and Touch reveals the optional touchscreen pad/buttons. Beginner setup and ordered test checkpoints are in `godot/TNGAmateur/START_HERE.md`.

All six checkpoints passed directly in Godot, including actual GUI controls, key events, touch release and portrait/landscape bounds. A source ZIP was extracted into a fresh directory, reimported and retested. A compiled PCK pack was built, launched and rendered with the installed Godot engine. Neither a standalone Windows EXE nor a Web/WASM game was produced: matching export templates are not installed. Windows and physical phone testing remain outstanding. This source prototype does not replace the existing admin-only browser game or use TNGOS account/financial data. Public static downloads contain only project source/assets and a Godot resource pack, with a SHA-256 manifest.

## Browser amateur fights, targets and mitts

Unreal setup is paused. The browser game remains admin-only and now defaults to a three-round training fight. Arrows step/pivot, keys 1–6 punch, A/D slip, S rolls, Space guards, C covers the body, P pauses and F toggles fullscreen. Held movement and guards repeat only while active; pause, focus loss, round/rest transitions and touch cancellation clear held inputs. Keyboard help and Setup are collapsed initially, and the desktop punch-button grid is removed. Phones retain touch controls. Target and mitt drills show punch controls only.

The amateur wrapper reuses sparring mechanics, records one prototype 10/9 or 10/10 card per round from clean contacts, inserts timed rests and stops on zero health. Two-minute rounds with 60-second rests are the default. Quick practice uses 30-second rounds and 10-second rests; other lengths remain training options. Health carries between rounds with a 12-point capped recovery, stamina refills at the next bell, and a voluntary early end declares no winner. Scorecards are explicitly training scores, not official USA Boxing judging. Pause shifts both fight and rest clocks. Both fighters' stamina bars reflect actual simulated expenditure/recovery.

Incoming targets approach the first-person view and require the matching punch to land in the contact window. Early/wrong punches consume energy without awarding a hit; expired targets reduce training health. Mitt work follows numbered combinations with a completion bonus and a clear active mitt marker. The existing rigged trainer uses focus-mitt equipment; no new character likeness was introduced. These sessions stay in memory and do not change actual boxer records, event results, attendance or account data.

Uppercuts 5 and 6 use a distinct chamber → rising contact → guard path with an upward fist rotation, rather than the straight-punch trajectory. In target/mitt modes, the contact direction is projected from the active cue and captured for that punch, keeping the follow-through aimed at its original target. World-rig uppercuts also finish upward. Cue sides mirror for southpaw, and the player’s lead hand meets the trainer’s opposite mitt. Tests check the path and actual glove positions/rotations, in addition to scoring.

Validation: all 97 frontend tests pass, including three rounds/rests/decisions, early stoppage, no scores after the bell, pause clocks, enemy energy, target timing, mitt combinations and uppercut trajectories. Real-component Chromium checks cover hidden desktop commands, help, held arrows, fight/rest pauses, final scorecards, scored target/mitt hits, phone multi-touch, guard cancellation, portrait/landscape, fullscreen fallback and scroll restoration. GPU rendering and physical phone/controller performance still need testing on real hardware. The browser art remains a prototype and is not a MetaHuman/AAA replacement.

## Mobile play and training gym

Touch-sized screens enter a compact play view on Start. Native fullscreen is optional; the full-window fallback covers TNGOS navigation and restores it on exit. Setup opens a bottom sheet with fullscreen-contained selectors; punch/defense targets are at least 44px. Rotation pauses and releases inputs. Active play requests an optional screen wake lock and releases it during pause/rest/end. Unsupported browsers continue normally.

The default fictional training gym has a ring, clear walkway, bag lane, warm-up mat, benches, windows and overhead lighting. Setup offers Gym overview and the existing cameras; Fight-night arena remains selectable. Geometry is shared/instanced where appropriate and battery saver omits expensive passes. This is a game environment, not a surveyed layout of the physical gym.

For a home-screen shortcut, open TNGOS in Safari and choose Share → Add to Home Screen, or use the Android browser's Install/Add to Home Screen command when available. Sign in as an administrator and open the boxing game. The root standalone manifest preserves the normal account entry; it does not add offline access or a native APK.

Validation: 101 frontend tests, production build, and Chromium checks of portrait/landscape play, multi-touch scoring, setup selectors, three-round results, wake-lock lifecycle, rotation, environment switching and the real AppShell fullscreen fallback. No browser console errors occurred. Physical Android/iPhone GPU and installation behavior still require device testing.

## Opposite-hand mitt catching and swipe punches

The trainer presents the anatomical opposite hand for each punch in both stances: trainer right catches player left, trainer left catches player right. Only the active mitt is extended; straight pads face the player, hook pads angle outward into the punch, and uppercut pads face downward. Contact points now come from the padded face's actual transform. The trainer updates before glove targeting, and the caught mitt holds through recovery before the next cue is presented. Each pending punch is bound to its original target ID to prevent credit against a replacement cue. Mitt response windows are 3.2/2.4/1.8 seconds for Learn/Flow/Fast.

In first-person view, touch the unobstructed scene: tap for a straight, swipe sideways for a hook, swipe upward for an uppercut. The starting screen half selects the anatomical left/right hand, and punch numbering mirrors for southpaw. Downward/diagonal swipes, long holds, canceled touches, mouse events, paused play and other camera modes do not throw swipe punches. Buttons and keyboard remain available. Swipes use the existing stamina, recovery and combination resolver, with no extra scoring path.

Validation: 108 frontend tests include actual rig pad positions/normals, both stances, target identity/recovery, gesture classification and pointer cancellation. Chromium phone touch tests completed a jab–cross mitt combination for 450 points and exercised hook/uppercut swipes without console errors. Physical touch devices still require performance testing.
