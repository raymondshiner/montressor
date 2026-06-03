#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/sound-popup.pid'
POPUP_WIDTH = 300 + 16
SINK = '@DEFAULT_SINK@'

CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(220, 220, 220, 0.55),
        0 40px 40px rgba(220, 220, 220, 0.25);
}
.section-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    margin-bottom: 8px;
}
scale trough {
    background-color: #2A2D3A;
    border-radius: 3px;
    min-height: 4px;
}
scale highlight {
    background-color: #00E8C6;
    border-radius: 3px;
}
scale.muted highlight {
    background-color: #677691;
}
scale slider {
    background-color: #00E8C6;
    border-radius: 50%;
    min-width: 12px;
    min-height: 12px;
    margin: -4px;
}
scale.muted slider {
    background-color: #677691;
}
scale value {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}
.mute-btn {
    background: transparent;
    background-image: none;
    color: #00E8C6;
    border: 1px solid #00E8C6;
    border-radius: 4px;
    padding: 4px 10px;
    margin-right: 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    box-shadow: none;
    text-shadow: none;
    min-width: 24px;
}
.mute-btn:hover {
    background-color: rgba(0, 232, 198, 0.10);
}
.mute-btn.muted {
    color: #677691;
    border-color: #2A2D3A;
}
.mute-btn.muted:hover {
    background-color: rgba(103, 118, 145, 0.10);
}
.settings-btn {
    background: transparent;
    background-image: none;
    color: #00E8C6;
    border: 1px solid #00E8C6;
    border-radius: 4px;
    padding: 6px 10px;
    margin-top: 14px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.settings-btn:hover {
    background-color: rgba(0, 232, 198, 0.10);
}
.settings-btn.muted {
    color: #677691;
    border-color: #2A2D3A;
}
.settings-btn.muted:hover {
    background-color: rgba(103, 118, 145, 0.10);
}
"""


def get_volume():
    try:
        out = subprocess.check_output(['pactl', 'get-sink-volume', SINK], text=True)
        m = re.search(r'(\d+)%', out)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def set_volume(pct):
    pct = max(0, min(150, int(pct)))
    subprocess.run(['pactl', 'set-sink-volume', SINK, f'{pct}%'], check=False)


def get_mute():
    try:
        out = subprocess.check_output(['pactl', 'get-sink-mute', SINK], text=True)
        return 'yes' in out.lower()
    except Exception:
        return False


def toggle_mute():
    subprocess.run(['pactl', 'set-sink-mute', SINK, 'toggle'], check=False)


class SoundPopup(Gtk.Window):
    def __init__(self):
        super().__init__()

        popup_lib.setup_window(self)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        blocker = popup_lib.wrap_with_click_outside(self, POPUP_WIDTH)

        self._muted = get_mute()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        if self._muted:
            root.get_style_context().add_class('muted')
        root.set_size_request(300, -1)
        blocker.add(root)
        self._root = root

        hdr = Gtk.Label(label='Volume')
        hdr.get_style_context().add_class('section-label')
        hdr.set_xalign(0)
        root.pack_start(hdr, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        self._mute_btn = Gtk.Button(label='󰝟' if self._muted else '󰕾')
        self._mute_btn.get_style_context().add_class('mute-btn')
        if self._muted:
            self._mute_btn.get_style_context().add_class('muted')
        self._mute_btn.connect('clicked', self._on_mute)
        row.pack_start(self._mute_btn, False, False, 0)

        self._slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self._slider.set_value(get_volume())
        self._slider.set_draw_value(True)
        self._slider.set_value_pos(Gtk.PositionType.RIGHT)
        self._slider.set_hexpand(True)
        self._slider.connect('format-value', lambda s, v: f'{int(v)}%')
        self._slider.connect('value-changed', self._on_volume)
        if self._muted:
            self._slider.get_style_context().add_class('muted')
        self._vol_timer = None
        row.pack_start(self._slider, True, True, 0)

        root.pack_start(row, False, False, 0)

        self._settings_btn = Gtk.Button(label='  Sound Settings')
        self._settings_btn.get_style_context().add_class('settings-btn')
        if self._muted:
            self._settings_btn.get_style_context().add_class('muted')
        self._settings_btn.connect('clicked', self._on_settings)
        root.pack_start(self._settings_btn, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _on_volume(self, scale):
        if self._vol_timer:
            GLib.source_remove(self._vol_timer)
        pct = int(scale.get_value())
        self._vol_timer = GLib.timeout_add(40, lambda: set_volume(pct) or False)

    def _on_mute(self, _btn):
        toggle_mute()
        self._muted = get_mute()
        for ctx in (self._root.get_style_context(),
                    self._mute_btn.get_style_context(),
                    self._slider.get_style_context(),
                    self._settings_btn.get_style_context()):
            if self._muted:
                ctx.add_class('muted')
            else:
                ctx.remove_class('muted')
        self._mute_btn.set_label('󰝟' if self._muted else '󰕾')

    def _on_settings(self, _btn):
        subprocess.Popen(['pavucontrol'], start_new_session=True)
        self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, SoundPopup)
