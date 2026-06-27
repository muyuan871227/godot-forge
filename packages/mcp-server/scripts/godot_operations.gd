## Headless Godot operations — run via `godot --headless --script`
## Used by MCP server and AI pipelines for batch operations.
extends SceneTree

var _operation: String = ""
var _params: Dictionary = {}

func _init() -> void:
	# Parse command line args
	var args := OS.get_cmdline_args()
	for i in range(args.size()):
		if args[i] == "--operation" and i + 1 < args.size():
			_operation = args[i + 1]
		elif args[i] == "--params" and i + 1 < args.size():
			var json := JSON.new()
			if json.parse(args[i + 1]) == OK:
				_params = json.data

	match _operation:
		"screenshot":
			_take_screenshot()
		"validate_project":
			_validate_project()
		"export_resources":
			_export_resources()
		"compile_check":
			_compile_check()
		_:
			_print_result({"error": "Unknown operation: %s" % _operation})
			quit(1)

func _take_screenshot() -> void:
	var scene_path: String = _params.get("scene", "")
	var output_path: String = _params.get("output", "user://screenshot.png")
	var wait_frames: int = _params.get("wait_frames", 10)

	if scene_path.is_empty():
		_print_result({"error": "Missing 'scene' parameter"})
		quit(1)
		return

	var packed := load(scene_path) as PackedScene
	if not packed:
		_print_result({"error": "Failed to load scene: %s" % scene_path})
		quit(1)
		return

	var instance := packed.instantiate()
	root.add_child(instance)

	# Wait for rendering to stabilize
	for i in range(wait_frames):
		await process_frame

	# Capture
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	img.save_png(output_path)

	_print_result({
		"success": true,
		"output": output_path,
		"size": [img.get_width(), img.get_height()],
	})
	quit()

func _validate_project() -> void:
	var errors := []
	var warnings := []

	# Check project.godot exists
	if not FileAccess.file_exists("res://project.godot"):
		errors.append("Missing project.godot")

	# Check main scene
	var main_scene: String = ProjectSettings.get_setting("application/run/main_scene", "")
	if main_scene.is_empty():
		warnings.append("No main scene configured")
	elif not FileAccess.file_exists(main_scene):
		errors.append("Main scene not found: %s" % main_scene)

	# Scan for script errors
	var script_files := _find_files("res://", "*.gd")
	for path in script_files:
		var script := load(path) as GDScript
		if script and not script.can_instantiate():
			errors.append("Script error in: %s" % path)

	_print_result({
		"valid": errors.is_empty(),
		"errors": errors,
		"warnings": warnings,
		"scripts_checked": script_files.size(),
	})
	quit()

func _export_resources() -> void:
	var output_dir: String = _params.get("output_dir", "user://export/")
	var resource_types: Array = _params.get("types", ["tscn", "tres", "gd"])

	DirAccess.make_dir_recursive_absolute(output_dir)
	var exported := []

	for ext in resource_types:
		var files := _find_files("res://", "*.%s" % ext)
		for file_path in files:
			exported.append(file_path)

	_print_result({
		"exported": exported.size(),
		"files": exported,
		"output_dir": output_dir,
	})
	quit()

func _compile_check() -> void:
	var script_files := _find_files("res://", "*.gd")
	var errors := []

	for path in script_files:
		var script := load(path)
		if script == null:
			errors.append({"path": path, "error": "Failed to load"})
		elif script is GDScript and not script.can_instantiate():
			errors.append({"path": path, "error": "Cannot instantiate (parse/compile error)"})

	_print_result({
		"total_scripts": script_files.size(),
		"errors": errors,
		"success": errors.is_empty(),
	})
	quit()

func _find_files(base_path: String, pattern: String) -> Array[String]:
	var results: Array[String] = []
	var dir := DirAccess.open(base_path)
	if not dir:
		return results
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		var full_path := base_path.path_join(file_name)
		if dir.current_is_dir():
			if file_name != "." and file_name != ".." and file_name != ".godot":
				results.append_array(_find_files(full_path, pattern))
		elif file_name.match(pattern):
			results.append(full_path)
		file_name = dir.get_next()
	dir.list_dir_end()
	return results

func _print_result(data: Dictionary) -> void:
	print(JSON.stringify(data))
