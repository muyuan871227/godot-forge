## Puzzle Manager — board state, matching, scoring, and level flow.
##
## Attach to a Node2D that acts as the board root. Pieces are spawned as
## children. The manager handles grid logic; visuals are delegated to
## PuzzlePiece nodes.
class_name PuzzleManager
extends Node2D

# -- Grid config ---------------------------------------------------------------
@export var columns: int = 8
@export var rows: int = 8
@export var cell_size: float = 64.0
@export var num_piece_types: int = 5       ## how many distinct colors / shapes
@export var match_min: int = 3             ## minimum in-a-row to count

# -- Interaction ---------------------------------------------------------------
@export_enum("swap", "drag", "slide") var interaction_mode: String = "swap"

# -- Timer ---------------------------------------------------------------------
@export var time_limit: float = 0.0        ## 0 = unlimited

# -- State ---------------------------------------------------------------------
var _board: Array = []                     ## 2D array [col][row] -> PuzzlePiece
var _selected: Vector2i = Vector2i(-1, -1)
var _moves: int = 0
var _score: int = 0
var _time_elapsed: float = 0.0
var _is_processing: bool = false           ## true while matches are resolving
var _undo_stack: Array = []
var _game_active: bool = false

# -- Signals -------------------------------------------------------------------
signal board_ready
signal pieces_matched(cells: Array, piece_type: int)
signal score_changed(new_score: int)
signal moves_changed(new_moves: int)
signal time_updated(elapsed: float, remaining: float)
signal level_complete
signal game_over


func _ready() -> void:
	_init_board()


func _process(delta: float) -> void:
	if not _game_active:
		return
	if time_limit > 0.0:
		_time_elapsed += delta
		var remaining := maxf(time_limit - _time_elapsed, 0.0)
		time_updated.emit(_time_elapsed, remaining)
		if remaining <= 0.0:
			_game_active = false
			game_over.emit()


func _unhandled_input(event: InputEvent) -> void:
	if not _game_active or _is_processing:
		return

	if event.is_action_pressed("puzzle_click"):
		var mouse_pos := get_local_mouse_position()
		var cell := _pos_to_cell(mouse_pos)
		if _is_valid_cell(cell):
			_on_cell_clicked(cell)

	if event.is_action_pressed("puzzle_undo"):
		undo()
	if event.is_action_pressed("puzzle_hint"):
		show_hint()
	if event.is_action_pressed("puzzle_restart"):
		restart()


# -- Board initialization ------------------------------------------------------

func _init_board() -> void:
	# Clear existing
	for child in get_children():
		child.queue_free()
	_board.clear()
	_moves = 0
	_score = 0
	_time_elapsed = 0.0
	_undo_stack.clear()
	_is_processing = false

	# Create grid
	_board.resize(columns)
	for x in range(columns):
		_board[x] = []
		_board[x].resize(rows)
		for y in range(rows):
			var piece_type := randi_range(0, num_piece_types - 1)
			var piece := _create_piece(x, y, piece_type)
			_board[x][y] = piece

	# Remove initial matches
	_remove_initial_matches()
	_game_active = true
	board_ready.emit()


func _remove_initial_matches() -> void:
	"""Re-roll pieces that form matches on the initial board."""
	for x in range(columns):
		for y in range(rows):
			var attempts := 0
			while attempts < 20 and _has_match_at(x, y):
				var piece: PuzzlePiece = _board[x][y]
				piece.piece_type = randi_range(0, num_piece_types - 1)
				piece.update_visuals()
				attempts += 1


func _has_match_at(x: int, y: int) -> bool:
	"""Check if placing the current piece type at (x,y) creates a match."""
	var t: int = _board[x][y].piece_type

	# Horizontal check
	var h_count := 1
	var cx := x - 1
	while cx >= 0 and _board[cx][y] != null and _board[cx][y].piece_type == t:
		h_count += 1
		cx -= 1
	cx = x + 1
	while cx < columns and _board[cx][y] != null and _board[cx][y].piece_type == t:
		h_count += 1
		cx += 1
	if h_count >= match_min:
		return true

	# Vertical check
	var v_count := 1
	var cy := y - 1
	while cy >= 0 and _board[x][cy] != null and _board[x][cy].piece_type == t:
		v_count += 1
		cy -= 1
	cy = y + 1
	while cy < rows and _board[x][cy] != null and _board[x][cy].piece_type == t:
		v_count += 1
		cy += 1
	if v_count >= match_min:
		return true

	return false


# -- Piece factory -------------------------------------------------------------

func _create_piece(col: int, row: int, piece_type: int) -> PuzzlePiece:
	var piece := PuzzlePiece.new()
	piece.grid_pos = Vector2i(col, row)
	piece.piece_type = piece_type
	piece.cell_size = cell_size
	piece.position = _cell_to_pos(Vector2i(col, row))
	add_child(piece)
	return piece


# -- Coordinate helpers --------------------------------------------------------

func _cell_to_pos(cell: Vector2i) -> Vector2:
	return Vector2(cell.x * cell_size + cell_size * 0.5, cell.y * cell_size + cell_size * 0.5)


func _pos_to_cell(pos: Vector2) -> Vector2i:
	return Vector2i(int(pos.x / cell_size), int(pos.y / cell_size))


func _is_valid_cell(cell: Vector2i) -> bool:
	return cell.x >= 0 and cell.x < columns and cell.y >= 0 and cell.y < rows


# -- Interaction: click to select/swap -----------------------------------------

func _on_cell_clicked(cell: Vector2i) -> void:
	if _selected == Vector2i(-1, -1):
		_selected = cell
		var piece: PuzzlePiece = _board[cell.x][cell.y]
		if piece:
			piece.set_selected(true)
	else:
		if _is_adjacent(_selected, cell):
			_swap_and_check(_selected, cell)
		else:
			# Deselect old, select new
			var old_piece: PuzzlePiece = _board[_selected.x][_selected.y]
			if old_piece:
				old_piece.set_selected(false)
			_selected = cell
			var new_piece: PuzzlePiece = _board[cell.x][cell.y]
			if new_piece:
				new_piece.set_selected(true)


func _is_adjacent(a: Vector2i, b: Vector2i) -> bool:
	return absi(a.x - b.x) + absi(a.y - b.y) == 1


# -- Swap and match resolution -------------------------------------------------

func _swap_and_check(a: Vector2i, b: Vector2i) -> void:
	_is_processing = true

	# Deselect
	var piece_a: PuzzlePiece = _board[a.x][a.y]
	var piece_b: PuzzlePiece = _board[b.x][b.y]
	if piece_a:
		piece_a.set_selected(false)
	_selected = Vector2i(-1, -1)

	# Save undo state
	_undo_stack.append({"a": a, "b": b})

	# Perform swap
	_swap_pieces(a, b)
	_moves += 1
	moves_changed.emit(_moves)

	# Check for matches
	var matches := _find_all_matches()
	if matches.is_empty():
		# No match — swap back
		_swap_pieces(a, b)
		_moves -= 1
		moves_changed.emit(_moves)
		_undo_stack.pop_back()
		_is_processing = false
	else:
		# Resolve matches in a loop
		await _resolve_matches_loop()
		_is_processing = false

		# Check win condition
		if _check_win():
			_game_active = false
			level_complete.emit()


func _swap_pieces(a: Vector2i, b: Vector2i) -> void:
	var tmp: PuzzlePiece = _board[a.x][a.y]
	_board[a.x][a.y] = _board[b.x][b.y]
	_board[b.x][b.y] = tmp

	if _board[a.x][a.y]:
		_board[a.x][a.y].grid_pos = a
		_board[a.x][a.y].animate_to(_cell_to_pos(a))
	if _board[b.x][b.y]:
		_board[b.x][b.y].grid_pos = b
		_board[b.x][b.y].animate_to(_cell_to_pos(b))


# -- Match finding -------------------------------------------------------------

func _find_all_matches() -> Array:
	"""Return an array of arrays, each inner array being matched cell positions."""
	var matched_cells: Dictionary = {}  # Vector2i -> true

	# Horizontal
	for y in range(rows):
		var run_start := 0
		for x in range(1, columns + 1):
			var same := (x < columns
				and _board[x][y] != null
				and _board[run_start][y] != null
				and _board[x][y].piece_type == _board[run_start][y].piece_type)
			if not same:
				var run_len := x - run_start
				if run_len >= match_min:
					for rx in range(run_start, x):
						matched_cells[Vector2i(rx, y)] = _board[run_start][y].piece_type
				run_start = x

	# Vertical
	for x in range(columns):
		var run_start := 0
		for y in range(1, rows + 1):
			var same := (y < rows
				and _board[x][y] != null
				and _board[x][run_start] != null
				and _board[x][y].piece_type == _board[x][run_start].piece_type)
			if not same:
				var run_len := y - run_start
				if run_len >= match_min:
					for ry in range(run_start, y):
						matched_cells[Vector2i(x, ry)] = _board[x][run_start].piece_type
				run_start = y

	# Group into connected sets (simplified: just return all matched cells)
	if matched_cells.is_empty():
		return []

	var result: Array = []
	# Group by piece type for scoring
	var by_type: Dictionary = {}
	for cell: Vector2i in matched_cells.keys():
		var t: int = matched_cells[cell]
		if t not in by_type:
			by_type[t] = []
		by_type[t].append(cell)
	for t: int in by_type:
		result.append({"cells": by_type[t], "type": t})
	return result


# -- Match resolution loop -----------------------------------------------------

func _resolve_matches_loop() -> void:
	var matches := _find_all_matches()
	while not matches.is_empty():
		# Remove matched pieces
		for group in matches:
			var cells: Array = group["cells"]
			var t: int = group["type"]
			_score += cells.size() * 10
			pieces_matched.emit(cells, t)
			for cell: Vector2i in cells:
				var piece: PuzzlePiece = _board[cell.x][cell.y]
				if piece:
					piece.destroy()
					_board[cell.x][cell.y] = null

		score_changed.emit(_score)

		# Wait for destruction animation
		await get_tree().create_timer(0.3).timeout

		# Gravity: drop pieces down
		_apply_gravity()
		await get_tree().create_timer(0.25).timeout

		# Refill empty cells
		_refill_board()
		await get_tree().create_timer(0.2).timeout

		# Check for new matches
		matches = _find_all_matches()


func _apply_gravity() -> void:
	"""Drop pieces down to fill gaps."""
	for x in range(columns):
		var write_y := rows - 1
		for y in range(rows - 1, -1, -1):
			if _board[x][y] != null:
				if y != write_y:
					_board[x][write_y] = _board[x][y]
					_board[x][y] = null
					_board[x][write_y].grid_pos = Vector2i(x, write_y)
					_board[x][write_y].animate_to(_cell_to_pos(Vector2i(x, write_y)))
				write_y -= 1
		# Remaining cells above write_y are null (empty)


func _refill_board() -> void:
	"""Fill empty cells at the top with new random pieces."""
	for x in range(columns):
		for y in range(rows):
			if _board[x][y] == null:
				var t := randi_range(0, num_piece_types - 1)
				var piece := _create_piece(x, y, t)
				# Start above the board and animate down
				piece.position = _cell_to_pos(Vector2i(x, -1))
				piece.animate_to(_cell_to_pos(Vector2i(x, y)))
				_board[x][y] = piece


# -- Win condition (override for different puzzle types) -----------------------

func _check_win() -> bool:
	"""Default: no pieces of a specific type remain, or all cells are clear.
	Override this for your specific puzzle logic."""
	# For a basic match-3, the game is endless — levels end by score/moves/time
	return false


# -- Public API ----------------------------------------------------------------

func restart() -> void:
	_init_board()


func undo() -> void:
	if _undo_stack.is_empty() or _is_processing:
		return
	var last: Dictionary = _undo_stack.pop_back()
	_swap_pieces(last["a"], last["b"])
	_moves -= 1
	moves_changed.emit(_moves)


func show_hint() -> void:
	"""Highlight a pair of cells that would create a match if swapped."""
	for x in range(columns):
		for y in range(rows):
			# Try swap right
			if x + 1 < columns:
				_swap_pieces(Vector2i(x, y), Vector2i(x + 1, y))
				if not _find_all_matches().is_empty():
					_swap_pieces(Vector2i(x, y), Vector2i(x + 1, y))
					var pa: PuzzlePiece = _board[x][y]
					var pb: PuzzlePiece = _board[x + 1][y]
					if pa:
						pa.highlight_hint()
					if pb:
						pb.highlight_hint()
					return
				_swap_pieces(Vector2i(x, y), Vector2i(x + 1, y))
			# Try swap down
			if y + 1 < rows:
				_swap_pieces(Vector2i(x, y), Vector2i(x, y + 1))
				if not _find_all_matches().is_empty():
					_swap_pieces(Vector2i(x, y), Vector2i(x, y + 1))
					var pa: PuzzlePiece = _board[x][y]
					var pb: PuzzlePiece = _board[x][y + 1]
					if pa:
						pa.highlight_hint()
					if pb:
						pb.highlight_hint()
					return
				_swap_pieces(Vector2i(x, y), Vector2i(x, y + 1))


func shuffle() -> void:
	"""Randomly shuffle all pieces on the board."""
	var all_pieces: Array[PuzzlePiece] = []
	for x in range(columns):
		for y in range(rows):
			if _board[x][y] != null:
				all_pieces.append(_board[x][y])
	all_pieces.shuffle()

	var idx := 0
	for x in range(columns):
		for y in range(rows):
			if idx < all_pieces.size():
				_board[x][y] = all_pieces[idx]
				_board[x][y].grid_pos = Vector2i(x, y)
				_board[x][y].animate_to(_cell_to_pos(Vector2i(x, y)))
				idx += 1
