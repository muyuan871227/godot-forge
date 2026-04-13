@tool
extends VBoxContainer

@onready var status_label: Label = $StatusBar/StatusLabel
@onready var chat_input: TextEdit = $InputArea/ChatInput
@onready var send_button: Button = $InputArea/SendButton
@onready var chat_log: RichTextLabel = $ChatLog

var is_connected := false

func _ready():
	send_button.pressed.connect(_on_send)
	set_connection_status(false)

func set_connection_status(connected: bool):
	is_connected = connected
	if status_label:
		status_label.text = "● MCP Connected" if connected else "○ MCP Disconnected"
		status_label.modulate = Color.GREEN if connected else Color.RED

func _on_send():
	var text = chat_input.text.strip_edges()
	if text.is_empty():
		return
	chat_log.append_text("\n[b]You:[/b] %s\n" % text)
	chat_input.text = ""
	# TODO: 发送到 AI 服务
	chat_log.append_text("[i]Processing...[/i]\n")
