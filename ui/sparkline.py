from collections import deque
import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk


class SparklineWidget(Gtk.DrawingArea):
    def __init__(self, max_points: int = 36, width: int = 90, height: int = 22):
        super().__init__()
        self.set_content_width(width)
        self.set_content_height(height)
        self.values: deque[float] = deque([0.0] * max_points, maxlen=max_points)
        self.accent_hex = "#bd93f9"
        self.set_draw_func(self._on_draw)

    def set_color(self, hex_color: str) -> None:
        self.accent_hex = hex_color
        self.queue_draw()

    def push(self, value: float) -> None:
        clamped = max(0.0, min(100.0, float(value)))
        self.values.append(clamped)
        self.queue_draw()

    def _on_draw(self, _area, cr: cairo.Context, width: int, height: int) -> None:
        if width <= 2 or height <= 2:
            return

        rgba = Gdk.RGBA()
        if not rgba.parse(self.accent_hex):
            rgba.parse("#bd93f9")

        pts = list(self.values)
        n = len(pts)
        if n < 2:
            return

        step_x = width / (n - 1)
        pad_y = 2.0
        usable_h = height - (pad_y * 2)

        cr.new_path()
        cr.move_to(0, height)
        for i, val in enumerate(pts):
            x = i * step_x
            y = height - pad_y - ((val / 100.0) * usable_h)
            cr.line_to(x, y)
        cr.line_to(width, height)
        cr.close_path()
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 0.18)
        cr.fill()

        cr.new_path()
        for i, val in enumerate(pts):
            x = i * step_x
            y = height - pad_y - ((val / 100.0) * usable_h)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 0.95)
        cr.set_line_width(1.5)
        cr.stroke()
