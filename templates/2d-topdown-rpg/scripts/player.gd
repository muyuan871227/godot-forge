## 2D Top-Down RPG Player Controller
##
## Attach to a CharacterBody2D. Provides smooth 8-directional movement with
## run support, direction tracking for animation, and interaction raycasting.
class_name TopDownPlayer
extends CharacterBody2D

# -- Movement ------------------------------------------------------------------
@export var walk_speed: float = 200.0
@export var run_speed: float = 340.0
@export var acceleration: float = 1600.0
@export var friction: float = 2000.0

# -- Interaction ---------------------------------------------------------------
@export var interact_range: float = 48.0

# -- State ---------------------------------------------------------------------
enum Direction { DOWN, UP, LEFT, RIGHT, DOWN_LEFT, DOWN_RIGHT, UP_LEFT, UP_RIGHT }
var facing: Direction = Direction.DOWN
var is_running: bool = false
var can_move: bool = true          ## set false during cutscenes / dialogue

# -- Signals -------------------------------------------------------------------
signal direction_changed(new_dir: Direction)
signal interact_pressed(target: Node)

# -- Child references ----------------------------------------------------------
@onready var _interact_ray: RayCast2D = _ensure_interact_ray()


func _ready() -> void:
	pass


func _physics_process(delta: float) -> void:
	if not can_move:
		_apply_friction(delta)
		move_and_slide()
		return

	var input := _get_input_vector()
	is_running = Input.is_action_pressed("run")

	if input != Vector2.ZERO:
		_update_facing(input)
		var spd := run_speed if is_running else walk_speed
		var target_vel := input.normalized() * spd
		velocity = velocity.move_toward(target_vel, acceleration * delta)
	else:
		_apply_friction(delta)

	move_and_slide()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact"):
		_try_interact()


# -- Input helpers -------------------------------------------------------------

func _get_input_vector() -> Vector2:
	return Vector2(
		Input.get_axis("move_left", "move_right"),
		Input.get_axis("move_up", "move_down"),
	)


# -- Facing / animation -------------------------------------------------------

func _update_facing(input: Vector2) -> void:
	var old := facing

	# Determine 8-way direction from input vector
	if input.x < 0.0 and input.y < 0.0:
		facing = Direction.UP_LEFT
	elif input.x > 0.0 and input.y < 0.0:
		facing = Direction.UP_RIGHT
	elif input.x < 0.0 and input.y > 0.0:
		facing = Direction.DOWN_LEFT
	elif input.x > 0.0 and input.y > 0.0:
		facing = Direction.DOWN_RIGHT
	elif input.y < 0.0:
		facing = Direction.UP
	elif input.y > 0.0:
		facing = Direction.DOWN
	elif input.x < 0.0:
		facing = Direction.LEFT
	elif input.x > 0.0:
		facing = Direction.RIGHT

	if facing != old:
		direction_changed.emit(facing)
		_orient_interact_ray()


func _orient_interact_ray() -> void:
	"""Point the interaction raycast in the facing direction."""
	var dir_vectors := {
		Direction.DOWN: Vector2.DOWN,
		Direction.UP: Vector2.UP,
		Direction.LEFT: Vector2.LEFT,
		Direction.RIGHT: Vector2.RIGHT,
		Direction.DOWN_LEFT: Vector2(-1, 1).normalized(),
		Direction.DOWN_RIGHT: Vector2(1, 1).normalized(),
		Direction.UP_LEFT: Vector2(-1, -1).normalized(),
		Direction.UP_RIGHT: Vector2(1, -1).normalized(),
	}
	_interact_ray.target_position = dir_vectors[facing] * interact_range


# -- Interaction ---------------------------------------------------------------

func _try_interact() -> void:
	_interact_ray.force_raycast_update()
	if _interact_ray.is_colliding():
		var collider := _interact_ray.get_collider()
		if collider and collider.has_method("interact"):
			collider.interact(self)
		interact_pressed.emit(collider)


# -- Friction helper -----------------------------------------------------------

func _apply_friction(delta: float) -> void:
	velocity = velocity.move_toward(Vector2.ZERO, friction * delta)


# -- Ensure interact ray exists ------------------------------------------------

func _ensure_interact_ray() -> RayCast2D:
	var ray := get_node_or_null("InteractRay") as RayCast2D
	if ray == null:
		ray = RayCast2D.new()
		ray.name = "InteractRay"
		ray.target_position = Vector2.DOWN * interact_range
		ray.collision_mask = 0b0100  # layer 3 = NPCs
		ray.enabled = true
		add_child(ray)
	return ray
