#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/battery-popup.pid'
POPUP_WIDTH = 260 + 16  # size_request + .popup-inner CSS margin*2

BACKLIGHT = '/sys/class/backlight/intel_backlight'

CSS_TEMPLATE = """
window {{
    background: transparent;
}}
.popup-inner {{
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(220, 220, 220, 0.55),
        0 40px 40px rgba(220, 220, 220, 0.25);
}}
.time-value {{
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    font-weight: bold;
}}
.section-label {{
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    margin-top: 6px;
}}
.slider-label {{
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}}
scale trough {{
    background-color: #2A2D3A;
    border-radius: 3px;
    min-height: 4px;
}}
scale highlight {{
    background-color: #00E8C6;
    border-radius: 3px;
}}
scale slider {{
    background-color: #00E8C6;
    border-radius: 50%;
    min-width: 12px;
    min-height: 12px;
    margin: -4px;
}}
scale value {{
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}}
.profile-btn {{
    background: transparent;
    background-image: none;
    color: #677691;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}}
.profile-btn:hover {{
    background-color: #2A2D3A;
    color: #D5CED9;
    border-color: #3A3D4A;
}}
.profile-active {{
    color: #1C1E26;
    border-color: #00E8C6;
    background-color: #00E8C6;
}}
.profile-active:hover {{
    background-color: #00E8C6;
    color: #1C1E26;
}}
"""

def get_battery_time():
    try:
        devs = subprocess.check_output(['upower', '-e'], text=True).strip().split('\n')
        bat  = next((d for d in devs if 'battery' in d.lower()), None)
        if not bat:
            return '  Battery'
        info = subprocess.check_output(['upower', '-i', bat], text=True)
        for line in info.split('\n'):
            l = line.strip()
            if 'time to empty' in l:
                return '  ' + l.split(':', 1)[1].strip() + ' remaining'
            if 'time to full' in l:
                return '  ' + l.split(':', 1)[1].strip() + ' to full'
        for line in info.split('\n'):
            if 'percentage' in line:
                return '  ' + line.split(':', 1)[1].strip()
    except Exception:
        pass
    return '  Unknown'

def read_brightness():
    try:
        cur = int(open(f'{BACKLIGHT}/brightness').read())
        mx  = int(open(f'{BACKLIGHT}/max_brightness').read())
        return cur, mx
    except Exception:
        return 50, 100

def write_brightness(pct, mx):
    val = max(0, min(mx, int(pct * mx / 100)))
    try:
        with open(f'{BACKLIGHT}/brightness', 'w') as f:
            f.write(str(val))
    except Exception:
        subprocess.run(['sudo', 'tee', f'{BACKLIGHT}/brightness'],
                       input=str(val).encode(), capture_output=True)

def detect_external_monitors():
    """Return list of dicts: {'display': N, 'model': str} for DDC/CI-capable external displays."""
    try:
        out = subprocess.run(
            ['ddcutil', 'detect', '--terse'],
            capture_output=True, text=True, timeout=4,
        ).stdout
    except Exception:
        return []
    monitors = []
    cur = None
    for raw in out.splitlines():
        line = raw.strip()
        if line.startswith('Display '):
            if cur and 'display' in cur:
                monitors.append(cur)
            try:
                cur = {'display': int(line.split()[1])}
            except Exception:
                cur = None
        elif cur is not None and line.startswith('Monitor:'):
            parts = [p for p in line.split(':', 1)[1].split(':') if p]
            cur['model'] = parts[1].strip() if len(parts) >= 2 else 'External'
    if cur and 'display' in cur:
        monitors.append(cur)
    return [m for m in monitors if m.get('model')]

def read_external_brightness(display):
    try:
        out = subprocess.run(
            ['ddcutil', '--display', str(display), '--terse', 'getvcp', '10'],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        parts = out.split()
        if len(parts) >= 5 and parts[0] == 'VCP':
            return int(parts[3]), int(parts[4])
    except Exception:
        pass
    return None

def write_external_brightness(display, pct):
    val = max(0, min(100, int(pct)))
    try:
        subprocess.run(
            ['ddcutil', '--display', str(display), '--noverify',
             'setvcp', '10', str(val)],
            capture_output=True, timeout=3,
        )
    except Exception:
        pass

def get_profile():
    try:
        return subprocess.check_output(['powerprofilesctl', 'get'], text=True).strip()
    except Exception:
        return 'balanced'

def set_profile(p):
    subprocess.run(['powerprofilesctl', 'set', p])

def get_glow_color():
    try:
        devs = subprocess.check_output(['upower', '-e'], text=True).strip().split('\n')
        bat  = next((d for d in devs if 'battery' in d.lower()), None)
        if not bat:
            return '0, 232, 198'
        info = subprocess.check_output(['upower', '-i', bat], text=True)
        state = ''
        pct   = 100
        for line in info.split('\n'):
            l = line.strip()
            if l.startswith('state:'):
                state = l.split(':', 1)[1].strip()
            if l.startswith('percentage:'):
                pct = int(l.split(':', 1)[1].strip().rstrip('%'))
        if state in ('charging', 'fully-charged', 'pending-charge'):
            return '0, 232, 198'   # cyan
        if pct <= 20:
            return '238, 93, 67'   # red
        if pct <= 50:
            return '255, 230, 109' # yellow
        return '168, 255, 96'      # green
    except Exception:
        return '0, 232, 198'


class BatteryPopup(Gtk.Window):
    def __init__(self):
        super().__init__()

        popup_lib.setup_window(self)

        # CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS_TEMPLATE.format().encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        blocker = popup_lib.wrap_with_click_outside(self, POPUP_WIDTH)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(260, -1)
        blocker.add(root)

        # --- Battery time ---
        time_lbl = Gtk.Label(label=get_battery_time())
        time_lbl.get_style_context().add_class('time-value')
        time_lbl.set_xalign(0)
        root.pack_start(time_lbl, False, False, 0)

        # --- Brightness ---
        brt_hdr = Gtk.Label(label='Brightness')
        brt_hdr.get_style_context().add_class('section-label')
        brt_hdr.set_xalign(0)
        root.pack_start(brt_hdr, False, False, 0)

        cur_b, self._max_b = read_brightness()
        self._slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        self._slider.set_value(cur_b * 100 // self._max_b)
        self._slider.set_draw_value(True)
        self._slider.set_value_pos(Gtk.PositionType.RIGHT)
        self._slider.set_hexpand(True)
        self._slider.connect('format-value', lambda s, v: f'{int(v)}%')
        self._slider.connect('value-changed', self._on_brightness)
        self._bright_timer = None

        # Pre-build the internal row with a hidden "Built-in" label;
        # it's revealed only if an external monitor is later detected.
        self._label_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self._int_label = Gtk.Label(label='Built-in')
        self._int_label.get_style_context().add_class('slider-label')
        self._int_label.set_xalign(0)
        self._int_label.set_no_show_all(True)
        self._int_label.set_visible(False)
        self._label_group.add_widget(self._int_label)

        internal_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        internal_row.pack_start(self._int_label, False, False, 0)
        internal_row.pack_start(self._slider, True, True, 0)
        root.pack_start(internal_row, False, False, 0)

        # External sliders are populated asynchronously to keep open instant.
        self._ext_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(self._ext_container, False, False, 0)
        self._ext_sliders = []
        threading.Thread(target=self._load_externals, daemon=True).start()

        # --- Power mode ---
        pwr_hdr = Gtk.Label(label='Power Mode')
        pwr_hdr.get_style_context().add_class('section-label')
        pwr_hdr.set_xalign(0)
        root.pack_start(pwr_hdr, False, False, 0)

        self._active_profile = get_profile()
        self._btns = {}
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        btn_row.set_margin_top(5)
        for pid, plabel in [('performance', 'High Perf'),
                             ('balanced',    'Balanced'),
                             ('power-saver', 'Power Saver')]:
            b = Gtk.Button(label=plabel)
            b.get_style_context().add_class('profile-btn')
            if pid == self._active_profile:
                b.get_style_context().add_class('profile-active')
            b.connect('clicked', self._on_profile, pid)
            self._btns[pid] = b
            btn_row.pack_start(b, True, True, 0)
        root.pack_start(btn_row, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _on_brightness(self, scale):
        if self._bright_timer:
            GLib.source_remove(self._bright_timer)
        pct = int(scale.get_value())
        self._bright_timer = GLib.timeout_add(40, lambda: write_brightness(pct, self._max_b) or False)

    def _load_externals(self):
        data = []
        for mon in detect_external_monitors():
            br = read_external_brightness(mon['display'])
            if br is not None:
                data.append((mon, br))
        if data:
            GLib.idle_add(self._render_externals, data)

    def _render_externals(self, data):
        self._int_label.set_visible(True)
        for mon, (cur, mx) in data:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=mon['model'][:14])
            lbl.get_style_context().add_class('slider-label')
            lbl.set_xalign(0)
            self._label_group.add_widget(lbl)
            row.pack_start(lbl, False, False, 0)

            ext_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, mx, 1)
            ext_slider.set_value(cur)
            ext_slider.set_draw_value(True)
            ext_slider.set_value_pos(Gtk.PositionType.RIGHT)
            ext_slider.set_hexpand(True)
            ext_slider.connect('format-value', lambda s, v: f'{int(v)}%')
            entry = {'display': mon['display'], 'slider': ext_slider, 'timer': None}
            ext_slider.connect('value-changed', self._on_external_brightness, entry)
            row.pack_start(ext_slider, True, True, 0)
            self._ext_container.pack_start(row, False, False, 0)
            self._ext_sliders.append(entry)
        self._ext_container.show_all()
        return False

    def _on_external_brightness(self, scale, entry):
        if entry['timer']:
            GLib.source_remove(entry['timer'])
        val = int(scale.get_value())
        entry['timer'] = GLib.timeout_add(
            250,
            lambda: write_external_brightness(entry['display'], val) or False,
        )

    def _on_profile(self, btn, pid):
        set_profile(pid)
        for p, b in self._btns.items():
            ctx = b.get_style_context()
            if p == pid:
                ctx.add_class('profile-active')
            else:
                ctx.remove_class('profile-active')


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, BatteryPopup)
