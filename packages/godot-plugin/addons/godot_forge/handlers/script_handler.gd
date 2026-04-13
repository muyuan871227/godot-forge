@tool
class_name ScriptHandler
extends RefCounted
## Handles script-level MCP tool calls: read, write, delete, attach/detach,
## editor navigation, search/replace, and format.

var _editor: EditorInterface


func _init(editor: EditorInterface) -> void:
	_editor = editor


# ------------------------------------------------------------------
# read_script — return the source text of a script file
# ------------------------------------------------------------------
func read_script(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	if not FileAccess.file_exists(path):
		return {"error": "Script file not found: %s" % path}
	var content := FileAccess.get_file_as_string(path)
	var line_count := content.count("\n") + 1
	return {"path": path, "content": content, "line_count": line_count}


# ------------------------------------------------------------------
# update_script — overwrite (or patch) a script file
# ------------------------------------------------------------------
func update_script(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	var content: String = params.get("content", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	if content.is_empty():
		return {"error": "Missing required parameter: content"}

	# Support for partial update via line range
	var start_line: int = params.get("start_line", -1)
	var end_line: int = params.get("end_line", -1)

	if start_line >= 0 and end_line >= 0:
		# Patch mode: replace lines [start_line..end_line] inclusive (0-based)
		if not FileAccess.file_exists(path):
			return {"error": "Script file not found for patching: %s" % path}
		var existing := FileAccess.get_file_as_string(path)
		var lines := existing.split("\n")
		if start_line > lines.size() or end_line > lines.size():
			return {"error": "Line range out of bounds"}
		var new_lines: PackedStringArray = []
		new_lines.append_array(lines.slice(0, start_line))
		new_lines.append_array(content.split("\n"))
		new_lines.append_array(lines.slice(end_line + 1))
		content = "\n".join(new_lines)

	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return {"error": "Failed to open file for writing: %s" % path}
	file.store_string(content)
	file.close()

	# Tell the editor to reimport so open tabs refresh
	_editor.get_resource_filesystem().scan()
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# delete_script — delete a script file from the project
# ------------------------------------------------------------------
func delete_script(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	if not FileAccess.file_exists(path):
		return {"error": "Script file not found: %s" % path}
	var err := DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	if err != OK:
		return {"error": "Failed to delete script (code %d)" % err}
	# Also remove the .import companion if it exists
	var import_path := path + ".import"
	if FileAccess.file_exists(import_path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(import_path))
	_editor.get_resource_filesystem().scan()
	return {"success": true, "deleted": path}


# ------------------------------------------------------------------
# attach_script — attach a script to a node (create if needed)
# ------------------------------------------------------------------
func attach_script(params: Dictionary) -> Dictionary:
	var node_path: String = params.get("node_path", "")
	var script_path: String = params.get("script_path", "")
	if node_path.is_empty() or script_path.is_empty():
		return {"error": "Missing required parameters: node_path, script_path"}
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var node: Node = root.get_node_or_null(node_path)
	if node == null:
		return {"error": "Node not found: %s" % node_path}

	# Create the script file if it does not exist
	if not FileAccess.file_exists(script_path):
		var base_class := node.get_class()
		var template := "extends %s\n\n\nfunc _ready() -> void:\n\tpass\n" % base_class
		var content: String = params.get("content", template)
		DirAccess.make_dir_recursive_absolute(script_path.get_base_dir())
		var file := FileAccess.open(script_path, FileAccess.WRITE)
		if file == null:
			return {"error": "Failed to create script at %s" % script_path}
		file.store_string(content)
		file.close()
		_editor.get_resource_filesystem().scan()

	var script := load(script_path) as Script
	if script == null:
		return {"error": "Failed to load script: %s" % script_path}
	node.set_script(script)
	return {"success": true, "node": node_path, "script": script_path}


# ------------------------------------------------------------------
# detach_script — remove script from a node without deleting the file
# ------------------------------------------------------------------
func detach_script(params: Dictionary) -> Dictionary:
	var node_path: String = params.get("node_path", "")
	if node_path.is_empty():
		return {"error": "Missing required parameter: node_path"}
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var node: Node = root.get_node_or_null(node_path)
	if node == null:
		return {"error": "Node not found: %s" % node_path}
	if node.get_script() == null:
		return {"error": "Node has no script attached"}
	var old_path: String = (node.get_script() as Script).resource_path
	node.set_script(null)
	return {"success": true, "node": node_path, "detached_script": old_path}


# ------------------------------------------------------------------
# get_open_script — return the script currently open in the editor
# ------------------------------------------------------------------
func get_open_script(_params: Dictionary) -> Dictionary:
	var script := _editor.get_script_editor().get_current_script()
	if script == null:
		return {"error": "No script currently open in the script editor"}
	return {
		"path": script.resource_path,
		"class": script.get_instance_base_type(),
		"content": script.source_code,
		"line_count": script.source_code.count("\n") + 1,
	}


# ------------------------------------------------------------------
# set_open_script — open a specific script in the script editor
# ------------------------------------------------------------------
func set_open_script(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	if not FileAccess.file_exists(path):
		return {"error": "Script file not found: %s" % path}
	var script := load(path) as Script
	if script == null:
		return {"error": "Failed to load script: %s" % path}
	var line: int = params.get("line", 0)
	var col: int = params.get("column", 0)
	_editor.edit_script(script, line, col)
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# search_in_scripts — search for a pattern across all project scripts
# ------------------------------------------------------------------
func search_in_scripts(params: Dictionary) -> Dictionary:
	var pattern: String = params.get("pattern", "")
	if pattern.is_empty():
		# Backward compat: also accept "query" key
		pattern = params.get("query", "")
	if pattern.is_empty():
		return {"error": "Missing required parameter: pattern"}
	var case_sensitive: bool = params.get("case_sensitive", false)
	var base_dir: String = params.get("base_dir", "res://")
	var max_results: int = params.get("max_results", 200)

	var regex := RegEx.new()
	var flags := "" if case_sensitive else "(?i)"
	var err := regex.compile(flags + pattern)
	if err != OK:
		# Fall back to literal search
		regex = null

	var script_paths: Array[Dictionary] = []
	_scan_scripts(base_dir, script_paths)

	var results: Array[Dictionary] = []
	for entry in script_paths:
		if results.size() >= max_results:
			break
		var content := FileAccess.get_file_as_string(entry["path"])
		var lines := content.split("\n")
		for i in range(lines.size()):
			if results.size() >= max_results:
				break
			var line_text: String = lines[i]
			var matched := false
			if regex:
				matched = regex.search(line_text) != null
			else:
				if case_sensitive:
					matched = line_text.contains(pattern)
				else:
					matched = line_text.containsn(pattern)
			if matched:
				results.append({
					"path": entry["path"],
					"line": i + 1,
					"text": line_text.strip_edges(),
				})
	return {"results": results, "count": results.size(), "truncated": results.size() >= max_results}


# ------------------------------------------------------------------
# replace_in_scripts — search-and-replace across project scripts
# ------------------------------------------------------------------
func replace_in_scripts(params: Dictionary) -> Dictionary:
	var pattern: String = params.get("pattern", "")
	if pattern.is_empty():
		# Backward compat: also accept "search" key
		pattern = params.get("search", "")
	var replacement: String = params.get("replacement", "")
	if replacement.is_empty():
		replacement = params.get("replace", "")
	if pattern.is_empty():
		return {"error": "Missing required parameter: pattern"}
	var case_sensitive: bool = params.get("case_sensitive", false)
	var dry_run: bool = params.get("dry_run", false)
	var base_dir: String = params.get("base_dir", "res://")

	var script_paths: Array[Dictionary] = []
	_scan_scripts(base_dir, script_paths)

	var regex := RegEx.new()
	var flags := "" if case_sensitive else "(?i)"
	var err := regex.compile(flags + pattern)
	var use_regex := (err == OK)

	var files_changed: int = 0
	var total_replacements: int = 0
	var changes: Array[Dictionary] = []

	for entry in script_paths:
		var content := FileAccess.get_file_as_string(entry["path"])
		var new_content: String
		var count: int = 0
		if use_regex:
			var result := regex.sub(content, replacement, true)
			count = regex.search_all(content).size()
			new_content = result
		else:
			if case_sensitive:
				count = content.count(pattern)
				new_content = content.replace(pattern, replacement)
			else:
				count = content.countn(pattern)
				new_content = content.replacen(pattern, replacement)

		if count > 0:
			total_replacements += count
			files_changed += 1
			changes.append({"path": entry["path"], "replacements": count})
			if not dry_run:
				var file := FileAccess.open(entry["path"], FileAccess.WRITE)
				if file:
					file.store_string(new_content)
					file.close()

	if not dry_run and files_changed > 0:
		_editor.get_resource_filesystem().scan()

	return {
		"files_changed": files_changed,
		"total_replacements": total_replacements,
		"dry_run": dry_run,
		"changes": changes,
	}


# ------------------------------------------------------------------
# format_script — basic GDScript formatting (normalise whitespace)
# ------------------------------------------------------------------
func format_script(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	if not FileAccess.file_exists(path):
		return {"error": "Script file not found: %s" % path}

	var content := FileAccess.get_file_as_string(path)
	var formatted := _format_gdscript(content)

	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		return {"error": "Failed to open script for writing"}
	file.store_string(formatted)
	file.close()

	_editor.get_resource_filesystem().scan()
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

func _scan_scripts(base_dir: String, out: Array) -> void:
	var dir := DirAccess.open(base_dir)
	if dir == null:
		return
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		var full_path := base_dir.path_join(file_name)
		if dir.current_is_dir():
			if not file_name.begins_with(".") and file_name != "addons":
				_scan_scripts(full_path, out)
		else:
			var ext := file_name.get_extension().to_lower()
			if ext == "gd" or ext == "cs":
				out.append({"path": full_path, "name": file_name, "extension": ext})
		file_name = dir.get_next()
	dir.list_dir_end()


## Basic GDScript formatter: strip trailing whitespace, ensure single trailing
## newline, normalise blank lines (max 2 consecutive).
func _format_gdscript(source: String) -> String:
	var lines := source.split("\n")
	var output: PackedStringArray = []
	var consecutive_blanks: int = 0
	for line in lines:
		var stripped := line.rstrip(" \t")
		if stripped.is_empty():
			consecutive_blanks += 1
			if consecutive_blanks <= 2:
				output.append("")
		else:
			consecutive_blanks = 0
			output.append(stripped)
	# Ensure single trailing newline
	while output.size() > 1 and output[output.size() - 1].is_empty():
		output.remove_at(output.size() - 1)
	output.append("")
	return "\n".join(output)
