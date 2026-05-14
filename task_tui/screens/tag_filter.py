from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem
from textual.containers import Vertical
from textual.screen import ModalScreen


class PassthroughListView(ListView):
    """ListView that passes Escape key to parent."""
    
    def on_key(self, event) -> None:
        if event.key == "escape":
            # Let Escape bubble to parent (ModalScreen)
            return
        
        # Handle navigation keys normally for ListView
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
            self.action_first()
            event.stop()
        elif event.key == "end":
            self.action_last()
            event.stop()


class TagFilterScreen(ModalScreen):
    """Modal for filtering tasks by tag with multi-select support."""

    BINDINGS = [
        ("escape", "apply_filter", "Apply Filter"),
    ]

    CSS = """
    #tag_filter_container {
        background: $surface;
        border: thick $primary;
        width: 50;
        height: auto;
        align: center middle;
        padding: 1;
    }
    #tag_filter_header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #tag_filter_list {
        height: auto;
        max-height: 20;
        margin-bottom: 1;
        border: solid $accent;
    }
    """

    def __init__(self, all_tags, selected_tags):
        super().__init__()
        self.all_tags = sorted(all_tags)  # Sort for consistent ordering
        self.selected_tags = set(selected_tags)  # Copy to avoid modifying original
        self.show_untagged = "__untagged__" in selected_tags
        self.tag_items = {}  # Map tag name to ListItem

    def compose(self) -> ComposeResult:
        with Vertical(id="tag_filter_container"):
            yield Label("🏷️ FILTER BY TAG", id="tag_filter_header")
            yield Label(
                "[b]Enter[/b] to toggle · [b]Esc[/b] to apply",
                id="tag_filter_help",
            )
            yield PassthroughListView(id="tag_filter_list")

    def on_mount(self) -> None:
        list_view = self.query_one("#tag_filter_list")

        # Create special items
        untagged_check = "✓" if self.show_untagged else " "
        untagged_item = ListItem(Static(f"[dim]{untagged_check}[/dim] [bold][cyan]Untagged[/cyan][/bold]"))
        untagged_item.tag_name = "__untagged__"
        list_view.append(untagged_item)

        select_all_item = ListItem(Static("[bold][green]✓ SELECT ALL[/green][/bold]"))
        select_all_item.tag_name = "__select_all__"
        list_view.append(select_all_item)

        clear_item = ListItem(Static("[bold][red]✗ CLEAR ALL[/red][/bold]"))
        clear_item.tag_name = "__clear_all__"
        list_view.append(clear_item)

        # Add tags
        for tag in self.all_tags:
            check = "✓" if tag in self.selected_tags else " "
            item = ListItem(Static(f"[dim]{check}[/dim] {tag}"))
            item.tag_name = tag
            self.tag_items[tag] = item
            list_view.append(item)

        if list_view.children:
            list_view.focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            # Return selected tags with untagged flag
            result = self.selected_tags.copy()
            if self.show_untagged:
                result.add("__untagged__")
            self.dismiss(result)
            return  # Don't let other handlers process this
        
        list_view = self.query_one("#tag_filter_list")

        if event.key == "j":
            list_view.action_cursor_down()
            event.stop()
        elif event.key == "k":
            list_view.action_cursor_up()
            event.stop()
        elif event.key == "enter":
            self._toggle_current_selection()
            event.stop()

    def _toggle_current_selection(self) -> None:
        list_view = self.query_one("#tag_filter_list")
        if list_view.highlighted_child is None:
            return

        item = list_view.highlighted_child
        tag_name = getattr(item, "tag_name", None)

        if tag_name == "__select_all__":
            self.selected_tags = set(self.all_tags)
            self.show_untagged = True
            self._update_display()
        elif tag_name == "__clear_all__":
            self.selected_tags.clear()
            self.show_untagged = False
            self._update_display()
        elif tag_name == "__untagged__":
            self.show_untagged = not self.show_untagged
            self._update_display()
        elif tag_name:
            if tag_name in self.selected_tags:
                self.selected_tags.discard(tag_name)
            else:
                self.selected_tags.add(tag_name)
            self._update_display()

    def _update_display(self) -> None:
        """Update the checkmarks in the list view."""
        list_view = self.query_one("#tag_filter_list")

        for item in list_view.children:
            tag_name = getattr(item, "tag_name", None)

            if tag_name == "__select_all__" or tag_name == "__clear_all__":
                continue

            if tag_name == "__untagged__":
                check = "✓" if self.show_untagged else " "
                item.children[0].update(f"[dim]{check}[/dim] [bold][cyan]Untagged[/cyan][/bold]")
            elif tag_name in self.selected_tags:
                # Show checkmark
                item.children[0].update(f"[dim]✓[/dim] {tag_name}")
            else:
                # Show empty space
                item.children[0].update(f"[dim] [/dim] {tag_name}")

    def action_apply_filter(self) -> None:
        """Action handler for applying the filter when Escape is pressed."""
        # Return selected tags with untagged flag
        result = self.selected_tags.copy()
        if self.show_untagged:
            result.add("__untagged__")
        self.dismiss(result)
