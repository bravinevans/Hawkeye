import os
from pathlib import Path
import shlex
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Vte", "3.91")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, Gio, Vte, GLib, Pango

from core.shell import detect_shell, get_working_directory


class HawkeyeTerminal(Gtk.Box):
    def __init__(
        self,
        config: dict,
        theme: dict,
        initial_cwd: str | None = None,
        on_exit_callback=None,
        on_focus_callback=None,
        on_split_h=None,
        on_split_v=None,
        on_close_pane=None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.add_css_class("terminal-frame")
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.config = config
        self.initial_cwd = initial_cwd
        self.on_exit_callback = on_exit_callback
        self.on_focus_callback = on_focus_callback
        self.on_split_h = on_split_h
        self.on_split_v = on_split_v
        self.on_close_pane = on_close_pane
        self.child_pid: int = -1

        self.pane_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pane_bar.set_visible(False)

        self.pane_lbl = Gtk.Label(label="PANE 01")
        self.pane_lbl.add_css_class("hawkeye-tagline")
        self.pane_lbl.set_xalign(0.0)
        self.pane_lbl.set_hexpand(True)

        close_pane_btn = Gtk.Button(label="×")
        close_pane_btn.add_css_class("tab-close-btn")
        close_pane_btn.set_tooltip_text("Close Split Pane (Ctrl+Shift+X)")
        close_pane_btn.connect(
            "clicked",
            lambda *_: self.on_close_pane(self) if self.on_close_pane else None,
        )

        self.pane_bar.append(self.pane_lbl)
        self.pane_bar.append(close_pane_btn)
        self.append(self.pane_bar)

        self.search_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_bar.set_visible(False)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Find in terminal output...")
        self.search_entry.add_css_class("hawkeye-input")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", lambda *_: self.find_next())

        prev_btn = Gtk.Button(label="↑")
        prev_btn.add_css_class("flat-btn")
        prev_btn.connect("clicked", lambda *_: self.find_previous())

        next_btn = Gtk.Button(label="↓")
        next_btn.add_css_class("flat-btn")
        next_btn.connect("clicked", lambda *_: self.find_next())

        close_search_btn = Gtk.Button(label="×")
        close_search_btn.add_css_class("flat-btn")
        close_search_btn.connect("clicked", lambda *_: self.toggle_search(False))

        self.search_bar.append(self.search_entry)
        self.search_bar.append(prev_btn)
        self.search_bar.append(next_btn)
        self.search_bar.append(close_search_btn)
        self.append(self.search_bar)

        self.vte = Vte.Terminal()
        self.vte.set_hexpand(True)
        self.vte.set_vexpand(True)
        self.vte.set_size_request(120, 80)

        self.apply_terminal_settings(self.config.get("terminal", {}))
        self.apply_theme(theme)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.vte)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        self.append(scrolled)

        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("enter", self._on_focus_enter)
        focus_ctrl.connect("leave", self._on_focus_leave)
        self.vte.add_controller(focus_ctrl)

        self._setup_drag_and_drop()
        self._setup_context_menu()
        self.vte.connect("child-exited", self._on_child_exited)
        self.spawn_shell()

    def _setup_drag_and_drop(self) -> None:
        drop = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)

        def on_drop(_target, value, _x, _y) -> bool:
            if isinstance(value, Gio.File):
                path = value.get_path()
                if path:
                    self.send_command(shlex.quote(path) + " ", execute=False)
                    return True
            return False

        drop.connect("drop", on_drop)
        self.vte.add_controller(drop)

    def set_split_header_visible(self, visible: bool, index: int = 1) -> None:
        self.pane_lbl.set_text(f"PANE 0{index}")
        self.pane_bar.set_visible(visible)

    def get_current_cwd(self) -> str:
        if self.child_pid > 0:
            proc_cwd = Path(f"/proc/{self.child_pid}/cwd")
            try:
                if proc_cwd.exists():
                    return str(proc_cwd.resolve())
            except Exception:
                pass
        return self.initial_cwd or get_working_directory()

    def _setup_context_menu(self) -> None:
        action_group = Gio.SimpleActionGroup()
        actions = {
            "copy": lambda *_: self.vte.copy_clipboard_format(Vte.Format.TEXT),
            "paste": lambda *_: self.vte.paste_clipboard(),
            "clear": lambda *_: self.vte.reset(True, True),
            "find": lambda *_: self.toggle_search(True),
            "split_h": lambda *_: self.on_split_h() if self.on_split_h else None,
            "split_v": lambda *_: self.on_split_v() if self.on_split_v else None,
            "close_pane": lambda *_: self.on_close_pane(self) if self.on_close_pane else None,
        }
        for name, cb in actions.items():
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", cb)
            action_group.add_action(act)

        self.insert_action_group("term", action_group)

        menu = Gio.Menu()
        menu.append("Copy", "term.copy")
        menu.append("Paste", "term.paste")
        menu.append("Find in Output", "term.find")
        menu.append("Split Horizontally", "term.split_h")
        menu.append("Split Vertically", "term.split_v")
        menu.append("Close Pane", "term.close_pane")
        menu.append("Clear Scrollback", "term.clear")

        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self.vte)
        popover.set_has_arrow(False)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)

        def on_right_click(_g, _n_press, x, y):
            rect = Gdk.Rectangle()
            rect.x = int(x)
            rect.y = int(y)
            rect.width = 1
            rect.height = 1
            popover.set_pointing_to(rect)
            popover.popup()

        gesture.connect("pressed", on_right_click)
        self.vte.add_controller(gesture)

    def toggle_search(self, show: bool | None = None) -> None:
        target = (not self.search_bar.get_visible()) if show is None else show
        self.search_bar.set_visible(target)
        if target:
            self.search_entry.grab_focus()
        else:
            self.vte.grab_focus()

    def _update_search_regex(self) -> bool:
        pattern = self.search_entry.get_text()
        if not pattern:
            return False
        try:
            regex = Vte.Regex.new_for_search(pattern, len(pattern.encode("utf-8")), 0)
            self.vte.search_set_regex(regex, 0)
            self.vte.search_set_wrap_around(True)
            return True
        except Exception:
            return False

    def find_next(self) -> None:
        if self._update_search_regex():
            self.vte.search_find_next()

    def find_previous(self) -> None:
        if self._update_search_regex():
            self.vte.search_find_previous()

    def _on_focus_enter(self, _ctrl) -> None:
        self.add_css_class("focused-pane")
        if self.on_focus_callback:
            self.on_focus_callback(self)

    def _on_focus_leave(self, _ctrl) -> None:
        self.remove_css_class("focused-pane")

    def apply_terminal_settings(self, term_cfg: dict) -> None:
        font_family = term_cfg.get("font_family", "Monospace")
        font_size = int(term_cfg.get("font_size", 11))
        scrollback = int(term_cfg.get("scrollback_lines", 10000))
        blink = bool(term_cfg.get("cursor_blink", True))
        shape_name = str(term_cfg.get("cursor_shape", "block")).lower()

        font_desc = Pango.FontDescription.from_string(f"{font_family} {font_size}")
        self.vte.set_font(font_desc)
        self.vte.set_scrollback_lines(scrollback)
        self.vte.set_scroll_on_output(False)
        self.vte.set_scroll_on_keystroke(True)
        self.vte.set_mouse_autohide(True)

        blink_mode = Vte.CursorBlinkMode.ON if blink else Vte.CursorBlinkMode.OFF
        self.vte.set_cursor_blink_mode(blink_mode)

        shapes = {
            "block": Vte.CursorShape.BLOCK,
            "ibeam": Vte.CursorShape.IBEAM,
            "underline": Vte.CursorShape.UNDERLINE,
        }
        self.vte.set_cursor_shape(shapes.get(shape_name, Vte.CursorShape.BLOCK))

    def apply_theme(self, theme: dict) -> None:
        p = theme["palette"]
        opacity = float(self.config.get("terminal", {}).get("opacity", 1.0))

        fg = Gdk.RGBA()
        fg.parse(p["terminal_fg"])

        bg = Gdk.RGBA()
        bg.parse(p["terminal_bg"])
        bg.alpha = max(0.35, min(1.0, opacity))

        cursor = Gdk.RGBA()
        cursor.parse(p["cursor"])

        ansi_palette = []
        for hex_color in p["ansi"]:
            rgba = Gdk.RGBA()
            rgba.parse(hex_color)
            ansi_palette.append(rgba)

        self.vte.set_colors(fg, bg, ansi_palette)
        self.vte.set_color_cursor(cursor)

    def send_command(self, command: str, execute: bool = False) -> None:
        payload = f"{command}\n" if execute else command
        self.vte.feed_child(payload.encode("utf-8"))
        self.vte.grab_focus()

    def has_foreground_process(self) -> bool:
        pty = self.vte.get_pty()
        if not pty or self.child_pid <= 0:
            return False
        try:
            fd = pty.get_fd()
            fg_pgid = os.tcgetpgrp(fd)
            return fg_pgid > 0 and fg_pgid != self.child_pid
        except Exception:
            return False

    def spawn_shell(self) -> None:
        shell = detect_shell(self.config.get("terminal", {}).get("shell", ""))
        cwd = get_working_directory(self.initial_cwd)

        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["COLORTERM"] = "truecolor"
        env["HAWKEYE_SESSION"] = "1"
        envp = [f"{k}={v}" for k, v in env.items()]

        self.vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            cwd,
            [shell],
            envp,
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            self._on_spawn_complete,
        )

    def _on_spawn_complete(self, terminal, pid, error) -> None:
        if error:
            msg = f"\r\n[HAWKEYE] Failed to start shell: {error.message}\r\n"
            self.vte.feed(msg.encode("utf-8"))
        else:
            self.child_pid = pid
            self.vte.grab_focus()

    def _on_child_exited(self, terminal, status: int) -> None:
        if self.on_exit_callback:
            self.on_exit_callback(self, status)
        else:
            self.spawn_shell()

    def focus_terminal(self) -> None:
        self.vte.grab_focus()

    def _on_vte_key_pressed(self, _ctrl, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if ctrl and shift:
            if keyval in (Gdk.KEY_C, Gdk.KEY_c):
                if hasattr(self.vte, "copy_clipboard_format"):
                    self.vte.copy_clipboard_format(Vte.Format.TEXT)
                elif hasattr(self.vte, "copy_clipboard"):
                    self.vte.copy_clipboard()
                return True
            if keyval in (Gdk.KEY_V, Gdk.KEY_v):
                if hasattr(self.vte, "paste_clipboard"):
                    self.vte.paste_clipboard()
                return True
        return False
