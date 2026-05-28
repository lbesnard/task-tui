from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static
from textual.containers import Vertical


class PassthroughListView(ListView):
    """ListView that lets Escape bubble to the parent ModalScreen."""

    def on_key(self, event) -> None:
        if event.key == "escape":
            return  # let it bubble
        if event.key == "down":
            self.action_cursor_down()
            event.stop()
        elif event.key == "up":
            self.action_cursor_up()
            event.stop()
        elif event.key == "pagedown":
            self.action_page_down()
            event.stop()
        elif event.key == "pageup":
            self.action_page_up()
            event.stop()
        elif event.key == "home":
            self.action_scroll_home()
            event.stop()
        elif event.key == "end":
            self.action_scroll_end()
            event.stop()


class MultiSelectFilterScreen(ModalScreen):
    """Generic multi-select filter modal.

    Args:
        title:          Header label (e.g. "FILTER BY PROJECT").
        all_items:      Sorted iterable of all selectable item names.
        selected_items: Currently selected item names (may include sentinel keys).
        sentinel_key:   Internal key for the "none assigned" bucket
                        (e.g. "__unassigned__" or "__untagged__").
        sentinel_label: Display label for the sentinel row (e.g. "Unassigned").

    Dismisses with:
        A ``set[str]`` of selected item names, potentially containing
        ``sentinel_key`` when the unassigned/untagged bucket is active.
        ``None`` if the user cancels without changing anything (Esc with no
        changes — currently same as applying; caller handles both).
    """

    BINDINGS = [("escape", "apply_filter", "Apply Filter")]

    CSS = """
    #msf_container {
        background: $surface;
        border: thick $primary;
        width: 50;
        height: auto;
        align: center middle;
        padding: 1;
    }
    #msf_header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #msf_list {
        height: auto;
        max-height: 20;
        margin-bottom: 1;
        border: solid $accent;
    }
    """

    def __init__(
        self,
        title: str,
        all_items: list[str],
        selected_items: set[str],
        sentinel_key: str,
        sentinel_label: str,
    ) -> None:
        super().__init__()
        self.filter_title = title
        self.all_items = sorted(all_items)
        self.selected_items: set[str] = set(selected_items)
        self.sentinel_key = sentinel_key
        self.sentinel_label = sentinel_label
        self.show_sentinel = sentinel_key in selected_items
        self._item_nodes: dict[str, ListItem] = {}

    # ------------------------------------------------------------------ #
    # Compose
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        with Vertical(id="msf_container"):
            yield Label(f"🔍 {self.filter_title}", id="msf_header")
            yield Label("[b]Enter[/b] to toggle · [b]Esc[/b] to apply", id="msf_help")
            yield PassthroughListView(id="msf_list")

    def on_mount(self) -> None:
        lv = self.query_one("#msf_list")

        sentinel_check = "✓" if self.show_sentinel else " "
        sentinel_item = ListItem(
            Static(f"[dim]{sentinel_check}[/dim] [bold][cyan]{self.sentinel_label}[/cyan][/bold]")
        )
        sentinel_item._msf_key = self.sentinel_key  # type: ignore[attr-defined]
        lv.append(sentinel_item)

        for label, item_node in (
            ("[bold][green]✓ SELECT ALL[/green][/bold]", "__select_all__"),
            ("[bold][red]✗ CLEAR ALL[/red][/bold]", "__clear_all__"),
        ):
            node = ListItem(Static(label))
            node._msf_key = item_node  # type: ignore[attr-defined]
            lv.append(node)

        for name in self.all_items:
            check = "✓" if name in self.selected_items else " "
            node = ListItem(Static(f"[dim]{check}[/dim] {name}"))
            node._msf_key = name  # type: ignore[attr-defined]
            self._item_nodes[name] = node
            lv.append(node)

        lv.focus()

    # ------------------------------------------------------------------ #
    # Key handling
    # ------------------------------------------------------------------ #

    def on_key(self, event) -> None:
        lv = self.query_one("#msf_list")
        key = event.key
        if key == "escape":
            self.action_apply_filter()
        elif key == "j":
            lv.action_cursor_down()
            event.stop()
        elif key == "k":
            lv.action_cursor_up()
            event.stop()
        elif key == "enter":
            self._toggle_current()
            event.stop()

    def action_apply_filter(self) -> None:
        result = set(self.selected_items)
        if self.show_sentinel:
            result.add(self.sentinel_key)
        self.dismiss(result)

    # ------------------------------------------------------------------ #
    # Toggle logic
    # ------------------------------------------------------------------ #

    def _toggle_current(self) -> None:
        lv = self.query_one("#msf_list")
        item = lv.highlighted_child
        if item is None:
            return
        key = getattr(item, "_msf_key", None)
        if key == "__select_all__":
            self.selected_items = set(self.all_items)
            self.show_sentinel = True
        elif key == "__clear_all__":
            self.selected_items.clear()
            self.show_sentinel = False
        elif key == self.sentinel_key:
            self.show_sentinel = not self.show_sentinel
        elif key:
            if key in self.selected_items:
                self.selected_items.discard(key)
            else:
                self.selected_items.add(key)
        self._refresh_display()

    def _refresh_display(self) -> None:
        lv = self.query_one("#msf_list")
        for item in lv.children:
            key = getattr(item, "_msf_key", None)
            if key in ("__select_all__", "__clear_all__", None):
                continue
            static = item.children[0]  # type: ignore[index]
            if key == self.sentinel_key:
                check = "✓" if self.show_sentinel else " "
                static.update(
                    f"[dim]{check}[/dim] [bold][cyan]{self.sentinel_label}[/cyan][/bold]"
                )
            else:
                check = "✓" if key in self.selected_items else " "
                static.update(f"[dim]{check}[/dim] {key}")
