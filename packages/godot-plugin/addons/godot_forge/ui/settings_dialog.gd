@tool
extends AcceptDialog

@onready var api_url_input: LineEdit = %APIUrlInput
@onready var api_key_input: LineEdit = %APIKeyInput
@onready var provider_option: OptionButton = %ProviderOption
@onready var model_path_input: LineEdit = %ModelPathInput
@onready var test_button: Button = %TestButton
@onready var status_label: Label = %StatusLabel

signal settings_saved(settings: Dictionary)

var current_settings := {
	"api_url": "http://localhost:8100",
	"api_key": "",
	"llm_provider": "anthropic",
	"model_path": "",
}

func _ready() -> void:
	title = "GodotForge Settings"
	min_size = Vector2(450, 350)

	provider_option.add_item("Anthropic Claude", 0)
	provider_option.add_item("OpenAI GPT", 1)
	provider_option.add_item("Ollama (Local)", 2)

	api_key_input.secret = true
	test_button.pressed.connect(_on_test_connection)
	confirmed.connect(_on_save)

	_load_settings()

func _load_settings() -> void:
	var config := ConfigFile.new()
	if config.load("res://addons/godot_forge/settings.cfg") == OK:
		current_settings["api_url"] = config.get_value("ai", "api_url", "http://localhost:8100")
		current_settings["api_key"] = config.get_value("ai", "api_key", "")
		current_settings["llm_provider"] = config.get_value("ai", "llm_provider", "anthropic")
		current_settings["model_path"] = config.get_value("ai", "model_path", "")

	if api_url_input:
		api_url_input.text = current_settings["api_url"]
		api_key_input.text = current_settings["api_key"]
		model_path_input.text = current_settings["model_path"]
		match current_settings["llm_provider"]:
			"anthropic": provider_option.selected = 0
			"openai": provider_option.selected = 1
			"ollama": provider_option.selected = 2

func _on_save() -> void:
	current_settings["api_url"] = api_url_input.text
	current_settings["api_key"] = api_key_input.text
	current_settings["model_path"] = model_path_input.text
	match provider_option.selected:
		0: current_settings["llm_provider"] = "anthropic"
		1: current_settings["llm_provider"] = "openai"
		2: current_settings["llm_provider"] = "ollama"

	var config := ConfigFile.new()
	for key in current_settings:
		config.set_value("ai", key, current_settings[key])
	config.save("res://addons/godot_forge/settings.cfg")
	settings_saved.emit(current_settings)

func _on_test_connection() -> void:
	status_label.text = "Testing..."
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_test_result.bind(http))
	http.request(api_url_input.text + "/health")

func _on_test_result(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray, http: HTTPRequest) -> void:
	http.queue_free()
	if code == 200:
		status_label.text = "Connected!"
		status_label.modulate = Color.GREEN
	else:
		status_label.text = "Connection failed (HTTP %d)" % code
		status_label.modulate = Color.RED
