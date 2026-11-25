extends SceneTree
var failures: Array[String] = []
func check(ok: bool,message: String) -> void:
 if not ok:
  failures.append(message)
  push_error(message)
func key(code: int,pressed: bool) -> InputEventKey:
 var event := InputEventKey.new()
 event.keycode=code
 event.physical_keycode=code
 event.pressed=pressed
 return event
func _initialize() -> void:
 call_deferred("run")
func run() -> void:
 var game=load("res://main.tscn").instantiate()
 root.add_child(game)
 await process_frame
 await process_frame
 game.set_process(false)
 game.sound_enabled=false
 game.start_fight()
 game.fight.ai_enabled=false
 for code in [KEY_UP,KEY_DOWN,KEY_LEFT,KEY_RIGHT]:
  var before: Vector2=game.fight.player_position
  Input.parse_input_event(key(code,true))
  Input.flush_buffered_events()
  game._process(0.1)
  Input.parse_input_event(key(code,false))
  Input.flush_buffered_events()
  check(game.fight.player_position.distance_to(before)>0.1,"arrow moves player: %s" % code)
 game.fight.player_position=Vector2(0,1)
 game.fight.opponent_position=Vector2.ZERO
 for index in range(6):
  game.fight.tick(0.5)
  game.fight.tick(0.5)
  game._unhandled_key_input(key(KEY_1+index,true))
  check(game.fight.player_action==index and not game.fight.pending_player.is_empty(),"number key maps punch: %d" % (index+1))
 game._unhandled_key_input(key(KEY_P,true))
 check(game.fight.paused,"P pauses")
 game._unhandled_key_input(key(KEY_P,true))
 check(not game.fight.paused,"P resumes")
 game.guard_held=true
 game._notification(Node.NOTIFICATION_APPLICATION_FOCUS_OUT)
 check(game.fight.paused and not game.guard_held,"focus loss pauses and clears guard")
 game.queue_free()
 await process_frame
 await create_timer(0.05).timeout
 if failures.is_empty():
  print("PASS CHECKPOINT 6: all four arrow keys, punches 1–6, P pause/resume and focus-loss safety")
  quit(0)
 else:
  print("FAIL: ",failures)
  quit(1)
