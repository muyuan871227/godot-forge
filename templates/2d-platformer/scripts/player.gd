## 2D Platformer Player Controller
##
## Attach to a CharacterBody2D node. Provides responsive horizontal movement
## with acceleration/deceleration, variable-height jump, coyote time, and
## optional double jump.
class_name PlatformerPlayer
extends CharacterBody2D

# -- Movement tuning ----------------------------------------------------------
@export var speed: float = 300.0
@export var acceleration: float = 2000.0
@export var deceleration: float = 2400.0
@export var air_acceleration: float = 1200.0
@export var air_deceleration: float = 600.0

# -- Jump tuning ---------------------------------------------------------------
@export var jump_velocity: float = -400.0
@export var jump_cut_multiplier: float = 0.4          ## applied when releasing jump early
@export var coyote_time: float = 0.12                  ## seconds after leaving ground
@export var jump_buffer_time: float = 0.1              ## pre-land jump buffer
@export var enable_double_jump: bool = true

# -- Gravity -------------------------------------------------------------------
@export var gravity_scale: float = 1.0
@export var fall_gravity_scale: float = 1.5            ## heavier on the way down
@export var max_fall_speed: float = 800.0

# -- State ---------------------------------------------------------------------
var _coyote_timer: float = 0.0
var _jump_buffer_timer: float = 0.0
var _jumps_remaining: int = 0
var _was_on_floor: bool = false

# -- Signals -------------------------------------------------------------------
signal jumped
signal landed
signal died


func _ready() -> void:
	_jumps_remaining = _max_jumps()


func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()

	# ----- Gravity ------------------------------------------------------------
	if not on_floor:
		var grav := _get_gravity(delta)
		velocity.y = minf(velocity.y + grav, max_fall_speed)

	# ----- Coyote time --------------------------------------------------------
	if on_floor:
		_coyote_timer = coyote_time
		_jumps_remaining = _max_jumps()
	else:
		_coyote_timer -= delta

	# Landing detection
	if on_floor and not _was_on_floor:
		landed.emit()
	_was_on_floor = on_floor

	# ----- Jump buffer --------------------------------------------------------
	if Input.is_action_just_pressed("jump"):
		_jump_buffer_timer = jump_buffer_time
	else:
		_jump_buffer_timer -= delta

	# ----- Jump execution -----------------------------------------------------
	if _jump_buffer_timer > 0.0:
		if on_floor or _coyote_timer > 0.0:
			_perform_jump()
		elif enable_double_jump and _jumps_remaining > 0:
			_perform_jump()

	# Variable jump height: cut upward velocity on release
	if Input.is_action_just_released("jump") and velocity.y < 0.0:
		velocity.y *= jump_cut_multiplier

	# ----- Horizontal movement ------------------------------------------------
	var input_dir := Input.get_axis("move_left", "move_right")
	var accel: float
	if on_floor:
		accel = acceleration if input_dir != 0.0 else deceleration
	else:
		accel = air_acceleration if input_dir != 0.0 else air_deceleration

	var target_vx := input_dir * speed
	velocity.x = move_toward(velocity.x, target_vx, accel * delta)

	# ----- Flip sprite (if AnimatedSprite2D child exists) ---------------------
	if input_dir != 0.0:
		var sprite := get_node_or_null("AnimatedSprite2D") as AnimatedSprite2D
		if sprite:
			sprite.flip_h = input_dir < 0.0

	move_and_slide()


# -- Internals ----------------------------------------------------------------

func _max_jumps() -> int:
	return 2 if enable_double_jump else 1


func _get_gravity(delta: float) -> float:
	var base_gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity", 980.0)
	var scale := fall_gravity_scale if velocity.y > 0.0 else gravity_scale
	return base_gravity * scale * delta


func _perform_jump() -> void:
	velocity.y = jump_velocity
	_coyote_timer = 0.0
	_jump_buffer_timer = 0.0
	_jumps_remaining -= 1
	jumped.emit()


# -- Public API ---------------------------------------------------------------

func kill() -> void:
	"""Call to trigger death (e.g. from a hazard Area2D signal)."""
	died.emit()
	# Subclass or connect to `died` to handle respawn / game over.
	set_physics_process(false)
	var tween := create_tween()
	tween.tween_property(self, "modulate:a", 0.0, 0.4)
	tween.tween_callback(queue_free)
