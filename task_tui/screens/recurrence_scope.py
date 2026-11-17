from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ..models.commands import RECUR_SERIES, RECUR_THIS


class RecurrenceScopeScreen(ModalScreen):
    """Ask how far a change to a recurring task should reach.

    Taskwarrior asks this itself ("Do you want to modify all pending
    recurrences of this same task?"), but task-tui runs ``task`` without a
    terminal, so the question is asked here and the answer handed over as
    ``rc.recurrence.confirmation``.

    Dismisses with ``RECUR_THIS`` on ``t``/Enter, ``RECUR_SERIES`` on ``a``
    and ``None`` on ``n``/Esc (nothing is changed).
    """

    CSS = """
    #recur_container { background: $surface; border: thick $warning; width: 60%; height: auto; max-height: 80%; padding: 1 2; align: center middle; }
    #recur_title { text-align: center; text-style: bold; color: $warning; margin-bottom: 1; }
    #recur_body { margin-bottom: 1; }
    #recur_hint { text-align: center; color: $text-muted; }
    """

    def __init__(self, deleting: bool = False) -> None:
        super().__init__()
        verb = "Delete" if deleting else "Apply the change to"
        self.title_text = "🔁 RECURRING TASK"
        self.body_text = (
            f"{verb}\n\n"
            "[b]t[/b]  this task only\n"
            "[b]a[/b]  the whole series: every pending occurrence and the\n"
            "   recurrence template, which future occurrences are made from"
        )

    def compose(self) -> ComposeResult:
        with Vertical(id="recur_container"):
            yield Label(self.title_text, id="recur_title")
            yield Static(self.body_text, id="recur_body")
            yield Label(
                "[b]t[/b]/[b]Enter[/b] this task | [b]a[/b] whole series | [b]n[/b]/[b]Esc[/b] cancel",
                id="recur_hint",
            )

    def on_key(self, event) -> None:
        event.stop()
        if event.key in ("t", "enter"):
            self.dismiss(RECUR_THIS)
        elif event.key == "a":
            self.dismiss(RECUR_SERIES)
        elif event.key in ("n", "escape"):
            self.dismiss(None)
