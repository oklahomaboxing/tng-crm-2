class_name BoxingTouchPad
extends Control
var value := Vector2.ZERO
var pointer := -999
func _ready() -> void:
 mouse_filter = Control.MOUSE_FILTER_STOP
 custom_minimum_size = Vector2(112,112)
func _draw() -> void:
 var center := size*0.5
 var radius := minf(size.x,size.y)*0.47
 draw_circle(center,radius,Color(0.04,0.07,0.12,0.85))
 draw_arc(center,radius,0,TAU,48,Color(0.4,0.55,0.7,0.6),2,true)
 draw_line(center-Vector2(radius*0.6,0),center+Vector2(radius*0.6,0),Color(0.5,0.6,0.8,0.2),1)
 draw_line(center-Vector2(0,radius*0.6),center+Vector2(0,radius*0.6),Color(0.5,0.6,0.8,0.2),1)
 draw_circle(center+value*radius*0.55,radius*0.37,Color(0.32,0.43,0.58))
func reset_pad() -> void:
 pointer = -999
 value = Vector2.ZERO
 queue_redraw()
func _update_point(point: Vector2) -> void:
 value = ((point-global_position-size*0.5)/(minf(size.x,size.y)*0.45)).limit_length(1)
 queue_redraw()
func _gui_input(event: InputEvent) -> void:
 if event is InputEventScreenTouch and event.pressed and pointer == -999:
  pointer = event.index
  _update_point(event.position+global_position)
  accept_event()
 elif event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
  if event.pressed and pointer==-999:
   pointer = -1
   _update_point(event.position+global_position)
   accept_event()
  elif not event.pressed and pointer==-1:
   reset_pad()
func _input(event: InputEvent) -> void:
 if event is InputEventScreenDrag and event.index==pointer:
  _update_point(event.position)
 elif event is InputEventScreenTouch and not event.pressed and event.index==pointer:
  reset_pad()
 elif event is InputEventMouseMotion and pointer==-1:
  _update_point(event.position)
 elif event is InputEventMouseButton and not event.pressed and pointer==-1:
  reset_pad()
func _notification(what: int) -> void:
 if what==NOTIFICATION_APPLICATION_FOCUS_OUT:
  reset_pad()
