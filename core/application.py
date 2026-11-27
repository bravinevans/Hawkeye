from pathlib import Path
import tomllib
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gio

from themes.engine import ThemeEngine
from ui.window import HawkeyeWindow

PROJECT_ROOT = Path(__file__).resolve().parent.parent
USER_CFG = Path.home() / ".config" / "hawkeye" / "user_settings.toml"


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(base_dir: Path) -> dict:
    default_cfg = base_dir / "config" / "defaults.toml"
    cfg = {}
    if default_cfg.exists():
        cfg = tomllib.loads(default_cfg.read_text(encoding="utf-8"))
    if USER_CFG.exists():
        try:
            user_data = tomllib.loads(USER_CFG.read_text(encoding="utf-8"))
            cfg = _deep_merge(cfg, user_data)
        except Exception:
            pass
    return cfg


class HawkeyeApplication(Gtk.Application):
    def __init__(self, base_dir: Path | None = None):
        super().__init__(
            application_id="com.hawkeye.terminal",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.base_dir = Path(base_dir) if base_dir is not None else PROJECT_ROOT
        self.config = load_config(self.base_dir)
        self.theme_engine = ThemeEngine(self.base_dir / "themes")
        self.window: HawkeyeWindow | None = None

    def do_activate(self) -> None:
        display = Gdk.Display.get_default()
        if display is not None:
            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_theme.add_search_path(str(self.base_dir / "assets" / "logo"))
        Gtk.Window.set_default_icon_name("hawkeye")

        default_theme = self.config.get("app", {}).get("default_theme", "cyberpunk_neon")
        self.theme_engine.load_theme(default_theme)

        if self.window is None:
            self.window = HawkeyeWindow(self, self.config, self.theme_engine)
        self.window.present()
