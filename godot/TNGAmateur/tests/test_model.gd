extends SceneTree
const Model = preload("res://scripts/fight_model.gd")
var failures: Array[String] = []
func check(ok: bool, message: String) -> void:
 if not ok:
  failures.append(message)
  push_error(message)
func fresh():
 var m = Model.new()
 m.ai_enabled = false
 m.start()
 return m
func advance(m, seconds: float) -> void:
 var left := seconds
 while left>0.00001:
  m.tick(minf(left,0.1))
  left-=minf(left,0.1)
func _initialize() -> void:
 var stage := 1
 for arg in OS.get_cmdline_user_args():
  if arg.begins_with("--stage="):
   stage = int(arg.trim_prefix("--stage="))
 var m = fresh()
 var original: Vector2 = m.player_position
 m.move_player(Vector2(1,0),0.2)
 check(m.player_position.distance_to(original)>0.2,"movement changes position")
 check(m.player_position.distance_to(original)<=0.311,"movement speed is bounded")
 for i in range(500):
  m.move_player(Vector2(1,-1),0.1)
 check(absf(m.player_position.x)<=2.65001 and absf(m.player_position.y)<=2.65001,"ring bounds hold")
 m.phase = Model.Phase.READY
 original = m.player_position
 m.move_player(Vector2.ONE,1)
 check(m.player_position==original,"cannot move before the fight")
 print("CHECKPOINT 1: movement and ring bounds checked")
 if stage>=2:
  m = fresh()
  m.player_position = Vector2(0,1)
  m.opponent_position = Vector2.ZERO
  check(m.punch(0),"jab accepted")
  check(m.player_stamina<100,"punch consumes stamina")
  check(m.opponent_health==100,"health unchanged before impact")
  check(not m.punch(1),"recovery blocks repeated punches")
  advance(m,0.1)
  check(m.opponent_health==100,"startup is respected")
  advance(m,0.1)
  check(m.opponent_health<100 and m.player_clean==1,"contact happens once at impact")
  var health: float = m.opponent_health
  advance(m,0.2)
  check(m.opponent_health==health,"same punch cannot score twice")
  m.player_stamina = 1
  check(not m.punch(5),"exhaustion blocks expensive punches")
  advance(m,2)
  check(m.player_stamina>20 and m.player_stamina<=100,"stamina recovers with rest")
  m = fresh()
  check(m.punch(2),"out-of-range hook can be thrown")
  advance(m,0.3)
  check(m.opponent_health==100 and m.player_clean==0,"out-of-range punch misses")
  check(not m.punch(-1) and not m.punch(6),"invalid punches rejected")
  print("CHECKPOINT 2: punches, timing, recovery, range and stamina checked")
 if stage>=3:
  m = fresh()
  m.ai_enabled = true
  m.player_position = Vector2(0,1)
  m.opponent_position = Vector2.ZERO
  m.next_attack = 0
  advance(m,0.9)
  check(m.player_health<100 and m.opponent_clean==1,"opponent attacks reduce health")
  m = fresh()
  m.ai_enabled = true
  m.player_position = Vector2(0,1)
  m.opponent_position = Vector2.ZERO
  m.guard_requested = true
  m.next_attack = 0
  advance(m,0.9)
  check(m.player_health==100 and m.opponent_clean==0,"guard prevents a clean contact")
  check(m.player_stamina<100,"guard has a stamina cost")
  m = fresh()
  m.ai_enabled = true
  m.player_position = Vector2(0,1)
  m.opponent_position = Vector2.ZERO
  m.next_attack = 0
  advance(m,0.6)
  check(m.slip(),"slip accepted")
  advance(m,0.3)
  check(m.player_health==100,"timed slip evades contact")
  m = fresh()
  m.ai_enabled = true
  m.player_position = Vector2(0,1)
  m.opponent_position = Vector2.ZERO
  m.player_health = 1
  m.next_attack = 0
  advance(m,0.9)
  check(m.phase==Model.Phase.FINISHED and m.winner=="PARTNER","zero health stops fight")
  check(m.player_health==0,"health is clamped at zero")
  print("CHECKPOINT 3: opponent, health, guard, slip and stoppage checked")
 if stage>=4:
  m = fresh()
  m.start(1,0.2)
  m.guard_requested = true
  m.toggle_pause()
  var time_before: float = m.time
  var clock_before: float = m.remaining
  advance(m,2)
  check(m.time==time_before and m.remaining==clock_before,"pause freezes all match time")
  check(not m.guard_requested,"pause releases held guard")
  m.toggle_pause()
  m.player_clean = 2
  advance(m,1.01)
  check(m.phase==Model.Phase.REST and m.round_number==2,"round one transitions to rest")
  check(m.scorecards.size()==1 and m.scorecards[0].you==10 and m.scorecards[0].partner==9,"round score is saved")
  m.toggle_pause()
  clock_before = m.remaining
  advance(m,1)
  check(m.remaining==clock_before,"rest clock also pauses")
  m.toggle_pause()
  advance(m,2.5)
  check(m.phase==Model.Phase.FINISHED and m.scorecards.size()==3,"fight ends after exactly three rounds")
  check(m.winner=="YOU","all round scorecards decide the winner")
  var cards: int = m.scorecards.size()
  advance(m,5)
  check(m.scorecards.size()==cards,"finished fight cannot append more rounds")
  m.start(120,60)
  check(m.scorecards.is_empty() and m.player_health==100 and m.round_number==1,"restart resets match state")
  print("CHECKPOINT 4: three rounds, rests, pause, scorecards and restart checked")
 if failures.is_empty():
  print("PASS stage %d" % stage)
  quit(0)
 else:
  print("FAIL: ",failures)
  quit(1)
