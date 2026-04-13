@tool
extends VBoxContainer

@onready var filter_input: LineEdit = $FilterBar/FilterInput
@onready var asset_list: ItemList = $AssetList
@onready var preview_rect: TextureRect = $Preview/PreviewRect
@onready var generate_button: Button = $ActionBar/GenerateButton
@onready var status_label: Label = $ActionBar/StatusLabel

signal asset_selected(asset_data: Dictionary)

var assets: Array[Dictionary] = []
var api_url: String = "http://localhost:8100"

func _ready() -> void:
	generate_button.pressed.connect(_on_generate)
	asset_list.item_selected.connect(_on_item_selected)
	filter_input.text_changed.connect(_on_filter_changed)

func _on_generate() -> void:
	var prompt := filter_input.text.strip_edges()
	if prompt.is_empty():
		return
	status_label.text = "Generating..."
	var http := HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_generate_result.bind(http))
	var body := JSON.stringify({"prompt": prompt, "style": "pixel_art", "width": 64, "height": 64})
	http.request(api_url + "/api/v1/imagegen/generate", ["Content-Type: application/json"], HTTPClient.METHOD_POST, body)

func _on_generate_result(result: int, code: int, _headers: PackedStringArray, body: PackedByteArray, http: HTTPRequest) -> void:
	http.queue_free()
	if code != 200:
		status_label.text = "Generation failed"
		return
	var data := JSON.parse_string(body.get_string_from_utf8())
	if data and data is Dictionary:
		var asset := {
			"name": "Generated Asset %d" % (assets.size() + 1),
			"path": data.get("image_path", ""),
			"status": "done",
			"data": data,
		}
		assets.append(asset)
		_refresh_list()
		status_label.text = "Done!"

func _on_item_selected(index: int) -> void:
	if index < 0 or index >= assets.size():
		return
	var asset := assets[index]
	asset_selected.emit(asset)
	# Try to load preview
	var b64: String = asset.get("data", {}).get("image_base64", "")
	if not b64.is_empty():
		var img := Image.new()
		img.load_png_from_buffer(Marshalls.base64_to_raw(b64))
		preview_rect.texture = ImageTexture.create_from_image(img)

func _on_filter_changed(text: String) -> void:
	_refresh_list()

func _refresh_list() -> void:
	asset_list.clear()
	var filter := filter_input.text.to_lower()
	for asset in assets:
		var name: String = asset.get("name", "")
		if filter.is_empty() or filter in name.to_lower():
			var status: String = asset.get("status", "")
			var icon := "[ ] " if status == "done" else "[...] "
			asset_list.add_item(icon + name)
