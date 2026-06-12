#!/usr/bin/env python3
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

PID_FILE = '/tmp/workspace-popup.pid'
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
entry {
    background-color: #23262E;
    color: #D5CED9;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    min-width: 60px;
}
entry:focus {
    border-color: #B084EB;
}
.action-btn {
    background: transparent;
    background-image: none;
    color: #B084EB;
    border: 1px solid #B084EB;
    border-radius: 4px;
    padding: 4px 12px;
    margin-left: 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.action-btn:hover {
    background-color: rgba(176, 132, 235, 0.12);
}
combobox {
    background-color: #23262E;
    color: #D5CED9;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
}
combobox button {
    background: transparent;
    background-image: none;
    color: #D5CED9;
    border: none;
    padding: 4px 8px;
    box-shadow: none;
    text-shadow: none;
}
combobox button:hover {
    background-color: rgba(176, 132, 235, 0.10);
}
combobox arrow {
    color: #B084EB;
    min-width: 12px;
    min-height: 12px;
}
combobox window.popup {
    background-color: #1C1E26;
    border: 1px solid #2A2D3A;
}
combobox menuitem {
    color: #D5CED9;
    padding: 4px 10px;
}
combobox menuitem:hover {
    background-color: rgba(176, 132, 235, 0.18);
    color: #D5CED9;
}
.monitor-btn {
    background: transparent;
    background-image: none;
    color: #00E8C6;
    border: 1px solid #00E8C6;
    border-radius: 4px;
    padding: 6px 10px;
    margin-top: 4px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.monitor-btn:hover {
    background-color: rgba(0, 232, 198, 0.12);
}
.monitor-btn.active {
    background-color: rgba(0, 232, 198, 0.18);
    color: #00E8C6;
    border-color: #00E8C6;
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


def hypr_dispatch(*args):
    subprocess.run(['hyprctl', 'dispatch', *args], check=False)


class WorkspacePopup(Gtk.Window):
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
        self._ws_monitor = ws['monitor']
        monitors = hyprctl_json('monitors')
        all_workspaces = sorted(
            hyprctl_json('workspaces'),
            key=lambda w: w['id'],
        )

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(300, -1)
        blocker.add(root)

        hdr = Gtk.Label()
        hdr.set_markup(
            f'<span foreground="#D5CED9">Workspace </span>'
            f'<span foreground="#B084EB"><b>{self._ws_name}</b></span>'
            f'<span foreground="#677691">  on  </span>'
            f'<span foreground="#00E8C6">{self._ws_monitor}</span>'
        )
        hdr.get_style_context().add_class('ws-header')
        hdr.set_xalign(0)
        root.pack_start(hdr, False, False, 0)

        # --- Renumber ---
        ren_lbl = Gtk.Label(label='Renumber')
        ren_lbl.get_style_context().add_class('section-label')
        ren_lbl.set_xalign(0)
        root.pack_start(ren_lbl, False, False, 0)

        ren_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._entry = Gtk.Entry()
        self._entry.set_text(str(self._ws_id))
        self._entry.set_width_chars(6)
        self._entry.connect('activate', self._on_renumber)
        ren_row.pack_start(self._entry, False, False, 0)

        ren_btn = Gtk.Button(label='Apply')
        ren_btn.get_style_context().add_class('action-btn')
        ren_btn.connect('clicked', self._on_renumber)
        ren_row.pack_start(ren_btn, False, False, 0)
        root.pack_start(ren_row, False, False, 0)

        # divider
        div1 = Gtk.Box()
        div1.get_style_context().add_class('divider')
        root.pack_start(div1, False, False, 0)

        # --- Move active window to workspace ---
        mv_lbl = Gtk.Label(label='Move active window to workspace')
        mv_lbl.get_style_context().add_class('section-label')
        mv_lbl.set_xalign(0)
        root.pack_start(mv_lbl, False, False, 0)

        self._combo = Gtk.ComboBoxText()
        existing_ids = {w['id'] for w in all_workspaces if w['id'] > 0}
        ids = sorted(existing_ids | set(range(1, 11)))
        for wid in ids:
            label = str(wid)
            if wid == self._ws_id:
                label += '  (current)'
            self._combo.append(str(wid), label)
        # Default selection: first non-current
        for wid in ids:
            if wid != self._ws_id:
                self._combo.set_active_id(str(wid))
                break
        self._combo.connect('changed', self._on_move_window)
        root.pack_start(self._combo, False, False, 0)

        # divider
        div2 = Gtk.Box()
        div2.get_style_context().add_class('divider')
        root.pack_start(div2, False, False, 0)

        # --- Move workspace to monitor ---
        mon_lbl = Gtk.Label(label='Move workspace to monitor')
        mon_lbl.get_style_context().add_class('section-label')
        mon_lbl.set_xalign(0)
        root.pack_start(mon_lbl, False, False, 0)

        for m in monitors:
            name = m['name']
            desc = m.get('description', '') or ''
            label = f'  {name}'
            if desc:
                label += f'   {desc[:30]}'
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class('monitor-btn')
            btn.set_alignment(0, 0.5)
            if name == self._ws_monitor:
                btn.get_style_context().add_class('active')
            btn.connect('clicked', self._on_move_monitor, name)
            root.pack_start(btn, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _on_renumber(self, _w):
        txt = self._entry.get_text().strip()
        if not txt:
            return
        try:
            new_id = int(txt)
        except ValueError:
            return
        if new_id == self._ws_id:
            self.destroy()
            return
        hypr_dispatch('renameworkspace', str(self._ws_id), str(new_id))
        self.destroy()

    def _on_move_window(self, combo):
        wid = combo.get_active_id()
        if not wid:
            return
        try:
            target = int(wid)
        except ValueError:
            return
        if target == self._ws_id:
            return
        hypr_dispatch('movetoworkspace', str(target))
        self.destroy()

    def _on_move_monitor(self, _btn, monitor_name):
        if monitor_name == self._ws_monitor:
            self.destroy()
            return
        hypr_dispatch('moveworkspacetomonitor',
                      str(self._ws_id), monitor_name)
        self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, WorkspacePopup)
