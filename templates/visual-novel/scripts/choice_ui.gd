## Visual Novel Choice UI
##
## Displays branching choices as clickable buttons. Connect to a
## DialogueManager's `choice_presented` signal and wire `_on_choice_pressed`
## back to `DialogueManager.select_choice()`.
##
## Attach to a VBoxContainer (or any Container). Buttons are created
## dynamically when choices are presented and removed when one is selected.
class_name ChoiceUI
extends VBoxContainer

# -- Config --------------------------------------------------------------------
@export var button_theme: Theme = null
@export var fade_in_duration: float = 0.3
@export var button_min_width: float = 400.0
@export var button_min_height: float = 50.0

# -- References ----------------------------------------------------------------
@export var dialogue_manager_path: NodePath = ""

# -- State ---------------------------------------------------------------------
var _dialogue_manager: DialogueManager = null
var _buttons: Array[Button] = []

# -- Signals -------------------------------------------------------------------
signal choice_made(index: int, text: String)


func _ready() -> void:
	# Try to find DialogueManager
	if dialogue_manager_path != "":
		_dialogue_manager = get_node_or_null(dialogue_manager_path) as DialogueManager
	if _dialogue_manager == null:
		# Search upward
		_dialogue_manager = _find_ancestor(DialogueManager)
	if _dialogue_manager == null:
		# Search in scene
		_dialogue_manager = _find_in_tree(get_tree().root, DialogueManager)

	if _dialogue_manager:
		_dialogue_manager.choice_presented.connect(_on_choices_presented)
		_dialogue_manager.dialogue_ended.connect(_clear_choices)

	visible = false


# -- Display choices -----------------------------------------------------------

func _on_choices_presented(choices: Array) -> void:
	_clear_choices()
	visible = true

	for i in range(choices.size()):
		var choice: Dictionary = choices[i]
		var btn := Button.new()
		btn.text = choice.get("text", "Choice %d" % (i + 1))
		btn.custom_minimum_size = Vector2(button_min_width, button_min_height)
		btn.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		btn.focus_mode = Control.FOCUS_ALL

		if button_theme:
			btn.theme = button_theme

		# Fade-in animation
		btn.modulate.a = 0.0
		var tw := create_tween()
		tw.tween_property(btn, "modulate:a", 1.0, fade_in_duration).set_delay(i * 0.1)

		# Connect click
		var idx := i  # capture loop variable
		btn.pressed.connect(_on_choice_pressed.bind(idx, btn.text))

		add_child(btn)
		_buttons.append(btn)

	# Focus the first button
	if _buttons.size() > 0:
		_buttons[0].grab_focus()


func _on_choice_pressed(index: int, text: String) -> void:
	choice_made.emit(index, text)
	if _dialogue_manager:
		_dialogue_manager.select_choice(index)
	_clear_choices()


func _clear_choices() -> void:
	for btn in _buttons:
		if is_instance_valid(btn):
			btn.queue_free()
	_buttons.clear()
	visible = false


# -- Input: allow keyboard navigation -----------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if not visible or _buttons.is_empty():
		return

	if event.is_action_pressed("ui_up"):
		_move_focus(-1)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("ui_down"):
		_move_focus(1)
		get_viewport().set_input_as_handled()


func _move_focus(direction: int) -> void:
	var focused := get_viewport().gui_get_focus_owner()
	var current_idx := -1
	for i in range(_buttons.size()):
		if _buttons[i] == focused:
			current_idx = i
			break
	if current_idx == -1:
		_buttons[0].grab_focus()
		return

	var next_idx := clampi(current_idx + direction, 0, _buttons.size() - 1)
	_buttons[next_idx].grab_focus()


# -- Utility: find node helpers ------------------------------------------------

func _find_ancestor(type: Variant) -> Node:
	var node := get_parent()
	while node:
		if is_instance_of(node, type):
			return node
		node = node.get_parent()
	return null


func _find_in_tree(root: Node, type: Variant) -> Node:
	if is_instance_of(root, type):
		return root
	for child in root.get_children():
		var found := _find_in_tree(child, type)
		if found:
			return found
	return null
