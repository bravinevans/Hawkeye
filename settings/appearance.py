import copy
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk


class AppearanceSettingsView(Gtk.Box):
    def __init__(self, config: dict, theme_engine, on_select_theme, on_update_terminal_prefs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self.config = config
        self.theme_engine = theme_engine
        self.on_select_theme = on_select_theme
        self.on_update_terminal_prefs = on_update_terminal_prefs
        self.cards: dict[str, Gtk.Box] = {}

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scrolled)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        scrolled.set_child(content)

        title = Gtk.Label(label="HAWKEYE // VISUAL IDENTITY & THEMES")
        title.add_css_class("hawkeye-brand")
        title.set_xalign(0.0)

        subtitle = Gtk.Label(
            label="Switch between built-in skins or your saved custom themes without disrupting running shells."
        )
        subtitle.add_css_class("hawkeye-tagline")
        subtitle.set_xalign(0.0)

        content.append(title)
        content.append(subtitle)

        self.grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        self.grid.set_column_homogeneous(True)
        content.append(self.grid)
        self._rebuild_theme_grid()

        studio_title = Gtk.Label(label="CUSTOM THEME STUDIO // LIVE PALETTE & SURFACE")
        studio_title.add_css_class("hawkeye-brand")
        studio_title.set_xalign(0.0)
        content.append(studio_title)

        studio_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        studio_card.add_css_class("panel-card")
        content.append(studio_card)

        pal = self.theme_engine.current_theme.get("palette", {})
        color_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        self.color_buttons: dict[str, Gtk.ColorDialogButton] = {}
        color_specs = [
            ("accent", "Accent", pal.get("accent", "#9333ea")),
            ("bg_primary", "Window", pal.get("bg_primary", "#110f1a")),
            ("bg_secondary", "Panels", pal.get("bg_secondary", "#181524")),
            ("terminal_bg", "Terminal BG", pal.get("terminal_bg", "#0d0b14")),
            ("terminal_fg", "Terminal Text", pal.get("terminal_fg", "#e9d5ff")),
        ]
        for key, label, default_hex in color_specs:
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            lbl = Gtk.Label(label=label)
            lbl.add_css_class("hawkeye-tagline")
            btn = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
            rgba = Gdk.RGBA()
            rgba.parse(default_hex)
            btn.set_rgba(rgba)
            col.append(lbl)
            col.append(btn)
            color_row.append(col)
            self.color_buttons[key] = btn

        studio_card.append(color_row)

        save_theme_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.custom_name_entry = Gtk.Entry()
        self.custom_name_entry.add_css_class("hawkeye-input")
        self.custom_name_entry.set_placeholder_text("Custom skin name (e.g. Midnight Slate)...")
        self.custom_name_entry.set_hexpand(True)

        save_skin_btn = Gtk.Button(label="Save & Apply Custom Skin")
        save_skin_btn.add_css_class("accent-btn")
        save_skin_btn.connect("clicked", lambda *_: self._save_custom_skin())

        save_theme_row.append(self.custom_name_entry)
        save_theme_row.append(save_skin_btn)
        studio_card.append(save_theme_row)

        term_title = Gtk.Label(label="TERMINAL // TYPOGRAPHY, OPACITY & CURSOR")
        term_title.add_css_class("hawkeye-brand")
        term_title.set_xalign(0.0)
        content.append(term_title)

        term_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        term_card.add_css_class("panel-card")
        content.append(term_card)

        term_cfg = self.config.get("terminal", {})
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.font_entry = Gtk.Entry()
        self.font_entry.add_css_class("hawkeye-input")
        self.font_entry.set_text(term_cfg.get("font_family", "Monospace"))
        self.font_entry.set_placeholder_text("Font family")
        self.font_entry.set_hexpand(True)

        self.size_spin = Gtk.SpinButton.new_with_range(8, 28, 1)
        self.size_spin.set_value(int(term_cfg.get("font_size", 11)))

        self.cursor_combo = Gtk.ComboBoxText()
        for shape in ("block", "ibeam", "underline"):
            self.cursor_combo.append(shape, shape.capitalize())
        self.cursor_combo.set_active_id(term_cfg.get("cursor_shape", "block"))

        row1.append(self.font_entry)
        row1.append(self.size_spin)
        row1.append(self.cursor_combo)
        term_card.append(row1)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        op_lbl = Gtk.Label(label="Opacity:")
        op_lbl.add_css_class("hawkeye-tagline")
        self.opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.50, 1.00, 0.05)
        self.opacity_scale.set_value(float(term_cfg.get("opacity", 1.0)))
        self.opacity_scale.set_hexpand(True)

        rad_lbl = Gtk.Label(label="Corner Radius:")
        rad_lbl.add_css_class("hawkeye-tagline")
        self.radius_spin = Gtk.SpinButton.new_with_range(0, 16, 1)
        self.radius_spin.set_value(int(term_cfg.get("border_radius", 6)))

        apply_term_btn = Gtk.Button(label="Apply Style")
        apply_term_btn.add_css_class("accent-btn")
        apply_term_btn.connect("clicked", lambda *_: self._apply_terminal_style())

        row2.append(op_lbl)
        row2.append(self.opacity_scale)
        row2.append(rad_lbl)
        row2.append(self.radius_spin)
        row2.append(apply_term_btn)
        term_card.append(row2)

        self.refresh_selection()

    def _rebuild_theme_grid(self) -> None:
        child = self.grid.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.grid.remove(child)
            child = nxt
        self.cards.clear()

        for idx, (theme_id, theme_name) in enumerate(self.theme_engine.list_all_themes()):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("panel-card")

            name_lbl = Gtk.Label(label=f"0{idx + 1}. {theme_name}")
            name_lbl.set_xalign(0.0)

            apply_btn = Gtk.Button(label="Apply Skin")
            apply_btn.add_css_class("accent-btn")
            apply_btn.connect("clicked", lambda *_, tid=theme_id: self._pick(tid))

            card.append(name_lbl)
            card.append(apply_btn)

            self.cards[theme_id] = card
            self.grid.attach(card, idx % 3, idx // 3, 1, 1)

    def _rgba_to_hex(self, rgba: Gdk.RGBA) -> str:
        r = int(round(rgba.red * 255))
        g = int(round(rgba.green * 255))
        b = int(round(rgba.blue * 255))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _save_custom_skin(self) -> None:
        raw_name = self.custom_name_entry.get_text().strip() or "Custom Skin"
        slug = "custom_" + "".join(c.lower() if c.isalnum() else "_" for c in raw_name).strip("_")

        base = copy.deepcopy(self.theme_engine.current_theme)
        base["id"] = slug
        base["name"] = raw_name
        pal = base["palette"]

        for key, btn in self.color_buttons.items():
            pal[key] = self._rgba_to_hex(btn.get_rgba())
        pal["border_focus"] = pal["accent"]
        pal["cursor"] = pal["accent"]

        self.theme_engine.save_custom_theme(base)
        self._rebuild_theme_grid()
        self._pick(slug)

    def _apply_terminal_style(self) -> None:
        family = self.font_entry.get_text().strip() or "Monospace"
        size = int(self.size_spin.get_value())
        shape = self.cursor_combo.get_active_id() or "block"
        opacity = round(float(self.opacity_scale.get_value()), 2)
        radius = int(self.radius_spin.get_value())
        self.on_update_terminal_prefs(family, size, shape, opacity, radius)

    def _pick(self, theme_id: str) -> None:
        self.on_select_theme(theme_id)
        self.refresh_selection()

    def refresh_selection(self) -> None:
        active_id = self.theme_engine.current_theme.get("id", "dracula_inspired")
        for tid, card in self.cards.items():
            if tid == active_id:
                card.add_css_class("selected-card")
            else:
                card.remove_css_class("selected-card")
