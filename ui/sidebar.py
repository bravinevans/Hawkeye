import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

NAV_ITEMS = [
    ("home", "⌂", "Home"),
    ("terminal", "▶", "Terminal"),
    ("system", "◈", "System"),
    ("files", "◫", "Files"),
    ("search", "⌕", "Search"),
    ("assistant", "✦", "Helper"),
    ("shortcuts", "⌘", "Shortcuts"),
    ("settings", "⚙", "Settings"),
]


class HawkeyeSidebar(Gtk.Box):
    def __init__(self, width: int, on_navigate):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class("hawkeye-sidebar")
        self.expanded_width = max(140, width)
        self.compact_width = 48
        self.compact = False
        self.set_size_request(self.expanded_width, -1)
        self.on_navigate = on_navigate
        self.buttons: dict[str, Gtk.Button] = {}
        self.btn_labels: dict[str, tuple[Gtk.Label, str]] = {}

        for item_id, icon, label in NAV_ITEMS:
            btn = self._make_nav_button(item_id, icon, label)
            self.append(btn)
            self.buttons[item_id] = btn

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        self.append(spacer)

        about_btn = self._make_nav_button("about", "ⓘ", "About")
        self.append(about_btn)
        self.buttons["about"] = about_btn

        self.set_active("terminal")

    def _make_nav_button(self, item_id: str, icon: str, label: str) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("nav-item")
        btn.set_tooltip_text(label)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_lbl = Gtk.Label(label=icon)
        icon_lbl.set_xalign(0.5)
        icon_lbl.set_size_request(18, -1)

        text_lbl = Gtk.Label(label=label)
        text_lbl.set_xalign(0.0)
        text_lbl.set_hexpand(True)

        row.append(icon_lbl)
        row.append(text_lbl)
        btn.set_child(row)

        self.btn_labels[item_id] = (text_lbl, label)
        btn.connect("clicked", lambda *_, target=item_id: self.on_navigate(target))
        return btn

    def set_compact(self, compact: bool) -> None:
        self.compact = compact
        self.set_size_request(self.compact_width if compact else self.expanded_width, -1)
        for text_lbl, full_label in self.btn_labels.values():
            text_lbl.set_visible(not compact)
            text_lbl.set_label(full_label)

    def set_active(self, active_id: str) -> None:
        for item_id, btn in self.buttons.items():
            if item_id == active_id:
                btn.add_css_class("active-nav")
            else:
                btn.remove_css_class("active-nav")
