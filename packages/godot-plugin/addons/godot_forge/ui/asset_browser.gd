@tool
extends VBoxContainer
## AI Asset Browser panel — lists AI-generated assets with thumbnail preview,
## generation status tracking, and drag-to-scene support.

signal asset_selected(asset_data: Dictionary)
signal asset_drag_started(asset_data: Dictionary)

enum AssetStatus { QUEUED, GENERATING, DONE, FAILED }

const STATUS_ICONS := {
	AssetStatus.QUEUED: "[Q]",
	AssetStatus.GENERATING: "[~]",
	AssetStatus.DONE: "[+]",
	AssetStatus.FAILED: "[!]",
}
const STATUS_COLORS := {
	AssetStatus.QUEUED: Color.GRAY,
	AssetStatus.GENERATING: Color.YELLOW,
	AssetStatus.DONE: Color.GREEN,
	AssetStatus.FAILED: Color.RED,
}

@onready var filter_input: LineEdit = $FilterBar/FilterInput
@onready var type_filter: OptionButton = $FilterBar/TypeFilter
@onready var asset_list: ItemList = $AssetGrid
@onready var preview_rect: TextureRect = $PreviewPanel/PreviewRect
@onready var preview_info: Label = $PreviewPanel/InfoLabel
@onready var generate_button: Button = $ActionBar/GenerateButton
@onready var refresh_button: Button = $ActionBar/RefreshButton
@onready var status_label: Label = $ActionBar/StatusLabel

var assets: Array[Dictionary] = []
var api_url: String = "http://localhost:8100"
var _poll_timer: Timer
var _pending_jobs: Array[String] = []  # job IDs still in progress


func _ready() -> void:
	# Wire up signals
	generate_button.pressed.connect(_on_generate_pressed)
	refresh_button.pressed.connect(_on_refresh_pressed)
	asset_list.item_selected.connect(_on_item_selected)
	filter_input.text_changed.connect(_on_filter_changed)
	type_filter.item_selected.connect(_on_filter_changed.unbind(1))

	# Populate type filter dropdown
	type_filter.add_item("All Types", 0)
	type_filter.add_item("Sprite", 1)
	type_filter.add_item("Tilemap", 2)
	type_filter.add_item("Audio", 3)
	type_filter.add_item("3D Model", 4)

	# Enable drag-and-drop from the item list
	asset_list.set_drag_forwarding(_get_drag_data, Callable(), Callable())

	# Status poll timer for in-progress generations
	_poll_timer = Timer.new()
	_poll_timer.wait_time = 3.0
	_poll_timer.timeout.connect(_poll_pending_jobs)
	add_child(_poll_timer)


# ------------------------------------------------------------------
# Public API — external code can add assets (e.g. from the MCP layer)
# ------------------------------------------------------------------

func add_asset(data: Dictionary) -> void:
	if not data.has("name"):
		data["name"] = "Asset %d" % (assets.size() + 1)
	if not data.has("status"):
		data["status"] = AssetStatus.QUEUED
	assets.append(data)
	_refresh_list()


func set_api_url(url: String) -> void:
	api_url = url


func get_selected_asset() -> Dictionary:
	var idx := asset_list.get_selected_items()
	if idx.is_empty():
		return {}
	return _visible_asset(idx[0])


# ------------------------------------------------------------------
# Generation request
# ------------------------------------------------------------------

func _on_generate_pressed() -> void:
	var prompt := filter_input.text.strip_edges()
	if prompt.is_empty():
		status_label.text = "Enter a prompt first"
		return

	var asset_type := "sprite"
	match type_filter.selected:
		1: asset_type = "sprite"
		2: asset_type = "tilemap"
		3: asset_type = "audio"
		4: asset_type = "model3d"

	# Create a placeholder asset in QUEUED state
	var placeholder := {
		"name": prompt.substr(0, 32),
		"prompt": prompt,
		"type": asset_type,
		"status": AssetStatus.GENERATING,
		"job_id": "",
		"path": "",
		"thumbnail": null,
		"data": {},
	}
	assets.append(placeholder)
	_refresh_list()
	status_label.text = "Requesting generation..."

	# Fire HTTP request to AI services
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_generate_response.bind(http, assets.size() - 1))
	var body := JSON.stringify({
		"prompt": prompt,
		"type": asset_type,
		"width": 64,
		"height": 64,
	})
	var endpoint := api_url + "/api/v1/imagegen/generate"
	if asset_type == "audio":
		endpoint = api_url + "/api/v1/audiogen/generate"
	elif asset_type == "model3d":
		endpoint = api_url + "/api/v1/modelgen/generate"
	http.request(endpoint, ["Content-Type: application/json"], HTTPClient.METHOD_POST, body)


func _on_generate_response(result: int, code: int, _headers: PackedStringArray,
		body: PackedByteArray, http: HTTPRequest, asset_idx: int) -> void:
	http.queue_free()
	if asset_idx >= assets.size():
		return

	if code != 200 and code != 201 and code != 202:
		assets[asset_idx]["status"] = AssetStatus.FAILED
		status_label.text = "Generation failed (HTTP %d)" % code
		_refresh_list()
		return

	var json := JSON.parse_string(body.get_string_from_utf8())
	if json == null or not json is Dictionary:
		assets[asset_idx]["status"] = AssetStatus.FAILED
		status_label.text = "Invalid response from server"
		_refresh_list()
		return

	var data: Dictionary = json
	assets[asset_idx]["data"] = data
	assets[asset_idx]["job_id"] = data.get("job_id", "")

	# If response includes the asset path directly, mark done
	if data.has("image_path") or data.has("audio_path") or data.has("model_path"):
		assets[asset_idx]["status"] = AssetStatus.DONE
		assets[asset_idx]["path"] = data.get("image_path",
				data.get("audio_path", data.get("model_path", "")))
		status_label.text = "Done!"
		_load_thumbnail(asset_idx)
	else:
		# Async job — poll for completion
		var job_id: String = data.get("job_id", "")
		if not job_id.is_empty():
			_pending_jobs.append(job_id)
			assets[asset_idx]["status"] = AssetStatus.GENERATING
			status_label.text = "Generating (job %s)..." % job_id
			if _poll_timer.is_stopped():
				_poll_timer.start()

	_refresh_list()


# ------------------------------------------------------------------
# Job polling
# ------------------------------------------------------------------

func _poll_pending_jobs() -> void:
	if _pending_jobs.is_empty():
		_poll_timer.stop()
		return
	for job_id in _pending_jobs.duplicate():
		var http := HTTPRequest.new()
		add_child(http)
		http.request_completed.connect(_on_poll_response.bind(http, job_id))
		http.request(api_url + "/api/v1/jobs/" + job_id)


func _on_poll_response(result: int, code: int, _headers: PackedStringArray,
		body: PackedByteArray, http: HTTPRequest, job_id: String) -> void:
	http.queue_free()
	if code != 200:
		return
	var data := JSON.parse_string(body.get_string_from_utf8())
	if data == null or not data is Dictionary:
		return
	var status_str: String = data.get("status", "")
	if status_str == "done" or status_str == "completed":
		_pending_jobs.erase(job_id)
		# Find the asset with this job_id and update it
		for i in range(assets.size()):
			if assets[i].get("job_id", "") == job_id:
				assets[i]["status"] = AssetStatus.DONE
				assets[i]["data"] = data
				assets[i]["path"] = data.get("image_path",
						data.get("audio_path", data.get("model_path", "")))
				_load_thumbnail(i)
				break
		_refresh_list()
		status_label.text = "Generation complete"
	elif status_str == "failed" or status_str == "error":
		_pending_jobs.erase(job_id)
		for i in range(assets.size()):
			if assets[i].get("job_id", "") == job_id:
				assets[i]["status"] = AssetStatus.FAILED
				break
		_refresh_list()
		status_label.text = "Generation failed"


# ------------------------------------------------------------------
# Thumbnail loading
# ------------------------------------------------------------------

func _load_thumbnail(asset_idx: int) -> void:
	var asset := assets[asset_idx]
	# First try base64-encoded image from response
	var b64: String = asset.get("data", {}).get("image_base64", "")
	if not b64.is_empty():
		var img := Image.new()
		var err := img.load_png_from_buffer(Marshalls.base64_to_raw(b64))
		if err == OK:
			asset["thumbnail"] = ImageTexture.create_from_image(img)
			return
	# Try loading from disk path
	var path: String = asset.get("path", "")
	if not path.is_empty() and FileAccess.file_exists(path):
		var img := Image.new()
		var err := img.load(ProjectSettings.globalize_path(path))
		if err == OK:
			asset["thumbnail"] = ImageTexture.create_from_image(img)


# ------------------------------------------------------------------
# List display
# ------------------------------------------------------------------

func _refresh_list() -> void:
	asset_list.clear()
	var filter_text := filter_input.text.to_lower()
	var type_idx := type_filter.selected

	for asset in assets:
		var asset_name: String = asset.get("name", "")
		# Text filter
		if not filter_text.is_empty() and not asset_name.to_lower().contains(filter_text):
			continue
		# Type filter (0 = all)
		if type_idx > 0:
			var type_map := {1: "sprite", 2: "tilemap", 3: "audio", 4: "model3d"}
			if asset.get("type", "") != type_map.get(type_idx, ""):
				continue

		var status: int = asset.get("status", AssetStatus.QUEUED)
		var icon_str: String = STATUS_ICONS.get(status, "[ ]")
		var idx := asset_list.add_item("%s %s" % [icon_str, asset_name])
		asset_list.set_item_metadata(idx, asset)
		# Set item color based on status
		var color: Color = STATUS_COLORS.get(status, Color.WHITE)
		asset_list.set_item_custom_fg_color(idx, color)
		# Set thumbnail if available
		var thumb: Texture2D = asset.get("thumbnail")
		if thumb:
			asset_list.set_item_icon(idx, thumb)


func _on_item_selected(index: int) -> void:
	var asset := _visible_asset(index)
	if asset.is_empty():
		return
	asset_selected.emit(asset)

	# Update preview panel
	var thumb: Texture2D = asset.get("thumbnail")
	if thumb:
		preview_rect.texture = thumb
	else:
		preview_rect.texture = null

	var info_parts: PackedStringArray = []
	info_parts.append("Name: %s" % asset.get("name", ""))
	info_parts.append("Type: %s" % asset.get("type", "unknown"))
	var status_val: int = asset.get("status", AssetStatus.QUEUED)
	var status_names := {
		AssetStatus.QUEUED: "Queued",
		AssetStatus.GENERATING: "Generating...",
		AssetStatus.DONE: "Done",
		AssetStatus.FAILED: "Failed",
	}
	info_parts.append("Status: %s" % status_names.get(status_val, "Unknown"))
	if not asset.get("path", "").is_empty():
		info_parts.append("Path: %s" % asset["path"])
	preview_info.text = "\n".join(info_parts)


func _on_filter_changed(_text: String = "") -> void:
	_refresh_list()


func _on_refresh_pressed() -> void:
	_refresh_list()
	status_label.text = "Refreshed"


# ------------------------------------------------------------------
# Drag-and-drop support — drag asset from list into the scene
# ------------------------------------------------------------------

func _get_drag_data(at_position: Vector2) -> Variant:
	var idx := asset_list.get_item_at_position(at_position, true)
	if idx < 0:
		return null
	var asset := _visible_asset(idx)
	if asset.is_empty():
		return null
	var path: String = asset.get("path", "")
	if path.is_empty():
		return null

	# Build a drag preview
	var preview := Label.new()
	preview.text = asset.get("name", "Asset")
	set_drag_preview(preview)

	asset_drag_started.emit(asset)

	# Return data compatible with Godot editor drop
	return {"type": "files", "files": [path]}


## Get the asset dict for a visible list index (accounting for filtering).
func _visible_asset(index: int) -> Dictionary:
	if index < 0 or index >= asset_list.item_count:
		return {}
	var meta = asset_list.get_item_metadata(index)
	if meta is Dictionary:
		return meta
	return {}
