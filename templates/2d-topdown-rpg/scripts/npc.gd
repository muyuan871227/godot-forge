## Top-Down RPG NPC
##
## Attach to a CharacterBody2D (or StaticBody2D) on physics layer 3 (NPCs).
## Provides:
##   - Simple patrol between waypoints (optional)
##   - Dialogue data with multiple pages
##   - `interact()` method called by the player's raycast
##   - Typewriter-style text display via a child Label / RichTextLabel
class_name TopDownNPC
extends CharacterBody2D

# -- Config --------------------------------------------------------------------
@export var npc_name: str = "Villager"
@export var dialogue_pages: PackedStringArray = PackedStringArray([
	"Hello, traveler!",
	"It's a fine day for an adventure.",
])
@export var dialogue_speed: float = 0.03       ## seconds per character
@export var can_repeat: bool = true             ## restart dialogue after finishing

# -- Patrol (optional) ---------------------------------------------------------
@export var patrol_points: PackedVector2Array = PackedVector2Array()
@export var patrol_speed: float = 60.0
@export var patrol_wait_time: float = 2.0

# -- State ---------------------------------------------------------------------
var _current_page: int = 0
var _is_talking: bool = false
var _patrol_index: int = 0
var _patrol_waiting: bool = false
var _patrol_timer: float = 0.0

# -- Signals -------------------------------------------------------------------
signal dialogue_started(npc: TopDownNPC)
signal dialogue_page(npc: TopDownNPC, page_index: int, text: String)
signal dialogue_ended(npc: TopDownNPC)

# -- Child references ----------------------------------------------------------
var _label: RichTextLabel = null


func _ready() -> void:
	# Auto-find or create a RichTextLabel child for dialogue display
	_label = get_node_or_null("DialogueLabel") as RichTextLabel
	if _label == null:
		_label = RichTextLabel.new()
		_label.name = "DialogueLabel"
		_label.bbcode_enabled = true
		_label.fit_content = true
		_label.size = Vector2(200, 80)
		_label.position = Vector2(-100, -80)
		_label.visible = false
		_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(_label)


func _physics_process(delta: float) -> void:
	if _is_talking:
		return
	_process_patrol(delta)


# -- Interaction (called by player) --------------------------------------------

func interact(_player: Node = null) -> void:
	"""Called when the player presses interact while facing this NPC."""
	if _is_talking:
		_advance_dialogue()
	else:
		_start_dialogue()


# -- Dialogue system -----------------------------------------------------------

func _start_dialogue() -> void:
	if dialogue_pages.is_empty():
		return
	_is_talking = true
	_current_page = 0
	dialogue_started.emit(self)
	_show_page(_current_page)


func _advance_dialogue() -> void:
	# If the typewriter hasn't finished, show full text instantly
	if _label and _label.visible_ratio < 1.0:
		_label.visible_ratio = 1.0
		return

	_current_page += 1
	if _current_page >= dialogue_pages.size():
		_end_dialogue()
	else:
		_show_page(_current_page)


func _show_page(index: int) -> void:
	var text := dialogue_pages[index]
	dialogue_page.emit(self, index, text)
	if _label:
		_label.text = "[b]%s[/b]\n%s" % [npc_name, text]
		_label.visible = true
		_label.visible_ratio = 0.0
		# Typewriter tween
		var total_time := text.length() * dialogue_speed
		var tw := create_tween()
		tw.tween_property(_label, "visible_ratio", 1.0, total_time)


func _end_dialogue() -> void:
	_is_talking = false
	if _label:
		_label.visible = false
	dialogue_ended.emit(self)
	if can_repeat:
		_current_page = 0  # reset for next interaction


# -- Patrol system -------------------------------------------------------------

func _process_patrol(delta: float) -> void:
	if patrol_points.is_empty():
		return

	if _patrol_waiting:
		_patrol_timer -= delta
		if _patrol_timer <= 0.0:
			_patrol_waiting = false
			_patrol_index = (_patrol_index + 1) % patrol_points.size()
		return

	var target := patrol_points[_patrol_index]
	var direction := (target - global_position)
	if direction.length() < 4.0:
		# Reached waypoint
		velocity = Vector2.ZERO
		_patrol_waiting = true
		_patrol_timer = patrol_wait_time
	else:
		velocity = direction.normalized() * patrol_speed

	move_and_slide()
