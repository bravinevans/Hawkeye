import getpass
import os
import platform
import socket
import subprocess
import time
import psutil
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from ui.hawk_emblem import HawkEmblemWidget
from ui.sparkline import SparklineWidget


class HawkeyeHomeDashboard(Gtk.Box):
    """Master-sheet Home Hero: Hawk Emblem + Neofetch System Specs + Live Telemetry Sparklines."""

    def __init__(self, palette: dict, on_navigate, on_quick_command):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.set_margin_top(18)
        self.set_margin_bottom(18)
        self.set_margin_start(22)
        self.set_margin_end(22)

        self.on_navigate = on_navigate
        self.on_quick_command = on_quick_command

        # Hero Card matching Master Sheet center composition
        hero_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=28)
        hero_card.add_css_class("panel-card")
        hero_card.set_vexpand(True)
        self.append(hero_card)

        # Left side: Large Hawk Emblem + inline prompt preview
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        left_col.set_valign(Gtk.Align.CENTER)
        left_col.set_halign(Gtk.Align.CENTER)
        left_col.set_hexpand(True)

        self.hero_emblem = HawkEmblemWidget(pixel_size=132)
        left_col.append(self.hero_emblem)

        prompt_preview = Gtk.Label(
            label=f"[{getpass.getuser()}@{socket.gethostname()} ~]$ _"
        )
        prompt_preview.add_css_class("cmd-code-box")
        left_col.append(prompt_preview)
        hero_card.append(left_col)

        # Right side: Neofetch-style System Specs + 8-Color Palette Swatches
        right_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_col.set_valign(Gtk.Align.CENTER)
        right_col.set_hexpand(True)
        hero_card.append(right_col)

        user_host = Gtk.Label(label=f"{getpass.getuser()}@{socket.gethostname()}")
        user_host.add_css_class("hawkeye-brand")
        user_host.set_xalign(0.0)
        right_col.append(user_host)

        sep = Gtk.Label(label="──────────────────────────────")
        sep.add_css_class("hawkeye-tagline")
        sep.set_xalign(0.0)
        right_col.append(sep)

        self.theme_spec_lbl = Gtk.Label()
        self.theme_spec_lbl.set_xalign(0.0)

        specs = [
            ("OS", self._read_os_name()),
            ("Kernel", platform.release()),
            ("Uptime", self._read_uptime()),
            ("Packages", f"{self._count_pacman_packages()} (pacman)"),
            ("Shell", os.path.basename(os.environ.get("SHELL", "/bin/bash"))),
            ("DE / WM", os.environ.get("XDG_CURRENT_DESKTOP", "KDE / Wayland")),
        ]
        for k, v in specs:
            row = Gtk.Label(label=f"{k}: {v}")
            row.set_xalign(0.0)
            right_col.append(row)

        right_col.append(self.theme_spec_lbl)

        # 8-color ANSI swatch bar (directly from Master Sheet)
        self.swatch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.swatch_box.set_margin_top(8)
        right_col.append(self.swatch_box)

        # Quick Action Bar
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_row.set_margin_top(10)
        for label, cb in [
            ("Open Terminal", lambda: self.on_navigate("terminal")),
            ("Helper Studio", lambda: self.on_navigate("assistant")),
            ("System Telemetry", lambda: self.on_navigate("system")),
            ("Themes & Customizer", lambda: self.on_navigate("settings")),
        ]:
            btn = Gtk.Button(label=label)
            btn.add_css_class("flat-btn")
            btn.connect("clicked", lambda *_, fn=cb: fn())
            actions_row.append(btn)
        right_col.append(actions_row)

        # Bottom Telemetry Strip (CPU / RAM / DISK with live sparklines, matching Master Sheet)
        tele_grid = Gtk.Grid(column_spacing=12)
        tele_grid.set_column_homogeneous(True)
        self.append(tele_grid)

        c_card, self.cpu_lbl, self.cpu_spark = self._make_mini_telemetry("CPU")
        r_card, self.ram_lbl, self.ram_spark = self._make_mini_telemetry("RAM")
        d_card, self.disk_lbl, self.disk_spark = self._make_mini_telemetry("DISK")

        tele_grid.attach(c_card, 0, 0, 1, 1)
        tele_grid.attach(r_card, 1, 0, 1, 1)
        tele_grid.attach(d_card, 2, 0, 1, 1)

        self.update_theme_visuals("Dracula Inspired", palette)
        self._tick()
        GLib.timeout_add_seconds(2, self._tick)

    def _make_mini_telemetry(self, title: str):
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        card.add_css_class("panel-card")

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        t_lbl = Gtk.Label(label=title)
        t_lbl.add_css_class("hawkeye-tagline")
        t_lbl.set_xalign(0.0)

        v_lbl = Gtk.Label(label="--%")
        v_lbl.add_css_class("metric-value")
        v_lbl.set_xalign(0.0)

        left.append(t_lbl)
        left.append(v_lbl)

        spark = SparklineWidget(max_points=32, width=150, height=34)
        spark.set_hexpand(True)

        card.append(left)
        card.append(spark)
        return card, v_lbl, spark

    def update_theme_visuals(self, theme_name: str, palette: dict) -> None:
        self.hero_emblem.update_palette(palette)
        self.theme_spec_lbl.set_text(f"Theme: {theme_name}")
        accent = palette.get("accent", "#9333ea")
        for s in (self.cpu_spark, self.ram_spark, self.disk_spark):
            s.set_color(accent)

        child = self.swatch_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.swatch_box.remove(child)
            child = nxt

        for hex_col in palette.get("ansi", [])[:8]:
            swatch = Gtk.Label(label="   ")
            css = Gtk.CssProvider()
            css.load_from_data(
                f"label {{ background-color: {hex_col}; border-radius: 2px; min-height: 14px; min-width: 24px; }}".encode("utf-8")
            )
            swatch.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self.swatch_box.append(swatch)

    def _tick(self) -> bool:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        self.cpu_lbl.set_text(f"{cpu:.0f}%")
        self.ram_lbl.set_text(f"{ram:.0f}%")
        self.disk_lbl.set_text(f"{disk:.0f}%")

        self.cpu_spark.push(cpu)
        self.ram_spark.push(ram)
        self.disk_spark.push(disk)
        return True

    def _read_os_name(self) -> str:
        try:
            with open("/etc/os-release", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except OSError:
            pass
        return f"Arch Linux {platform.machine()}"

    def _read_uptime(self) -> str:
        secs = int(time.time() - psutil.boot_time())
        hrs, rem = divmod(secs, 3600)
        mins, _ = divmod(rem, 60)
        return f"{hrs}h {mins}m"

    def _count_pacman_packages(self) -> str:
        try:
            res = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                return str(len(res.stdout.splitlines()))
        except Exception:
            pass
        return "N/A"
