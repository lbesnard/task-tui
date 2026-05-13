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


class ProjectFilterScreen(ModalScreen):
    """Modal for filtering tasks by project with multi-select and hierarchical support."""

    BINDINGS = [
        ("escape", "apply_filter", "Apply Filter"),
    ]

    CSS = """
    #proj_filter_container {
        background: $surface;
        border: thick $primary;
        width: 50;
        height: auto;
        align: center middle;
        padding: 1;
    }
    #proj_filter_header {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #proj_filter_list {
        height: auto;
        max-height: 20;
        margin-bottom: 1;
        border: solid $accent;
    }
    """

    def __init__(self, all_projects, selected_projects):
        super().__init__()
        self.all_projects = sorted(all_projects)  # Sort for consistent ordering
        self.selected_projects = set(selected_projects)  # Copy to avoid modifying original
        self.show_unassigned = "__unassigned__" in selected_projects
        self.project_items = {}  # Map project name to ListItem
        self.organized_projects = self._organize_projects()

    def _organize_projects(self):
        """Organize projects hierarchically for better display."""
        organized = []
        
        # Separate parent and child projects
        parents = set()
        children_map = {}  # parent -> list of children
        
        for proj in self.all_projects:
            if "." in proj:
                parent = proj.split(".")[0]
                if parent not in children_map:
                    children_map[parent] = []
                children_map[parent].append(proj)
                parents.add(parent)
            else:
                # Top-level project
                if proj not in parents:
                    parents.add(proj)
        
        # Build organized list with parents followed by their children
        processed = set()
        for parent in sorted(parents):
            organized.append((parent, 0))  # (project_name, indent_level)
            processed.add(parent)
            
            # Add children of this parent if they exist
            if parent in children_map:
                for child in sorted(children_map[parent]):
                    organized.append((child, 1))  # Indent children
                    processed.add(child)
        
        # Add any remaining projects not yet added (shouldn't happen but safety check)
        for proj in sorted(self.all_projects):
            if proj not in processed:
                organized.append((proj, 0))
        
        return organized

    def compose(self) -> ComposeResult:
        with Vertical(id="proj_filter_container"):
            yield Label("🔍 FILTER BY PROJECT", id="proj_filter_header")
            yield Label(
                "[b]Enter[/b] to toggle · [b]Esc[/b] to apply",
                id="proj_filter_help",
            )
            yield PassthroughListView(id="proj_filter_list")

    def on_mount(self) -> None:
        list_view = self.query_one("#proj_filter_list")

        # Create special items
        unassigned_check = "✓" if self.show_unassigned else " "
        unassigned_item = ListItem(Static(f"[dim]{unassigned_check}[/dim] [bold][cyan]Unassigned[/cyan][/bold]"))
        unassigned_item.project_name = "__unassigned__"
        list_view.append(unassigned_item)

        select_all_item = ListItem(Static("[bold][green]✓ SELECT ALL[/green][/bold]"))
        select_all_item.project_name = "__select_all__"
        list_view.append(select_all_item)

        clear_item = ListItem(Static("[bold][red]✗ CLEAR ALL[/red][/bold]"))
        clear_item.project_name = "__clear_all__"
        list_view.append(clear_item)

        # Add organized projects with hierarchy
        for project, indent in self.organized_projects:
            check = "✓" if project in self.selected_projects else " "
            indent_str = "  " if indent > 0 else ""
            item = ListItem(Static(f"{indent_str}[dim]{check}[/dim] {project}"))
            item.project_name = project
            self.project_items[project] = item
            list_view.append(item)

        if list_view.children:
            list_view.focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            # Return selected projects with unassigned flag
            result = self.selected_projects.copy()
            if self.show_unassigned:
                result.add("__unassigned__")
            self.dismiss(result)
            return  # Don't let other handlers process this
        
        list_view = self.query_one("#proj_filter_list")

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
        list_view = self.query_one("#proj_filter_list")
        if list_view.highlighted_child is None:
            return

        item = list_view.highlighted_child
        project_name = getattr(item, "project_name", None)

        if project_name == "__select_all__":
            self.selected_projects = set(self.all_projects)
            self.show_unassigned = True
            self._update_display()
        elif project_name == "__clear_all__":
            self.selected_projects.clear()
            self.show_unassigned = False
            self._update_display()
        elif project_name == "__unassigned__":
            self.show_unassigned = not self.show_unassigned
            self._update_display()
        elif project_name:
            if project_name in self.selected_projects:
                self.selected_projects.discard(project_name)
            else:
                self.selected_projects.add(project_name)
            self._update_display()

    def _update_display(self) -> None:
        """Update the checkmarks in the list view."""
        list_view = self.query_one("#proj_filter_list")

        for item in list_view.children:
            project_name = getattr(item, "project_name", None)

            if project_name == "__select_all__" or project_name == "__clear_all__":
                continue

            if project_name == "__unassigned__":
                check = "✓" if self.show_unassigned else " "
                item.children[0].update(f"[dim]{check}[/dim] [bold][cyan]Unassigned[/cyan][/bold]")
            elif project_name in self.selected_projects:
                # Show checkmark
                indent = "  " if "." in project_name else ""
                item.children[0].update(f"{indent}[dim]✓[/dim] {project_name}")
            else:
                # Show empty space
                indent = "  " if "." in project_name else ""
                item.children[0].update(f"{indent}[dim] [/dim] {project_name}")

    def action_apply_filter(self) -> None:
        """Action handler for applying the filter when Escape is pressed."""
        # Return selected projects with unassigned flag
        result = self.selected_projects.copy()
        if self.show_unassigned:
            result.add("__unassigned__")
        self.dismiss(result)

