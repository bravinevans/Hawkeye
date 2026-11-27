import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from core.terminal import HawkeyeTerminal


class SplitWorkspace(Gtk.Box):
    def __init__(
        self,
        config: dict,
        theme_engine,
        initial_cwd: str | None = None,
        on_empty_callback=None,
        on_state_change=None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.config = config
        self.theme_engine = theme_engine
        self.initial_cwd = initial_cwd
        self.on_empty_callback = on_empty_callback
        self.on_state_change = on_state_change

        self.terminals: list[HawkeyeTerminal] = []
        self.active_terminal: HawkeyeTerminal | None = None

        initial = self._create_terminal(initial_cwd)
        self.append(initial)
        self.active_terminal = initial

    def _create_terminal(self, cwd: str | None = None) -> HawkeyeTerminal:
        term = HawkeyeTerminal(
            config=self.config,
            theme=self.theme_engine.current_theme,
            initial_cwd=cwd,
            on_exit_callback=self._on_terminal_exited,
            on_focus_callback=self._on_terminal_focused,
            on_split_h=lambda: self.split_active(Gtk.Orientation.HORIZONTAL),
            on_split_v=lambda: self.split_active(Gtk.Orientation.VERTICAL),
            on_close_pane=self.close_pane,
        )
        self.terminals.append(term)
        self._sync_pane_headers()
        return term

    def _sync_pane_headers(self) -> None:
        show_bars = len(self.terminals) > 1
        for idx, term in enumerate(self.terminals, start=1):
            term.set_split_header_visible(show_bars, idx)

    def _on_terminal_focused(self, term: HawkeyeTerminal) -> None:
        self.active_terminal = term

    def split_active(self, orientation: Gtk.Orientation) -> None:
        target = self.active_terminal or (self.terminals[0] if self.terminals else None)
        if not target:
            return

        parent = target.get_parent()
        if not parent:
            return

        new_term = self._create_terminal(target.get_current_cwd())
        paned = Gtk.Paned(orientation=orientation)
        paned.set_hexpand(True)
        paned.set_vexpand(True)
        paned.set_wide_handle(False)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(True)
        paned.set_shrink_end_child(True)

        if isinstance(parent, Gtk.Paned):
            is_start = parent.get_start_child() == target
            if is_start:
                parent.set_start_child(None)
            else:
                parent.set_end_child(None)

            paned.set_start_child(target)
            paned.set_end_child(new_term)

            if is_start:
                parent.set_start_child(paned)
            else:
                parent.set_end_child(paned)
        else:
            self.remove(target)
            paned.set_start_child(target)
            paned.set_end_child(new_term)
            self.append(paned)

        alloc = paned.get_allocation()
        if orientation == Gtk.Orientation.HORIZONTAL and alloc.width > 0:
            paned.set_position(alloc.width // 2)
        elif orientation == Gtk.Orientation.VERTICAL and alloc.height > 0:
            paned.set_position(alloc.height // 2)

        self.active_terminal = new_term
        self._sync_pane_headers()
        new_term.focus_terminal()
        if self.on_state_change:
            self.on_state_change()

    def close_pane(self, term: HawkeyeTerminal) -> None:
        self._remove_terminal(term)

    def close_active_pane(self) -> None:
        if self.active_terminal:
            self._remove_terminal(self.active_terminal)

    def _on_terminal_exited(self, term: HawkeyeTerminal, _status: int) -> None:
        self._remove_terminal(term)

    def _remove_terminal(self, term: HawkeyeTerminal) -> None:
        if term not in self.terminals:
            return
        self.terminals.remove(term)

        if not self.terminals:
            if self.on_empty_callback:
                self.on_empty_callback(self)
            return

        parent = term.get_parent()
        if isinstance(parent, Gtk.Paned):
            sibling = (
                parent.get_end_child()
                if parent.get_start_child() == term
                else parent.get_start_child()
            )
            parent.set_start_child(None)
            parent.set_end_child(None)

            grandparent = parent.get_parent()
            if isinstance(grandparent, Gtk.Paned):
                if grandparent.get_start_child() == parent:
                    grandparent.set_start_child(sibling)
                else:
                    grandparent.set_end_child(sibling)
            elif grandparent == self:
                self.remove(parent)
                if sibling:
                    self.append(sibling)
        elif parent == self:
            self.remove(term)

        self.active_terminal = self.terminals[-1]
        self._sync_pane_headers()
        self.active_terminal.focus_terminal()
        if self.on_state_change:
            self.on_state_change()

    def apply_theme(self, theme: dict) -> None:
        for term in self.terminals:
            term.apply_theme(theme)

    def apply_terminal_settings(self, term_cfg: dict) -> None:
        for term in self.terminals:
            term.apply_terminal_settings(term_cfg)

    def has_active_processes(self) -> bool:
        return any(t.has_foreground_process() for t in self.terminals)

    def focus_active(self) -> None:
        if self.active_terminal:
            self.active_terminal.focus_terminal()
