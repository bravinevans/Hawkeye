import os
import platform
import signal
import time
import psutil
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from ui.sparkline import SparklineWidget


class SystemMonitorView(Gtk.Box):
    def __init__(self, accent_color: str = "#bd93f9"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.set_margin_start(24)
        self.set_margin_end(24)

        self._last_net = psutil.net_io_counters()
        self._last_time = time.monotonic()

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        title = Gtk.Label(label="HAWKEYE // LIVE SYSTEM TELEMETRY")
        title.add_css_class("hawkeye-brand")
        title.set_xalign(0.0)
        title.set_hexpand(True)

        sys_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        info_lbl = Gtk.Label(label=sys_info)
        info_lbl.add_css_class("hawkeye-tagline")

        header.append(title)
        header.append(info_lbl)
        self.append(header)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_column_homogeneous(True)
        self.append(grid)

        cpu_card, self.cpu_val, self.cpu_sub, self.cpu_spark = self._make_metric_card("CPU LOAD", accent_color)
        ram_card, self.ram_val, self.ram_sub, self.ram_spark = self._make_metric_card("MEMORY", accent_color)
        disk_card, self.disk_val, self.disk_sub, self.disk_spark = self._make_metric_card("ROOT DISK (/)", accent_color)
        net_card, self.net_val, self.net_sub, self.net_spark = self._make_metric_card("NETWORK I/O", accent_color)

        grid.attach(cpu_card, 0, 0, 1, 1)
        grid.attach(ram_card, 1, 0, 1, 1)
        grid.attach(disk_card, 2, 0, 1, 1)
        grid.attach(net_card, 3, 0, 1, 1)

        proc_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        proc_card.add_css_class("panel-card")
        proc_card.set_vexpand(True)

        proc_hdr = Gtk.Label(label="TOP ACTIVE PROCESSES (WITH SAFE TERMINATION)")
        proc_hdr.add_css_class("hawkeye-tagline")
        proc_hdr.set_xalign(0.0)
        proc_card.append(proc_hdr)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        proc_card.append(scrolled)

        self.proc_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(self.proc_list)
        self.append(proc_card)

        self._refresh()
        GLib.timeout_add_seconds(2, self._refresh)

    def set_accent_color(self, hex_color: str) -> None:
        for spark in (self.cpu_spark, self.ram_spark, self.disk_spark, self.net_spark):
            spark.set_color(hex_color)

    def _make_metric_card(self, label: str, accent_color: str):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("panel-card")

        top = Gtk.Label(label=label)
        top.add_css_class("hawkeye-tagline")
        top.set_xalign(0.0)

        val = Gtk.Label(label="--")
        val.add_css_class("metric-value")
        val.set_xalign(0.0)

        spark = SparklineWidget(max_points=30, width=180, height=28)
        spark.set_color(accent_color)
        spark.set_hexpand(True)

        sub = Gtk.Label(label="Collecting...")
        sub.add_css_class("hawkeye-tagline")
        sub.set_xalign(0.0)

        card.append(top)
        card.append(val)
        card.append(spark)
        card.append(sub)
        return card, val, sub, spark

    def _terminate_pid(self, pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        self._refresh_processes()

    def _refresh(self) -> bool:
        cpu_pct = psutil.cpu_percent(interval=None)
        cores = psutil.cpu_count(logical=True) or 1
        self.cpu_val.set_text(f"{cpu_pct:.1f}%")
        self.cpu_spark.push(cpu_pct)
        self.cpu_sub.set_text(f"{cores} logical cores active")

        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        self.ram_val.set_text(f"{mem.percent:.1f}%")
        self.ram_spark.push(mem.percent)
        self.ram_sub.set_text(f"{used_gb:.2f} / {total_gb:.2f} GiB")

        disk = psutil.disk_usage("/")
        d_used = disk.used / (1024 ** 3)
        d_total = disk.total / (1024 ** 3)
        self.disk_val.set_text(f"{disk.percent:.1f}%")
        self.disk_spark.push(disk.percent)
        self.disk_sub.set_text(f"{d_used:.1f} / {d_total:.1f} GiB")

        now = time.monotonic()
        dt = max(now - self._last_time, 0.1)
        net = psutil.net_io_counters()
        rx_kb = (net.bytes_recv - self._last_net.bytes_recv) / dt / 1024.0
        tx_kb = (net.bytes_sent - self._last_net.bytes_sent) / dt / 1024.0
        self._last_net = net
        self._last_time = now

        self.net_val.set_text(f"{rx_kb:.1f} KB/s")
        self.net_spark.push(min(((rx_kb + tx_kb) / 1024.0) * 100.0, 100.0))
        self.net_sub.set_text(f"DL: {rx_kb:.1f} KB/s | UL: {tx_kb:.1f} KB/s")

        self._refresh_processes()
        return True

    def _refresh_processes(self) -> None:
        child = self.proc_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.proc_list.remove(child)
            child = nxt

        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        procs.sort(
            key=lambda x: (x.get("cpu_percent") or 0.0, x.get("memory_percent") or 0.0),
            reverse=True,
        )

        my_pid = os.getpid()
        for info in procs[:14]:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("cmd-code-box")

            pid = info["pid"]
            pid_lbl = Gtk.Label(label=f"PID {pid:<6}")
            name_lbl = Gtk.Label(label=f"{(info.get('name') or 'unknown')[:26]:<26}")
            name_lbl.set_hexpand(True)
            name_lbl.set_xalign(0.0)

            cpu_lbl = Gtk.Label(label=f"CPU: {(info.get('cpu_percent') or 0.0):5.1f}%")
            mem_lbl = Gtk.Label(label=f"RAM: {(info.get('memory_percent') or 0.0):4.1f}%")

            row.append(pid_lbl)
            row.append(name_lbl)
            row.append(cpu_lbl)
            row.append(mem_lbl)

            if pid != my_pid and pid > 1:
                kill_btn = Gtk.Button(label="End")
                kill_btn.add_css_class("tab-close-btn")
                kill_btn.set_tooltip_text(f"Send SIGTERM to PID {pid}")
                kill_btn.connect("clicked", lambda *_, p_id=pid: self._terminate_pid(p_id))
                row.append(kill_btn)

            self.proc_list.append(row)
