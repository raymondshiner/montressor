#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk
import subprocess
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/calendar-popup.pid'
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
        0 40px 40px rgba(176, 132, 235, 0.2);
}
.date-value {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    font-weight: bold;
}
.time-value {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}
calendar {
    background-color: transparent;
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    padding: 4px 0;
}
calendar:selected {
    background-color: #B084EB;
    color: #1C1E26;
    border-radius: 4px;
}
calendar.header {
    color: #B084EB;
    font-weight: bold;
    border: none;
}
calendar.button {
    color: #B084EB;
    background: transparent;
    border: none;
    box-shadow: none;
}
calendar.button:hover {
    color: #D5CED9;
}
calendar:indeterminate {
    color: #3A3D4A;
}
calendar.highlight {
    color: #00E8C6;
    font-weight: bold;
}
.open-btn {
    background: transparent;
    background-image: none;
    color: #B084EB;
    border: 1px solid #B084EB;
    border-radius: 4px;
    padding: 6px 10px;
    margin-top: 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}
.open-btn:hover {
    background-color: #B084EB;
    color: #1C1E26;
}
"""


class CalendarPopup(Gtk.Window):
    def __init__(self):
        super().__init__()

        popup_lib.setup_window(self)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        blocker = popup_lib.wrap_with_click_outside(self, POPUP_WIDTH)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(280, -1)
        blocker.add(root)

        now = datetime.datetime.now()

        date_lbl = Gtk.Label(label=now.strftime('  %A, %B %-d'))
        date_lbl.get_style_context().add_class('date-value')
        date_lbl.set_xalign(0)
        root.pack_start(date_lbl, False, False, 0)

        time_lbl = Gtk.Label(label=now.strftime('%-I:%M %p  ·  Week %W'))
        time_lbl.get_style_context().add_class('time-value')
        time_lbl.set_xalign(0)
        time_lbl.set_margin_top(2)
        root.pack_start(time_lbl, False, False, 0)

        cal = Gtk.Calendar()
        cal.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING
            | Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES
        )
        cal.mark_day(now.day)
        cal.set_margin_top(8)
        root.pack_start(cal, False, False, 0)

        open_btn = Gtk.Button(label='Open Google Calendar')
        open_btn.get_style_context().add_class('open-btn')
        open_btn.connect('clicked', self._open_gcal)
        root.pack_start(open_btn, False, False, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _open_gcal(self, _btn):
        subprocess.Popen(
            ['xdg-open', 'https://calendar.google.com/'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, CalendarPopup)
