## Game Manager — global score, lives, and level flow for 2D Platformer.
##
## Add as an autoload singleton (Project > Project Settings > Autoload).
## Other scripts access it via `GameManager.add_score(10)` etc.
class_name PlatformerGameManager
extends Node

# -- Signals -------------------------------------------------------------------
signal score_changed(new_score: int)
signal lives_changed(new_lives: int)
signal game_over
signal level_completed

# -- Config --------------------------------------------------------------------
@export var starting_lives: int = 3
@export var starting_level: int = 0

# -- State ---------------------------------------------------------------------
var score: int = 0 : set = _set_score
var lives: int = 3 : set = _set_lives
var current_level: int = 0
var is_game_over: bool = false

# Level list — populate with your scene paths
var levels: PackedStringArray = PackedStringArray([
	# "res://levels/level_01.tscn",
	# "res://levels/level_02.tscn",
])


func _ready() -> void:
	reset_game()


# -- Score ---------------------------------------------------------------------

func add_score(amount: int) -> void:
	score += amount


func _set_score(value: int) -> void:
	score = maxi(value, 0)
	score_changed.emit(score)


# -- Lives ---------------------------------------------------------------------

func lose_life() -> void:
	if is_game_over:
		return
	lives -= 1
	if lives <= 0:
		_trigger_game_over()
	else:
		restart_level()


func add_life() -> void:
	lives += 1


func _set_lives(value: int) -> void:
	lives = value
	lives_changed.emit(lives)


# -- Level flow ----------------------------------------------------------------

func restart_level() -> void:
	get_tree().reload_current_scene()


func next_level() -> void:
	current_level += 1
	if current_level < levels.size():
		get_tree().change_scene_to_file(levels[current_level])
	else:
		level_completed.emit()


func go_to_level(index: int) -> void:
	if index >= 0 and index < levels.size():
		current_level = index
		get_tree().change_scene_to_file(levels[current_level])


# -- Game state ----------------------------------------------------------------

func reset_game() -> void:
	score = 0
	lives = starting_lives
	current_level = starting_level
	is_game_over = false


func _trigger_game_over() -> void:
	is_game_over = true
	game_over.emit()


# -- Pause / Unpause ----------------------------------------------------------

func pause() -> void:
	get_tree().paused = true


func unpause() -> void:
	get_tree().paused = false


func toggle_pause() -> void:
	get_tree().paused = not get_tree().paused
