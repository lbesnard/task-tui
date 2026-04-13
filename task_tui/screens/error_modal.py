from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical
from textual.screen import ModalScreen


class ErrorModalScreen(ModalScreen):
    CSS = """
    #error_container {
        background: $surface;
        border: thick $error;
        width: 70%;
        height: auto;
        max-height: 80%;
        align: center middle;
        padding: 1 2;
    }
    #error_title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }
    #error_body {
        color: $text;
        overflow-y: auto;
        margin-bottom: 1;
    }
    #error_hint {
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, error_message: str) -> None:
        super().__init__()
        self.error_message = error_message

    def compose(self) -> ComposeResult:
        with Vertical(id="error_container"):
            yield Label("❌ Save Failed", id="error_title")
            yield Static(self.error_message, id="error_body")
            yield Label("[b]Enter[/b] or [b]Esc[/b] to close", id="error_hint")

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter"):
            self.dismiss(None)
            event.stop()
