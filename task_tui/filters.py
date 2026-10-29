from __future__ import annotations

from .screens import FilterMenuScreen, MultiSelectFilterScreen


class FilterActionsMixin:
    """Project/tag filter actions for TaskProApp.

    Expects the host app to provide ``state`` (AppState), ``push_screen``,
    ``notify`` and ``update_table_view``.
    """

    def action_filter_mode(self) -> None:
        def handle(result: str | None) -> None:
            if result == "project":
                self._open_project_filter()
            elif result == "tag":
                self._open_tag_filter()

        self.push_screen(FilterMenuScreen(), handle)

    def _open_project_filter(self) -> None:
        all_projects = self.state.get_all_projects()
        if not all_projects:
            self.notify("No projects found in tasks", severity="warning")
            return
        current = self.state.project_filter or all_projects
        selected = set(current)
        if self.state.show_unassigned_tasks:
            selected.add("__unassigned__")

        def on_done(result: set[str] | None) -> None:
            if result is not None:
                self.state.set_project_filter(result)
                self.update_table_view()

        self.push_screen(
            MultiSelectFilterScreen(
                title="FILTER BY PROJECT",
                all_items=sorted(all_projects),
                selected_items=selected,
                sentinel_key="__unassigned__",
                sentinel_label="Unassigned",
            ),
            on_done,
        )

    def _open_tag_filter(self) -> None:
        all_tags = self.state.get_all_tags()
        if not all_tags:
            self.notify("No tags found in tasks", severity="warning")
            return
        current = self.state.tag_filter or all_tags
        selected = set(current)
        if self.state.show_untagged_tasks:
            selected.add("__untagged__")

        def on_done(result: set[str] | None) -> None:
            if result is not None:
                self.state.set_tag_filter(result)
                self.update_table_view()

        self.push_screen(
            MultiSelectFilterScreen(
                title="FILTER BY TAG",
                all_items=sorted(all_tags),
                selected_items=selected,
                sentinel_key="__untagged__",
                sentinel_label="Untagged",
            ),
            on_done,
        )
