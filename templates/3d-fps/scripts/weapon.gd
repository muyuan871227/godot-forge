## FPS Hitscan Weapon
##
## Attach to a Node3D child of the camera (e.g. HeadPivot/Camera3D/WeaponPivot).
## Uses a RayCast3D for instant hit detection. Supports fire rate, ammo,
## reload, recoil, and spread.
class_name FPSWeapon
extends Node3D

# -- Damage / Fire rate --------------------------------------------------------
@export var damage: float = 25.0
@export var fire_rate: float = 0.1           ## seconds between shots
@export var automatic: bool = true            ## hold to fire continuously

# -- Ammo ----------------------------------------------------------------------
@export var max_ammo: int = 30
@export var reserve_ammo: int = 90
@export var reload_time: float = 1.5

# -- Recoil / Spread -----------------------------------------------------------
@export var recoil_pitch: float = 0.01       ## radians per shot (camera kick up)
@export var recoil_recovery: float = 5.0     ## speed the camera returns
@export var spread_angle: float = 0.5        ## degrees of bullet spread
@export var spread_increase: float = 0.1     ## spread added per consecutive shot
@export var max_spread: float = 3.0
@export var spread_recovery: float = 6.0

# -- Ray -----------------------------------------------------------------------
@export var ray_length: float = 1000.0
@export var collision_mask: int = 0b0110     ## layers 2+3: environment + enemies

# -- State ---------------------------------------------------------------------
var current_ammo: int = 30
var _fire_timer: float = 0.0
var _reload_timer: float = 0.0
var _is_reloading: bool = false
var _current_spread: float = 0.0
var _recoil_offset: float = 0.0

# -- Signals -------------------------------------------------------------------
signal fired(hit_info: Dictionary)
signal reloaded
signal ammo_changed(current: int, reserve: int)

# -- Internal ------------------------------------------------------------------
var _ray: RayCast3D
var _camera: Camera3D


func _ready() -> void:
	current_ammo = max_ammo
	_setup_raycast()
	ammo_changed.emit(current_ammo, reserve_ammo)


func _process(delta: float) -> void:
	_fire_timer -= delta

	# Reload countdown
	if _is_reloading:
		_reload_timer -= delta
		if _reload_timer <= 0.0:
			_finish_reload()
		return

	# Fire input
	if automatic:
		if Input.is_action_pressed("shoot"):
			_try_fire()
	else:
		if Input.is_action_just_pressed("shoot"):
			_try_fire()

	# Reload input
	if Input.is_action_just_pressed("reload"):
		start_reload()

	# Recover spread
	_current_spread = move_toward(_current_spread, 0.0, spread_recovery * delta)

	# Recover recoil
	if _recoil_offset > 0.0:
		_recoil_offset = move_toward(_recoil_offset, 0.0, recoil_recovery * delta)
		if _camera:
			_camera.rotation.x = clampf(
				_camera.rotation.x + recoil_recovery * delta * 0.1,
				deg_to_rad(-89), deg_to_rad(89)
			)


# -- Fire ----------------------------------------------------------------------

func _try_fire() -> void:
	if _fire_timer > 0.0 or current_ammo <= 0:
		if current_ammo <= 0:
			start_reload()
		return

	_fire_timer = fire_rate
	current_ammo -= 1
	ammo_changed.emit(current_ammo, reserve_ammo)

	# Apply spread
	var spread_rad := deg_to_rad(_current_spread + spread_angle)
	var random_spread := Vector2(
		randf_range(-spread_rad, spread_rad),
		randf_range(-spread_rad, spread_rad),
	)

	_current_spread = minf(_current_spread + spread_increase, max_spread)

	# Raycast
	var cam := _get_camera()
	if cam == null:
		return

	var from := cam.global_position
	var forward := -cam.global_basis.z
	var right := cam.global_basis.x
	var up := cam.global_basis.y
	var direction := (forward + right * random_spread.x + up * random_spread.y).normalized()
	var to := from + direction * ray_length

	# Direct physics query (more reliable for one-shot than RayCast3D node)
	var space := get_world_3d().direct_space_state
	var query := PhysicsRayQueryParameters3D.create(from, to, collision_mask)
	var result := space.intersect_ray(query)

	var hit_info := {
		"hit": not result.is_empty(),
		"position": result.get("position", Vector3.ZERO),
		"normal": result.get("normal", Vector3.UP),
		"collider": result.get("collider", null),
	}

	# Apply damage
	if hit_info["hit"] and hit_info["collider"] != null:
		var collider: Node = hit_info["collider"]
		if collider.has_method("take_damage"):
			collider.take_damage(damage, hit_info["position"], hit_info["normal"])

	# Recoil kick
	if cam:
		cam.rotation.x -= recoil_pitch
		cam.rotation.x = clampf(cam.rotation.x, deg_to_rad(-89), deg_to_rad(89))
		_recoil_offset += recoil_pitch

	fired.emit(hit_info)

	# Auto-reload when empty
	if current_ammo <= 0 and reserve_ammo > 0:
		start_reload()


# -- Reload --------------------------------------------------------------------

func start_reload() -> void:
	if _is_reloading or current_ammo == max_ammo or reserve_ammo <= 0:
		return
	_is_reloading = true
	_reload_timer = reload_time


func _finish_reload() -> void:
	var needed := max_ammo - current_ammo
	var available := mini(needed, reserve_ammo)
	current_ammo += available
	reserve_ammo -= available
	_is_reloading = false
	ammo_changed.emit(current_ammo, reserve_ammo)
	reloaded.emit()


# -- Setup ---------------------------------------------------------------------

func _setup_raycast() -> void:
	_ray = RayCast3D.new()
	_ray.name = "WeaponRay"
	_ray.target_position = Vector3(0, 0, -ray_length)
	_ray.collision_mask = collision_mask
	_ray.enabled = false  # we use direct space queries instead
	add_child(_ray)


func _get_camera() -> Camera3D:
	if _camera:
		return _camera
	# Walk up to find the camera
	var node := get_parent()
	while node:
		if node is Camera3D:
			_camera = node
			return _camera
		node = node.get_parent()
	# Fallback: find any Camera3D in the scene
	_camera = get_viewport().get_camera_3d()
	return _camera
