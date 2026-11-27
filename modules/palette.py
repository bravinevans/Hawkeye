import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk


class CommandPalette(Gtk.Window):
    def __init__(self, parent_window: Gtk.Window, actions: list[tuple[str, str, callable]]):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_decorated(False)
        self.set_default_size(520, 340)
        self.add_css_class("palette-window")

        self.actions = actions

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.set_child(root)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Type a Hawkeye command...")
        self.search_entry.add_css_class("palette-entry")
        self.search_entry.connect("changed", self._on_filter_changed)
        self.search_entry.connect("activate", self._on_entry_activate)
        root.append(self.search_entry)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.append(scrolled)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(self.list_box)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

        self.visible_callbacks: list[callable] = []
        self._populate("")
        self.search_entry.grab_focus()

    def _populate(self, query: str) -> None:
        child = self.list_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt

        self.visible_callbacks.clear()
        q = query.strip().lower()

        for title, shortcut, callback in self.actions:
            if q and q not in title.lower() and q not in shortcut.lower():
                continue

            btn = Gtk.Button()
            btn.add_css_class("palette-row")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            lbl = Gtk.Label(label=title)
            lbl.set_xalign(0.0)
            lbl.set_hexpand(True)

            sc_lbl = Gtk.Label(label=shortcut)
            sc_lbl.add_css_class("hawkeye-tagline")

            row.append(lbl)
            row.append(sc_lbl)
            btn.set_child(row)

            btn.connect("clicked", lambda *_, cb=callback: self._execute(cb))
            self.list_box.append(btn)
            self.visible_callbacks.append(callback)

    def _on_filter_changed(self, entry: Gtk.Entry) -> None:
        self._populate(entry.get_text())

    def _on_entry_activate(self, _entry: Gtk.Entry) -> None:
        if self.visible_callbacks:
            self._execute(self.visible_callbacks[0])

    def _execute(self, callback: callable) -> None:
        self.close()
        callback()

    def _on_key_pressed(self, _ctrl, keyval: int, _keycode: int, _state: Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False
