extends Node3D
const Model = preload("res://scripts/fight_model.gd")
const TouchPad = preload("res://scripts/touch_pad.gd")
const Boxer = preload("res://scripts/boxer_visual.gd")
var fight = Model.new()
var camera: Camera3D
var opponent: Node3D
var gloves: Array[Node3D] = []
var health_you: ProgressBar
var health_partner: ProgressBar
var stamina_you: ProgressBar
var stamina_partner: ProgressBar
var clock_label: Label
var round_label: Label
var feedback_label: Label
var dialog_title: Label
var dialog_text: Label
var dialog_panel: PanelContainer
var start_button: Button
var pause_button: Button
var format_choice: OptionButton
var pad: Control
var guard_held := false
var format := 0
var last_sound_event := -1
@export var sound_enabled := true
var audio: AudioStreamPlayer
var ui_root: Control
var top_row: HBoxContainer
var punch_controls: VBoxContainer
var footer: HBoxContainer
var help_label: Label
var touch_button: Button
var rounds_label: Label
var capture_path := ""
var capture_frames := 0

func _ready() -> void:
 get_window().content_scale_size = Vector2i.ZERO
 _build_ring()
 _build_fighters()
 _build_ui()
 audio = AudioStreamPlayer.new()
 audio.volume_db = -18
 add_child(audio)
 for arg in OS.get_cmdline_user_args():
  if arg.begins_with("--capture="):
   capture_path = arg.trim_prefix("--capture=")
  if arg=="--autostart":
   start_fight(2)
 _update_ui()

func _mat(color: Color, roughness: float = 0.6) -> StandardMaterial3D:
 var m := StandardMaterial3D.new()
 m.albedo_color = color
 m.roughness = roughness
 return m
func _mesh(mesh: Mesh, mat: Material, parent: Node3D, pos: Vector3) -> MeshInstance3D:
 var node := MeshInstance3D.new()
 node.mesh = mesh
 node.material_override = mat
 node.position = pos
 parent.add_child(node)
 return node
func _box(parent: Node3D, pos: Vector3, dimensions: Vector3, color: Color) -> MeshInstance3D:
 var mesh := BoxMesh.new()
 mesh.size = dimensions
 return _mesh(mesh,_mat(color),parent,pos)
func _rod(parent: Node3D, a: Vector3, b: Vector3, radius: float, mat: Material) -> MeshInstance3D:
 var mesh := CylinderMesh.new()
 mesh.top_radius = radius
 mesh.bottom_radius = radius
 mesh.height = a.distance_to(b)
 var node := _mesh(mesh,mat,parent,(a+b)*0.5)
 node.basis = Basis(Quaternion(Vector3.UP,(b-a).normalized()))
 return node
func _build_ring() -> void:
 var world := WorldEnvironment.new()
 var env := Environment.new()
 env.background_mode = Environment.BG_COLOR
 env.background_color = Color("070c16")
 env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
 env.ambient_light_color = Color("9fb3cf")
 env.ambient_light_energy = 0.55
 env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
 world.environment = env
 add_child(world)
 var light := DirectionalLight3D.new()
 light.light_color = Color("ffe7d5")
 light.light_energy = 1.5
 light.rotation_degrees = Vector3(-52,-25,0)
 light.shadow_enabled = true
 add_child(light)
 var fill := OmniLight3D.new()
 fill.position = Vector3(2,3,-2)
 fill.omni_range = 10
 fill.light_energy = 1.4
 fill.light_color = Color("729fe8")
 add_child(fill)
 _box(self,Vector3(0,-0.15,0),Vector3(7,0.3,7),Color("263649"))
 _box(self,Vector3(0,-0.35,0),Vector3(30,0.1,30),Color("080b11"))
 var brand := Label3D.new()
 brand.text = "TNGOS\nAMATEUR BOXING"
 brand.font_size = 96
 brand.pixel_size = 0.005
 brand.modulate = Color("d8dfe9")
 brand.rotation_degrees.x = -90
 brand.position = Vector3(0,0.01,0)
 add_child(brand)
 var red := _mat(Color("d92142"))
 var white := _mat(Color("d8e3f2"))
 for x in [-3.15,3.15]:
  for z in [-3.15,3.15]:
   _box(self,Vector3(x,0.85,z),Vector3(0.12,1.7,0.12),Color("69768a"))
   _box(self,Vector3(x,1.1,z),Vector3(0.21,0.8,0.21),Color("d92142") if x*z>0 else Color("2662b5"))
 for y in [0.5,0.83,1.16,1.5]:
  for edge in [-3.1,3.1]:
   _rod(self,Vector3(-3.1,y,edge),Vector3(3.1,y,edge),0.024,red if y<0.8 or y>1.4 else white)
   _rod(self,Vector3(edge,y,-3.1),Vector3(edge,y,3.1),0.024,red if y<0.8 or y>1.4 else white)
 for z in [-4.3,4.3]:
  var sign := Label3D.new()
  sign.text = "TNGOS\nTHE NEXT GENERATION"
  sign.font_size = 90
  sign.pixel_size = 0.005
  sign.position = Vector3(0,2.4,z)
  sign.rotation.y = PI if z>0 else 0
  add_child(sign)

func _build_fighters() -> void:
 opponent = Boxer.new()
 add_child(opponent)
 camera = Camera3D.new()
 camera.near = 0.025
 camera.fov = 76
 camera.current = true
 add_child(camera)
 var leather := _mat(Color("d51d40"),0.33)
 leather.no_depth_test = true
 leather.render_priority = 10
 var tape := _mat(Color("e0e6ed"))
 tape.no_depth_test = true
 tape.render_priority = 10
 var skin := _mat(Color("b27b56"))
 skin.no_depth_test = true
 skin.render_priority = 10
 for i in range(2):
  var hand := Node3D.new()
  camera.add_child(hand)
  gloves.append(hand)
  var sphere := SphereMesh.new()
  sphere.radius = 0.077
  sphere.height = 0.19
  var glove := _mesh(sphere,leather,hand,Vector3.ZERO)
  glove.scale.z = 1.25
  var cuff := CylinderMesh.new()
  cuff.top_radius = 0.056
  cuff.bottom_radius = 0.056
  cuff.height = 0.055
  var wrist := _mesh(cuff,tape,hand,Vector3(0,-0.01,0.1))
  wrist.rotation.x = PI/2
  _rod(hand,Vector3(0,-0.01,0.13),Vector3(-0.02 if i==0 else 0.02,-0.24,0.43),0.044,skin)

func _panel(color: Color = Color("101a29")) -> PanelContainer:
 var panel := PanelContainer.new()
 var style := StyleBoxFlat.new()
 style.bg_color = color
 style.corner_radius_top_left = 8
 style.corner_radius_top_right = 8
 style.corner_radius_bottom_left = 8
 style.corner_radius_bottom_right = 8
 style.content_margin_left = 12
 style.content_margin_right = 12
 style.content_margin_top = 8
 style.content_margin_bottom = 8
 panel.add_theme_stylebox_override("panel",style)
 return panel
func _label(text: String, font_size: int = 16) -> Label:
 var label := Label.new()
 label.text = text
 label.add_theme_font_size_override("font_size",font_size)
 label.add_theme_color_override("font_color",Color("eef3fa"))
 return label
func _bar(color: Color) -> ProgressBar:
 var bar := ProgressBar.new()
 bar.min_value = 0
 bar.max_value = 100
 bar.value = 100
 bar.show_percentage = false
 bar.custom_minimum_size.y = 13
 var fill := StyleBoxFlat.new()
 fill.bg_color = color
 fill.corner_radius_top_left = 3
 fill.corner_radius_top_right = 3
 fill.corner_radius_bottom_left = 3
 fill.corner_radius_bottom_right = 3
 var bg := StyleBoxFlat.new()
 bg.bg_color = Color("26354a")
 bar.add_theme_stylebox_override("fill",fill)
 bar.add_theme_stylebox_override("background",bg)
 return bar
func _fighter_card(title: String, color: Color) -> Array:
 var panel := _panel()
 panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 var stack := VBoxContainer.new()
 panel.add_child(stack)
 var label := _label(title,15)
 label.clip_text = true
 stack.add_child(label)
 stack.add_child(_label("HEALTH",10))
 var health := _bar(color)
 stack.add_child(health)
 stack.add_child(_label("STAMINA",10))
 var stamina := _bar(Color("e4b94e"))
 stack.add_child(stamina)
 top_row.add_child(panel)
 return [health,stamina]
func _button(text: String, action: Callable) -> Button:
 var button := Button.new()
 button.text = text
 button.custom_minimum_size = Vector2(58,44)
 button.focus_mode = Control.FOCUS_NONE
 button.add_theme_font_size_override("font_size",13)
 var normal := StyleBoxFlat.new()
 normal.bg_color = Color("8b1a32")
 normal.corner_radius_top_left = 7
 normal.corner_radius_top_right = 7
 normal.corner_radius_bottom_left = 7
 normal.corner_radius_bottom_right = 7
 var pressed := normal.duplicate()
 pressed.bg_color = Color("e0284c")
 button.add_theme_stylebox_override("normal",normal)
 button.add_theme_stylebox_override("pressed",pressed)
 button.add_theme_stylebox_override("hover",pressed)
 button.pressed.connect(action)
 return button
func _build_ui() -> void:
 var layer := CanvasLayer.new()
 add_child(layer)
 ui_root = Control.new()
 ui_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 layer.add_child(ui_root)
 var margin := MarginContainer.new()
 margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 for edge in ["left","right","top","bottom"]:
  margin.add_theme_constant_override("margin_"+edge,10)
 ui_root.add_child(margin)
 var column := VBoxContainer.new()
 column.add_theme_constant_override("separation",8)
 margin.add_child(column)
 top_row = HBoxContainer.new()
 top_row.add_theme_constant_override("separation",7)
 column.add_child(top_row)
 var yours := _fighter_card("YOU • RED",Color("f02e54"))
 health_you = yours[0]
 stamina_you = yours[1]
 var center := _panel(Color("dde5ef"))
 center.custom_minimum_size.x = 88
 var center_stack := VBoxContainer.new()
 center.add_child(center_stack)
 var logo := _label("TNGOS",15)
 logo.add_theme_color_override("font_color",Color("111b2b"))
 logo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
 center_stack.add_child(logo)
 clock_label = _label("2:00",27)
 clock_label.add_theme_color_override("font_color",Color("111b2b"))
 clock_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
 center_stack.add_child(clock_label)
 round_label = _label("ROUND 1 / 3",10)
 round_label.add_theme_color_override("font_color",Color("111b2b"))
 round_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
 center_stack.add_child(round_label)
 top_row.add_child(center)
 var theirs := _fighter_card("PARTNER • BLUE",Color("4aa7ef"))
 health_partner = theirs[0]
 stamina_partner = theirs[1]
 var middle := CenterContainer.new()
 middle.size_flags_vertical = Control.SIZE_EXPAND_FILL
 middle.mouse_filter = Control.MOUSE_FILTER_IGNORE
 column.add_child(middle)
 dialog_panel = _panel(Color(0.04,0.07,0.12,0.95))
 dialog_panel.custom_minimum_size.x = 300
 middle.add_child(dialog_panel)
 var dialog := VBoxContainer.new()
 dialog.add_theme_constant_override("separation",10)
 dialog_panel.add_child(dialog)
 dialog_title = _label("TNGOS • AMATEUR",20)
 dialog_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
 dialog.add_child(dialog_title)
 dialog_text = _label("3 rounds • first-person training",14)
 dialog_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 dialog_text.custom_minimum_size.x = 270
 dialog.add_child(dialog_text)
 format_choice = OptionButton.new()
 format_choice.add_item("3 × 2 min • 60 sec rest")
 format_choice.add_item("3 × 3 min • 60 sec rest")
 format_choice.add_item("Quick practice • 3 × 30 sec")
 format_choice.custom_minimum_size.y = 44
 format_choice.focus_mode = Control.FOCUS_NONE
 format_choice.item_selected.connect(_choose_format)
 dialog.add_child(format_choice)
 start_button = _button("START FIGHT",func():
  if fight.paused:
   pause_fight()
  else:
   start_fight(format))
 dialog.add_child(start_button)
 feedback_label = _label("",14)
 feedback_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 column.add_child(feedback_label)
 footer = HBoxContainer.new()
 footer.add_theme_constant_override("separation",12)
 column.add_child(footer)
 pad = TouchPad.new()
 footer.add_child(pad)
 var spacer := Control.new()
 spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 footer.add_child(spacer)
 var controls := VBoxContainer.new()
 punch_controls = controls
 controls.custom_minimum_size.x = 330
 footer.add_child(controls)
 var grid := GridContainer.new()
 grid.columns = 3
 controls.add_child(grid)
 for i in range(6):
  var index := i
  var button := _button(["1 · JAB","2 · CROSS","3 · L HOOK","4 · R HOOK","5 · L UPPER","6 · R UPPER"][i],func():fight.punch(index))
  button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
  grid.add_child(button)
 var defense := HBoxContainer.new()
 controls.add_child(defense)
 var guard := _button("HOLD GUARD",func():pass)
 guard.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 guard.button_down.connect(func():guard_held=true)
 guard.button_up.connect(func():guard_held=false)
 defense.add_child(guard)
 var slip_button := _button("SLIP · Q/E",func():fight.slip())
 slip_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 defense.add_child(slip_button)
 var toolbar := HBoxContainer.new()
 toolbar.alignment = BoxContainer.ALIGNMENT_END
 column.add_child(toolbar)
 pause_button = _button("PAUSE",pause_fight)
 toolbar.add_child(pause_button)
 toolbar.add_child(_button("RESTART",_reset_to_menu))
 toolbar.add_child(_button("CONTROLS",func():help_label.visible=not help_label.visible))
 touch_button = _button("TOUCH CONTROLS",func():set_touch_controls(not footer.visible))
 toolbar.add_child(touch_button)
 toolbar.add_child(_button("FULL",func():
  DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if DisplayServer.window_get_mode()==DisplayServer.WINDOW_MODE_FULLSCREEN else DisplayServer.WINDOW_MODE_FULLSCREEN)))
 help_label = _label("ARROWS: move   •   1–6: punch   •   SPACE: guard   •   Q/E: slip   •   P: pause\nWASD also works. Touch controls are optional.",13)
 help_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 help_label.visible = false
 column.add_child(help_label)
 rounds_label = _label("Prototype training scoring • not official USA Boxing judging",10)
 rounds_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 column.add_child(rounds_label)
 set_touch_controls(DisplayServer.is_touchscreen_available())

func set_touch_controls(enabled: bool) -> void:
 footer.visible = enabled
 touch_button.text = "HIDE TOUCH" if enabled else "TOUCH"
 _release_controls()

func _choose_format(index: int) -> void:
 format = index
 if fight.phase==Model.Phase.READY:
  fight.remaining = 120 if format==0 else 180 if format==1 else 30

func _reset_to_menu() -> void:
 fight = Model.new()
 _choose_format(format)
 _release_controls()

func start_fight(chosen_format: int = 0) -> void:
 format = chosen_format
 fight.start(120 if format==0 else 180 if format==1 else 30,60 if format<2 else 10)
 _release_controls()
func _release_controls() -> void:
 guard_held = false
 fight.guard_requested = false
 if pad:
  pad.reset_pad()
func pause_fight() -> void:
 fight.toggle_pause()
 _release_controls()
func _notification(what: int) -> void:
 if what==NOTIFICATION_APPLICATION_FOCUS_OUT and is_instance_valid(fight):
  if not fight.paused:
   fight.toggle_pause()
  _release_controls()
func _unhandled_key_input(event: InputEvent) -> void:
 if not event is InputEventKey or not event.pressed or event.echo:
  return
 if event.physical_keycode>=KEY_1 and event.physical_keycode<=KEY_6:
  fight.punch(event.physical_keycode-KEY_1)
 elif event.physical_keycode==KEY_Q or event.physical_keycode==KEY_E:
  fight.slip()
 elif event.physical_keycode==KEY_P or event.physical_keycode==KEY_ESCAPE:
  pause_fight()
func _process(delta: float) -> void:
 var move := Vector2.ZERO
 if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT): move.x-=1
 if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT): move.x+=1
 if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP): move.y+=1
 if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN): move.y-=1
 if pad.value.length()>0.2:
  move = Vector2(pad.value.x,-pad.value.y)
 fight.guard_requested = guard_held or Input.is_physical_key_pressed(KEY_SPACE)
 fight.move_player(move,delta)
 fight.tick(delta)
 _animate()
 _update_ui()
 if fight.event_id!=last_sound_event:
  last_sound_event=fight.event_id
  if fight.event_type=="bell":
   _tone(740,0.22)
  elif fight.event_type in ["landed","caught","block"]:
   _tone(95,0.07)
 if not capture_path.is_empty():
  capture_frames+=1
  if capture_frames==30:
   await RenderingServer.frame_post_draw
   get_viewport().get_texture().get_image().save_png(capture_path)
   get_tree().quit()
func _animate() -> void:
 opponent.position = Vector3(fight.opponent_position.x,0,fight.opponent_position.y)
 var target := Vector3(fight.player_position.x,0,fight.player_position.y)
 opponent.rotation.y = atan2(target.x-opponent.position.x,target.z-opponent.position.z)
 opponent.animate(fight)
 var slip := sin((fight.player_slip_until-fight.time)/0.38*PI)*0.1 if fight.time<fight.player_slip_until else 0.0
 camera.position = Vector3(target.x+slip,1.64,target.z)
 camera.look_at(opponent.position+Vector3(0,1.59,0))
 camera.fov = 96 if get_viewport().get_visible_rect().size.y>get_viewport().get_visible_rect().size.x else 76
 for i in range(2):
  var side: float = -1 if i==0 else 1
  var base := Vector3(side*0.19,-0.16,-0.45)
  var t: float = (fight.time-fight.player_action_at)/0.5
  if fight.player_action>=0 and fight.player_action%2==i and t>=0 and t<1:
   base = base.lerp(Vector3(side*0.025,-0.015,-0.72),sin(t*PI))
  gloves[i].position = base
  gloves[i].rotation.z = side*-0.14
func _update_ui() -> void:
 health_you.value = fight.player_health
 health_partner.value = fight.opponent_health
 stamina_you.value = fight.player_stamina
 stamina_partner.value = fight.opponent_stamina
 var seconds := maxi(0,ceili(fight.remaining))
 clock_label.text = "%d:%02d" % [seconds/60,seconds%60]
 round_label.text = "REST → %d / 3" % fight.round_number if fight.phase==Model.Phase.REST else "ROUND %d / 3" % fight.round_number
 feedback_label.text = "PAUSED — resume when ready." if fight.paused else fight.feedback
 var is_ready: bool = fight.phase==Model.Phase.READY
 var is_finished: bool = fight.phase==Model.Phase.FINISHED
 dialog_panel.visible = is_ready or is_finished or fight.paused or fight.phase==Model.Phase.REST
 format_choice.visible = is_ready
 start_button.visible = is_ready or is_finished or fight.paused
 start_button.text = "RESUME" if fight.paused else "FIGHT AGAIN" if is_finished else "START FIGHT"
 pause_button.disabled = is_ready or is_finished
 pause_button.text = "RESUME" if fight.paused else "PAUSE"
 dialog_title.text = "PAUSED" if fight.paused else "FIGHT COMPLETE" if is_finished else "IN YOUR CORNER" if fight.phase==Model.Phase.REST else "TNGOS • AMATEUR"
 if is_finished:
  var text := "%s — %s\n\nPrototype scorecard\n" % [fight.winner,fight.finish_reason]
  for card in fight.scorecards:
   text += "R%d   YOU %d — %d PARTNER   (%d / %d clean)\n" % [card.round,card.you,card.partner,card.you_hits,card.partner_hits]
  dialog_text.text = text
 elif fight.phase==Model.Phase.REST:
  dialog_text.text = "Recover and prepare for round %d.\nStamina refills at the bell.\nHealth recovers slightly between rounds." % fight.round_number
 else:
  dialog_text.text = "THREE ROUNDS. YOUR CORNER.\n\nStep into the ring and face your partner.\nPress Controls if you need the key guide."
 var portrait: bool = get_viewport().get_visible_rect().size.x<650
 pad.custom_minimum_size = Vector2(96,96) if portrait else Vector2(112,112)
 punch_controls.custom_minimum_size.x = minf(330,get_viewport().get_visible_rect().size.x-pad.custom_minimum_size.x-36)
func _tone(frequency: float, duration: float) -> void:
 if not audio or not sound_enabled:
  return
 var sample_rate := 22050
 var count := int(sample_rate*duration)
 var data := PackedByteArray()
 data.resize(count*2)
 for i in range(count):
  var sample := int(sin(TAU*frequency*i/sample_rate)*exp(-5.0*i/count)*10000)
  data.encode_s16(i*2,sample)
 var sound := AudioStreamWAV.new()
 sound.format = AudioStreamWAV.FORMAT_16_BITS
 sound.mix_rate = sample_rate
 sound.data = data
 audio.stream = sound
 audio.play()

func _exit_tree() -> void:
 if is_instance_valid(audio):
  audio.stop()
  audio.stream = null
