@tool
class_name GodotForgeNPC
extends Node
## NPC AI node: adds LLM-driven dialogue and behavior to any NPC.
##
## Supports two modes:
## 1. Local GGUF model via GdLlama (offline, fast, limited)
## 2. Remote API via HTTP (online, high quality, requires server)

signal response_ready(text: String)
signal thinking_started()
signal thinking_finished()

enum AIMode { LOCAL, REMOTE }

@export var character_name: String = "NPC"
@export_multiline var character_description: String = ""
@export_multiline var character_knowledge: String = ""
@export var ai_mode: AIMode = AIMode.REMOTE
@export_file("*.gguf") var model_path: String = ""
@export var api_url: String = "http://localhost:8100"
@export var max_response_length: int = 100
@export var temperature: float = 0.7

var _conversation_history: Array[Dictionary] = []
var _is_thinking: bool = false
var _gdllama: Node = null  # GdLlama instance (if available)


func _ready() -> void:
	if ai_mode == AIMode.LOCAL and not model_path.is_empty():
		_init_local_model()


func _init_local_model() -> void:
	# Try to load GdLlama plugin
	if ClassDB.class_exists("GdLlama"):
		_gdllama = ClassDB.instantiate("GdLlama")
		_gdllama.set("model_path", model_path)
		_gdllama.set("n_predict", max_response_length)
		_gdllama.set("temperature", temperature)
		add_child(_gdllama)
		if _gdllama.has_signal("generate_text_finished"):
			_gdllama.connect("generate_text_finished", _on_local_response)
		print("[NPC AI] Local model loaded for %s" % character_name)
	else:
		push_warning("[NPC AI] GdLlama not available. Install gdllama addon for local inference.")
		ai_mode = AIMode.REMOTE


func _get_system_prompt() -> String:
	var prompt := "You are %s." % character_name
	if not character_description.is_empty():
		prompt += " %s" % character_description
	if not character_knowledge.is_empty():
		prompt += "\n\nYour knowledge:\n%s" % character_knowledge
	prompt += "\n\nRules:\n"
	prompt += "- Stay in character at all times.\n"
	prompt += "- Keep responses under %d words.\n" % max_response_length
	prompt += "- Be conversational and engaging.\n"
	prompt += "- If asked about things outside your knowledge, deflect in character."
	return prompt


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

func chat(player_message: String) -> String:
	"""Synchronous chat — blocks until response is ready.
	Use chat_async() for non-blocking dialogue."""
	if ai_mode == AIMode.LOCAL:
		return _chat_local_sync(player_message)
	else:
		return await _chat_remote(player_message)


func chat_async(player_message: String) -> void:
	"""Async chat — emits response_ready when done."""
	_is_thinking = true
	thinking_started.emit()

	if ai_mode == AIMode.LOCAL:
		_chat_local_async(player_message)
	else:
		var response := await _chat_remote(player_message)
		_is_thinking = false
		thinking_finished.emit()
		response_ready.emit(response)


func reset_conversation() -> void:
	"""Clear conversation history."""
	_conversation_history.clear()


func get_conversation_history() -> Array[Dictionary]:
	return _conversation_history.duplicate()


var is_thinking: bool:
	get: return _is_thinking


# ------------------------------------------------------------------
# Local inference (GdLlama)
# ------------------------------------------------------------------

func _chat_local_sync(player_message: String) -> String:
	if not _gdllama:
		return "[No AI model loaded]"

	_conversation_history.append({"role": "user", "content": player_message})
	var system := _get_system_prompt()
	var response: String = _gdllama.call("generate_text", player_message, system, "")
	_conversation_history.append({"role": "assistant", "content": response})
	return response


func _chat_local_async(player_message: String) -> void:
	if not _gdllama:
		_is_thinking = false
		thinking_finished.emit()
		response_ready.emit("[No AI model loaded]")
		return

	_conversation_history.append({"role": "user", "content": player_message})
	var system := _get_system_prompt()
	_gdllama.call("run_generate_text", player_message, system, "")


func _on_local_response(text: String) -> void:
	_conversation_history.append({"role": "assistant", "content": text})
	_is_thinking = false
	thinking_finished.emit()
	response_ready.emit(text)


# ------------------------------------------------------------------
# Remote inference (API)
# ------------------------------------------------------------------

func _chat_remote(player_message: String) -> String:
	_conversation_history.append({"role": "user", "content": player_message})

	var request_body := {
		"character_name": character_name,
		"character_description": character_description,
		"character_knowledge": character_knowledge,
		"player_message": player_message,
		"conversation_history": _conversation_history,
		"max_length": max_response_length,
		"temperature": temperature,
	}

	var http := HTTPRequest.new()
	add_child(http)

	var body := JSON.stringify(request_body)
	var err := http.request(
		api_url + "/api/v1/npcai/dialogue",
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		body,
	)

	if err != OK:
		http.queue_free()
		var fallback := "[%s looks confused]" % character_name
		_conversation_history.append({"role": "assistant", "content": fallback})
		return fallback

	# Wait for response
	var result: Array = await http.request_completed
	http.queue_free()

	var code: int = result[1]
	var response_body: PackedByteArray = result[3]

	if code != 200:
		var fallback := "[%s is unable to respond right now]" % character_name
		_conversation_history.append({"role": "assistant", "content": fallback})
		return fallback

	var data := JSON.parse_string(response_body.get_string_from_utf8())
	var response_text: String = ""
	if data is Dictionary:
		response_text = data.get("response", data.get("dialogue", ""))
	if response_text.is_empty():
		response_text = "[%s remains silent]" % character_name

	_conversation_history.append({"role": "assistant", "content": response_text})
	return response_text
