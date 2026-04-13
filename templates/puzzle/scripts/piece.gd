## Puzzle Piece — visual representation of a single grid cell.
##
## Draws a colored rectangle (placeholder) and handles selection highlight,
## hint glow, destruction animation, and movement tweening.
class_name PuzzlePiece
extends Node2D

# -- Config --------------------------------------------------------------------
@export var piece_type: int = 0
@export var cell_size: float = 64.0
var grid_pos: Vector2i = Vector2i.ZERO

# -- Piece colors (indexed by piece_type) --------------------------------------
const PIECE_COLORS: Array[Color] = [
	Color.RED,
	Color.DODGER_BLUE,
	Color.LIME_GREEN,
	Color.GOLD,
	Color.MEDIUM_PURPLE,
	Color.ORANGE_RED,
	Color.CYAN,
	Color.HOT_PINK,
]

# -- State ---------------------------------------------------------------------
var _is_selected: bool = false
var _is_hinting: bool = false
var _move_tween: Tween = null
var _is_destroyed: bool = false

# -- Visual sizes --------------------------------------------------------------
var _inner_margin: float = 4.0
var _corner_radius: float = 8.0


func _ready() -> void:
	update_visuals()


func _draw() -> void:
	if _is_destroyed:
		return

	var half := cell_size * 0.5 - _inner_margin
	var rect := Rect2(-half, -half, half * 2, half * 2)
	var color := _get_color()

	# Main piece body
	draw_rect(rect, color, true)

	# Inner highlight (lighter)
	var inner_rect := rect.grow(-6)
	draw_rect(inner_rect, color.lightened(0.25), true)

	# Selection border
	if _is_selected:
		draw_rect(rect, Color.WHITE, false, 3.0)

	# Hint glow
	if _is_hinting:
		draw_rect(rect.grow(2), Color(1, 1, 1, 0.5), false, 2.0)


# -- Color helper --------------------------------------------------------------

func _get_color() -> Color:
	if piece_type >= 0 and piece_type < PIECE_COLORS.size():
		return PIECE_COLORS[piece_type]
	# Procedural color for types beyond the palette
	var hue := fmod(piece_type * 0.618033988749895, 1.0)
	return Color.from_hsv(hue, 0.7, 0.9)


# -- Public API ----------------------------------------------------------------

func update_visuals() -> void:
	queue_redraw()


func set_selected(selected: bool) -> void:
	_is_selected = selected
	queue_redraw()
	if selected:
		var tw := create_tween()
		tw.tween_property(self, "scale", Vector2(1.1, 1.1), 0.1)
		tw.tween_property(self, "scale", Vector2.ONE, 0.1)


func highlight_hint() -> void:
	_is_hinting = true
	queue_redraw()
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.5, 0.2)
	tw.tween_property(self, "modulate:a", 1.0, 0.2)
	tw.set_loops(3)
	tw.tween_callback(func():
		_is_hinting = false
		queue_redraw()
	)


func animate_to(target_pos: Vector2, duration: float = 0.2) -> void:
	"""Smoothly move this piece to a new position."""
	if _move_tween and _move_tween.is_valid():
		_move_tween.kill()
	_move_tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_move_tween.tween_property(self, "position", target_pos, duration)


func destroy() -> void:
	"""Play destruction animation then queue_free."""
	_is_destroyed = true
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(self, "scale", Vector2.ZERO, 0.25).set_ease(Tween.EASE_IN)
	tw.tween_property(self, "modulate:a", 0.0, 0.25)
	tw.chain().tween_callback(queue_free)
