#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import subprocess
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/drives-popup.pid'
POPUP_WIDTH = 320 + 16

CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 0 28px rgba(0, 0, 0, 0.8),
        0 0 20px rgba(220, 220, 220, 0.55),
        0 0 40px rgba(220, 220, 220, 0.25);
}
.header {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    margin-bottom: 4px;
}
.empty {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    padding: 12px 4px;
}
.drive-row {
    background-color: rgba(42, 45, 58, 0.6);
    border-radius: 6px;
    padding: 8px 10px;
    margin-top: 6px;
}
.drive-label {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    font-weight: bold;
}
.drive-meta {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.usage-bar trough {
    background-color: #1C1E26;
    border-radius: 2px;
    min-height: 4px;
}
.usage-bar progress {
    background-color: #00E8C6;
    border-radius: 2px;
    min-height: 4px;
}
.usage-bar.warn progress { background-color: #FFE66D; }
.usage-bar.crit progress { background-color: #EE5D43; }
.icon-btn {
    background: transparent;
    background-image: none;
    color: #677691;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 4px 8px;
    margin-left: 6px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.icon-btn:hover {
    color: #D5CED9;
    border-color: #00E8C6;
    background-color: rgba(0, 232, 198, 0.10);
}
.eject-btn:hover {
    color: #EE5D43;
    border-color: #EE5D43;
    background-color: rgba(238, 93, 67, 0.10);
}
"""


def list_drives():
    try:
        out = subprocess.check_output(
            ['lsblk', '-J', '-b', '-o', 'NAME,PATH,LABEL,MOUNTPOINT,RM,TYPE,SIZE,FSUSED,FSAVAIL,VENDOR,MODEL'],
            text=True,
        )
        data = json.loads(out)
    except Exception:
        return []

    drives = []

    def walk(nodes, parent=None):
        for n in nodes:
            if n.get('rm') and n.get('mountpoint') and n.get('type') in ('part', 'disk'):
                drives.append({
                    'path': n.get('path'),
                    'label': n.get('label') or n.get('name'),
                    'mount': n.get('mountpoint'),
                    'size': n.get('size') or 0,
                    'used': n.get('fsused') or 0,
                    'avail': n.get('fsavail') or 0,
                    'vendor': (parent or {}).get('vendor') or n.get('vendor') or '',
                    'model': (parent or {}).get('model') or n.get('model') or '',
                })
            if n.get('children'):
                walk(n['children'], parent=n)

    walk(data.get('blockdevices', []))
    return drives


def human(n):
    n = int(n or 0)
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if n < 1024:
            return f'{n:.1f}{unit}' if unit != 'B' else f'{n}{unit}'
        n /= 1024
    return f'{n:.1f}P'


def open_in_fm(path):
    fm = shutil.which('thunar') or shutil.which('nautilus') or shutil.which('nemo') or 'xdg-open'
    subprocess.Popen([fm, path], start_new_session=True)


def eject(path):
    subprocess.Popen(
        ['sh', '-c', f'udisksctl unmount -b {path} && udisksctl power-off -b {path}'],
        start_new_session=True,
    )


class DrivesPopup(Gtk.Window):
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

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(320, -1)
        blocker.add(root)

        hdr = Gtk.Label(label='Removable Drives')
        hdr.get_style_context().add_class('header')
        hdr.set_xalign(0)
        root.pack_start(hdr, False, False, 0)

        drives = list_drives()
        if not drives:
            empty = Gtk.Label(label='No drives connected')
            empty.get_style_context().add_class('empty')
            empty.set_xalign(0)
            root.pack_start(empty, False, False, 0)
        else:
            for d in drives:
                root.pack_start(self._row(d), False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _row(self, d):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.get_style_context().add_class('drive-row')

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        left.set_hexpand(True)

        title = d['label'] or d['path']
        if d['vendor'] or d['model']:
            sub = f"{d['vendor']} {d['model']}".strip()
        else:
            sub = d['path']

        lbl = Gtk.Label(label=f'󰋊  {title}')
        lbl.get_style_context().add_class('drive-label')
        lbl.set_xalign(0)
        left.pack_start(lbl, False, False, 0)

        meta_txt = f"{sub}  ·  {human(d['used'])} / {human(d['size'])} used  ·  {d['mount']}"
        meta = Gtk.Label(label=meta_txt)
        meta.get_style_context().add_class('drive-meta')
        meta.set_xalign(0)
        meta.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        left.pack_start(meta, False, False, 0)

        used = int(d['used'] or 0)
        size = int(d['size'] or 1)
        frac = used / size if size else 0
        bar = Gtk.ProgressBar()
        bar.set_fraction(frac)
        bar.get_style_context().add_class('usage-bar')
        if frac >= 0.9:
            bar.get_style_context().add_class('crit')
        elif frac >= 0.75:
            bar.get_style_context().add_class('warn')
        bar.set_margin_top(4)
        left.pack_start(bar, False, False, 0)

        row.pack_start(left, True, True, 0)

        open_btn = Gtk.Button(label='󰉋')
        open_btn.get_style_context().add_class('icon-btn')
        open_btn.set_tooltip_text(f"Open {d['mount']}")
        open_btn.connect('clicked', lambda _b, p=d['mount']: (open_in_fm(p), self.destroy()))
        row.pack_start(open_btn, False, False, 0)

        ej_btn = Gtk.Button(label='󰒲')
        ej_btn.get_style_context().add_class('icon-btn')
        ej_btn.get_style_context().add_class('eject-btn')
        ej_btn.set_tooltip_text(f"Eject {d['path']}")
        ej_btn.connect('clicked', lambda _b, p=d['path']: (eject(p), self.destroy()))
        row.pack_start(ej_btn, False, False, 0)

        return row

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, DrivesPopup)
