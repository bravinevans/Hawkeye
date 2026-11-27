from pathlib import Path
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk


class HawkeyeFilesView(Gtk.Box):
    def __init__(self, on_inject_command):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self.on_inject_command = on_inject_command
        self.current_dir = Path.home()
        self.show_hidden = False

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="HAWKEYE // FILE INTEGRATION")
        title.add_css_class("hawkeye-brand")
        title.set_xalign(0.0)
        title.set_hexpand(True)

        up_btn = Gtk.Button(label="↑ Parent")
        up_btn.add_css_class("flat-btn")
        up_btn.connect("clicked", lambda *_: self._go_up())

        home_btn = Gtk.Button(label="~ Home")
        home_btn.add_css_class("flat-btn")
        home_btn.connect("clicked", lambda *_: self._load_dir(Path.home()))

        hidden_btn = Gtk.Button(label=".* Hidden")
        hidden_btn.add_css_class("flat-btn")
        hidden_btn.connect("clicked", lambda *_: self._toggle_hidden())

        cd_btn = Gtk.Button(label="cd in Terminal")
        cd_btn.add_css_class("accent-btn")
        cd_btn.connect(
            "clicked",
            lambda *_: self.on_inject_command(f'cd "{self.current_dir}"', True),
        )

        header.append(title)
        header.append(up_btn)
        header.append(home_btn)
        header.append(hidden_btn)
        header.append(cd_btn)
        self.append(header)

        self.path_lbl = Gtk.Label()
        self.path_lbl.add_css_class("cmd-code-box")
        self.path_lbl.set_xalign(0.0)
        self.append(self.path_lbl)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(self.list_box)

        self._load_dir(self.current_dir)

    def _go_up(self) -> None:
        if self.current_dir.parent != self.current_dir:
            self._load_dir(self.current_dir.parent)

    def _toggle_hidden(self) -> None:
        self.show_hidden = not self.show_hidden
        self._load_dir(self.current_dir)

    def _copy_path(self, path: Path) -> None:
        display = Gdk.Display.get_default()
        if display:
            display.get_clipboard().set(str(path))

    def _open_external(self, path: Path) -> None:
        subprocess.Popen(["xdg-open", str(path)])

    def _load_dir(self, target: Path) -> None:
        if not target.exists() or not target.is_dir():
            return
        self.current_dir = target
        self.path_lbl.set_text(str(self.current_dir))

        child = self.list_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt

        try:
            entries = sorted(
                self.current_dir.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except PermissionError:
            lbl = Gtk.Label(label="Permission denied.")
            lbl.add_css_class("hawkeye-tagline")
            self.list_box.append(lbl)
            return

        for entry in entries:
            if not self.show_hidden and entry.name.startswith("."):
                continue

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("panel-card")

            prefix = "[DIR]" if entry.is_dir() else "[FILE]"
            name_btn = Gtk.Button(label=f"{prefix}  {entry.name}")
            name_btn.add_css_class("tab-select-btn")
            name_btn.set_hexpand(True)
            name_btn.get_child().set_xalign(0.0)

            if entry.is_dir():
                name_btn.connect("clicked", lambda *_, p=entry: self._load_dir(p))
            else:
                name_btn.connect("clicked", lambda *_, p=entry: self._open_external(p))

            copy_btn = Gtk.Button(label="Copy Path")
            copy_btn.add_css_class("flat-btn")
            copy_btn.connect("clicked", lambda *_, p=entry: self._copy_path(p))

            term_btn = Gtk.Button(label="Send to Shell")
            term_btn.add_css_class("flat-btn")
            cmd = f'cd "{entry}"' if entry.is_dir() else f'"{entry}"'
            term_btn.connect("clicked", lambda *_, c=cmd: self.on_inject_command(c, False))

            row.append(name_btn)
            row.append(copy_btn)
            row.append(term_btn)
            self.list_box.append(row)
