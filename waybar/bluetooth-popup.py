#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/bluetooth-popup.pid'
POPUP_WIDTH = 340 + 16


def _set_pointer_cursor(widget):
    def on_enter(w, _e):
        top = w.get_toplevel().get_window()
        if top:
            top.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), 'pointer'))
    def on_leave(w, _e):
        top = w.get_toplevel().get_window()
        if top:
            top.set_cursor(None)
    widget.connect('enter-notify-event', on_enter)
    widget.connect('leave-notify-event', on_leave)

ICON_MAP = {
    'input-keyboard':   '󰌌',
    'audio-headphones': '󰋋',
    'audio-headset':    '󰋎',
    'audio-card':       '󰓃',
    'input-mouse':      '󰍽',
    'phone':            '󰏲',
    'computer':         '󰟀',
    'input-gaming':     '󰊴',
}

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
.header {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    font-weight: bold;
    margin-bottom: 6px;
}
.power-btn {
    background: transparent;
    background-image: none;
    color: #00E8C6;
    border: 1px solid #00E8C6;
    border-radius: 4px;
    padding: 2px 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}
.power-btn.off {
    color: #677691;
    border-color: #2A2D3A;
}
.power-btn:hover {
    background-color: rgba(0, 232, 198, 0.10);
}
.power-btn.off:hover {
    background-color: rgba(103, 118, 145, 0.10);
}
.empty {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    padding: 12px 4px;
}
.dev-row {
    background-color: rgba(42, 45, 58, 0.6);
    border-radius: 6px;
    padding: 8px 10px;
    margin-top: 6px;
}
.dev-glyph {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 18px;
    margin-right: 10px;
}
.dev-glyph.connected {
    color: #00E8C6;
}
.dev-name {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    font-weight: bold;
}
.dev-mac {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.act-btn {
    background: transparent;
    background-image: none;
    color: #00E8C6;
    border: 1px solid #00E8C6;
    border-radius: 4px;
    padding: 4px 10px;
    margin-left: 6px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}
.act-btn:hover {
    background-color: rgba(0, 232, 198, 0.10);
}
.act-btn.disconnect {
    color: #EE5D43;
    border-color: #EE5D43;
}
.act-btn.disconnect:hover {
    background-color: rgba(238, 93, 67, 0.10);
}
.refresh-btn {
    background: transparent;
    background-image: none;
    color: #677691;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 4px 10px;
    margin-top: 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}
.refresh-btn:hover {
    color: #D5CED9;
    border-color: #00E8C6;
    background-color: rgba(0, 232, 198, 0.10);
}
"""


def bt(*args):
    try:
        return subprocess.check_output(['bluetoothctl', *args], text=True, timeout=2)
    except Exception:
        return ''


def get_powered():
    for line in bt('show').splitlines():
        l = line.strip()
        if l.startswith('Powered:'):
            return 'yes' in l.lower()
    return False


def set_powered(on):
    subprocess.Popen(['bluetoothctl', 'power', 'on' if on else 'off'],
                     start_new_session=True)


def get_paired_devices():
    devs = []
    for line in bt('devices', 'Paired').splitlines():
        parts = line.strip().split(' ', 2)
        if len(parts) >= 3 and parts[0] == 'Device':
            devs.append({'mac': parts[1], 'name': parts[2]})
    for d in devs:
        info = bt('info', d['mac'])
        d['connected'] = False
        d['icon'] = 'computer'
        for line in info.splitlines():
            l = line.strip()
            if l.startswith('Connected:'):
                d['connected'] = 'yes' in l.lower()
            elif l.startswith('Icon:'):
                d['icon'] = l.split(':', 1)[1].strip()
    # Connected devices float to the top
    devs.sort(key=lambda d: (not d['connected'], d['name'].lower()))
    return devs


def connect_device(mac):
    subprocess.Popen(['bluetoothctl', 'connect', mac], start_new_session=True)


def disconnect_device(mac):
    subprocess.Popen(['bluetoothctl', 'disconnect', mac], start_new_session=True)


class BluetoothPopup(Gtk.Window):
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

        self._root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._root.get_style_context().add_class('popup-inner')
        self._root.set_size_request(340, -1)
        blocker.add(self._root)

        self._render()
        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _render(self):
        for child in self._root.get_children():
            self._root.remove(child)

        powered = get_powered()
        devs = get_paired_devices() if powered else []
        connected = sum(1 for d in devs if d['connected'])

        ctx = self._root.get_style_context()
        for k in ('idle', 'off'):
            ctx.remove_class(k)
        if not powered:
            ctx.add_class('off')
        elif connected == 0:
            ctx.add_class('idle')

        # Header row
        hdr_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr_row.set_margin_bottom(4)
        hdr = Gtk.Label(label='󰂯  Bluetooth')
        hdr.get_style_context().add_class('header')
        hdr.set_xalign(0)
        hdr_row.pack_start(hdr, True, True, 0)

        pwr = Gtk.Button(label='On' if powered else 'Off')
        pwr.get_style_context().add_class('power-btn')
        if not powered:
            pwr.get_style_context().add_class('off')
        pwr.connect('clicked', self._on_power, powered)
        _set_pointer_cursor(pwr)
        hdr_row.pack_start(pwr, False, False, 0)
        self._root.pack_start(hdr_row, False, False, 0)

        # Devices
        if not powered:
            self._add_empty('Bluetooth is off')
        elif not devs:
            self._add_empty('No paired devices')
        else:
            for d in devs:
                self._root.pack_start(self._row(d), False, False, 0)

        # Refresh
        ref = Gtk.Button(label='󰑐  Refresh')
        ref.get_style_context().add_class('refresh-btn')
        ref.set_halign(Gtk.Align.END)
        ref.connect('clicked', lambda _b: self._refresh())
        _set_pointer_cursor(ref)
        self._root.pack_start(ref, False, False, 0)

        self._root.show_all()

    def _add_empty(self, msg):
        e = Gtk.Label(label=msg)
        e.get_style_context().add_class('empty')
        e.set_xalign(0)
        self._root.pack_start(e, False, False, 0)

    def _row(self, d):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.get_style_context().add_class('dev-row')

        glyph = Gtk.Label(label=ICON_MAP.get(d['icon'], '󰂯'))
        glyph.get_style_context().add_class('dev-glyph')
        if d['connected']:
            glyph.get_style_context().add_class('connected')
        row.pack_start(glyph, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        info.set_hexpand(True)
        name = Gtk.Label(label=d['name'])
        name.get_style_context().add_class('dev-name')
        name.set_xalign(0)
        name.set_ellipsize(3)
        info.pack_start(name, False, False, 0)

        mac = Gtk.Label(label=d['mac'])
        mac.get_style_context().add_class('dev-mac')
        mac.set_xalign(0)
        info.pack_start(mac, False, False, 0)

        row.pack_start(info, True, True, 0)

        if d['connected']:
            act = Gtk.Button(label='󰂲  Disconnect')
            act.get_style_context().add_class('act-btn')
            act.get_style_context().add_class('disconnect')
        else:
            act = Gtk.Button(label='󰂯  Connect')
            act.get_style_context().add_class('act-btn')
        act.connect('clicked', self._on_act, d)
        _set_pointer_cursor(act)
        row.pack_start(act, False, False, 0)

        return row

    def _refresh(self):
        self._render()
        self.show_all()

    def _on_power(self, _btn, was_on):
        set_powered(not was_on)
        GLib.timeout_add(800, lambda: (self._refresh(), False)[1])

    def _on_act(self, _btn, d):
        if d['connected']:
            disconnect_device(d['mac'])
        else:
            connect_device(d['mac'])
        GLib.timeout_add(1800, lambda: (self._refresh(), False)[1])

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, BluetoothPopup)
