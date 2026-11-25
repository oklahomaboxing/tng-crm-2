extends SceneTree
var failures: Array[String] = []
func check(ok: bool,message: String) -> void:
 if not ok:
  failures.append(message)
  push_error(message)
func find_button(node: Node,label: String) -> Button:
 if node is Button and node.text==label:
  return node
 for child in node.get_children():
  var found := find_button(child,label)
  if found:
   return found
 return null
func _initialize() -> void:
 call_deferred("run")
func run() -> void:
 var game = load("res://main.tscn").instantiate()
 root.add_child(game)
 await process_frame
 await process_frame
 game.set_process(false)
 check(game.fight.phase==0,"initial menu is ready")
 check(not game.footer.visible and not game.help_label.visible,"desktop combat commands and help are hidden by default")
 find_button(game,"CONTROLS").pressed.emit()
 check(game.help_label.visible,"controls guide is available on demand")
 find_button(game,"CONTROLS").pressed.emit()
 check(game.health_you.value==100 and game.stamina_you.value==100,"health and stamina bars start full")
 game.start_button.pressed.emit()
 game.fight.ai_enabled=false
 check(game.fight.phase==1 and game.fight.round_number==1,"Start button starts round one")
 game.fight.player_position=Vector2(0,1)
 game.fight.opponent_position=Vector2.ZERO
 var jab := find_button(game,"1 · JAB")
 check(jab!=null,"jab touchscreen button exists")
 jab.pressed.emit()
 game.fight.tick(0.3)
 game._update_ui()
 check(game.stamina_you.value<100,"stamina bar follows punches")
 check(game.health_partner.value<100,"health bar follows clean contact")
 check(game.health_you.value==100,"opponent health is separate from player health")
 game.guard_held=true
 game.pause_button.pressed.emit()
 game._update_ui()
 check(game.fight.paused and not game.guard_held,"Pause button pauses and releases held guard")
 check(game.start_button.text=="RESUME","paused menu offers Resume")
 game.start_button.pressed.emit()
 check(not game.fight.paused,"Resume button resumes")
 game.set_touch_controls(true)
 root.size=Vector2i(390,844)
 game._update_ui()
 await process_frame
 await process_frame
 var touch := InputEventScreenTouch.new()
 touch.index=2
 touch.pressed=true
 touch.position=game.pad.size*0.5+Vector2(30,0)
 game.pad._gui_input(touch)
 check(game.pad.value.x>0.2,"touchscreen pad responds to touch")
 game.fight.player_ready_at=game.fight.time
 jab.pressed.emit()
 check(game.pad.pointer==2 and not game.fight.pending_player.is_empty(),"movement touch and punch coexist")
 touch.pressed=false
 game.pad._input(touch)
 check(game.pad.value==Vector2.ZERO,"touch release resets the pad")
 for label in ["1 · JAB","6 · R UPPER","HOLD GUARD","SLIP · Q/E","PAUSE","RESTART","FULL"]:
  var button := find_button(game,label)
  if not button and label=="PAUSE":
   button = game.pause_button
  check(button!=null,"control exists: "+label)
  if button:
   var rect := button.get_global_rect()
   check(rect.position.x>=-1 and rect.end.x<=391,"portrait controls fit horizontally: "+label)
 root.size=Vector2i(844,390)
 game._update_ui()
 await process_frame
 await process_frame
 for label in ["1 · JAB","6 · R UPPER","HOLD GUARD","SLIP · Q/E"]:
  var rect := find_button(game,label).get_global_rect()
  check(rect.position.x>=-1 and rect.end.x<=845,"landscape controls fit: "+label)
 game.set_touch_controls(false)
 check(game.pad.value==Vector2.ZERO and not game.guard_held,"hiding touch controls clears held inputs")
 game.fight.start(1,0.1)
 for i in range(35):
  game.fight.tick(0.1)
 game._update_ui()
 check(game.fight.phase==3 and game.dialog_title.text=="FIGHT COMPLETE","final fight screen is displayed")
 check("R1" in game.dialog_text.text and "R2" in game.dialog_text.text and "R3" in game.dialog_text.text,"all round scorecards appear")
 find_button(game,"RESTART").pressed.emit()
 game._update_ui()
 check(game.fight.phase==0 and game.format_choice.visible,"Restart returns to format selection")
 game.queue_free()
 await process_frame
 if failures.is_empty():
  print("PASS CHECKPOINT 5: real scene, buttons, health/stamina bars, pause/resume, multi-touch, portrait/landscape and final scorecards")
  quit(0)
 else:
  print("FAIL: ",failures)
  quit(1)
