@tool
class_name ProjectHandler
extends RefCounted
## Handles project-level MCP tool calls: filesystem queries, project settings,
## and Godot version info.

var _editor: EditorInterface


func _init(editor: EditorInterface) -> void:
	_editor = editor


# ------------------------------------------------------------------
# list_scenes — recursively find all .tscn / .scn files under res://
# ------------------------------------------------------------------
func list_scenes(params: Dictionary) -> Dictionary:
	var base_dir: String = params.get("base_dir", "res://")
	var scenes: Array[Dictionary] = []
	_scan_dir_for_ext(base_dir, ["tscn", "scn"], scenes)
	return {"scenes": scenes}


# ------------------------------------------------------------------
# list_scripts — recursively find all .gd / .cs files under res://
# ------------------------------------------------------------------
func list_scripts(params: Dictionary) -> Dictionary:
	var base_dir: String = params.get("base_dir", "res://")
	var scripts: Array[Dictionary] = []
	_scan_dir_for_ext(base_dir, ["gd", "cs"], scripts)
	return {"scripts": scripts}


# ------------------------------------------------------------------
# list_resources — recursively find resource files (tres, res, png, etc.)
# ------------------------------------------------------------------
func list_resources(params: Dictionary) -> Dictionary:
	var base_dir: String = params.get("base_dir", "res://")
	var extensions: Array = params.get("extensions", [
		"tres", "res", "png", "jpg", "svg", "wav", "ogg", "mp3",
		"ttf", "otf", "material", "shader", "gdshader",
	])
	var resources: Array[Dictionary] = []
	_scan_dir_for_ext(base_dir, extensions, resources)
	return {"resources": resources}


# ------------------------------------------------------------------
# get_project_settings — return a subset (or all) project settings
# ------------------------------------------------------------------
func get_project_settings(params: Dictionary) -> Dictionary:
	var keys: Array = params.get("keys", [])
	if keys.is_empty():
		# Return common settings when no specific keys requested
		keys = [
			"application/config/name",
			"application/run/main_scene",
			"display/window/size/viewport_width",
			"display/window/size/viewport_height",
			"rendering/renderer/rendering_method",
			"physics/2d/default_gravity",
			"physics/3d/default_gravity",
		]
	var settings: Dictionary = {}
	for key in keys:
		if ProjectSettings.has_setting(key):
			settings[key] = _variant_to_json_safe(ProjectSettings.get_setting(key))
	return {"settings": settings}


# ------------------------------------------------------------------
# set_project_setting — set a single project setting and save
# ------------------------------------------------------------------
func set_project_setting(params: Dictionary) -> Dictionary:
	var key: String = params.get("key", "")
	if key.is_empty():
		return {"error": "Missing required parameter: key"}
	var value = params.get("value")
	ProjectSettings.set_setting(key, value)
	var err := ProjectSettings.save()
	if err != OK:
		return {"error": "Failed to save project settings (code %d)" % err}
	return {"success": true, "key": key}


# ------------------------------------------------------------------
# rescan_filesystem — tell the editor to re-import / rescan files
# ------------------------------------------------------------------
func rescan_filesystem(_params: Dictionary) -> Dictionary:
	_editor.get_resource_filesystem().scan()
	return {"success": true}


# ------------------------------------------------------------------
# get_godot_version — return full version info dict
# ------------------------------------------------------------------
func get_godot_version(_params: Dictionary) -> Dictionary:
	var info: Dictionary = Engine.get_version_info()
	return {
		"major": info.get("major", 0),
		"minor": info.get("minor", 0),
		"patch": info.get("patch", 0),
		"status": info.get("status", ""),
		"hex": info.get("hex", 0),
		"string": "%d.%d.%d-%s" % [
			info.get("major", 0),
			info.get("minor", 0),
			info.get("patch", 0),
			info.get("status", ""),
		],
	}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

## Recursively scan a directory for files matching any of the given extensions.
func _scan_dir_for_ext(path: String, extensions: Array, out: Array) -> void:
	var dir := DirAccess.open(path)
	if dir == null:
		return
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		var full_path := path.path_join(file_name)
		if dir.current_is_dir():
			if not file_name.begins_with("."):
				_scan_dir_for_ext(full_path, extensions, out)
		else:
			var ext := file_name.get_extension().to_lower()
			if ext in extensions:
				out.append({
					"path": full_path,
					"name": file_name,
					"extension": ext,
				})
		file_name = dir.get_next()
	dir.list_dir_end()


## Convert a Variant to something JSON-safe (string fallback for complex types).
func _variant_to_json_safe(value: Variant) -> Variant:
	match typeof(value):
		TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING:
			return value
		TYPE_VECTOR2, TYPE_VECTOR3, TYPE_COLOR, TYPE_RECT2:
			return str(value)
		TYPE_ARRAY:
			var arr: Array = []
			for item in value:
				arr.append(_variant_to_json_safe(item))
			return arr
		TYPE_DICTIONARY:
			var dict: Dictionary = {}
			for key in value:
				dict[str(key)] = _variant_to_json_safe(value[key])
			return dict
		_:
			return str(value)
