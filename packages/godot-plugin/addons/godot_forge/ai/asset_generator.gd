@tool
class_name AssetGenerator
extends RefCounted
## Generates game assets (sprites, audio, 3D models) from text descriptions.
## Saves directly to the Godot project's asset directories.

var _api_url: String = "http://localhost:8100"
var _editor: EditorInterface


func _init(editor: EditorInterface, api_url: String = "") -> void:
	_editor = editor
	if not api_url.is_empty():
		_api_url = api_url


func generate_sprite(description: String, style: String = "pixel_art", size: int = 64) -> Dictionary:
	"""Generate a 2D sprite and save to project.

	Returns: {success: bool, path: String, error: String}
	"""
	var request := {
		"prompt": description,
		"style": style,
		"width": size,
		"height": size,
		"transparent_bg": true,
	}
	return await _generate_and_save(
		"/api/v1/imagegen/generate",
		request,
		"res://assets/sprites/",
		".png",
		"image_base64",
	)


func generate_sound_effect(description: String, duration: float = 1.0) -> Dictionary:
	"""Generate a sound effect and save to project."""
	var request := {
		"description": description,
		"duration": duration,
		"format": "wav",
	}
	return await _generate_and_save(
		"/api/v1/audiogen/sfx",
		request,
		"res://assets/audio/sfx/",
		".wav",
		"audio_base64",
	)


func generate_music(description: String, duration: float = 30.0, loop: bool = true) -> Dictionary:
	"""Generate background music and save to project."""
	var request := {
		"description": description,
		"duration": duration,
		"loop": loop,
	}
	return await _generate_and_save(
		"/api/v1/audiogen/bgm",
		request,
		"res://assets/audio/music/",
		".wav",
		"audio_base64",
	)


func _generate_and_save(
	endpoint: String,
	request: Dictionary,
	save_dir: String,
	extension: String,
	base64_key: String,
) -> Dictionary:
	var http := HTTPRequest.new()
	_editor.get_base_control().add_child(http)

	var body := JSON.stringify(request)
	var err := http.request(
		_api_url + endpoint,
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		body,
	)

	if err != OK:
		http.queue_free()
		return {"success": false, "error": "HTTP request failed"}

	var result: Array = await http.request_completed
	http.queue_free()

	var code: int = result[1]
	var response_body: PackedByteArray = result[3]

	if code != 200:
		return {"success": false, "error": "API returned HTTP %d" % code}

	var data := JSON.parse_string(response_body.get_string_from_utf8())
	if not data is Dictionary:
		return {"success": false, "error": "Invalid response"}

	var b64: String = data.get(base64_key, "")
	if b64.is_empty():
		return {"success": false, "error": "No data in response"}

	# Save to project
	var file_name := "generated_%d%s" % [Time.get_ticks_msec(), extension]
	var save_path := save_dir + file_name

	DirAccess.make_dir_recursive_absolute(save_dir)
	var file := FileAccess.open(save_path, FileAccess.WRITE)
	if not file:
		return {"success": false, "error": "Cannot write to %s" % save_path}

	file.store_buffer(Marshalls.base64_to_raw(b64))
	file.close()

	_editor.get_resource_filesystem().scan()

	return {
		"success": true,
		"path": save_path,
		"metadata": data.get("metadata", {}),
	}
