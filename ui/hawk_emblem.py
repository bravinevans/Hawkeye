from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf

LOGO_DIR = Path(__file__).resolve().parent.parent / "assets" / "logo"
SVG_LOGO = LOGO_DIR / "hawkeye.svg"
PNG_LOGO = LOGO_DIR / "hawkeye.png"


def resolve_logo_path() -> Path | None:
    if SVG_LOGO.exists() and SVG_LOGO.stat().st_size > 0:
        return SVG_LOGO
    if PNG_LOGO.exists() and PNG_LOGO.stat().st_size > 0:
        return PNG_LOGO
    return None


class HawkEmblemWidget(Gtk.Picture):
    """Scales the Hawkeye emblem cleanly to exact pixel dimensions in GTK4."""

    def __init__(self, pixel_size: int = 28):
        super().__init__()
        self.pixel_size = max(16, int(pixel_size))
        self.set_size_request(self.pixel_size, self.pixel_size)
        self.set_can_shrink(False)
        self.set_content_fit(Gtk.ContentFit.FILL)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self._load_scaled()

    def _load_scaled(self) -> None:
        logo = resolve_logo_path()
        if logo is None:
            return
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(logo),
                self.pixel_size,
                self.pixel_size,
                True,
            )
            if pixbuf is not None:
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                self.set_paintable(texture)
                w = pixbuf.get_width()
                h = pixbuf.get_height()
                self.set_size_request(w, h)
                return
        except Exception:
            pass
        self.set_filename(str(logo))

    def update_palette(self, _palette: dict) -> None:
        self._load_scaled()
