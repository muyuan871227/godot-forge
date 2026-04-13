## Visual Novel Dialogue Manager
##
## Drives the visual novel experience: loads a JSON script, displays dialogue
## with a typewriter effect, handles branching choices, and manages
## background/character display commands.
##
## JSON script format (array of steps):
## [
##   {"speaker": "Narrator", "text": "It was a dark and stormy night..."},
##   {"speaker": "Alice", "text": "Who's there?", "portrait": "alice_surprised"},
##   {"command": "bg", "value": "res://backgrounds/forest.png"},
##   {"command": "portrait", "character": "Alice", "position": "left", "expression": "happy"},
##   {
##     "speaker": "Alice", "text": "Which path should we take?",
##     "choices": [
##       {"text": "Go left",  "jump": "path_left"},
##       {"text": "Go right", "jump": "path_right"}
##     ]
##   },
##   {"command": "label", "value": "path_left"},
##   {"speaker": "Narrator", "text": "You chose the left path..."},
##   {"command": "end"}
## ]
class_name DialogueManager
extends Node

# -- Config --------------------------------------------------------------------
@export var text_speed: float = 0.03              ## seconds per character
@export var auto_advance_delay: float = 2.0       ## delay before auto-advance
@export var script_path: String = ""              ## path to JSON script file

# -- State ---------------------------------------------------------------------
var _steps: Array = []
var _current_index: int = 0
var _is_typing: bool = false
var _auto_mode: bool = false
var _skip_mode: bool = false
var _waiting_for_choice: bool = false
var _labels: Dictionary = {}       # label_name -> step index
var _variables: Dictionary = {}    # for conditional logic

# -- Signals -------------------------------------------------------------------
signal dialogue_started
signal dialogue_line(speaker: String, text: String)
signal dialogue_typing_finished
signal choice_presented(choices: Array)
signal choice_selected(index: int, text: String)
signal background_changed(path: String)
signal portrait_changed(character: String, position: String, expression: String)
signal dialogue_ended

# -- Typing tween reference ----------------------------------------------------
var _type_tween: Tween = null


func _ready() -> void:
	if script_path != "":
		load_script(script_path)


func _unhandled_input(event: InputEvent) -> void:
	if _waiting_for_choice:
		return

	if event.is_action_pressed("vn_advance"):
		if _is_typing:
			# Skip to end of current line
			_finish_typing()
		else:
			advance()

	if event.is_action_pressed("vn_auto"):
		_auto_mode = not _auto_mode
		_skip_mode = false

	if event.is_action_pressed("vn_skip"):
		_skip_mode = not _skip_mode
		_auto_mode = false
		if _skip_mode:
			_finish_typing()
			advance()


# -- Script loading ------------------------------------------------------------

func load_script(path: String) -> void:
	"""Load a JSON dialogue script from the given resource path."""
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("DialogueManager: Cannot open script at %s" % path)
		return
	var json := JSON.new()
	var err := json.parse(file.get_as_text())
	file.close()
	if err != OK:
		push_error("DialogueManager: JSON parse error — %s" % json.get_error_message())
		return

	_steps = json.data if json.data is Array else []
	_build_label_index()
	_current_index = 0
	dialogue_started.emit()
	_process_step()


func load_script_from_array(steps: Array) -> void:
	"""Load dialogue steps directly from a GDScript array."""
	_steps = steps
	_build_label_index()
	_current_index = 0
	dialogue_started.emit()
	_process_step()


# -- Advance -------------------------------------------------------------------

func advance() -> void:
	"""Move to the next step."""
	if _waiting_for_choice or _current_index >= _steps.size():
		return
	_current_index += 1
	_process_step()


func jump_to_label(label_name: String) -> void:
	"""Jump to a named label in the script."""
	if label_name in _labels:
		_current_index = _labels[label_name]
		_process_step()
	else:
		push_warning("DialogueManager: Label '%s' not found" % label_name)
		advance()


# -- Step processing -----------------------------------------------------------

func _process_step() -> void:
	if _current_index >= _steps.size():
		dialogue_ended.emit()
		return

	var step: Dictionary = _steps[_current_index]

	# Command steps
	if step.has("command"):
		_handle_command(step)
		return

	# Dialogue steps
	var speaker: String = step.get("speaker", "")
	var text: String = step.get("text", "")

	dialogue_line.emit(speaker, text)
	_start_typing(text)

	# Portrait hint
	if step.has("portrait"):
		portrait_changed.emit(speaker, "center", step["portrait"])

	# Choices
	if step.has("choices"):
		_waiting_for_choice = true
		choice_presented.emit(step["choices"])


func _handle_command(step: Dictionary) -> void:
	var cmd: String = step["command"]

	match cmd:
		"bg":
			background_changed.emit(step.get("value", ""))
			_current_index += 1
			_process_step()
		"portrait":
			portrait_changed.emit(
				step.get("character", ""),
				step.get("position", "center"),
				step.get("expression", "default"),
			)
			_current_index += 1
			_process_step()
		"label":
			# Labels are just markers — skip over them
			_current_index += 1
			_process_step()
		"set":
			_variables[step.get("var", "")] = step.get("value", "")
			_current_index += 1
			_process_step()
		"jump":
			jump_to_label(step.get("value", ""))
		"wait":
			var seconds: float = step.get("value", 1.0)
			await get_tree().create_timer(seconds).timeout
			_current_index += 1
			_process_step()
		"end":
			dialogue_ended.emit()
		_:
			push_warning("DialogueManager: Unknown command '%s'" % cmd)
			_current_index += 1
			_process_step()


# -- Choice handling -----------------------------------------------------------

func select_choice(index: int) -> void:
	"""Called by the ChoiceUI when the player picks an option."""
	if not _waiting_for_choice:
		return
	var step: Dictionary = _steps[_current_index]
	var choices: Array = step.get("choices", [])
	if index < 0 or index >= choices.size():
		return

	_waiting_for_choice = false
	var chosen: Dictionary = choices[index]
	choice_selected.emit(index, chosen.get("text", ""))

	if chosen.has("jump"):
		jump_to_label(chosen["jump"])
	else:
		advance()


# -- Typewriter ----------------------------------------------------------------

func _start_typing(text: String) -> void:
	_is_typing = true
	if _skip_mode:
		_finish_typing()
		return

	# We emit text character count via a dummy property tween
	# The actual display is handled by whoever listens to dialogue_line + typing_finished
	var duration := text.length() * text_speed
	if duration <= 0.0:
		_finish_typing()
		return

	if _type_tween and _type_tween.is_valid():
		_type_tween.kill()
	_type_tween = create_tween()
	_type_tween.tween_interval(duration)
	_type_tween.tween_callback(_finish_typing)


func _finish_typing() -> void:
	if _type_tween and _type_tween.is_valid():
		_type_tween.kill()
	_is_typing = false
	dialogue_typing_finished.emit()

	# Auto advance
	if _auto_mode and not _waiting_for_choice:
		await get_tree().create_timer(auto_advance_delay).timeout
		if _auto_mode:
			advance()

	# Skip mode — keep advancing
	if _skip_mode and not _waiting_for_choice:
		advance()


# -- Label index ---------------------------------------------------------------

func _build_label_index() -> void:
	_labels.clear()
	for i in range(_steps.size()):
		var step: Dictionary = _steps[i]
		if step.get("command", "") == "label":
			_labels[step.get("value", "")] = i


# -- Save / Load state ---------------------------------------------------------

func get_save_data() -> Dictionary:
	return {
		"script_path": script_path,
		"current_index": _current_index,
		"variables": _variables.duplicate(),
	}


func load_save_data(data: Dictionary) -> void:
	_variables = data.get("variables", {})
	_current_index = data.get("current_index", 0)
	var path: String = data.get("script_path", "")
	if path != "" and path != script_path:
		load_script(path)
	else:
		_process_step()
