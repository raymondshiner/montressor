#!/usr/bin/env python3
"""Layout popup — one-click window arrangements for the current workspace.

The desktop runs Hyprland's master layout, so every preset is just
orientation + master-count + mfact. Master count isn't queryable, so each
preset normalizes it: removemaster down to 1, addmaster up to target.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk
import subprocess
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/layout-popup.pid'
POPUP_WIDTH = 300 + 16

CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(176, 132, 235, 0.45),
        0 40px 40px rgba(176, 132, 235, 0.20);
}
.section-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    margin-bottom: 6px;
}
.ws-header {
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    margin-bottom: 12px;
}
.layout-btn {
    background: transparent;
    background-image: none;
    color: #B084EB;
    border: 1px solid #B084EB;
    border-radius: 4px;
    padding: 8px 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.layout-btn:hover {
    background-color: rgba(176, 132, 235, 0.12);
}
.layout-btn:disabled {
    color: #677691;
    border-color: #2A2D3A;
}
.quick-btn {
    background: transparent;
    background-image: none;
    color: #00E8C6;
    border: 1px solid #00E8C6;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.quick-btn:hover {
    background-color: rgba(0, 232, 198, 0.12);
}
.quick-btn:disabled {
    color: #677691;
    border-color: #2A2D3A;
}
.divider {
    background-color: #2A2D3A;
    min-height: 1px;
    margin-top: 14px;
    margin-bottom: 12px;
}
"""


def hyprctl_json(*args):
    out = subprocess.check_output(['hyprctl', '-j', *args], text=True)
    return json.loads(out)


def hypr_batch(commands):
    arg = ' ; '.join(f'dispatch {c}' for c in commands)
    subprocess.run(['hyprctl', '--batch', arg], check=False,
                   capture_output=True)


class LayoutPopup(Gtk.Window):
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

        ws = hyprctl_json('activeworkspace')
        self._ws_id = ws['id']
        self._ws_name = ws['name']
        clients = hyprctl_json('clients')
        self._windows = [
            c for c in clients
            if c.get('workspace', {}).get('id') == self._ws_id
            and c.get('mapped')
        ]
        n = len(self._windows)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(300, -1)
        blocker.add(root)

        hdr = Gtk.Label()
        hdr.set_markup(
            f'<span foreground="#D5CED9">Layout on </span>'
            f'<span foreground="#B084EB"><b>{self._ws_name}</b></span>'
            f'<span foreground="#677691">  ·  {n} window{"s" if n != 1 else ""}</span>'
        )
        hdr.get_style_context().add_class('ws-header')
        hdr.set_xalign(0)
        root.pack_start(hdr, False, False, 0)

        lbl = Gtk.Label(label='Arrange windows')
        lbl.get_style_context().add_class('section-label')
        lbl.set_xalign(0)
        root.pack_start(lbl, False, False, 0)

        # (label, min windows, preset builder)
        presets = [
            ('󰤼  Side by side',   2, self._side_by_side),
            ('󰙀  Main + stack',   2, self._main_stack),
            ('󱂩  3 columns',      3, self._three_columns),
            ('󰕰  Grid',           4, self._grid),
            ('󰯋  Rows',           2, self._rows),
        ]
        grid = Gtk.Grid()
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)
        grid.set_column_homogeneous(True)
        for i, (label, min_n, fn) in enumerate(presets):
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class('layout-btn')
            btn.set_alignment(0, 0.5)
            btn.set_sensitive(n >= min_n)
            btn.connect('clicked', self._apply, fn)
            grid.attach(btn, i % 2, i // 2, 1, 1)

        full_btn = Gtk.Button(label='󰊓  Maximize')
        full_btn.get_style_context().add_class('layout-btn')
        full_btn.set_alignment(0, 0.5)
        full_btn.set_sensitive(n >= 1)
        full_btn.connect('clicked', self._on_maximize)
        grid.attach(full_btn, len(presets) % 2, len(presets) // 2, 1, 1)
        root.pack_start(grid, False, False, 0)

        div = Gtk.Box()
        div.get_style_context().add_class('divider')
        root.pack_start(div, False, False, 0)

        q_lbl = Gtk.Label(label='Quick actions')
        q_lbl.get_style_context().add_class('section-label')
        q_lbl.set_xalign(0)
        root.pack_start(q_lbl, False, False, 0)

        q_grid = Gtk.Grid()
        q_grid.set_row_spacing(6)
        q_grid.set_column_spacing(6)
        q_grid.set_column_homogeneous(True)
        quick = [
            ('󰓡  Swap main',  2, ['layoutmsg swapwithmaster']),
            ('󰑖  Rotate',     2, ['layoutmsg rollnext']),
        ]
        for i, (label, min_n, cmds) in enumerate(quick):
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class('quick-btn')
            btn.set_alignment(0, 0.5)
            btn.set_sensitive(n >= min_n)
            btn.connect('clicked', self._on_quick, cmds)
            q_grid.attach(btn, i % 2, i // 2, 1, 1)
        root.pack_start(q_grid, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    # --- preset command builders -------------------------------------
    def _prep(self):
        """Undo fullscreen and floating so every window tiles."""
        cmds = []
        for c in self._windows:
            addr = c['address']
            if c.get('fullscreen'):
                cmds.append(f'focuswindow address:{addr}')
                cmds.append('fullscreenstate 0 0')
            if c.get('floating'):
                cmds.append(f'settiled address:{addr}')
        return cmds

    def _set_masters(self, target):
        n = len(self._windows)
        cmds = ['layoutmsg removemaster'] * max(0, n - 1)
        cmds += ['layoutmsg addmaster'] * max(0, target - 1)
        return cmds

    def _side_by_side(self):
        return (self._set_masters(1)
                + ['layoutmsg orientationleft',
                   'layoutmsg mfact exact 0.5'])

    def _main_stack(self):
        return (self._set_masters(1)
                + ['layoutmsg orientationleft',
                   'layoutmsg mfact exact 0.58'])

    def _three_columns(self):
        return (self._set_masters(1)
                + ['layoutmsg orientationcenter',
                   'layoutmsg mfact exact 0.34'])

    def _grid(self):
        return (self._set_masters(len(self._windows) // 2)
                + ['layoutmsg orientationleft',
                   'layoutmsg mfact exact 0.5'])

    def _rows(self):
        return (self._set_masters(1)
                + ['layoutmsg orientationtop',
                   'layoutmsg mfact exact 0.5'])

    # --- handlers -----------------------------------------------------
    def _apply(self, _btn, builder):
        hypr_batch(self._prep() + builder())
        self.destroy()

    def _on_maximize(self, _btn):
        hypr_batch(['fullscreen 1'])
        self.destroy()

    def _on_quick(self, _btn, cmds):
        hypr_batch(cmds)
        self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, LayoutPopup)
