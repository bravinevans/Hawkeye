import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

SHORTCUT_BINDINGS = [
    ("Ctrl + Shift + T", "New Terminal Tab"),
    ("Ctrl + Shift + W", "Close Active Tab"),
    ("Ctrl + Tab / Ctrl + Shift + Tab", "Next / Previous Tab"),
    ("Ctrl + Shift + D", "Split Terminal Horizontally"),
    ("Ctrl + Shift + E", "Split Terminal Vertically"),
    ("Ctrl + Shift + P", "Open Command Palette"),
    ("Ctrl + Shift + A", "Toggle Helper Drawer"),
    ("Ctrl + Shift + M", "Open Live System Monitor"),
    ("Ctrl + B", "Toggle Navigation Sidebar"),
    ("Ctrl + ,", "Open Settings & Themes"),
]


class ShortcutsAndAliasesView(Gtk.Box):
    def __init__(self, on_inject_command):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self.on_inject_command = on_inject_command
        self.custom_snippets = [
            ("Update Arch System", "sudo pacman -Syu"),
            ("Clean Package Cache", "sudo pacman -Sc"),
            ("Check Failed Systemd Units", "systemctl --failed"),
            ("Inspect Listening Ports", "ss -tulnp"),
        ]

        title = Gtk.Label(label="HAWKEYE // SHORTCUTS & QUICK COMMANDS")
        title.add_css_class("hawkeye-brand")
        title.set_xalign(0.0)
        self.append(title)

        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        cols.set_vexpand(True)
        self.append(cols)

        # Left column: Keybindings
        kb_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        kb_card.add_css_class("panel-card")
        kb_card.set_hexpand(True)
        cols.append(kb_card)

        kb_hdr = Gtk.Label(label="KEYBOARD SHORTCUTS")
        kb_hdr.add_css_class("hawkeye-tagline")
        kb_hdr.set_xalign(0.0)
        kb_card.append(kb_hdr)

        for keys, desc in SHORTCUT_BINDINGS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            d_lbl = Gtk.Label(label=desc)
            d_lbl.set_xalign(0.0)
            d_lbl.set_hexpand(True)

            k_lbl = Gtk.Label(label=keys)
            k_lbl.add_css_class("cmd-code-box")

            row.append(d_lbl)
            row.append(k_lbl)
            kb_card.append(row)

        # Right column: Custom Quick Commands
        cmd_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        cmd_card.add_css_class("panel-card")
        cmd_card.set_hexpand(True)
        cols.append(cmd_card)

        cmd_hdr = Gtk.Label(label="CUSTOM COMMAND SNIPPETS")
        cmd_hdr.add_css_class("hawkeye-tagline")
        cmd_hdr.set_xalign(0.0)
        cmd_card.append(cmd_hdr)

        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Label")
        self.name_entry.add_css_class("hawkeye-input")

        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_placeholder_text("Shell command...")
        self.cmd_entry.add_css_class("hawkeye-input")
        self.cmd_entry.set_hexpand(True)

        add_btn = Gtk.Button(label="Add")
        add_btn.add_css_class("accent-btn")
        add_btn.connect("clicked", lambda *_: self._add_snippet())

        add_row.append(self.name_entry)
        add_row.append(self.cmd_entry)
        add_row.append(add_btn)
        cmd_card.append(add_row)

        self.snippets_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        cmd_card.append(self.snippets_list)
        self._render_snippets()

    def _add_snippet(self) -> None:
        name = self.name_entry.get_text().strip()
        cmd = self.cmd_entry.get_text().strip()
        if name and cmd:
            self.custom_snippets.append((name, cmd))
            self.name_entry.set_text("")
            self.cmd_entry.set_text("")
            self._render_snippets()

    def _render_snippets(self) -> None:
        child = self.snippets_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.snippets_list.remove(child)
            child = nxt

        for name, cmd in self.custom_snippets:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=f"{name}: {cmd}")
            lbl.add_css_class("cmd-code-box")
            lbl.set_xalign(0.0)
            lbl.set_hexpand(True)

            run_btn = Gtk.Button(label="Type")
            run_btn.add_css_class("flat-btn")
            run_btn.connect("clicked", lambda *_, c=cmd: self.on_inject_command(c, False))

            row.append(lbl)
            row.append(run_btn)
            self.snippets_list.append(row)
