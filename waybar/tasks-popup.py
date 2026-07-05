#!/usr/bin/env python3
"""Andromeda tasks popup — a lightweight task manager anchored to waybar.

Lists every open window (Hyprland client), grouped by workspace. Click a row
to focus it (switches workspace); click the ✕ to close it. The list refreshes
in place after a close so the popup stays open for bulk tidy-ups.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GLib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/tasks-popup.pid'
POPUP_WIDTH = 380 + 16
POPUP_HEIGHT = 520
GLOW = '176, 132, 235'  # purple, matches the bar icon

CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(176, 132, 235, 0.40),
        0 40px 40px rgba(176, 132, 235, 0.18);
}
.title-label {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    font-weight: bold;
}
.count-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}
.ws-label {
    color: #B084EB;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    margin-top: 8px;
    margin-bottom: 2px;
}
.task-row {
    background: transparent;
    background-image: none;
    border: none;
    border-radius: 6px;
    padding: 6px 8px;
    box-shadow: none;
    text-shadow: none;
}
.task-row:hover {
    background-color: rgba(176, 132, 235, 0.12);
}
.task-name {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
}
.task-class {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.close-btn {
    background: transparent;
    background-image: none;
    color: #677691;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    box-shadow: none;
    text-shadow: none;
}
.close-btn:hover {
    background-color: rgba(238, 93, 67, 0.16);
    color: #EE5D43;
}
.empty {
    color: #677691;
    font-size: 12px;
    padding: 8px;
}
scrolledwindow undershoot, scrolledwindow overshoot { background: none; }
scrollbar { background: transparent; }
scrollbar slider {
    background-color: rgba(103, 118, 145, 0.5);
    border-radius: 4px;
    min-width: 6px;
    min-height: 30px;
}
scrollbar slider:hover { background-color: rgba(176, 132, 235, 0.6); }
.divider {
    background-color: #2A2D3A;
    min-height: 1px;
    margin-top: 8px;
    margin-bottom: 4px;
}
"""


def get_clients():
    """Return Hyprland clients (mapped windows), sorted by workspace then title."""
    try:
        out = subprocess.check_output(['hyprctl', '-j', 'clients'],
                                      text=True, timeout=1)
        clients = json.loads(out)
    except Exception:
        return []
    wins = [c for c in clients if c.get('mapped') and c.get('class')]
    wins.sort(key=lambda c: (c.get('workspace', {}).get('id', 0),
                             (c.get('title') or '').lower()))
    return wins


def build_icon_map():
    """Map lowercased WM class → Gio icon, for the best-effort window icons."""
    icons = {}
    for info in Gio.AppInfo.get_all():
        if not isinstance(info, Gio.DesktopAppInfo):
            continue
        icon = info.get_icon()
        if not icon:
            continue
        wm = info.get_startup_wm_class()
        if wm:
            icons.setdefault(wm.lower(), icon)
        stem = (info.get_id() or '').rsplit('.desktop', 1)[0].rsplit('.', 1)[-1]
        if stem:
            icons.setdefault(stem.lower(), icon)
    return icons


def focus_window(addr):
    subprocess.run(['hyprctl', 'dispatch', 'focuswindow', f'address:{addr}'],
                   capture_output=True)


def close_window(addr):
    subprocess.run(['hyprctl', 'dispatch', 'closewindow', f'address:{addr}'],
                   capture_output=True)


class TasksPopup(Gtk.Window):
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

        self._icons = build_icon_map()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(380, POPUP_HEIGHT)
        blocker.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label='󰖯  Open Windows')
        title.get_style_context().add_class('title-label')
        title.set_xalign(0)
        header.pack_start(title, True, True, 0)
        self._count = Gtk.Label()
        self._count.get_style_context().add_class('count-label')
        self._count.set_xalign(1)
        header.pack_start(self._count, False, False, 0)
        root.pack_start(header, False, False, 0)

        div = Gtk.Box()
        div.get_style_context().add_class('divider')
        root.pack_start(div, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        root.pack_start(scrolled, True, True, 0)

        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scrolled.add(self._list_box)
        self._render()

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _icon_image(self, cls, size):
        img = Gtk.Image()
        icon = self._icons.get((cls or '').lower())
        if icon:
            img.set_from_gicon(icon, Gtk.IconSize.DIALOG)
        else:
            img.set_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
        img.set_pixel_size(size)
        return img

    def _render(self):
        for child in self._list_box.get_children():
            self._list_box.remove(child)

        wins = get_clients()
        self._count.set_text(f'{len(wins)} open')

        if not wins:
            empty = Gtk.Label(label='No open windows.')
            empty.get_style_context().add_class('empty')
            empty.set_xalign(0)
            self._list_box.pack_start(empty, False, False, 0)
            self._list_box.show_all()
            return

        cur_ws = None
        for c in wins:
            ws = c.get('workspace', {})
            ws_id = ws.get('id')
            if ws_id != cur_ws:
                cur_ws = ws_id
                ws_name = ws.get('name') or ws_id
                lbl = Gtk.Label(label=f'Workspace {ws_name}')
                lbl.get_style_context().add_class('ws-label')
                lbl.set_xalign(0)
                self._list_box.pack_start(lbl, False, False, 0)

            addr = c['address']
            cls = c.get('class', '')
            title = c.get('title') or cls or 'Untitled'

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

            focus_btn = Gtk.Button()
            focus_btn.get_style_context().add_class('task-row')
            focus_btn.set_hexpand(True)
            inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            inner.pack_start(self._icon_image(cls, 22), False, False, 0)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            name = Gtk.Label(label=title[:44])
            name.get_style_context().add_class('task-name')
            name.set_xalign(0)
            name.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            text.pack_start(name, False, False, 0)
            clbl = Gtk.Label(label=cls)
            clbl.get_style_context().add_class('task-class')
            clbl.set_xalign(0)
            text.pack_start(clbl, False, False, 0)
            inner.pack_start(text, True, True, 0)
            focus_btn.add(inner)
            focus_btn.connect('clicked', self._on_focus, addr)
            row.pack_start(focus_btn, True, True, 0)

            close_btn = Gtk.Button(label='')
            close_btn.get_style_context().add_class('close-btn')
            close_btn.set_tooltip_text('Close window')
            close_btn.connect('clicked', self._on_close, addr)
            row.pack_start(close_btn, False, False, 0)

            self._list_box.pack_start(row, False, False, 0)

        self._list_box.show_all()

    def _on_focus(self, _btn, addr):
        focus_window(addr)
        self.destroy()

    def _on_close(self, _btn, addr):
        close_window(addr)
        GLib.timeout_add(120, lambda: self._render() or False)

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, TasksPopup)
