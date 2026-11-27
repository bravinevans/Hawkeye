import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.splits import SplitWorkspace


class TabManager:
    def __init__(self, config: dict, theme_engine, on_tab_changed=None):
        self.config = config
        self.theme_engine = theme_engine
        self.on_tab_changed = on_tab_changed

        self.tabs: list[dict] = []
        self.active_index: int = -1
        self._counter: int = 0

        self.header_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.tab_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.new_tab_btn = Gtk.Button(label="+")
        self.new_tab_btn.add_css_class("header-btn")
        self.new_tab_btn.set_tooltip_text("New Terminal Tab (Ctrl+Shift+T)")
        self.new_tab_btn.connect("clicked", lambda *_: self.new_tab())

        self.header_container.append(self.tab_strip)
        self.header_container.append(self.new_tab_btn)

        self.workspace_stack = Gtk.Stack()
        self.workspace_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.workspace_stack.set_hexpand(True)
        self.workspace_stack.set_vexpand(True)

    def new_tab(self, title: str | None = None, initial_cwd: str | None = None) -> dict:
        self._counter += 1
        tab_id = f"tab_{self._counter}"
        label_text = title or f"{self._counter}: shell"

        workspace = SplitWorkspace(
            config=self.config,
            theme_engine=self.theme_engine,
            initial_cwd=initial_cwd,
            on_empty_callback=self._on_workspace_empty,
            on_state_change=self._notify_change,
        )
        self.workspace_stack.add_named(workspace, tab_id)

        pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        pill.add_css_class("tab-pill")

        select_btn = Gtk.Button(label=label_text)
        select_btn.add_css_class("tab-select-btn")

        close_btn = Gtk.Button(label="×")
        close_btn.add_css_class("tab-close-btn")
        close_btn.set_tooltip_text("Close Tab (Ctrl+Shift+W)")

        pill.append(select_btn)
        pill.append(close_btn)
        self.tab_strip.append(pill)

        tab_info = {
            "id": tab_id,
            "title": label_text,
            "pill": pill,
            "select_btn": select_btn,
            "workspace": workspace,
        }

        select_btn.connect("clicked", lambda *_, t=tab_info: self.activate_tab(t))
        close_btn.connect("clicked", lambda *_, t=tab_info: self.close_tab(t))

        self.tabs.append(tab_info)
        self.activate_tab(tab_info)
        return tab_info

    def activate_tab(self, tab_info: dict) -> None:
        if tab_info not in self.tabs:
            return
        self.active_index = self.tabs.index(tab_info)
        self.workspace_stack.set_visible_child_name(tab_info["id"])

        for idx, t in enumerate(self.tabs):
            if idx == self.active_index:
                t["pill"].add_css_class("active-tab")
            else:
                t["pill"].remove_css_class("active-tab")

        tab_info["workspace"].focus_active()
        self._notify_change()

    def close_tab(self, tab_info: dict) -> None:
        if tab_info not in self.tabs:
            return
        idx = self.tabs.index(tab_info)
        self.tabs.remove(tab_info)
        self.tab_strip.remove(tab_info["pill"])
        self.workspace_stack.remove(tab_info["workspace"])

        if not self.tabs:
            self.new_tab("1: shell")
            return

        next_idx = min(idx, len(self.tabs) - 1)
        self.activate_tab(self.tabs[next_idx])

    def close_active_tab(self) -> None:
        if 0 <= self.active_index < len(self.tabs):
            self.close_tab(self.tabs[self.active_index])

    def next_tab(self) -> None:
        if len(self.tabs) > 1:
            self.activate_tab(self.tabs[(self.active_index + 1) % len(self.tabs)])

    def prev_tab(self) -> None:
        if len(self.tabs) > 1:
            self.activate_tab(self.tabs[(self.active_index - 1) % len(self.tabs)])

    def get_active_workspace(self) -> SplitWorkspace | None:
        if 0 <= self.active_index < len(self.tabs):
            return self.tabs[self.active_index]["workspace"]
        return None

    def total_panes(self) -> int:
        return sum(len(t["workspace"].terminals) for t in self.tabs)

    def export_session(self) -> list[dict]:
        session_tabs = []
        for tab in self.tabs:
            ws: SplitWorkspace = tab["workspace"]
            cwd = ws.active_terminal.get_current_cwd() if ws.active_terminal else None
            session_tabs.append({"title": tab["title"], "cwd": cwd})
        return session_tabs

    def _on_workspace_empty(self, workspace: SplitWorkspace) -> None:
        for tab in list(self.tabs):
            if tab["workspace"] == workspace:
                self.close_tab(tab)
                break

    def _notify_change(self) -> None:
        if self.on_tab_changed:
            self.on_tab_changed()
