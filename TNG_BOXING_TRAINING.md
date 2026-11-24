# TNG Boxing Game training modes

The game remains admin-only under `/#/tng-boxing-game`. No member access, game APIs, external AI services or account data changes are introduced.

- **Combination Lab** preserves the existing numbered sequences, custom combinations and timing windows.
- **Heavy Bag** scores contact at the punch's impact time. Straight punches reach farther than hooks and uppercuts; stepping inside matters.
- **Defense & Counters** telegraphs jabs, hooks, crosses and body shots. Successful defense opens a limited counter window. Slipping a hook and high-guarding a body shot do not count as correct defenses.
- **Footwork** calls working range, outside range and left/right pivots. The player must reach and briefly hold each position.
- **Sparring** adds partner attacks, a changing guard, distance pressure and simulated round condition for both boxers.

Punches consume stamina and require startup/recovery. Rapid repeated inputs cannot create extra contacts. Rest restores stamina. Training difficulty changes the telegraph and attack cadence. Round length and player stance remain configurable. The illustrated arena adds a swinging heavy bag, positional movement, torso/guard changes, incoming attack cues and hit reactions. It remains a lightweight 2D training game, not a physical technique assessment.

Keyboard: 1–6 punches; A/D or left/right arrows slip; S/down rolls; Space/up high guard. In the simulation modes W steps in, Z steps out, Q/E pivot, and C guards the body. Standard controllers retain existing punch/defense controls and add right-stick footwork and left-stick click for body guard. On-screen controls work too. Controller edge logic is unit-tested; physical controller hardware was not available for verification.

P/Start pauses; Escape, tab hiding and browser blur pause automatically. Resume shifts attack, impact and round timers together, without granting recovery during the pause. Full screen and low-motion controls remain available; reduced-motion preferences disable animations. Sessions stay on this screen.

Validation covers impact timing, recovery/spam rejection, range, stamina, defense selection, counter windows, footwork goals, pause, round expiry, controller edges and existing combination behavior. Browser checks exercise keyboard play through all new modes, mobile layout and scene switching.
