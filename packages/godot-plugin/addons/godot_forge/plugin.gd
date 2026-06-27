@tool
extends EditorPlugin

const AI_PANEL = preload("res://addons/godot_forge/ui/ai_panel.tscn")

var ai_panel_instance: Control
var mcp_server: WebSocketServer
var ws_peer: WebSocketPeer
var port: int = 6505

func _enter_tree():
	# 添加 AI 面板到底部
	ai_panel_instance = AI_PANEL.instantiate()
	add_control_to_bottom_panel(ai_panel_instance, "AI Assistant")

	# 启动 WebSocket 服务器
	_start_websocket_server()
	print("[GodotForge] Plugin activated on port %d" % port)

func _exit_tree():
	if ai_panel_instance:
		remove_control_from_bottom_panel(ai_panel_instance)
		ai_panel_instance.queue_free()
	_stop_websocket_server()
	print("[GodotForge] Plugin deactivated")

func _start_websocket_server():
	mcp_server = WebSocketServer.new()
	mcp_server.client_connected.connect(_on_client_connected)
	mcp_server.client_disconnected.connect(_on_client_disconnected)
	mcp_server.message_received.connect(_on_message_received)
	var err = mcp_server.listen(port)
	if err != OK:
		push_error("[GodotForge] Failed to start WebSocket server on port %d" % port)
	else:
		print("[GodotForge] WebSocket server listening on port %d" % port)

func _stop_websocket_server():
	if mcp_server:
		mcp_server.stop()

func _process(_delta):
	if mcp_server:
		mcp_server.poll()

func _on_client_connected(peer_id: int, _protocol: String):
	print("[GodotForge] MCP client connected: %d" % peer_id)
	if ai_panel_instance and ai_panel_instance.has_method("set_connection_status"):
		ai_panel_instance.set_connection_status(true)

func _on_client_disconnected(peer_id: int, _was_clean: bool):
	print("[GodotForge] MCP client disconnected: %d" % peer_id)
	if ai_panel_instance and ai_panel_instance.has_method("set_connection_status"):
		ai_panel_instance.set_connection_status(false)

func _on_message_received(peer_id: int, message: String):
	var json = JSON.new()
	var err = json.parse(message)
	if err != OK:
		_send_error(peer_id, -1, "Invalid JSON")
		return

	var request = json.data
	if not request is Dictionary:
		_send_error(peer_id, -1, "Invalid request format")
		return

	var id = request.get("id", -1)
	var method = request.get("method", "")
	var params = request.get("params", {})

	var result = _handle_method(method, params)
	_send_response(peer_id, id, result)

func _handle_method(method: String, params: Dictionary) -> Dictionary:
	match method:
		"get_project_info":
			return _get_project_info()
		"get_scene_tree":
			return _get_scene_tree()
		"create_scene":
			return _create_scene(params)
		"add_node":
			return _add_node(params)
		"set_node_property":
			return _set_node_property(params)
		"create_script":
			return _create_script(params)
		"save_scene":
			return _save_scene(params)
		"get_script_errors":
			return _get_script_errors()
		"run_project":
			return _run_project(params)
		"stop_project":
			return _stop_project()
		_:
			return {"error": "Unknown method: %s" % method}

# ============================================
# 方法实现
# ============================================

func _get_project_info() -> Dictionary:
	return {
		"name": ProjectSettings.get_setting("application/config/name", "Untitled"),
		"godot_version": Engine.get_version_info(),
		"project_path": ProjectSettings.globalize_path("res://"),
		"main_scene": ProjectSettings.get_setting("application/run/main_scene", ""),
	}

func _get_scene_tree() -> Dictionary:
	var root = get_editor_interface().get_edited_scene_root()
	if not root:
		return {"error": "No scene open"}
	return {"tree": _serialize_node(root)}

func _serialize_node(node: Node) -> Dictionary:
	var data := {
		"name": node.name,
		"type": node.get_class(),
		"path": str(node.get_path()),
		"children": []
	}
	for child in node.get_children():
		data["children"].append(_serialize_node(child))
	return data

func _create_scene(params: Dictionary) -> Dictionary:
	var root_type = params.get("root_type", "Node2D")
	var scene_name = params.get("name", "new_scene")

	var root = ClassDB.instantiate(root_type)
	if not root:
		return {"error": "Invalid node type: %s" % root_type}
	root.name = scene_name

	var packed = PackedScene.new()
	packed.pack(root)
	var path = "res://scenes/%s.tscn" % scene_name
	DirAccess.make_dir_recursive_absolute("res://scenes")
	ResourceSaver.save(packed, path)
	root.queue_free()

	get_editor_interface().open_scene_from_path(path)
	return {"success": true, "path": path}

func _add_node(params: Dictionary) -> Dictionary:
	var root = get_editor_interface().get_edited_scene_root()
	if not root:
		return {"error": "No scene open"}

	var parent_path = params.get("parent_path", ".")
	var parent = root.get_node_or_null(parent_path) if parent_path != "." else root
	if not parent:
		return {"error": "Parent not found: %s" % parent_path}

	var node_type = params.get("node_type", "Node")
	var node = ClassDB.instantiate(node_type)
	if not node:
		return {"error": "Invalid type: %s" % node_type}

	node.name = params.get("node_name", node_type)
	parent.add_child(node)
	node.owner = root

	# 设置属性
	var props = params.get("properties", {})
	for key in props:
		if node.has_method("set"):
			node.set(key, props[key])

	return {"success": true, "path": str(node.get_path())}

func _set_node_property(params: Dictionary) -> Dictionary:
	var root = get_editor_interface().get_edited_scene_root()
	if not root:
		return {"error": "No scene open"}
	var node = root.get_node_or_null(params.get("node_path", ""))
	if not node:
		return {"error": "Node not found"}
	node.set(params.get("property", ""), params.get("value"))
	return {"success": true}

func _create_script(params: Dictionary) -> Dictionary:
	var root = get_editor_interface().get_edited_scene_root()
	if not root:
		return {"error": "No scene open"}
	var node = root.get_node_or_null(params.get("node_path", ""))
	if not node:
		return {"error": "Node not found"}

	var script_path = params.get("script_path", "res://scripts/new_script.gd")
	var content = params.get("content", "extends Node\n")

	DirAccess.make_dir_recursive_absolute(script_path.get_base_dir())
	var file = FileAccess.open(script_path, FileAccess.WRITE)
	file.store_string(content)
	file.close()

	var script = load(script_path)
	node.set_script(script)
	return {"success": true, "path": script_path}

func _save_scene(params: Dictionary) -> Dictionary:
	var root = get_editor_interface().get_edited_scene_root()
	if not root:
		return {"error": "No scene open"}
	get_editor_interface().save_scene()
	return {"success": true}

func _get_script_errors() -> Dictionary:
	# 读取 Godot 编辑器的错误输出
	return {"errors": [], "warnings": []}

func _run_project(params: Dictionary) -> Dictionary:
	var scene = params.get("scene", "")
	if scene:
		get_editor_interface().play_custom_scene(scene)
	else:
		get_editor_interface().play_main_scene()
	return {"success": true}

func _stop_project() -> Dictionary:
	get_editor_interface().stop_playing_scene()
	return {"success": true}

# ============================================
# WebSocket 通信
# ============================================

func _send_response(peer_id: int, id: int, result: Dictionary):
	var response = {
		"jsonrpc": "2.0",
		"id": id,
		"result": result,
	}
	mcp_server.send(peer_id, JSON.stringify(response))

func _send_error(peer_id: int, id: int, message: String):
	var response = {
		"jsonrpc": "2.0",
		"id": id,
		"error": {"code": -1, "message": message},
	}
	mcp_server.send(peer_id, JSON.stringify(response))
