@tool
extends AcceptDialog
## GodotForge Settings dialog — configure AI service URL, API key,
## LLM provider, local model path, and test the connection.

signal settings_saved(settings: Dictionary)

const CONFIG_PATH := "res://addons/godot_forge/settings.cfg"
const PROVIDERS := ["anthropic", "openai", "ollama"]
const PROVIDER_LABELS := ["Anthropic Claude", "OpenAI GPT", "Ollama (Local)"]

@onready var api_url_input: LineEdit = %APIUrlInput
@onready var api_key_input: LineEdit = %APIKeyInput
@onready var provider_option: OptionButton = %ProviderOption
@onready var model_path_input: LineEdit = %ModelPathInput
@onready var model_path_label: Label = %ModelPathLabel
@onready var test_button: Button = %TestButton
@onready var status_label: Label = %StatusLabel

var current_settings := {
	"api_url": "http://localhost:8100",
	"api_key": "",
	"llm_provider": "anthropic",
	"model_path": "",
}

var _http_test: HTTPRequest


func _ready() -> void:
	title = "GodotForge Settings"
	min_size = Vector2(480, 400)
	ok_button_text = "Save"
	add_cancel_button("Cancel")

	# Populate provider dropdown
	for i in range(PROVIDER_LABELS.size()):
		provider_option.add_item(PROVIDER_LABELS[i], i)

	# Wire signals
	api_key_input.secret = true
	test_button.pressed.connect(_on_test_connection)
	confirmed.connect(_on_save)
	provider_option.item_selected.connect(_on_provider_changed)

	_load_settings()
	_apply_to_ui()
	_update_model_path_visibility()


# ------------------------------------------------------------------
# Settings persistence
# ------------------------------------------------------------------

func _load_settings() -> void:
	var config := ConfigFile.new()
	if config.load(CONFIG_PATH) != OK:
		return
	current_settings["api_url"] = config.get_value("ai", "api_url", current_settings["api_url"])
	current_settings["api_key"] = config.get_value("ai", "api_key", current_settings["api_key"])
	current_settings["llm_provider"] = config.get_value("ai", "llm_provider", current_settings["llm_provider"])
	current_settings["model_path"] = config.get_value("ai", "model_path", current_settings["model_path"])


func _apply_to_ui() -> void:
	if not is_inside_tree():
		return
	api_url_input.text = current_settings["api_url"]
	api_key_input.text = current_settings["api_key"]
	model_path_input.text = current_settings["model_path"]
	var idx := PROVIDERS.find(current_settings["llm_provider"])
	provider_option.selected = idx if idx >= 0 else 0


func _on_save() -> void:
	_gather_from_ui()

	var config := ConfigFile.new()
	for key in current_settings:
		config.set_value("ai", key, current_settings[key])
	var err := config.save(CONFIG_PATH)
	if err != OK:
		push_error("[GodotForge] Failed to save settings (code %d)" % err)
		return

	settings_saved.emit(current_settings.duplicate())
	print("[GodotForge] Settings saved")


func _gather_from_ui() -> void:
	current_settings["api_url"] = api_url_input.text.strip_edges()
	current_settings["api_key"] = api_key_input.text.strip_edges()
	current_settings["model_path"] = model_path_input.text.strip_edges()
	var idx := provider_option.selected
	if idx >= 0 and idx < PROVIDERS.size():
		current_settings["llm_provider"] = PROVIDERS[idx]


func get_settings() -> Dictionary:
	return current_settings.duplicate()


# ------------------------------------------------------------------
# Provider-dependent UI
# ------------------------------------------------------------------

func _on_provider_changed(idx: int) -> void:
	_update_model_path_visibility()


func _update_model_path_visibility() -> void:
	var is_local := provider_option.selected == 2  # Ollama
	if model_path_input:
		model_path_input.visible = is_local
	if model_path_label:
		model_path_label.visible = is_local


# ------------------------------------------------------------------
# Connection test
# ------------------------------------------------------------------

func _on_test_connection() -> void:
	test_button.disabled = true
	status_label.text = "Testing connection..."
	status_label.modulate = Color.WHITE

	if _http_test:
		_http_test.queue_free()
	_http_test = HTTPRequest.new()
	add_child(_http_test)
	_http_test.timeout = 8.0
	_http_test.request_completed.connect(_on_test_result)

	var url := api_url_input.text.strip_edges()
	if url.is_empty():
		status_label.text = "Please enter a URL first"
		status_label.modulate = Color.RED
		test_button.disabled = false
		return

	var err := _http_test.request(url + "/health")
	if err != OK:
		status_label.text = "Request failed to start (code %d)" % err
		status_label.modulate = Color.RED
		test_button.disabled = false


func _on_test_result(result: int, code: int, _headers: PackedStringArray,
		body: PackedByteArray) -> void:
	test_button.disabled = false
	if _http_test:
		_http_test.queue_free()
		_http_test = null

	if result != HTTPRequest.RESULT_SUCCESS:
		status_label.text = "Connection failed (network error %d)" % result
		status_label.modulate = Color.RED
		return

	if code == 200:
		# Try to parse server info from response
		var data := JSON.parse_string(body.get_string_from_utf8())
		var server_info := ""
		if data is Dictionary:
			server_info = data.get("version", "")
		if server_info.is_empty():
			status_label.text = "Connected successfully!"
		else:
			status_label.text = "Connected! Server v%s" % server_info
		status_label.modulate = Color.GREEN
	else:
		status_label.text = "Server responded with HTTP %d" % code
		status_label.modulate = Color.ORANGE
