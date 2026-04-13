## 3D FPS Player Controller
##
## Hierarchy expected:
##   CharacterBody3D (this script)
##     ├── HeadPivot (Node3D)  — vertical look rotation
##     │   └── Camera3D
##     └── CollisionShape3D
##
## The script creates HeadPivot + Camera3D at runtime if they don't exist.
class_name FPSPlayer
extends CharacterBody3D

# -- Movement ------------------------------------------------------------------
@export var walk_speed: float = 5.0
@export var sprint_speed: float = 8.0
@export var acceleration: float = 10.0
@export var air_acceleration: float = 3.0
@export var jump_velocity: float = 4.5

# -- Mouse look ----------------------------------------------------------------
@export var mouse_sensitivity: float = 0.002
@export var max_pitch: float = 89.0  ## degrees

# -- Head bob ------------------------------------------------------------------
@export var head_bob_frequency: float = 2.4
@export var head_bob_amplitude: float = 0.06
@export var head_bob_sprint_mult: float = 1.4

# -- FOV effects ---------------------------------------------------------------
@export var base_fov: float = 75.0
@export var sprint_fov: float = 85.0
@export var fov_lerp_speed: float = 8.0

# -- Gravity -------------------------------------------------------------------
@export var gravity_scale: float = 1.0

# -- State ---------------------------------------------------------------------
var _head_bob_time: float = 0.0
var _is_sprinting: bool = false

# -- Child references ----------------------------------------------------------
var _head: Node3D
var _camera: Camera3D

# -- Signals -------------------------------------------------------------------
signal jumped
signal landed


func _ready() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	_ensure_head_and_camera()


func _unhandled_input(event: InputEvent) -> void:
	# Mouse look
	if event is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		_head.rotate_x(-event.relative.y * mouse_sensitivity)
		_head.rotation.x = clampf(_head.rotation.x, deg_to_rad(-max_pitch), deg_to_rad(max_pitch))

	# Toggle mouse capture with Escape
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

	# Movement input
	var input_dir := Vector2(
		Input.get_axis("move_left", "move_right"),
		Input.get_axis("move_forward", "move_back"),
	)
	var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()

	var target_speed := sprint_speed if _is_sprinting else walk_speed
	var accel := acceleration if on_floor else air_acceleration

	if direction != Vector3.ZERO:
		velocity.x = move_toward(velocity.x, direction.x * target_speed, accel * delta)
		velocity.z = move_toward(velocity.z, direction.z * target_speed, accel * delta)
	else:
		velocity.x = move_toward(velocity.x, 0.0, accel * delta)
		velocity.z = move_toward(velocity.z, 0.0, accel * delta)

	# Head bob
	_apply_head_bob(delta, on_floor and direction != Vector3.ZERO)

	# FOV effect
	_apply_fov_effect(delta)

	var was_on_floor := on_floor
	move_and_slide()
	if is_on_floor() and not was_on_floor:
		landed.emit()


# -- Head bob ------------------------------------------------------------------

func _apply_head_bob(delta: float, moving: bool) -> void:
	if moving:
		var freq := head_bob_frequency * (head_bob_sprint_mult if _is_sprinting else 1.0)
		_head_bob_time += delta * freq
		var bob_y := sin(_head_bob_time * TAU) * head_bob_amplitude
		var bob_x := cos(_head_bob_time * TAU * 0.5) * head_bob_amplitude * 0.5
		_head.position.y = lerp(_head.position.y, 0.6 + bob_y, 10.0 * delta)
		_head.position.x = lerp(_head.position.x, bob_x, 10.0 * delta)
	else:
		_head_bob_time = 0.0
		_head.position.y = lerp(_head.position.y, 0.6, 10.0 * delta)
		_head.position.x = lerp(_head.position.x, 0.0, 10.0 * delta)


# -- FOV effect ----------------------------------------------------------------

func _apply_fov_effect(delta: float) -> void:
	var target_fov := sprint_fov if _is_sprinting else base_fov
	_camera.fov = lerp(_camera.fov, target_fov, fov_lerp_speed * delta)


# -- Ensure hierarchy ----------------------------------------------------------

func _ensure_head_and_camera() -> void:
	_head = get_node_or_null("HeadPivot") as Node3D
	if _head == null:
		_head = Node3D.new()
		_head.name = "HeadPivot"
		_head.position = Vector3(0, 0.6, 0)
		add_child(_head)

	_camera = _head.get_node_or_null("Camera3D") as Camera3D
	if _camera == null:
		_camera = Camera3D.new()
		_camera.name = "Camera3D"
		_camera.fov = base_fov
		_camera.current = true
		_head.add_child(_camera)
