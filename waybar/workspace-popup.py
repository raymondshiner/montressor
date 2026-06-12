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
POPUP_WIDTH = 280 + 16

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
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    margin-bottom: 10px;
}
.ws-header .accent { color: #B084EB; }
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
    padding: 4px 10px;
    margin-left: 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    box-shadow: none;
    text-shadow: none;
}
.action-btn:hover {
    background-color: rgba(176, 132, 235, 0.12);
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
.monitor-btn.current {
    color: #677691;
    border-color: #2A2D3A;
}
.divider {
    background-color: #2A2D3A;
    min-height: 1px;
    margin-top: 12px;
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

        # Position under the cursor (left-anchored override since workspaces
        # are on the left of the bar).
        blocker = self._wrap_left_anchored(POPUP_WIDTH)

        ws = hyprctl_json('activeworkspace')
        self._ws_id = ws['id']
        self._ws_name = ws['name']
        self._ws_monitor = ws['monitor']
        monitors = hyprctl_json('monitors')

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(280, -1)
        blocker.add(root)

        hdr = Gtk.Label()
        hdr.set_markup(
            f'<span foreground="#D5CED9">Workspace </span>'
            f'<span foreground="#B084EB">{self._ws_name}</span>'
            f'<span foreground="#677691">  on  </span>'
            f'<span foreground="#00E8C6">{self._ws_monitor}</span>'
        )
        hdr.get_style_context().add_class('ws-header')
        hdr.set_xalign(0)
        root.pack_start(hdr, False, False, 0)

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

        # Divider
        div = Gtk.Box()
        div.get_style_context().add_class('divider')
        root.pack_start(div, False, False, 0)

        mon_lbl = Gtk.Label(label='Move to monitor')
        mon_lbl.get_style_context().add_class('section-label')
        mon_lbl.set_xalign(0)
        root.pack_start(mon_lbl, False, False, 0)

        for m in monitors:
            name = m['name']
            desc = m.get('description', '') or ''
            label = f'  {name}'
            if desc:
                label += f'   {desc[:32]}'
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class('monitor-btn')
            btn.set_alignment(0, 0.5)
            if name == self._ws_monitor:
                btn.get_style_context().add_class('current')
                btn.set_sensitive(False)
            else:
                btn.connect('clicked', self._on_move_monitor, name)
            root.pack_start(btn, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _wrap_left_anchored(self, popup_width):
        """Variant of popup_lib.wrap_with_click_outside that anchors to the
        cursor but biases toward the LEFT edge of the screen, since the
        workspaces module lives on the left of the bar."""
        import cairo
        from gi.repository import GtkLayerShell
        cursor_x = popup_lib.get_cursor_x()
        monitor = popup_lib._monitor_for_cursor(cursor_x)
        if monitor:
            geo = monitor.get_geometry()
            screen_x0 = geo.x
            screen_w = geo.width
        else:
            screen_x0 = 0
            screen_w = 1920

        catcher = Gtk.EventBox()
        catcher.connect('button-press-event',
                        lambda *_: self.destroy() or True)
        self.add(catcher)

        positioner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        positioner.set_valign(Gtk.Align.START)
        positioner.set_margin_top(popup_lib.WAYBAR_HEIGHT - 12)

        if cursor_x is None:
            positioner.set_halign(Gtk.Align.START)
            positioner.set_margin_start(2)
        else:
            local_x = cursor_x - screen_x0
            margin_left = max(2, min(screen_w - popup_width - 2,
                                     local_x - popup_width // 2))
            positioner.set_halign(Gtk.Align.START)
            positioner.set_margin_start(margin_left)
        catcher.add(positioner)

        blocker = Gtk.EventBox()
        blocker.connect('button-press-event', lambda *_: True)
        positioner.pack_start(blocker, False, False, 0)

        def _apply_input_region(*_):
            gdkwin = self.get_window()
            if not gdkwin:
                return False
            mon = (Gdk.Display.get_default().get_monitor_at_window(gdkwin)
                   or monitor)
            if not mon:
                return False
            g = mon.get_geometry()
            region = cairo.Region(
                cairo.RectangleInt(0, popup_lib.WAYBAR_HEIGHT, g.width,
                                   max(1, g.height - popup_lib.WAYBAR_HEIGHT))
            )
            alloc = blocker.get_allocation()
            if alloc.width > 0 and alloc.height > 0:
                region.union(cairo.RectangleInt(alloc.x, alloc.y,
                                                alloc.width, alloc.height))
            gdkwin.input_shape_combine_region(region, 0, 0)
            return False

        self.connect('map-event', _apply_input_region)
        self.connect('size-allocate', _apply_input_region)

        return blocker

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

    def _on_move_monitor(self, _btn, monitor_name):
        hypr_dispatch('moveworkspacetomonitor',
                      str(self._ws_id), monitor_name)
        self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, WorkspacePopup)
