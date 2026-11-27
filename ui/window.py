import json
import os
from pathlib import Path
import psutil
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from core.shell import detect_shell
from ui.header import HawkeyeHeader
from ui.sidebar import HawkeyeSidebar
from ui.tabs import TabManager
from ui.dashboard import HawkeyeHomeDashboard
from ui.hawk_emblem import HawkEmblemWidget
from ui.sparkline import SparklineWidget
from modules.palette import CommandPalette
from modules.ai import HawkeyeHelperPanel
from modules.monitor import SystemMonitorView
from modules.file_integration import HawkeyeFilesView
from modules.suggestions import HawkeyeSearchView
from settings.appearance import AppearanceSettingsView
from settings.shortcuts import ShortcutsAndAliasesView


class HawkeyeWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, config: dict, theme_engine):
        super().__init__(application=app)
        self.app = app
        self.config = config
        self.theme_engine = theme_engine
        self.session_file = Path.home() / ".config" / "hawkeye" / "session.json"
        self._prev_net = psutil.net_io_counters()
        self._prev_net_time = GLib.get_monotonic_time() / 1_000_000.0

        win_cfg = config.get("window", {})
        term_cfg = config.get("terminal", {})
        self.theme_engine.opacity = float(term_cfg.get("opacity", 0.96))
        self.theme_engine.border_radius = int(term_cfg.get("border_radius", 6))
        self.theme_engine.apply_css(self.theme_engine.current_theme)

        self.set_title("HAWKEYE")
        self.set_icon_name("hawkeye")
        self.set_default_size(
            win_cfg.get("width", 1140),
            win_cfg.get("height", 700),
        )
        self.set_resizable(True)
        display = Gdk.Display.get_default()
        if display is not None:
            monitors = display.get_monitors()
            if monitors.get_n_items() > 0:
                geom = monitors.get_item(0).get_geometry()
                if geom.width > 0 and geom.height > 0:
                    self.set_default_size(
                        min(win_cfg.get("width", 880), max(640, int(geom.width * 0.85))),
                        min(win_cfg.get("height", 540), max(420, int(geom.height * 0.82))),
                    )
        self.add_css_class("hawkeye-window")

        self.tab_manager = TabManager(
            config=self.config,
            theme_engine=self.theme_engine,
            on_tab_changed=self._update_status_counts,
        )

        palette = self.theme_engine.current_theme.get("palette", {})
        self.header = HawkeyeHeader(
            palette=palette,
            on_toggle_sidebar=self.toggle_sidebar,
            on_split_h=lambda: self.split_terminal(Gtk.Orientation.HORIZONTAL),
            on_split_v=lambda: self.split_terminal(Gtk.Orientation.VERTICAL),
            on_toggle_helper=self.toggle_helper_drawer,
            on_open_palette=self.open_command_palette,
            tab_widget=self.tab_manager.header_container,
        )
        self.set_titlebar(self.header)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root_box)

        body_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body_box.set_vexpand(True)
        root_box.append(body_box)

        self.sidebar = HawkeyeSidebar(
            width=win_cfg.get("sidebar_width", 180),
            on_navigate=self.navigate_to,
        )
        self.sidebar.set_visible(win_cfg.get("sidebar_visible", True))
        body_box.append(self.sidebar)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        body_box.append(self.stack)

        self.stack.add_named(self.tab_manager.workspace_stack, "terminal")

        self.home_view = HawkeyeHomeDashboard(
            palette=palette,
            on_navigate=self.navigate_to,
            on_quick_command=self.inject_command_into_terminal,
        )
        self.stack.add_named(self.home_view, "home")

        accent = palette.get("accent", "#00C9F0")
        self.system_view = SystemMonitorView(accent_color=accent)
        self.stack.add_named(self.system_view, "system")

        self.files_view = HawkeyeFilesView(on_inject_command=self.inject_command_into_terminal)
        self.stack.add_named(self.files_view, "files")

        self.search_view = HawkeyeSearchView(on_inject_command=self.inject_command_into_terminal)
        self.stack.add_named(self.search_view, "search")

        self.helper_page = HawkeyeHelperPanel(
            on_inject_command=self.inject_command_into_terminal,
            on_save_ai_config=self._save_ai_config,
            config=self.config,
            full_page=True,
        )
        self.stack.add_named(self.helper_page, "assistant")

        self.shortcuts_view = ShortcutsAndAliasesView(on_inject_command=self.inject_command_into_terminal)
        self.stack.add_named(self.shortcuts_view, "shortcuts")

        self.settings_view = AppearanceSettingsView(
            config=self.config,
            theme_engine=self.theme_engine,
            on_select_theme=self.switch_theme,
            on_update_terminal_prefs=self._update_terminal_prefs,
        )
        self.stack.add_named(self.settings_view, "settings")

        self.about_emblem = HawkEmblemWidget(pixel_size=96)
        self.about_emblem.update_palette(palette)
        self.stack.add_named(self._build_about_view(), "about")

        self.helper_drawer = HawkeyeHelperPanel(
            on_inject_command=self.inject_command_into_terminal,
            on_save_ai_config=self._save_ai_config,
            config=self.config,
            full_page=False,
        )
        self.helper_drawer.set_visible(False)
        body_box.append(self.helper_drawer)

        self.stack.set_visible_child_name("terminal")

        self.skin_lbl = Gtk.Label()
        self.cpu_spark = SparklineWidget(max_points=24, width=64, height=16)
        self.cpu_spark.set_color(accent)
        self.telemetry_lbl = Gtk.Label()
        self.session_info_lbl = Gtk.Label()
        self.statusbar = self._build_statusbar()
        root_box.append(self.statusbar)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

        self.connect("close-request", self._on_close_request)

        self._restore_or_init_session()
        self._update_status_telemetry()
        GLib.timeout_add_seconds(2, self._update_status_telemetry)

    def _restore_or_init_session(self) -> None:
        if self.config.get("app", {}).get("restore_session", True) and self.session_file.exists():
            try:
                data = json.loads(self.session_file.read_text(encoding="utf-8"))
                tabs = data.get("tabs", [])
                if tabs:
                    for item in tabs:
                        self.tab_manager.new_tab(
                            title=item.get("title"),
                            initial_cwd=item.get("cwd"),
                        )
                    return
            except Exception:
                pass
        self.tab_manager.new_tab("1: shell")

    def _save_session(self) -> None:
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {"tabs": self.tab_manager.export_session()}
            self.session_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _on_close_request(self, _win) -> bool:
        self._save_session()
        busy = any(t["workspace"].has_active_processes() for t in self.tab_manager.tabs)
        if not busy:
            return False

        dialog = Gtk.AlertDialog()
        dialog.set_message("Active Command Running")
        dialog.set_detail("One or more terminal panes are currently executing a process. Close Hawkeye anyway?")
        dialog.set_buttons(["Cancel", "Close Anyway"])
        dialog.set_cancel_button(0)
        dialog.set_default_button(0)

        def on_choice(dlg, res):
            try:
                idx = dlg.choose_finish(res)
                if idx == 1:
                    self.destroy()
            except Exception:
                pass

        dialog.choose(self, None, on_choice)
        return True

    def _build_about_view(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        box.append(self.about_emblem)

        title = Gtk.Label(label="HAWKEYE // ADVANCED TERMINAL ENVIRONMENT v1.0.0")
        title.add_css_class("hawkeye-brand")

        tag = Gtk.Label(label="SEE MORE. DO MORE.  |  GTK4 + VTE + ARCH NATIVE")
        tag.add_css_class("hawkeye-tagline")

        desc = Gtk.Label(
            label="Six visual identities + Custom Theme Studio. Real shell execution. Modular workspace with BYOK Helper."
        )
        desc.add_css_class("hawkeye-tagline")

        box.append(title)
        box.append(tag)
        box.append(desc)
        return box

    def _build_statusbar(self) -> Gtk.Box:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.add_css_class("hawkeye-statusbar")

        shell_path = detect_shell(self.config.get("terminal", {}).get("shell", ""))
        shell_name = os.path.basename(shell_path)
        theme_name = self.theme_engine.current_theme.get("name", "Cyberpunk Neon")

        shell_btn = Gtk.Button(label=f"SHELL: {shell_name}")
        shell_btn.add_css_class("flat-btn")
        shell_btn.set_tooltip_text(f"Active Shell: {shell_path} (click to open System view)")
        shell_btn.connect("clicked", lambda *_: self.navigate_to("system"))

        engine_btn = Gtk.Button(label="ENGINE: VTE-GTK4")
        engine_btn.add_css_class("flat-btn")
        engine_btn.set_tooltip_text("Click to open Settings & Appearance")
        engine_btn.connect("clicked", lambda *_: self.navigate_to("settings"))

        self.skin_lbl.set_text(f"SKIN: {theme_name.upper()}")
        self.skin_lbl.add_css_class("status-accent")

        spacer = Gtk.Box()
        spacer.set_hexpand(True)

        self.telemetry_lbl.add_css_class("hawkeye-tagline")
        self.session_info_lbl.add_css_class("status-accent")

        bar.append(shell_btn)
        bar.append(engine_btn)
        bar.append(self.skin_lbl)
        bar.append(spacer)
        bar.append(self.cpu_spark)
        bar.append(self.telemetry_lbl)
        bar.append(self.session_info_lbl)
        return bar

    def _update_status_telemetry(self) -> bool:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        now = GLib.get_monotonic_time() / 1_000_000.0
        net = psutil.net_io_counters()
        dt = max(0.25, now - self._prev_net_time)
        rx_rate = max(0.0, (net.bytes_recv - self._prev_net.bytes_recv) / dt / 1024.0)
        tx_rate = max(0.0, (net.bytes_sent - self._prev_net.bytes_sent) / dt / 1024.0)
        self._prev_net = net
        self._prev_net_time = now

        net_str = (
            f"↓{rx_rate/1024:.1f}M/s ↑{tx_rate/1024:.1f}M/s"
            if (rx_rate > 1024 or tx_rate > 1024)
            else f"↓{rx_rate:.0f}K/s ↑{tx_rate:.0f}K/s"
        )

        self.cpu_spark.push(cpu)
        self.telemetry_lbl.set_text(
            f"CPU: {cpu:.0f}%  |  RAM: {ram:.0f}%  |  DISK: {disk:.0f}%  |  NET: {net_str}"
        )
        return True

    def _update_status_counts(self) -> None:
        tab_count = len(self.tab_manager.tabs)
        pane_count = self.tab_manager.total_panes()
        self.session_info_lbl.set_text(f"TABS: {tab_count} | PANES: {pane_count}")

    def switch_theme(self, theme_id: str) -> None:
        theme = self.theme_engine.load_theme(theme_id)
        pal = theme.get("palette", {})
        accent = pal.get("accent", "#00C9F0")
        for tab in self.tab_manager.tabs:
            tab["workspace"].apply_theme(theme)
        self.header.update_palette(pal)
        self.about_emblem.update_palette(pal)
        self.home_view.update_theme_visuals(theme["name"], pal)
        self.cpu_spark.set_color(accent)
        self.system_view.set_accent_color(accent)
        self.skin_lbl.set_text(f"SKIN: {theme['name'].upper()}")
        self.settings_view.refresh_selection()
        self.config.setdefault("app", {})["default_theme"] = theme_id
        self._persist_user_settings()

    def _update_terminal_prefs(
        self,
        font_family: str,
        font_size: int,
        cursor_shape: str,
        opacity: float = 0.96,
        border_radius: int = 6,
    ) -> None:
        term_cfg = self.config.setdefault("terminal", {})
        term_cfg["font_family"] = font_family
        term_cfg["font_size"] = font_size
        term_cfg["cursor_shape"] = cursor_shape
        term_cfg["opacity"] = opacity
        term_cfg["border_radius"] = border_radius

        self.theme_engine.load_theme(
            self.theme_engine.current_theme.get("id", "cyberpunk_neon"),
            opacity=opacity,
            border_radius=border_radius,
        )
        for tab in self.tab_manager.tabs:
            tab["workspace"].apply_terminal_settings(term_cfg)
            tab["workspace"].apply_theme(self.theme_engine.current_theme)
        self._persist_user_settings()

    def _save_ai_config(self, api_url: str, model: str) -> None:
        self.config.setdefault("ai", {})["api_url"] = api_url
        self.config.setdefault("ai", {})["model"] = model
        self._persist_user_settings()
        self.helper_drawer.refresh_status()
        self.helper_page.refresh_status()

    def _persist_user_settings(self) -> None:
        user_cfg_path: Path = Path.home() / ".config" / "hawkeye" / "user_settings.toml"
        user_cfg_path.parent.mkdir(parents=True, exist_ok=True)
        theme_id = self.config.get("app", {}).get("default_theme", "cyberpunk_neon")
        term = self.config.get("terminal", {})
        font_family = term.get("font_family", "Monospace")
        font_size = int(term.get("font_size", 11))
        cursor_shape = term.get("cursor_shape", "block")
        opacity = float(term.get("opacity", 0.96))
        border_radius = int(term.get("border_radius", 6))
        api_url = self.config.get("ai", {}).get("api_url", "https://openrouter.ai/api/v1/chat/completions")
        model = self.config.get("ai", {}).get("model", "google/gemini-2.0-flash-exp:free")
        toml_text = (
            f'[app]\ndefault_theme = "{theme_id}"\n\n'
            f'[terminal]\nfont_family = "{font_family}"\nfont_size = {font_size}\n'
            f'cursor_shape = "{cursor_shape}"\nopacity = {opacity}\nborder_radius = {border_radius}\n\n'
            f'[ai]\napi_url = "{api_url}"\nmodel = "{model}"\n'
        )
        user_cfg_path.write_text(toml_text, encoding="utf-8")

    def inject_command_into_terminal(self, command: str, execute: bool = False) -> None:
        self.navigate_to("terminal")
        ws = self.tab_manager.get_active_workspace()
        if ws and ws.active_terminal:
            ws.active_terminal.send_command(command, execute=execute)

    def toggle_helper_drawer(self) -> None:
        visible = not self.helper_drawer.get_visible()
        self.helper_drawer.set_visible(visible)
        if visible:
            self.navigate_to("terminal")
            self.helper_drawer.prompt_entry.grab_focus()
        else:
            ws = self.tab_manager.get_active_workspace()
            if ws:
                ws.focus_active()

    def split_terminal(self, orientation: Gtk.Orientation) -> None:
        self.navigate_to("terminal")
        ws = self.tab_manager.get_active_workspace()
        if ws:
            ws.split_active(orientation)

    def close_active_split(self) -> None:
        ws = self.tab_manager.get_active_workspace()
        if ws:
            ws.close_active_pane()

    def toggle_sidebar(self) -> None:
        if not self.sidebar.get_visible():
            self.sidebar.set_visible(True)
            self.sidebar.set_compact(False)
        else:
            self.sidebar.set_compact(not self.sidebar.compact)
        if self.stack.get_visible_child_name() == "terminal":
            ws = self.tab_manager.get_active_workspace()
            if ws:
                ws.focus_active()

    def navigate_to(self, section_id: str) -> None:
        if section_id == "assistant":
            self.helper_drawer.set_visible(False)
        self.stack.set_visible_child_name(section_id)
        self.sidebar.set_active(section_id)
        if section_id == "terminal":
            ws = self.tab_manager.get_active_workspace()
            if ws:
                ws.focus_active()

    def open_command_palette(self) -> None:
        actions = [
            ("New Terminal Tab", "Ctrl+Shift+T", lambda: (self.navigate_to("terminal"), self.tab_manager.new_tab())),
            ("Close Current Tab", "Ctrl+Shift+W", self.tab_manager.close_active_tab),
            ("Next Tab", "Ctrl+Tab", self.tab_manager.next_tab),
            ("Previous Tab", "Ctrl+Shift+Tab", self.tab_manager.prev_tab),
            ("Split Horizontally", "Ctrl+Shift+D", lambda: self.split_terminal(Gtk.Orientation.HORIZONTAL)),
            ("Split Vertically", "Ctrl+Shift+E", lambda: self.split_terminal(Gtk.Orientation.VERTICAL)),
            ("Close Active Split Pane", "Ctrl+Shift+X", self.close_active_split),
            ("Find in Terminal Output", "Ctrl+Shift+F", self._toggle_active_terminal_search),
            ("Toggle Helper Side Drawer", "Ctrl+Shift+A", self.toggle_helper_drawer),
            ("Open Full Helper Studio", "Sidebar", lambda: self.navigate_to("assistant")),
            ("Open System Monitor", "Ctrl+Shift+M", lambda: self.navigate_to("system")),
            ("Open Home Hero View", "Sidebar", lambda: self.navigate_to("home")),
            ("Open File Browser", "Sidebar", lambda: self.navigate_to("files")),
            ("Search Shell History", "Sidebar", lambda: self.navigate_to("search")),
            ("Toggle / Collapse Sidebar", "Ctrl+B", self.toggle_sidebar),
            ("Open Settings & Custom Theme Studio", "Ctrl+,", lambda: self.navigate_to("settings")),
        ]
        for tid, tname in self.theme_engine.list_all_themes():
            actions.append((f"Theme: {tname}", "Skin", lambda theme_id=tid: self.switch_theme(theme_id)))

        palette = CommandPalette(self, actions)
        palette.present()

    def _toggle_active_terminal_search(self) -> None:
        self.navigate_to("terminal")
        ws = self.tab_manager.get_active_workspace()
        if ws and ws.active_terminal:
            ws.active_terminal.toggle_search()

    def _on_key_pressed(self, _ctrl, keyval: int, _keycode: int, state: Gdk.ModifierType) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if ctrl and shift:
            if keyval in (Gdk.KEY_T, Gdk.KEY_t):
                self.navigate_to("terminal")
                self.tab_manager.new_tab()
                return True
            if keyval in (Gdk.KEY_W, Gdk.KEY_w):
                self.tab_manager.close_active_tab()
                return True
            if keyval in (Gdk.KEY_D, Gdk.KEY_d):
                self.split_terminal(Gtk.Orientation.HORIZONTAL)
                return True
            if keyval in (Gdk.KEY_E, Gdk.KEY_e):
                self.split_terminal(Gtk.Orientation.VERTICAL)
                return True
            if keyval in (Gdk.KEY_X, Gdk.KEY_x):
                self.close_active_split()
                return True
            if keyval in (Gdk.KEY_F, Gdk.KEY_f):
                self._toggle_active_terminal_search()
                return True
            if keyval in (Gdk.KEY_P, Gdk.KEY_p):
                self.open_command_palette()
                return True
            if keyval in (Gdk.KEY_M, Gdk.KEY_m):
                self.navigate_to("system")
                return True
            if keyval in (Gdk.KEY_A, Gdk.KEY_a):
                self.toggle_helper_drawer()
                return True
            if keyval == Gdk.KEY_ISO_Left_Tab:
                self.tab_manager.prev_tab()
                return True

        if ctrl and not shift:
            if keyval == Gdk.KEY_Tab:
                self.tab_manager.next_tab()
                return True
            if keyval == Gdk.KEY_comma:
                self.navigate_to("settings")
                return True
            if keyval in (Gdk.KEY_b, Gdk.KEY_B):
                self.toggle_sidebar()
                return True

        return False
