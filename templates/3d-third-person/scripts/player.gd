## 3D Third-Person Player Controller
##
## Expected hierarchy (auto-created if missing):
##   CharacterBody3D (this script)
##     ├── CameraPivot (Node3D)        — horizontal orbit
##     │   └── SpringArm3D             — collision-safe boom
##     │       └── Camera3D
##     ├── MeshInstance3D              — placeholder capsule
##     └── CollisionShape3D
class_name ThirdPersonPlayer
extends CharacterBody3D

# -- Movement ------------------------------------------------------------------
@export var walk_speed: float = 5.0
@export var sprint_speed: float = 8.5
@export var acceleration: float = 12.0
@export var deceleration: float = 16.0
@export var air_control: float = 3.0
@export var jump_velocity: float = 5.0
@export var rotation_speed: float = 10.0

# -- Camera --------------------------------------------------------------------
@export var mouse_sensitivity: float = 0.003
@export var camera_distance: float = 4.0
@export var min_pitch: float = -40.0          ## degrees
@export var max_pitch: float = 60.0           ## degrees

# -- Gravity -------------------------------------------------------------------
@export var gravity_scale: float = 1.0

# -- State ---------------------------------------------------------------------
var _is_sprinting: bool = false

# -- Child references ----------------------------------------------------------
var _camera_pivot: Node3D
var _spring_arm: SpringArm3D
var _camera: Camera3D

# -- Signals -------------------------------------------------------------------
signal jumped
signal landed


func _ready() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	_ensure_camera_rig()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		# Horizontal orbit — rotate the pivot around Y
		_camera_pivot.rotate_y(-event.relative.x * mouse_sensitivity)
		# Vertical orbit — rotate the spring arm around X
		_spring_arm.rotation.x -= event.relative.y * mouse_sensitivity
		_spring_arm.rotation.x = clampf(
			_spring_arm.rotation.x,
			deg_to_rad(min_pitch),
			deg_to_rad(max_pitch),
		)

	if event.is_action_pressed("ui_cancel"):
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		else:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()

	# Gravity
	if not on_floor:
		var grav: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
		velocity.y -= grav * gravity_scale * delta

	# Jump
	if Input.is_action_just_pressed("jump") and on_floor:
		velocity.y = jump_velocity
		jumped.emit()

	# Sprint
	_is_sprinting = Input.is_action_pressed("sprint") and on_floor
	var speed := sprint_speed if _is_sprinting else walk_speed

	# Camera-relative input direction
	var input_dir := Vector2(
		Input.get_axis("move_left", "move_right"),
		Input.get_axis("move_forward", "move_back"),
	)

	# Transform input to be relative to the camera's horizontal facing
	var cam_basis := _camera_pivot.global_basis
	var forward := -cam_basis.z
	forward.y = 0.0
	forward = forward.normalized()
	var right := cam_basis.x
	right.y = 0.0
	right = right.normalized()

	var move_dir := (right * input_dir.x + forward * -input_dir.y).normalized()

	# Acceleration / deceleration
	var accel: float
	if on_floor:
		accel = acceleration if move_dir.length() > 0.01 else deceleration
	else:
		accel = air_control

	if move_dir.length() > 0.01:
		velocity.x = move_toward(velocity.x, move_dir.x * speed, accel * delta)
		velocity.z = move_toward(velocity.z, move_dir.z * speed, accel * delta)
		# Rotate character to face movement direction
		var target_angle := atan2(move_dir.x, move_dir.z)
		rotation.y = lerp_angle(rotation.y, target_angle, rotation_speed * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, accel * delta)
		velocity.z = move_toward(velocity.z, 0.0, accel * delta)

	var was_on_floor := on_floor
	move_and_slide()
	if is_on_floor() and not was_on_floor:
		landed.emit()


# -- Camera rig setup ----------------------------------------------------------

func _ensure_camera_rig() -> void:
	# Camera pivot (horizontal orbit)
	_camera_pivot = get_node_or_null("CameraPivot") as Node3D
	if _camera_pivot == null:
		_camera_pivot = Node3D.new()
		_camera_pivot.name = "CameraPivot"
		_camera_pivot.position = Vector3(0, 1.5, 0)
		add_child(_camera_pivot)
		# The pivot is a child of the player, so it follows position
		# but we DON'T want it to inherit the player's Y rotation
		_camera_pivot.set_as_top_level(true)

	# Spring arm (collision avoidance)
	_spring_arm = _camera_pivot.get_node_or_null("SpringArm3D") as SpringArm3D
	if _spring_arm == null:
		_spring_arm = SpringArm3D.new()
		_spring_arm.name = "SpringArm3D"
		_spring_arm.spring_length = camera_distance
		_spring_arm.collision_mask = 0b0010  # layer 2 = environment
		_spring_arm.rotation.x = deg_to_rad(-15)
		_camera_pivot.add_child(_spring_arm)

	# Camera
	_camera = _spring_arm.get_node_or_null("Camera3D") as Camera3D
	if _camera == null:
		_camera = Camera3D.new()
		_camera.name = "Camera3D"
		_camera.current = true
		_spring_arm.add_child(_camera)


# Override _physics_process slightly: keep camera pivot following player
func _process(_delta: float) -> void:
	if _camera_pivot and _camera_pivot.is_inside_tree():
		_camera_pivot.global_position = global_position + Vector3(0, 1.5, 0)
