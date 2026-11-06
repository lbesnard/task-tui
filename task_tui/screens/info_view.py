from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ..models import commands

# key -> (label, task command)
VIEWS: dict[str, tuple[str, str]] = {
    "s": ("Stats", "stats"),
    "m": ("Summary", "summary"),
    "c": ("Calendar", "calendar"),
    "b": ("Burndown", "burndown.weekly"),
    "h": ("History", "history.monthly"),
    "p": ("Projects", "projects"),
    "t": ("Tags", "tags"),
}


def views_bar(active: str) -> str:
    """Render the key legend, highlighting the active view."""
    parts = []
    for key, (label, _) in VIEWS.items():
        entry = f"[b]{key}[/b] {label}"
        parts.append(f"[reverse] {entry} [/reverse]" if key == active else f" {entry} ")
    return "|".join(parts)


class InfoViewScreen(ModalScreen):
    """Read-only Taskwarrior overviews (stats, summary, calendar, ...)."""

    CSS = """
    #info_container { background: $surface; border: thick $primary; width: 90%; height: 85%; padding: 1 2; }
    #info_bar { margin-bottom: 1; }
    #info_scroll { height: 1fr; }
    #info_hint { text-align: center; color: $text-muted; }
    """

    def __init__(self, width: int = 100, initial: str = "s") -> None:
        super().__init__()
        self.width = width
        self.active = initial

    def compose(self) -> ComposeResult:
        with Vertical(id="info_container"):
            yield Label(views_bar(self.active), id="info_bar")
            with VerticalScroll(id="info_scroll"):
                yield Static("Loading…", id="info_body", markup=False)
            yield Label("Press a highlighted key to switch | [b]j[/b]/[b]k[/b] scroll | [b]Esc[/b]/[b]q[/b] close", id="info_hint")

    def on_mount(self) -> None:
        self.load(self.active)

    def load(self, key: str) -> None:
        self.active = key
        self.query_one("#info_bar").update(views_bar(key))
        self.query_one("#info_body").update("Loading…")
        command = VIEWS[key][1]
        width = self.width

        def work() -> None:
            text = commands.run_info_view(command, width)
            self.app.call_from_thread(self._show, key, text)

        self.run_worker(work, thread=True, group="info-view", exclusive=True)

    def _show(self, key: str, text: str) -> None:
        if key == self.active:  # ignore a slow load the user already left
            self.query_one("#info_body").update(text)
            self.query_one("#info_scroll").scroll_home(animate=False)

    def on_key(self, event) -> None:
        key = event.key
        scroll = self.query_one("#info_scroll")
        if key in ("escape", "q"):
            self.dismiss(None)
        elif key in VIEWS:
            self.load(key)
        elif key == "j":
            scroll.scroll_down(animate=False)
        elif key == "k":
            scroll.scroll_up(animate=False)
        else:
            return
        event.stop()
