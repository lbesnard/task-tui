from textual.app import ComposeResult
from textual.widgets import Static
from textual.screen import ModalScreen


class QuickMenuScreen(ModalScreen):
    def __init__(self, menu_type, app_ref):
        super().__init__()
        self.menu_type = menu_type
        self.app_ref = app_ref

    def compose(self) -> ComposeResult:
        text = ""
        if self.menu_type == "main":
            text = "📅 SET DUE: [[n]] Today | [[t]] Tomorrow | [[e]] End of... | [[Esc]] Cancel"
        elif self.menu_type == "end_of":
            text = "📅 END OF: [[w]] Week | [[m]] Month | [[y]] Year | [[Esc]] Back"
        elif self.menu_type == "priority":
            text = "⚡ SET PRIO: [[h]] High | [[m]] Mid | [[l]] Low | [[x]] Clear | [[Esc]] Cancel"

        yield Static(text, id="context_bar", classes="visible")

    def on_key(self, event) -> None:
        key = event.key.lower()

        if key == "escape":
            if self.menu_type == "end_of":
                self.dismiss("back_to_main")
            else:
                self.dismiss(None)
        elif self.menu_type == "main":
            if key == "n":
                self.app_ref.apply_quick_date("today")
                self.dismiss(None)
            elif key == "t":
                self.app_ref.apply_quick_date("tomorrow")
                self.dismiss(None)
            elif key == "e":
                self.dismiss("go_to_end_of")
        elif self.menu_type == "end_of":
            if key == "w":
                self.app_ref.apply_quick_date("eow")
            elif key == "m":
                self.app_ref.apply_quick_date("eom")
            elif key == "y":
                self.app_ref.apply_quick_date("eoy")
            if key in ["w", "m", "y"]:
                self.dismiss(None)
        elif self.menu_type == "priority":
            if key == "h":
                self.app_ref.apply_quick_prio("H")
            elif key == "m":
                self.app_ref.apply_quick_prio("M")
            elif key == "l":
                self.app_ref.apply_quick_prio("L")
            elif key == "x":
                self.app_ref.apply_quick_prio("")
            if key in ["h", "m", "l", "x"]:
                self.dismiss(None)

        event.stop()
