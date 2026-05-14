from textual.app import ComposeResult
from textual.widgets import Static
from textual.screen import ModalScreen

from task_tui.screens.project_filter import ProjectFilterScreen
from task_tui.screens.tag_filter import TagFilterScreen


class FilterMenuScreen(ModalScreen):
    def __init__(self, app_ref):
        super().__init__()
        self.app_ref = app_ref

    def compose(self) -> ComposeResult:
        text = "🔍 FILTER: [[p]] Project · [[t]] Tag · [[Esc]] Cancel"
        yield Static(text, id="context_bar", classes="visible")

    def on_key(self, event) -> None:
        key = event.key.lower()

        if key == "escape":
            self.dismiss(None)
        elif key == "p":
            all_projects = self.app_ref._get_all_projects()
            if not all_projects:
                self.app_ref.notify("No projects found in tasks", severity="warning")
                self.dismiss(None)
            else:
                if not self.app_ref.project_filter:
                    self.app_ref.project_filter = all_projects.copy()
                self.app_ref.show_unassigned_tasks = "__unassigned__" in self.app_ref.project_filter

                def on_filter_select(selected_projects):
                    self.app_ref._apply_filter_result(selected_projects, all_projects)
                    self.dismiss(None)

                self.app.push_screen(
                    ProjectFilterScreen(all_projects, self.app_ref.project_filter),
                    on_filter_select,
                )
        elif key == "t":
            all_tags = self.app_ref._get_all_tags()
            if not all_tags:
                self.app_ref.notify("No tags found in tasks", severity="warning")
                self.dismiss(None)
            else:
                if not self.app_ref.tag_filter:
                    self.app_ref.tag_filter = all_tags.copy()
                self.app_ref.show_untagged_tasks = "__untagged__" in self.app_ref.tag_filter

                def on_tag_filter_select(selected_tags):
                    self.app_ref._apply_tag_filter_result(selected_tags, all_tags)
                    self.dismiss(None)

                self.app.push_screen(
                    TagFilterScreen(all_tags, self.app_ref.tag_filter),
                    on_tag_filter_select,
                )

        event.stop()
