class_name FightModel
extends RefCounted
# Pure match logic: no rendering, accounts, network, or external services.
enum Phase {READY, FIGHT, REST, FINISHED}
const TOTAL_ROUNDS := 3
const PUNCHES := [
 {"name":"Jab", "cost":7.0,"damage":6.0,"startup":0.13,"recovery":0.38,"reach":1.95},
 {"name":"Cross","cost":11.0,"damage":9.0,"startup":0.19,"recovery":0.50,"reach":1.85},
 {"name":"Lead hook","cost":14.0,"damage":11.0,"startup":0.22,"recovery":0.58,"reach":1.35},
 {"name":"Rear hook","cost":15.0,"damage":12.0,"startup":0.25,"recovery":0.62,"reach":1.35},
 {"name":"Lead upper","cost":14.0,"damage":10.0,"startup":0.22,"recovery":0.58,"reach":1.15},
 {"name":"Rear upper","cost":16.0,"damage":12.0,"startup":0.26,"recovery":0.65,"reach":1.15}]
var phase := Phase.READY
var paused := false
var round_number := 1
var round_seconds := 120.0
var rest_seconds := 60.0
var remaining := 120.0
var time := 0.0
var player_health := 100.0
var opponent_health := 100.0
var player_stamina := 100.0
var opponent_stamina := 100.0
var player_position := Vector2(0,1.7)
var opponent_position := Vector2(0,-0.5)
var player_guard := false
var guard_requested := false
var player_slip_until := 0.0
var player_ready_at := 0.0
var opponent_ready_at := 0.0
var player_last_effort := -100.0
var opponent_last_effort := -100.0
var player_action := -1
var player_action_at := -100.0
var opponent_action := -1
var opponent_action_at := -100.0
var pending_player: Dictionary = {}
var pending_opponent: Dictionary = {}
var next_attack := 1.8
var attack_index := 0
var player_clean := 0
var opponent_clean := 0
var scorecards: Array[Dictionary] = []
var winner := ""
var finish_reason := ""
var feedback := "Choose a format, then Start fight."
var event_id := 0
var event_type := ""
var player_hit_until := 0.0
var opponent_hit_until := 0.0
var ai_enabled := true
var opponent_guard := false

func start(seconds: float = 120.0, rest: float = 60.0) -> void:
 round_seconds = clampf(seconds,1.0,180.0)
 rest_seconds = clampf(rest,0.1,60.0)
 phase = Phase.FIGHT
 paused = false
 round_number = 1
 remaining = round_seconds
 time = 0
 player_health = 100
 opponent_health = 100
 player_stamina = 100
 opponent_stamina = 100
 player_position = Vector2(0,1.7)
 opponent_position = Vector2(0,-0.5)
 player_ready_at = 0
 opponent_ready_at = 0
 player_last_effort = -100
 opponent_last_effort = -100
 player_action_at = -100
 opponent_action_at = -100
 player_slip_until = 0
 player_hit_until = 0
 opponent_hit_until = 0
 player_action = -1
 opponent_action = -1
 guard_requested = false
 player_guard = false
 opponent_guard = false
 pending_player = {}
 pending_opponent = {}
 next_attack = 1.8
 attack_index = 0
 player_clean = 0
 opponent_clean = 0
 scorecards.clear()
 winner = ""
 finish_reason = ""
 emit_event("bell","Round 1. Box!")

func emit_event(kind: String, text: String) -> void:
 event_id += 1
 event_type = kind
 feedback = text

func toggle_pause() -> void:
 if phase == Phase.FIGHT or phase == Phase.REST:
  paused = not paused
  guard_requested = false
  player_guard = false

func distance() -> float:
 return player_position.distance_to(opponent_position)

func move_player(input: Vector2, delta: float) -> void:
 if phase != Phase.FIGHT or paused:
  return
 var forward := (opponent_position-player_position).normalized()
 var right := Vector2(-forward.y,forward.x)
 var proposed := player_position + (right*input.x+forward*input.y).limit_length(1.0)*delta*1.55
 proposed = proposed.clamp(Vector2(-2.65,-2.65),Vector2(2.65,2.65))
 if proposed.distance_to(opponent_position) >= 0.85:
  player_position = proposed

func slip() -> bool:
 if phase != Phase.FIGHT or paused or player_stamina < 5 or not pending_player.is_empty():
  return false
 player_stamina -= 5
 player_last_effort = time
 player_slip_until = time+0.38
 return true

func punch(index: int) -> bool:
 if index < 0 or index >= PUNCHES.size() or phase != Phase.FIGHT or paused or time < player_ready_at:
  return false
 var stats: Dictionary = PUNCHES[index]
 if player_stamina < stats.cost:
  feedback = "Low stamina. Lower your guard and recover."
  return false
 var fatigue := 1.0+(100.0-player_stamina)/160.0
 player_stamina -= stats.cost
 player_last_effort = time
 player_ready_at = time+stats.recovery*fatigue
 player_action = index
 player_action_at = time
 pending_player = {"index":index,"impact":time+stats.startup*fatigue}
 player_guard = false
 return true

func tick(delta: float) -> void:
 if paused or phase == Phase.READY or phase == Phase.FINISHED:
  return
 # Fixed-size substeps keep impacts deterministic after a slow render frame.
 var left := clampf(delta,0.0,0.5)
 while left > 0.00001 and phase != Phase.FINISHED:
  var step := minf(left,1.0/120.0)
  _step(step)
  left -= step

func _step(delta: float) -> void:
 time += delta
 remaining = maxf(0.0,remaining-delta)
 if phase == Phase.REST:
  if remaining <= 0.00001:
   phase = Phase.FIGHT
   remaining = round_seconds
   player_stamina = 100
   opponent_stamina = 100
   player_health = minf(100,player_health+12)
   opponent_health = minf(100,opponent_health+12)
   next_attack = time+1.1
   emit_event("bell","Round %d. Box!" % round_number)
  return
 # Bell takes precedence over impacts; no late punches after the round.
 if remaining <= 0.00001:
  _end_round()
  return
 player_guard = guard_requested and player_stamina > 2 and pending_player.is_empty() and time >= player_ready_at
 if player_guard:
  player_stamina = maxf(0,player_stamina-delta*7)
 elif time-player_last_effort > 0.55:
  player_stamina = minf(100,player_stamina+delta*17)
 if time-opponent_last_effort > 0.7:
  opponent_stamina = minf(100,opponent_stamina+delta*14)
 opponent_guard = ai_enabled and pending_opponent.is_empty() and fmod(time,4.0)>2.4 and opponent_stamina>15
 if not pending_player.is_empty() and time >= pending_player.impact:
  var stats: Dictionary = PUNCHES[pending_player.index]
  pending_player = {}
  if distance() > stats.reach:
   emit_event("miss","Out of range. Step in behind your jab.")
  elif opponent_guard:
   opponent_stamina = maxf(0,opponent_stamina-5)
   emit_event("block","Partner caught it. Find an opening.")
  else:
   opponent_health = maxf(0,opponent_health-stats.damage)
   player_clean += 1
   opponent_hit_until = time+0.2
   emit_event("landed","Clean contact. Return to your guard.")
 if ai_enabled:
  _enemy_step(delta)
 if player_health <= 0 or opponent_health <= 0:
  _finish("PARTNER" if player_health <= 0 else "YOU","Training stoppage")

func _enemy_step(delta: float) -> void:
 if distance() > 1.65 and pending_opponent.is_empty():
  opponent_position = opponent_position.move_toward(player_position,delta*0.48)
 if time >= next_attack and pending_opponent.is_empty() and time >= opponent_ready_at:
  var choices := [0,1,2,0,1,3]
  var index: int = choices[attack_index % choices.size()]
  var stats: Dictionary = PUNCHES[index]
  attack_index += 1
  next_attack = time+1.9
  if opponent_stamina >= stats.cost:
   opponent_stamina -= stats.cost
   opponent_last_effort = time
   pending_opponent = {"index":index,"windup":time+0.55,"impact":time+0.75}
   feedback = "%s incoming — guard or slip." % stats.name.to_upper()
 if not pending_opponent.is_empty():
  if time >= pending_opponent.windup and opponent_action_at < pending_opponent.windup:
   opponent_action = pending_opponent.index
   opponent_action_at = pending_opponent.windup
  if time >= pending_opponent.impact:
   var stats: Dictionary = PUNCHES[pending_opponent.index]
   pending_opponent = {}
   opponent_ready_at = time+0.55
   if distance() > stats.reach or time < player_slip_until:
    emit_event("defended","Good defense. Counter now!")
   elif player_guard and player_stamina > 2:
    player_stamina = maxf(0,player_stamina-8)
    emit_event("block","Guard held. Watch your stamina.")
   else:
    player_health = maxf(0,player_health-stats.damage)
    opponent_clean += 1
    player_hit_until = time+0.2
    emit_event("caught","Caught! Guard, slip or move out of range.")

func _save_scorecard() -> void:
 scorecards.append({"round":round_number,"you_hits":player_clean,"partner_hits":opponent_clean,"you":10 if player_clean>=opponent_clean else 9,"partner":10 if opponent_clean>=player_clean else 9})
 player_clean = 0
 opponent_clean = 0

func _end_round() -> void:
 _save_scorecard()
 pending_player = {}
 pending_opponent = {}
 player_action = -1
 opponent_action = -1
 guard_requested = false
 player_guard = false
 if round_number == TOTAL_ROUNDS:
  var you := 0
  var partner := 0
  for card in scorecards:
   you += card.you
   partner += card.partner
  _finish("YOU" if you>partner else "PARTNER" if partner>you else "DRAW","Prototype points decision")
 else:
  round_number += 1
  phase = Phase.REST
  remaining = rest_seconds
  emit_event("bell","In your corner. Next: round %d." % round_number)

func _finish(result: String, reason: String) -> void:
 if scorecards.size()<round_number:
  _save_scorecard()
 phase = Phase.FINISHED
 winner = result
 finish_reason = reason
 pending_player = {}
 pending_opponent = {}
 guard_requested = false
 player_guard = false
 emit_event("bell","%s — %s" % [result,reason])
