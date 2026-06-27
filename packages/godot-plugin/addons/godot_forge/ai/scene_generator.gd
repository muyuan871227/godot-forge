@tool
class_name SceneGenerator
extends RefCounted
## Generates Godot scenes from natural language descriptions.
## Uses the AI services API to create nodes, scripts, and resources.

var _api_url: String = "http://localhost:8100"
var _editor: EditorInterface


func _init(editor: EditorInterface, api_url: String = "") -> void:
	_editor = editor
	if not api_url.is_empty():
		_api_url = api_url


func generate_scene_from_description(description: String, scene_name: String = "") -> Dictionary:
	"""Generate a complete scene from a text description.

	Returns: {success: bool, scene_path: String, files: Array, error: String}
	"""
	var request := {
		"prompt": "Generate a complete Godot 4.4 scene: %s" % description,
		"godot_version": "4.4",
	}

	var http := HTTPRequest.new()
	# Need a node in the tree to use HTTPRequest
	_editor.get_base_control().add_child(http)

	var body := JSON.stringify(request)
	var err := http.request(
		_api_url + "/api/v1/codegen/generate",
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		body,
	)

	if err != OK:
		http.queue_free()
		return {"success": false, "error": "HTTP request failed: %d" % err}

	var result: Array = await http.request_completed
	http.queue_free()

	var code: int = result[1]
	var response_body: PackedByteArray = result[3]

	if code != 200:
		return {"success": false, "error": "API returned HTTP %d" % code}

	var data := JSON.parse_string(response_body.get_string_from_utf8())
	if not data is Dictionary:
		return {"success": false, "error": "Invalid API response"}

	# Write generated files to project
	var files: Array = data.get("files", [])
	var written := []
	for file_data in files:
		var path: String = file_data.get("path", "")
		var content: String = file_data.get("content", "")
		if path.is_empty() or content.is_empty():
			continue
		DirAccess.make_dir_recursive_absolute(path.get_base_dir())
		var file := FileAccess.open(path, FileAccess.WRITE)
		if file:
			file.store_string(content)
			file.close()
			written.append(path)

	_editor.get_resource_filesystem().scan()

	# Find the main .tscn file and open it
	var scene_path := ""
	for path in written:
		if path.ends_with(".tscn"):
			scene_path = path
			break

	if not scene_path.is_empty():
		_editor.open_scene_from_path(scene_path)

	return {
		"success": true,
		"scene_path": scene_path,
		"files": written,
		"explanation": data.get("explanation", ""),
	}
