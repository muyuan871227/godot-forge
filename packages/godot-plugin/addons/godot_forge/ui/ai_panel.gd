@tool
extends VBoxContainer
## AI Assistant chat panel — full flow: gather editor context, send to AI
## service, render response with per-file code blocks and "Apply" buttons.

signal code_applied(path: String)

const CONFIG_PATH := "res://addons/godot_forge/settings.cfg"

@onready var status_label: Label = $StatusBar/StatusLabel
@onready var settings_button: Button = $StatusBar/SettingsButton
@onready var chat_log: RichTextLabel = $ChatLog
@onready var chat_input: TextEdit = $InputArea/ChatInput
@onready var send_button: Button = $InputArea/SendButton

var is_connected := false

## AI service configuration (loaded from settings.cfg)
var _api_url: String = "http://localhost:8100"
var _api_key: String = ""
var _llm_provider: String = "anthropic"

## Tracks pending code blocks from the last AI response.
## Each entry: { "path": String, "content": String, "language": String }
var _pending_code_blocks: Array[Dictionary] = []

## Container that holds per-file "Apply" buttons after a response.
var _apply_container: VBoxContainer

var _http: HTTPRequest
var _is_waiting := false


func _ready() -> void:
	send_button.pressed.connect(_on_send)
	chat_input.gui_input.connect(_on_input_key)

	if settings_button:
		settings_button.pressed.connect(_on_settings_pressed)

	# Create a container for apply buttons (added after ChatLog)
	_apply_container = VBoxContainer.new()
	_apply_container.name = "ApplyContainer"
	add_child(_apply_container)
	move_child(_apply_container, chat_log.get_index() + 1)

	_load_settings()
	set_connection_status(false)


# ------------------------------------------------------------------
# Connection status (called by plugin.gd)
# ------------------------------------------------------------------

func set_connection_status(connected: bool) -> void:
	is_connected = connected
	if status_label:
		status_label.text = "● MCP Connected" if connected else "○ MCP Disconnected"
		status_label.modulate = Color.GREEN if connected else Color.RED


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------

func _load_settings() -> void:
	var config := ConfigFile.new()
	if config.load(CONFIG_PATH) != OK:
		return
	_api_url = config.get_value("ai", "api_url", _api_url)
	_api_key = config.get_value("ai", "api_key", _api_key)
	_llm_provider = config.get_value("ai", "llm_provider", _llm_provider)


func _on_settings_pressed() -> void:
	# The plugin.gd opens the settings dialog; emit a signal or call up.
	# For now just reload from disk.
	_load_settings()
	_append_system("Settings reloaded from disk.")


func apply_settings(settings: Dictionary) -> void:
	_api_url = settings.get("api_url", _api_url)
	_api_key = settings.get("api_key", _api_key)
	_llm_provider = settings.get("llm_provider", _llm_provider)


# ------------------------------------------------------------------
# Chat input handling
# ------------------------------------------------------------------

func _on_input_key(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		# Ctrl+Enter / Cmd+Enter to send
		if event.keycode == KEY_ENTER and (event.ctrl_pressed or event.meta_pressed):
			_on_send()
			get_viewport().set_input_as_handled()


func _on_send() -> void:
	var text := chat_input.text.strip_edges()
	if text.is_empty() or _is_waiting:
		return

	_append_user(text)
	chat_input.text = ""
	_clear_apply_buttons()

	# Gather context from the currently open editor state
	var context := _gather_context()

	_is_waiting = true
	send_button.disabled = true
	_append_system("Thinking...")

	_send_to_ai(text, context)


# ------------------------------------------------------------------
# Context gathering — snapshot of the current editor state
# ------------------------------------------------------------------

func _gather_context() -> Dictionary:
	var context := {}

	# Current scene info
	var editor := EditorInterface
	var root: Node = null
	if Engine.is_editor_hint():
		root = EditorInterface.get_edited_scene_root()
	if root:
		context["current_scene"] = {
			"path": root.scene_file_path,
			"root_type": root.get_class(),
			"root_name": root.name,
			"node_count": _count_nodes(root),
		}
		# Flat list of top-level children
		var children: Array[Dictionary] = []
		for child in root.get_children():
			children.append({
				"name": child.name,
				"type": child.get_class(),
				"has_script": child.get_script() != null,
			})
		context["scene_children"] = children

	# Currently open script
	if Engine.is_editor_hint():
		var script_editor := EditorInterface.get_script_editor()
		if script_editor:
			var current_script := script_editor.get_current_script()
			if current_script:
				context["open_script"] = {
					"path": current_script.resource_path,
					"content": current_script.source_code,
					"base_type": current_script.get_instance_base_type(),
				}

	# Project info
	context["project"] = {
		"name": ProjectSettings.get_setting("application/config/name", "Untitled"),
		"main_scene": ProjectSettings.get_setting("application/run/main_scene", ""),
		"godot_version": Engine.get_version_info().get("string", "4.x"),
	}

	return context


func _count_nodes(node: Node) -> int:
	var count := 1
	for child in node.get_children():
		count += _count_nodes(child)
	return count


# ------------------------------------------------------------------
# AI service HTTP request
# ------------------------------------------------------------------

func _send_to_ai(user_message: String, context: Dictionary) -> void:
	if _http:
		_http.queue_free()
	_http = HTTPRequest.new()
	_http.timeout = 60.0
	add_child(_http)
	_http.request_completed.connect(_on_ai_raw_response)

	var payload := {
		"messages": [
			{
				"role": "system",
				"content": _build_system_prompt(),
			},
			{
				"role": "user",
				"content": user_message,
			},
		],
		"context": context,
		"provider": _llm_provider,
		"stream": false,
	}

	var headers: PackedStringArray = ["Content-Type: application/json"]
	if not _api_key.is_empty():
		headers.append("Authorization: Bearer %s" % _api_key)

	var body := JSON.stringify(payload)
	var endpoint := _api_url + "/api/v1/codegen/chat"
	var err := _http.request(endpoint, headers, HTTPClient.METHOD_POST, body)
	if err != OK:
		_is_waiting = false
		send_button.disabled = false
		_append_system("Failed to send request (error %d). Check AI Service URL in settings." % err)


func _build_system_prompt() -> String:
	return (
		"You are GodotForge AI, an expert Godot 4.x game development assistant. "
		+ "When the user asks you to create or modify game code, respond with "
		+ "clearly delimited code blocks using triple backticks and a file path "
		+ "comment on the first line, like:\n"
		+ "```gdscript\n"
		+ "# res://scripts/player.gd\n"
		+ "extends CharacterBody2D\n"
		+ "...\n"
		+ "```\n"
		+ "Always use GDScript (Godot 4.4 syntax) with typed variables and signals. "
		+ "Provide complete, runnable files. If you modify an existing file, include "
		+ "the full updated content."
	)


# ------------------------------------------------------------------
# AI response handling
# ------------------------------------------------------------------

func _on_ai_raw_response(result: int, code: int, _headers: PackedStringArray,
		body: PackedByteArray) -> void:
	_is_waiting = false
	send_button.disabled = false
	if _http:
		_http.queue_free()
		_http = null

	# Remove the "Thinking..." line
	_remove_last_system_line()

	if result != HTTPRequest.RESULT_SUCCESS:
		_append_system("Network error (result %d). Is the AI service running?" % result)
		return
	if code != 200:
		_append_system("AI service returned HTTP %d." % code)
		return

	var json := JSON.parse_string(body.get_string_from_utf8())
	if json == null or not json is Dictionary:
		_append_system("Invalid response from AI service.")
		return

	# Extract the assistant message
	var message: String = ""
	if json.has("message"):
		message = json["message"]
	elif json.has("choices") and json["choices"] is Array:
		var choices: Array = json["choices"]
		if not choices.is_empty():
			message = choices[0].get("message", {}).get("content", "")
	elif json.has("content"):
		message = json["content"]

	if message.is_empty():
		_append_system("Empty response from AI service.")
		return

	_on_ai_response(message)


func _on_ai_response(message: String) -> void:
	# Parse code blocks from the response
	_pending_code_blocks = _extract_code_blocks(message)

	# Render the full message in the chat log with BBCode
	_append_assistant(message)

	# Create "Apply" buttons for each code block that has a file path
	_clear_apply_buttons()
	for i in range(_pending_code_blocks.size()):
		var block := _pending_code_blocks[i]
		var path: String = block.get("path", "")
		if path.is_empty():
			continue
		var btn := Button.new()
		btn.text = "Apply: %s" % path
		btn.tooltip_text = "Write this code block to %s" % path
		btn.pressed.connect(_on_apply_code.bind(i))
		_apply_container.add_child(btn)


# ------------------------------------------------------------------
# Code block extraction
# ------------------------------------------------------------------

## Parse markdown-style fenced code blocks from AI text.
## Looks for a file path comment (# res://...) on the first content line.
func _extract_code_blocks(text: String) -> Array[Dictionary]:
	var blocks: Array[Dictionary] = []
	var lines := text.split("\n")
	var in_block := false
	var current_lang := ""
	var current_lines: PackedStringArray = []
	var current_path := ""

	for line in lines:
		var trimmed := line.strip_edges()
		if not in_block and trimmed.begins_with("```"):
			in_block = true
			current_lang = trimmed.substr(3).strip_edges()
			current_lines = PackedStringArray()
			current_path = ""
		elif in_block and trimmed.begins_with("```"):
			in_block = false
			var content := "\n".join(current_lines)
			blocks.append({
				"language": current_lang,
				"content": content,
				"path": current_path,
			})
		elif in_block:
			# Check first non-empty line for a path comment
			if current_lines.is_empty() and trimmed.begins_with("#"):
				var possible_path := trimmed.trim_prefix("#").strip_edges()
				if possible_path.begins_with("res://"):
					current_path = possible_path
			current_lines.append(line)

	# Handle unclosed code block
	if in_block and not current_lines.is_empty():
		blocks.append({
			"language": current_lang,
			"content": "\n".join(current_lines),
			"path": current_path,
		})

	return blocks


# ------------------------------------------------------------------
# Apply code to disk
# ------------------------------------------------------------------

func _on_apply_code(block_index: int) -> void:
	if block_index < 0 or block_index >= _pending_code_blocks.size():
		return
	var block := _pending_code_blocks[block_index]
	var path: String = block.get("path", "")
	var content: String = block.get("content", "")
	if path.is_empty() or content.is_empty():
		_append_system("Cannot apply: missing path or content.")
		return

	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		_append_system("Failed to write to %s" % path)
		return
	file.store_string(content)
	file.close()

	# Trigger filesystem rescan so the editor picks up the change
	if Engine.is_editor_hint():
		EditorInterface.get_resource_filesystem().scan()

	_append_system("Applied code to %s" % path)
	code_applied.emit(path)

	# Disable the button to avoid double-apply
	var buttons := _apply_container.get_children()
	for btn in buttons:
		if btn is Button and btn.text.ends_with(path):
			btn.disabled = true
			btn.text = "(applied) %s" % path


func _clear_apply_buttons() -> void:
	for child in _apply_container.get_children():
		child.queue_free()


# ------------------------------------------------------------------
# Chat log helpers (BBCode)
# ------------------------------------------------------------------

func _append_user(text: String) -> void:
	chat_log.append_text("\n[b][color=#58a6ff]You:[/color][/b] %s\n" % _escape_bbcode(text))


func _append_assistant(text: String) -> void:
	# Render code blocks with monospace styling; leave prose as-is
	var rendered := _render_message_bbcode(text)
	chat_log.append_text("\n[b][color=#a5d6ff]AI:[/color][/b]\n%s\n" % rendered)


func _append_system(text: String) -> void:
	chat_log.append_text("[i][color=#888888]%s[/color][/i]\n" % _escape_bbcode(text))


func _remove_last_system_line() -> void:
	# Simple approach: parse the current text and remove trailing system line.
	# RichTextLabel doesn't expose line-level removal, so we reconstruct.
	var current := chat_log.text
	var idx := current.rfind("Thinking...")
	if idx >= 0:
		# Remove from that point to the end of that line
		var end := current.find("\n", idx)
		if end < 0:
			end = current.length()
		var before := current.substr(0, idx)
		var after := current.substr(end)
		chat_log.clear()
		chat_log.append_text(before + after)


## Convert AI markdown-ish text into BBCode for RichTextLabel.
func _render_message_bbcode(text: String) -> String:
	var output := ""
	var lines := text.split("\n")
	var in_code := false

	for line in lines:
		var trimmed := line.strip_edges()
		if not in_code and trimmed.begins_with("```"):
			in_code = true
			output += "[code]"
			continue
		if in_code and trimmed.begins_with("```"):
			in_code = false
			output += "[/code]\n"
			continue
		if in_code:
			output += _escape_bbcode(line) + "\n"
		else:
			# Basic markdown conversions
			var rendered_line := _escape_bbcode(line)
			# Bold **text**
			rendered_line = _replace_pattern(rendered_line, "**", "[b]", "[/b]")
			# Inline code `text`
			rendered_line = _replace_pattern(rendered_line, "`", "[code]", "[/code]")
			output += rendered_line + "\n"

	# Close unclosed code block
	if in_code:
		output += "[/code]\n"

	return output


## Replace paired delimiters with BBCode open/close tags.
func _replace_pattern(text: String, delimiter: String, open_tag: String, close_tag: String) -> String:
	var result := ""
	var parts := text.split(delimiter)
	for i in range(parts.size()):
		result += parts[i]
		if i < parts.size() - 1:
			if i % 2 == 0:
				result += open_tag
			else:
				result += close_tag
	return result


func _escape_bbcode(text: String) -> String:
	return text.replace("[", "[lb]")
