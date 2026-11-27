import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ui.hawk_emblem import HawkEmblemWidget


class HawkeyeHeader(Gtk.HeaderBar):
    def __init__(
        self,
        palette: dict,
        on_toggle_sidebar,
        on_split_h,
        on_split_v,
        on_toggle_helper,
        on_open_palette,
        tab_widget: Gtk.Widget,
    ):
        super().__init__()
        self.add_css_class("hawkeye-header")
        self.set_show_title_buttons(True)

        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        left_box.set_valign(Gtk.Align.CENTER)

        toggle_btn = Gtk.Button(label="☰")
        toggle_btn.add_css_class("header-btn")
        toggle_btn.set_valign(Gtk.Align.CENTER)
        toggle_btn.set_tooltip_text("Toggle / Collapse Sidebar (Ctrl+B)")
        toggle_btn.connect("clicked", lambda *_: on_toggle_sidebar())
        left_box.append(toggle_btn)

        self.emblem = HawkEmblemWidget(pixel_size=28)
        self.emblem.update_palette(palette)
        left_box.append(self.emblem)

        title_lbl = Gtk.Label(label="HAWKEYE")
        title_lbl.add_css_class("hawkeye-brand")
        title_lbl.set_valign(Gtk.Align.CENTER)
        left_box.append(title_lbl)

        self.pack_start(left_box)

        tab_widget.set_valign(Gtk.Align.CENTER)
        self.set_title_widget(tab_widget)

        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        right_box.set_valign(Gtk.Align.CENTER)

        for label, tooltip, cb in [
            ("Split H", "Split Horizontally (Ctrl+Shift+D)", on_split_h),
            ("Split V", "Split Vertically (Ctrl+Shift+E)", on_split_v),
            ("Helper", "Toggle Helper Drawer (Ctrl+Shift+A)", on_toggle_helper),
            ("⌘ Palette", "Command Palette (Ctrl+Shift+P)", on_open_palette),
        ]:
            btn = Gtk.Button(label=label)
            btn.add_css_class("header-btn")
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", lambda *_, fn=cb: fn())
            right_box.append(btn)

        self.pack_end(right_box)

    def update_palette(self, palette: dict) -> None:
        self.emblem.update_palette(palette)
