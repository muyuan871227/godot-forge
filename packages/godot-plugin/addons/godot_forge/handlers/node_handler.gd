@tool
class_name NodeHandler
extends RefCounted
## Handles node-level MCP tool calls: CRUD, properties, signals, groups,
## class introspection, and search queries.

var _editor: EditorInterface


func _init(editor: EditorInterface) -> void:
	_editor = editor


# ------------------------------------------------------------------
# remove_node — remove a node from the scene tree
# ------------------------------------------------------------------
func remove_node(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var path_str := str(node.get_path())
	var parent := node.get_parent()
	if parent:
		parent.remove_child(node)
	node.queue_free()
	return {"success": true, "removed": path_str}


# ------------------------------------------------------------------
# duplicate_node — duplicate a node (and its subtree)
# ------------------------------------------------------------------
func duplicate_node(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var flags: int = params.get("flags", Node.DUPLICATE_USE_INSTANTIATION)
	var dup := node.duplicate(flags)
	var new_name: String = params.get("new_name", node.name + "_copy")
	dup.name = new_name
	var parent := node.get_parent()
	if parent:
		parent.add_child(dup)
		dup.owner = _get_scene_root()
		_set_owner_recursive(dup, _get_scene_root())
	return {"success": true, "new_path": str(dup.get_path())}


# ------------------------------------------------------------------
# rename_node — rename a node
# ------------------------------------------------------------------
func rename_node(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var new_name: String = params.get("new_name", "")
	if new_name.is_empty():
		return {"error": "Missing required parameter: new_name"}
	node.name = new_name
	return {"success": true, "new_path": str(node.get_path())}


# ------------------------------------------------------------------
# reparent_node — move a node under a new parent
# ------------------------------------------------------------------
func reparent_node(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var new_parent_path: String = params.get("new_parent_path", "")
	if new_parent_path.is_empty():
		return {"error": "Missing required parameter: new_parent_path"}
	var root := _get_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var new_parent: Node = root.get_node_or_null(new_parent_path)
	if new_parent == null:
		return {"error": "New parent not found: %s" % new_parent_path}
	node.reparent(new_parent)
	node.owner = root
	return {"success": true, "new_path": str(node.get_path())}


# ------------------------------------------------------------------
# get_node_info — return detailed info about a node
# ------------------------------------------------------------------
func get_node_info(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var script_path := ""
	if node.get_script():
		script_path = (node.get_script() as Script).resource_path
	return {
		"name": node.name,
		"type": node.get_class(),
		"path": str(node.get_path()),
		"parent": str(node.get_parent().get_path()) if node.get_parent() else "",
		"child_count": node.get_child_count(),
		"has_script": node.get_script() != null,
		"script_path": script_path,
		"is_inside_tree": node.is_inside_tree(),
		"scene_file_path": node.scene_file_path,
		"groups": _get_node_groups(node),
		"owner": str(node.owner.get_path()) if node.owner else "",
	}


# ------------------------------------------------------------------
# get_node_properties — return all exported / inspectable properties
# ------------------------------------------------------------------
func get_node_properties(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var filter: String = params.get("filter", "")
	var props: Array[Dictionary] = []
	for prop in node.get_property_list():
		var prop_name: String = prop["name"]
		if not filter.is_empty() and not prop_name.containsn(filter):
			continue
		# Skip internal/metadata properties
		if prop["usage"] & PROPERTY_USAGE_EDITOR:
			props.append({
				"name": prop_name,
				"type": type_string(prop["type"]),
				"value": _variant_to_json_safe(node.get(prop_name)),
				"hint": prop.get("hint", 0),
				"hint_string": prop.get("hint_string", ""),
			})
	return {"properties": props, "count": props.size()}


# ------------------------------------------------------------------
# get_node_children — return direct children of a node
# ------------------------------------------------------------------
func get_node_children(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var children: Array[Dictionary] = []
	for child in node.get_children():
		children.append({
			"name": child.name,
			"type": child.get_class(),
			"path": str(child.get_path()),
		})
	return {"children": children, "count": children.size()}


# ------------------------------------------------------------------
# get_node_signals — list signals defined on a node
# ------------------------------------------------------------------
func get_node_signals(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var signals: Array[Dictionary] = []
	for sig in node.get_signal_list():
		var args: Array[Dictionary] = []
		for arg in sig.get("args", []):
			args.append({"name": arg["name"], "type": type_string(arg["type"])})
		signals.append({"name": sig["name"], "args": args})
	return {"signals": signals, "count": signals.size()}


# ------------------------------------------------------------------
# connect_signal — connect a signal from one node to a method on another
# ------------------------------------------------------------------
func connect_signal(params: Dictionary) -> Dictionary:
	var source := _resolve_node(params, "source_path")
	if source == null:
		return {"error": "Source node not found"}
	var signal_name: String = params.get("signal_name", "")
	if signal_name.is_empty():
		return {"error": "Missing required parameter: signal_name"}
	var target_path: String = params.get("target_path", "")
	var method_name: String = params.get("method_name", "")
	if target_path.is_empty() or method_name.is_empty():
		return {"error": "Missing required parameters: target_path, method_name"}
	var root := _get_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var target: Node = root.get_node_or_null(target_path)
	if target == null:
		return {"error": "Target node not found: %s" % target_path}
	if source.is_connected(signal_name, Callable(target, method_name)):
		return {"error": "Signal already connected"}
	source.connect(signal_name, Callable(target, method_name))
	return {"success": true}


# ------------------------------------------------------------------
# disconnect_signal — disconnect a signal connection
# ------------------------------------------------------------------
func disconnect_signal(params: Dictionary) -> Dictionary:
	var source := _resolve_node(params, "source_path")
	if source == null:
		return {"error": "Source node not found"}
	var signal_name: String = params.get("signal_name", "")
	var target_path: String = params.get("target_path", "")
	var method_name: String = params.get("method_name", "")
	if signal_name.is_empty() or target_path.is_empty() or method_name.is_empty():
		return {"error": "Missing required parameters: signal_name, target_path, method_name"}
	var root := _get_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var target: Node = root.get_node_or_null(target_path)
	if target == null:
		return {"error": "Target node not found: %s" % target_path}
	if not source.is_connected(signal_name, Callable(target, method_name)):
		return {"error": "Signal not connected"}
	source.disconnect(signal_name, Callable(target, method_name))
	return {"success": true}


# ------------------------------------------------------------------
# add_to_group — add a node to a named group
# ------------------------------------------------------------------
func add_to_group(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var group_name: String = params.get("group", "")
	if group_name.is_empty():
		return {"error": "Missing required parameter: group"}
	var persistent: bool = params.get("persistent", true)
	node.add_to_group(group_name, persistent)
	return {"success": true, "node": str(node.get_path()), "group": group_name}


# ------------------------------------------------------------------
# remove_from_group — remove a node from a named group
# ------------------------------------------------------------------
func remove_from_group(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	var group_name: String = params.get("group", "")
	if group_name.is_empty():
		return {"error": "Missing required parameter: group"}
	node.remove_from_group(group_name)
	return {"success": true, "node": str(node.get_path()), "group": group_name}


# ------------------------------------------------------------------
# get_groups — return all groups a node belongs to
# ------------------------------------------------------------------
func get_groups(params: Dictionary) -> Dictionary:
	var node := _resolve_node(params)
	if node == null:
		return _node_not_found(params)
	return {"groups": _get_node_groups(node)}


# ------------------------------------------------------------------
# get_class_list — return all registered class names
# ------------------------------------------------------------------
func get_class_list(params: Dictionary) -> Dictionary:
	var parent_class: String = params.get("parent_class", "")
	var classes: Array[String] = []
	for cls in ClassDB.get_class_list():
		if parent_class.is_empty() or ClassDB.is_parent_class(cls, parent_class):
			classes.append(cls)
	classes.sort()
	return {"classes": classes, "count": classes.size()}


# ------------------------------------------------------------------
# get_class_properties — return properties defined on a class
# ------------------------------------------------------------------
func get_class_properties(params: Dictionary) -> Dictionary:
	var class_name_str: String = params.get("class_name", "")
	if class_name_str.is_empty():
		return {"error": "Missing required parameter: class_name"}
	if not ClassDB.class_exists(class_name_str):
		return {"error": "Class not found: %s" % class_name_str}
	var props: Array[Dictionary] = []
	for prop in ClassDB.class_get_property_list(class_name_str):
		props.append({
			"name": prop["name"],
			"type": type_string(prop["type"]),
			"hint": prop.get("hint", 0),
			"hint_string": prop.get("hint_string", ""),
		})
	return {"class": class_name_str, "properties": props, "count": props.size()}


# ------------------------------------------------------------------
# get_class_methods — return methods defined on a class
# ------------------------------------------------------------------
func get_class_methods(params: Dictionary) -> Dictionary:
	var class_name_str: String = params.get("class_name", "")
	if class_name_str.is_empty():
		return {"error": "Missing required parameter: class_name"}
	if not ClassDB.class_exists(class_name_str):
		return {"error": "Class not found: %s" % class_name_str}
	var methods: Array[Dictionary] = []
	for method in ClassDB.class_get_method_list(class_name_str):
		var args: Array[Dictionary] = []
		for arg in method.get("args", []):
			args.append({"name": arg["name"], "type": type_string(arg["type"])})
		methods.append({
			"name": method["name"],
			"args": args,
			"return_type": type_string(method.get("return", {}).get("type", TYPE_NIL)),
		})
	return {"class": class_name_str, "methods": methods, "count": methods.size()}


# ------------------------------------------------------------------
# find_nodes_by_type — search the scene tree for nodes of a given type
# ------------------------------------------------------------------
func find_nodes_by_type(params: Dictionary) -> Dictionary:
	var type_name: String = params.get("type", "")
	if type_name.is_empty():
		return {"error": "Missing required parameter: type"}
	var root := _get_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var found: Array[Dictionary] = []
	_find_by_type(root, type_name, found)
	return {"nodes": found, "count": found.size()}


# ------------------------------------------------------------------
# find_nodes_by_group — search the scene tree for nodes in a group
# ------------------------------------------------------------------
func find_nodes_by_group(params: Dictionary) -> Dictionary:
	var group_name: String = params.get("group", "")
	if group_name.is_empty():
		return {"error": "Missing required parameter: group"}
	var root := _get_scene_root()
	if root == null:
		return {"error": "No scene currently open"}
	var found: Array[Dictionary] = []
	_find_by_group(root, group_name, found)
	return {"nodes": found, "count": found.size()}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

## Resolve a node from params using "node_path" (or a custom key).
func _resolve_node(params: Dictionary, key: String = "node_path") -> Node:
	var path: String = params.get(key, "")
	if path.is_empty():
		return null
	var root := _get_scene_root()
	if root == null:
		return null
	return root.get_node_or_null(path)


func _get_scene_root() -> Node:
	return _editor.get_edited_scene_root()


func _node_not_found(params: Dictionary) -> Dictionary:
	return {"error": "Node not found: %s" % params.get("node_path", "(empty)")}


func _get_node_groups(node: Node) -> Array:
	var groups: Array[String] = []
	for g in node.get_groups():
		groups.append(g)
	return groups


func _set_owner_recursive(node: Node, owner: Node) -> void:
	for child in node.get_children():
		child.owner = owner
		_set_owner_recursive(child, owner)


func _find_by_type(node: Node, type_name: String, out: Array) -> void:
	if node.is_class(type_name):
		out.append({
			"name": node.name,
			"type": node.get_class(),
			"path": str(node.get_path()),
		})
	for child in node.get_children():
		_find_by_type(child, type_name, out)


func _find_by_group(node: Node, group_name: String, out: Array) -> void:
	if node.is_in_group(group_name):
		out.append({
			"name": node.name,
			"type": node.get_class(),
			"path": str(node.get_path()),
		})
	for child in node.get_children():
		_find_by_group(child, group_name, out)


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
		TYPE_OBJECT:
			if value is Resource:
				return value.resource_path if not value.resource_path.is_empty() else str(value)
			return str(value)
		_:
			return str(value)
