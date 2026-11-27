import json
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk

AVAILABLE_THEMES = [
    ("cyberpunk_neon", "Cyberpunk Neon"),
    ("dracula_inspired", "Dracula Inspired"),
    ("light_modern", "Light Modern"),
    ("dark_professional", "Dark Professional"),
    ("matrix_terminal", "Matrix Terminal"),
    ("amber_tactical", "Amber Tactical"),
]


def _hex_to_rgba_str(hex_color: str, alpha: float) -> str:
    rgba = Gdk.RGBA()
    if rgba.parse(hex_color):
        r = int(round(rgba.red * 255))
        g = int(round(rgba.green * 255))
        b = int(round(rgba.blue * 255))
        return f"rgba({r}, {g}, {b}, {max(0.2, min(1.0, alpha)):.2f})"
    return hex_color


class ThemeEngine:
    def __init__(self, themes_dir: Path):
        self.themes_dir = themes_dir
        self.user_themes_dir = Path.home() / ".config" / "hawkeye" / "themes"
        self.user_themes_dir.mkdir(parents=True, exist_ok=True)
        self.css_provider = Gtk.CssProvider()
        self.current_theme: dict = {}
        self.opacity: float = 0.96
        self.border_radius: int = 6

        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self.css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def list_all_themes(self) -> list[tuple[str, str]]:
        items = list(AVAILABLE_THEMES)
        for p in sorted(self.user_themes_dir.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append((data.get("id", p.stem), data.get("name", p.stem)))
            except Exception:
                continue
        return items

    def load_theme(self, theme_id: str, opacity: float | None = None, border_radius: int | None = None) -> dict:
        if opacity is not None:
            self.opacity = max(0.35, min(1.0, float(opacity)))
        if border_radius is not None:
            self.border_radius = max(0, min(18, int(border_radius)))

        user_file = self.user_themes_dir / f"{theme_id}.json"
        builtin_file = self.themes_dir / f"{theme_id}.json"
        if user_file.exists():
            target = user_file
        elif builtin_file.exists():
            target = builtin_file
        else:
            target = self.themes_dir / "cyberpunk_neon.json"

        self.current_theme = json.loads(target.read_text(encoding="utf-8"))
        self.apply_css(self.current_theme)
        return self.current_theme

    def save_custom_theme(self, theme_data: dict) -> Path:
        tid = theme_data.get("id", "custom_user")
        out = self.user_themes_dir / f"{tid}.json"
        out.write_text(json.dumps(theme_data, indent=2), encoding="utf-8")
        return out

    def apply_css(self, theme: dict) -> None:
        p = theme["palette"]
        accent = p.get("accent", "#00C9F0")
        secondary = p.get("accent_secondary", "#A855F7")
        selected = p.get("accent_selected", "#E83BEF")
        term_bg_css = _hex_to_rgba_str(p["terminal_bg"], self.opacity)
        r = self.border_radius

        css = f"""
        window.hawkeye-window {{
            background-color: {p['bg_primary']};
            color: {p['fg_primary']};
        }}

        headerbar.hawkeye-header {{
            background-color: {p['bg_secondary']};
            color: {p['fg_primary']};
            border-bottom: 1px solid {p['border']};
            min-height: 76px;
            padding: 6px 12px;
        }}

        .hawkeye-brand {{
            font-weight: 800;
            font-size: 14px;
            letter-spacing: 1.6px;
            color: {p['fg_primary']};
        }}

        .hawkeye-tagline {{
            font-size: 10px;
            letter-spacing: 0.9px;
            color: {accent};
            font-weight: 600;
        }}

        .hawkeye-sidebar {{
            background-color: {p['bg_secondary']};
            border-right: 1px solid {p['border']};
            padding: 8px 6px;
        }}

        button.nav-item {{
            background: transparent;
            color: {p['fg_secondary']};
            border: 1px solid transparent;
            border-radius: {r}px;
            padding: 7px 10px;
            font-weight: 600;
            font-size: 12px;
        }}

        button.nav-item:hover {{
            background-color: {p['bg_surface']};
            color: {accent};
            border-color: {secondary};
        }}

        button.nav-item.active-nav {{
            background-color: {p['bg_active']};
            color: {selected};
            border: 1px solid {selected};
        }}

        button.header-btn, button.flat-btn {{
            background-color: {p['bg_surface']};
            color: {p['fg_primary']};
            border: 1px solid {p['border']};
            border-radius: {r}px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 600;
        }}

        button.header-btn:hover, button.flat-btn:hover {{
            border-color: {accent};
            color: {accent};
        }}

        button.accent-btn {{
            background-color: {accent};
            color: {p['accent_fg']};
            border: none;
            border-radius: {r}px;
            padding: 5px 12px;
            font-size: 11px;
            font-weight: 700;
        }}

        .tab-pill {{
            background-color: {p['bg_surface']};
            border: 1px solid {p['border']};
            border-radius: {r}px;
            padding: 1px 6px;
            min-height: 24px;
        }}

        .tab-pill.active-tab {{
            background-color: {p['bg_active']};
            border-color: {selected};
        }}

        .tab-pill.active-tab button.tab-select-btn {{
            color: {selected};
        }}

        button.tab-select-btn {{
            background: transparent;
            border: none;
            color: {p['fg_primary']};
            font-size: 11px;
            font-weight: 600;
            padding: 1px 4px;
        }}

        button.tab-close-btn {{
            background: transparent;
            border: none;
            color: {p['fg_muted']};
            font-size: 11px;
            padding: 0 3px;
        }}

        button.tab-close-btn:hover {{
            color: {selected};
        }}

        .terminal-frame {{
            background-color: {term_bg_css};
            border: 1px solid {p['border']};
            border-radius: {r}px;
            margin: 4px;
            padding: 6px;
        }}

        .terminal-frame.focused-pane {{
            border-color: {accent};
            box-shadow: inset 0 0 0 1px {secondary};
        }}

        paned > separator {{
            background-color: {p['border']};
            min-width: 3px;
            min-height: 3px;
        }}

        paned > separator:hover {{
            background-color: {accent};
        }}

        .panel-card {{
            background-color: {p['bg_secondary']};
            border: 1px solid {p['border']};
            border-radius: {r}px;
            padding: 12px;
        }}

        .panel-card.selected-card {{
            border-color: {selected};
            background-color: {p['bg_active']};
        }}

        .metric-value {{
            font-size: 18px;
            font-weight: 800;
            color: {accent};
        }}

        .cmd-code-box {{
            background-color: {p['terminal_bg']};
            color: {p['terminal_fg']};
            border: 1px solid {p['border']};
            border-radius: {max(2, r - 2)}px;
            padding: 6px 8px;
            font-family: monospace;
            font-size: 11px;
        }}

        entry.hawkeye-input {{
            background-color: {p['terminal_bg']};
            color: {p['fg_primary']};
            border: 1px solid {p['border']};
            border-radius: {r}px;
            padding: 6px 10px;
        }}

        entry.hawkeye-input:focus {{
            border-color: {accent};
        }}

        .hawkeye-statusbar {{
            background-color: {p['bg_secondary']};
            color: {p['fg_secondary']};
            border-top: 1px solid {p['border']};
            padding: 4px 12px;
            font-size: 11px;
        }}

        .status-accent {{
            color: {accent};
            font-weight: 700;
        }}
        """

        self.css_provider.load_from_data(css.encode("utf-8"))