extends Node3D
var skeleton: Skeleton3D
var joints: Dictionary = {}
var rest: Dictionary = {}
var hands: Dictionary = {}
func material(color: Color, roughness: float = 0.5) -> StandardMaterial3D:
 var m := StandardMaterial3D.new()
 m.albedo_color = color
 m.roughness = roughness
 return m
func shape(mesh: Mesh, mat: Material, parent: Node3D, position: Vector3) -> MeshInstance3D:
 var g := MeshInstance3D.new()
 g.mesh = mesh
 g.material_override = mat
 g.position = position
 parent.add_child(g)
 return g
func _ready() -> void:
 var model := preload("res://assets/boxer.glb").instantiate()
 add_child(model)
 var candidates := model.find_children("*","Skeleton3D",true,false)
 if candidates.is_empty():
  push_error("Boxer skeleton unavailable")
  return
 skeleton = candidates[0]
 for i in skeleton.get_bone_count():
  var bone_name := skeleton.get_bone_name(i)
  joints[bone_name] = i
  rest[bone_name] = skeleton.get_bone_global_rest(i)
 var kit := material(Color("1754aa"),0.4)
 var skin := material(Color("aa7455"),0.55)
 for node in model.find_children("*","MeshInstance3D",true,false):
  for surface in node.mesh.get_surface_count():
   var original: Material = node.mesh.surface_get_material(surface)
   var label: String = original.resource_name.to_lower() if original else "skin"
   node.set_surface_override_material(surface,kit if "short" in label or "vest" in label else material(Color("211b1a")) if "hair" in label else skin)
 for side in ["L","R"]:
  var attach := BoneAttachment3D.new()
  attach.bone_name = "hand"+side
  skeleton.add_child(attach)
  var glove := SphereMesh.new()
  glove.radius = 0.085
  glove.height = 0.21
  var hand := shape(glove,kit,attach,Vector3(0,0.06,0.025))
  hands[side] = hand
func _aim(name: String, target: Vector3) -> void:
 var index: int = joints[name]
 var child: String = "forearm"+name.right(1) if name.begins_with("arm") else "hand"+name.right(1)
 var pose: Transform3D = skeleton.get_bone_global_pose(index)
 var original: Vector3 = rest[child].origin-rest[name].origin
 var direction := target-pose.origin
 if direction.length()<0.001:
  return
 pose.basis = Basis(Quaternion(original.normalized(),direction.normalized()))*rest[name].basis
 skeleton.set_bone_global_pose(index,pose)
func _limb(side: String, target: Vector3) -> void:
 var upper: Transform3D = skeleton.get_bone_global_pose(joints["arm"+side])
 var start := upper.origin
 var a: float = rest["arm"+side].origin.distance_to(rest["forearm"+side].origin)
 var b: float = rest["forearm"+side].origin.distance_to(rest["hand"+side].origin)
 var direction := (target-start).normalized()
 var distance := clampf(target.distance_to(start),absf(a-b)+0.002,a+b-0.004)
 var along := (a*a-b*b+distance*distance)/(2*distance)
 var height := sqrt(maxf(0,a*a-along*along))
 var pole := Vector3(0.65 if side=="L" else -0.65,0.9,0.03)-start
 pole = (pole-direction*pole.dot(direction)).normalized()
 var elbow := start+direction*along+pole*height
 _aim("arm"+side,elbow)
 _aim("forearm"+side,start+direction*distance)
func animate(model) -> void:
 if not skeleton:
  return
 skeleton.reset_bone_poses()
 var progress: float = (model.time-model.opponent_action_at)/0.5
 var punch: bool = model.opponent_action>=0 and progress>=0 and progress<1
 var peak := sin(clampf(progress,0,1)*PI) if punch else 0.0
 for side in ["L","R"]:
  var sign: float = 1.0 if side=="L" else -1.0
  var target := Vector3(sign*0.14,1.48,0.27)
  var selected: bool = punch and ((model.opponent_action%2==0 and side=="L") or (model.opponent_action%2==1 and side=="R"))
  if selected:
   target = target.lerp(Vector3(0,1.61,0.68),peak)
  _limb(side,target)
 rotation.z = sin((model.time-model.opponent_hit_until)*22)*0.04 if model.time<model.opponent_hit_until else 0
