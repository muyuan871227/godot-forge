## Runtime MCP interaction — attached to running game instances
## Enables runtime inspection and manipulation via MCP tools.
extends Node

var _ws_client: WebSocketPeer
var _server_url: String = "ws://127.0.0.1:6506"
var _connected: bool = false
var _reconnect_timer: float = 0.0

func _ready() -> void:
	# Read config from command line or environment
	var args := OS.get_cmdline_args()
	for i in range(args.size()):
		if args[i] == "--mcp-url" and i + 1 < args.size():
			_server_url = args[i + 1]

	_connect_to_mcp()

func _connect_to_mcp() -> void:
	_ws_client = WebSocketPeer.new()
	var err := _ws_client.connect_to_url(_server_url)
	if err != OK:
		push_warning("[MCP Runtime] Failed to connect to %s" % _server_url)

func _process(delta: float) -> void:
	if _ws_client == null:
		return

	_ws_client.poll()
	var state := _ws_client.get_ready_state()

	match state:
		WebSocketPeer.STATE_OPEN:
			if not _connected:
				_connected = true
				_reconnect_timer = 0.0
				print("[MCP Runtime] Connected to MCP server")
				_send_event("runtime_connected", {
					"scene": get_tree().current_scene.scene_file_path if get_tree().current_scene else "",
				})

			while _ws_client.get_available_packet_count() > 0:
				var data := _ws_client.get_packet().get_string_from_utf8()
				_handle_message(data)

		WebSocketPeer.STATE_CLOSED:
			_connected = false
			_reconnect_timer += delta
			if _reconnect_timer > 5.0:
				_reconnect_timer = 0.0
				_connect_to_mcp()

func _handle_message(data: String) -> void:
	var json := JSON.new()
	if json.parse(data) != OK:
		return
	var msg: Dictionary = json.data
	var id: int = msg.get("id", -1)
	var method: String = msg.get("method", "")
	var params: Dictionary = msg.get("params", {})

	var result := _execute_runtime_method(method, params)
	_send_response(id, result)

func _execute_runtime_method(method: String, params: Dictionary) -> Dictionary:
	match method:
		"get_runtime_node_tree":
			return _get_runtime_tree()
		"game_eval":
			return _eval_expression(params.get("expression", ""))
		"get_node_property_runtime":
			return _get_runtime_property(params)
		"set_node_property_runtime":
			return _set_runtime_property(params)
		"get_fps":
			return {"fps": Engine.get_frames_per_second()}
		"get_memory_usage":
			return {
				"static": OS.get_static_memory_usage(),
				"dynamic": Performance.get_monitor(Performance.MEMORY_MESSAGE_BUFFER_MAX),
			}
		_:
			return {"error": "Unknown runtime method: %s" % method}

func _get_runtime_tree() -> Dictionary:
	var scene := get_tree().current_scene
	if not scene:
		return {"error": "No current scene"}
	return {"tree": _serialize_node(scene)}

func _serialize_node(node: Node) -> Dictionary:
	var data := {
		"name": node.name,
		"type": node.get_class(),
		"path": str(node.get_path()),
		"visible": node.is_inside_tree(),
		"children": [],
	}
	if node is Node2D:
		data["position"] = {"x": node.position.x, "y": node.position.y}
	elif node is Node3D:
		data["position"] = {"x": node.position.x, "y": node.position.y, "z": node.position.z}
	for child in node.get_children():
		data["children"].append(_serialize_node(child))
	return data

func _eval_expression(expr_str: String) -> Dictionary:
	var expression := Expression.new()
	var err := expression.parse(expr_str)
	if err != OK:
		return {"error": "Parse error: %s" % expression.get_error_text()}
	var result = expression.execute([], get_tree().current_scene)
	if expression.has_execute_failed():
		return {"error": "Execution failed"}
	return {"result": str(result)}

func _get_runtime_property(params: Dictionary) -> Dictionary:
	var node_path: String = params.get("node_path", "")
	var property: String = params.get("property", "")
	var scene := get_tree().current_scene
	if not scene:
		return {"error": "No current scene"}
	var node := scene.get_node_or_null(node_path)
	if not node:
		return {"error": "Node not found: %s" % node_path}
	var value = node.get(property)
	return {"property": property, "value": str(value), "type": typeof(value)}

func _set_runtime_property(params: Dictionary) -> Dictionary:
	var node_path: String = params.get("node_path", "")
	var property: String = params.get("property", "")
	var value = params.get("value")
	var scene := get_tree().current_scene
	if not scene:
		return {"error": "No current scene"}
	var node := scene.get_node_or_null(node_path)
	if not node:
		return {"error": "Node not found: %s" % node_path}
	node.set(property, value)
	return {"success": true}

func _send_response(id: int, result: Dictionary) -> void:
	if not _connected:
		return
	var response := JSON.stringify({
		"jsonrpc": "2.0",
		"id": id,
		"result": result,
	})
	_ws_client.send_text(response)

func _send_event(event_name: String, data: Dictionary) -> void:
	if not _connected:
		return
	var msg := JSON.stringify({
		"jsonrpc": "2.0",
		"method": "event",
		"params": {"event": event_name, "data": data},
	})
	_ws_client.send_text(msg)
