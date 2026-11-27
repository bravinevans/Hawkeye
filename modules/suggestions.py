from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class HawkeyeSearchView(Gtk.Box):
    def __init__(self, on_inject_command):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self.on_inject_command = on_inject_command

        title = Gtk.Label(label="HAWKEYE // SHELL HISTORY & COMMAND SEARCH")
        title.add_css_class("hawkeye-brand")
        title.set_xalign(0.0)
        self.append(title)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Filter your shell history (~/.bash_history, ~/.zsh_history)...")
        self.search_entry.add_css_class("hawkeye-input")
        self.search_entry.connect("changed", lambda *_: self._refresh())
        self.append(self.search_entry)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(self.list_box)

        self._refresh()

    def _read_history(self) -> list[str]:
        seen = set()
        commands = []
        for hist_name in (".zsh_history", ".bash_history"):
            p = Path.home() / hist_name
            if not p.exists():
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
                for raw in reversed(lines):
                    cmd = raw.split(";", 1)[1] if raw.startswith(":") and ";" in raw else raw
                    cmd = cmd.strip()
                    if cmd and cmd not in seen:
                        seen.add(cmd)
                        commands.append(cmd)
            except OSError:
                continue
        return commands

    def _refresh(self) -> None:
        child = self.list_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt

        query = self.search_entry.get_text().strip().lower()
        history = self._read_history()
        matches = [c for c in history if not query or query in c.lower()][:60]

        if not matches:
            lbl = Gtk.Label(label="No matching shell history entries found.")
            lbl.add_css_class("hawkeye-tagline")
            lbl.set_xalign(0.0)
            self.list_box.append(lbl)
            return

        for cmd in matches:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("panel-card")

            lbl = Gtk.Label(label=cmd)
            lbl.add_css_class("cmd-code-box")
            lbl.set_xalign(0.0)
            lbl.set_hexpand(True)
            lbl.set_ellipsize(3)

            type_btn = Gtk.Button(label="Type")
            type_btn.add_css_class("flat-btn")
            type_btn.connect("clicked", lambda *_, c=cmd: self.on_inject_command(c, False))

            run_btn = Gtk.Button(label="Run")
            run_btn.add_css_class("accent-btn")
            run_btn.connect("clicked", lambda *_, c=cmd: self.on_inject_command(c, True))

            row.append(lbl)
            row.append(type_btn)
            row.append(run_btn)
            self.list_box.append(row)
