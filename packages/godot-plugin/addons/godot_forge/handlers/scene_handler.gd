@tool
class_name SceneHandler
extends RefCounted
## Handles scene-level MCP tool calls: open, save, close, inspect,
## duplicate, instantiate, pack/unpack, and reload.

var _editor: EditorInterface


func _init(editor: EditorInterface) -> void:
	_editor = editor


# ------------------------------------------------------------------
# open_scene — open a scene file by path in the editor
# ------------------------------------------------------------------
func open_scene(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	if not FileAccess.file_exists(path):
		return {"error": "Scene file not found: %s" % path}
	_editor.open_scene_from_path(path)
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# save_scene_as — save the current scene to a new path
# ------------------------------------------------------------------
func save_scene_as(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var packed := PackedScene.new()
	var err := packed.pack(root)
	if err != OK:
		return {"error": "Failed to pack scene (code %d)" % err}
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	err = ResourceSaver.save(packed, path)
	if err != OK:
		return {"error": "Failed to save scene to %s (code %d)" % [path, err]}
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# close_scene — close a scene tab by path (or the current one)
# ------------------------------------------------------------------
func close_scene(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	# Godot 4.x doesn't expose close-by-path directly; save then close via
	# editor command palette workaround. We use the available API.
	if path.is_empty():
		# Close the currently edited scene
		var root := _editor.get_edited_scene_root()
		if root == null:
			return {"error": "No scene currently open"}
		path = root.scene_file_path
	# Attempt to close by selecting and using EditorInterface
	_editor.open_scene_from_path(path)
	# EditorNode close tab is not directly exposed; mark scene as saved then
	# rely on the editor's close flow.
	_editor.save_scene()
	return {"success": true, "path": path, "note": "Scene saved; use editor to close tab"}


# ------------------------------------------------------------------
# get_scene_tree_flat — return a flat list of all nodes in the edited scene
# ------------------------------------------------------------------
func get_scene_tree_flat(_params: Dictionary) -> Dictionary:
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var nodes: Array[Dictionary] = []
	_collect_nodes_flat(root, nodes)
	return {"nodes": nodes, "count": nodes.size()}


# ------------------------------------------------------------------
# get_open_scenes — list all scenes currently open in editor tabs
# ------------------------------------------------------------------
func get_open_scenes(_params: Dictionary) -> Dictionary:
	var scenes: Array[String] = []
	var edited := _editor.get_edited_scene_root()
	if edited:
		scenes.append(edited.scene_file_path)
	# Godot 4.x editor API provides get_open_scenes()
	var open_list := _editor.get_open_scenes()
	for scene_path in open_list:
		if scene_path not in scenes:
			scenes.append(scene_path)
	return {"scenes": scenes, "current": edited.scene_file_path if edited else ""}


# ------------------------------------------------------------------
# switch_scene — switch editor focus to a scene by path
# ------------------------------------------------------------------
func switch_scene(params: Dictionary) -> Dictionary:
	var path: String = params.get("path", "")
	if path.is_empty():
		return {"error": "Missing required parameter: path"}
	_editor.open_scene_from_path(path)
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# duplicate_scene — duplicate the current scene to a new path
# ------------------------------------------------------------------
func duplicate_scene(params: Dictionary) -> Dictionary:
	var new_path: String = params.get("new_path", "")
	var source_path: String = params.get("source_path", "")
	if new_path.is_empty():
		return {"error": "Missing required parameter: new_path"}
	if source_path.is_empty():
		var root := _editor.get_edited_scene_root()
		if root == null:
			return {"error": "No scene open and no source_path provided"}
		source_path = root.scene_file_path
	if not FileAccess.file_exists(source_path):
		return {"error": "Source scene not found: %s" % source_path}
	DirAccess.make_dir_recursive_absolute(new_path.get_base_dir())
	var err := DirAccess.copy_absolute(source_path, new_path)
	if err != OK:
		return {"error": "Failed to copy scene (code %d)" % err}
	_editor.get_resource_filesystem().scan()
	return {"success": true, "source": source_path, "new_path": new_path}


# ------------------------------------------------------------------
# instantiate_scene — add an instance of a PackedScene as a child
# ------------------------------------------------------------------
func instantiate_scene(params: Dictionary) -> Dictionary:
	var scene_path: String = params.get("scene_path", "")
	var parent_path: String = params.get("parent_path", ".")
	if scene_path.is_empty():
		return {"error": "Missing required parameter: scene_path"}
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var packed := load(scene_path) as PackedScene
	if packed == null:
		return {"error": "Failed to load scene: %s" % scene_path}
	var parent: Node = root.get_node_or_null(parent_path) if parent_path != "." else root
	if parent == null:
		return {"error": "Parent not found: %s" % parent_path}
	var instance := packed.instantiate()
	parent.add_child(instance)
	instance.owner = root
	# Also set owner for all descendants so they persist when saved
	_set_owner_recursive(instance, root)
	return {"success": true, "node_path": str(instance.get_path())}


# ------------------------------------------------------------------
# pack_scene — pack a subtree into a PackedScene resource and save
# ------------------------------------------------------------------
func pack_scene(params: Dictionary) -> Dictionary:
	var node_path: String = params.get("node_path", ".")
	var save_path: String = params.get("save_path", "")
	if save_path.is_empty():
		return {"error": "Missing required parameter: save_path"}
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var target: Node = root.get_node_or_null(node_path) if node_path != "." else root
	if target == null:
		return {"error": "Node not found: %s" % node_path}
	var packed := PackedScene.new()
	var err := packed.pack(target)
	if err != OK:
		return {"error": "Failed to pack node (code %d)" % err}
	DirAccess.make_dir_recursive_absolute(save_path.get_base_dir())
	err = ResourceSaver.save(packed, save_path)
	if err != OK:
		return {"error": "Failed to save packed scene (code %d)" % err}
	return {"success": true, "path": save_path}


# ------------------------------------------------------------------
# unpack_scene — replace an instanced scene with its expanded nodes
# ------------------------------------------------------------------
func unpack_scene(params: Dictionary) -> Dictionary:
	var node_path: String = params.get("node_path", "")
	if node_path.is_empty():
		return {"error": "Missing required parameter: node_path"}
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var target: Node = root.get_node_or_null(node_path)
	if target == null:
		return {"error": "Node not found: %s" % node_path}
	if target.scene_file_path.is_empty():
		return {"error": "Node is not a scene instance"}
	# Clear the scene_file_path to "unpack"
	target.scene_file_path = ""
	# Ensure all children are owned by the scene root so they persist
	_set_owner_recursive(target, root)
	return {"success": true, "node_path": str(target.get_path())}


# ------------------------------------------------------------------
# get_scene_resources — list all resources used by the current scene
# ------------------------------------------------------------------
func get_scene_resources(_params: Dictionary) -> Dictionary:
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var resources: Array[Dictionary] = []
	_collect_resources(root, resources, {})
	return {"resources": resources, "count": resources.size()}


# ------------------------------------------------------------------
# reload_scene — reload the current scene from disk
# ------------------------------------------------------------------
func reload_scene(_params: Dictionary) -> Dictionary:
	var root := _editor.get_edited_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var path := root.scene_file_path
	if path.is_empty():
		return {"error": "Scene has never been saved to disk"}
	_editor.reload_scene_from_path(path)
	return {"success": true, "path": path}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

func _collect_nodes_flat(node: Node, out: Array) -> void:
	out.append({
		"name": node.name,
		"type": node.get_class(),
		"path": str(node.get_path()),
		"has_script": node.get_script() != null,
		"visible": node.get("visible") if node.has_method("is_visible") else true,
		"child_count": node.get_child_count(),
	})
	for child in node.get_children():
		_collect_nodes_flat(child, out)


func _set_owner_recursive(node: Node, owner: Node) -> void:
	for child in node.get_children():
		child.owner = owner
		_set_owner_recursive(child, owner)


func _collect_resources(node: Node, out: Array, seen: Dictionary) -> void:
	# Check the node's script
	var script := node.get_script() as Script
	if script and script.resource_path not in seen:
		seen[script.resource_path] = true
		out.append({"path": script.resource_path, "type": "Script"})

	# Check exported properties for Resource values
	for prop in node.get_property_list():
		if prop["type"] == TYPE_OBJECT:
			var val = node.get(prop["name"])
			if val is Resource and not val.resource_path.is_empty():
				if val.resource_path not in seen:
					seen[val.resource_path] = true
					out.append({
						"path": val.resource_path,
						"type": val.get_class(),
						"property": prop["name"],
						"node": str(node.get_path()),
					})

	for child in node.get_children():
		_collect_resources(child, out, seen)
