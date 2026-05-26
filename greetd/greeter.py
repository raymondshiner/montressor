#!/usr/bin/env python3
"""Andromeda greeter — GTK3 fullscreen, single password field, talks to greetd.

Architecture: cage (kiosk Wayland compositor) → this script. We render a
centered "Enter Password" headline and a transparent password entry that
shows '*' per keystroke with a native blinking caret. On Enter we walk
the greetd auth protocol over $GREETD_SOCK and start Hyprland on success.

If anything explodes in setup we exec /usr/bin/agreety as a safety net so
the user is never locked out.
"""
import os
import json
import struct
import socket
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk

USER = 'sirlexicon'
SESSION_CMD = ['start-hyprland']

BG = '#1C1E26'
FG = '#D5CED9'
FONT = 'JetBrainsMono Nerd Font'

CSS = f"""
window {{
    background-color: {BG};
}}
label.headline {{
    color: {FG};
    font-family: '{FONT}';
    font-size: 40pt;
    font-weight: 500;
    letter-spacing: 4px;
    margin-bottom: 32px;
}}
entry.password {{
    background-color: transparent;
    background-image: none;
    border: 0;
    border-radius: 0;
    box-shadow: none;
    outline: none;
    color: {FG};
    caret-color: {FG};
    font-family: '{FONT}';
    font-size: 28pt;
    padding: 0;
    margin: 0;
    min-height: 0;
}}
entry.password selection {{
    background-color: transparent;
    color: {FG};
}}
""".encode()


def _chat(sock, payload):
    data = json.dumps(payload).encode()
    sock.sendall(struct.pack('=I', len(data)) + data)
    hdr = b''
    while len(hdr) < 4:
        chunk = sock.recv(4 - len(hdr))
        if not chunk:
            raise IOError('greetd closed connection')
        hdr += chunk
    n = struct.unpack('=I', hdr)[0]
    body = b''
    while len(body) < n:
        chunk = sock.recv(n - len(body))
        if not chunk:
            raise IOError('greetd closed connection')
        body += chunk
    return json.loads(body.decode())


class Greeter:
    def __init__(self):
        self.sock_path = os.environ.get('GREETD_SOCK')
        self.sock = None
        self._open_session()

    def _open_session(self):
        if self.sock:
            try: self.sock.close()
            except Exception: pass
            self.sock = None
        if not self.sock_path:
            return
        s = socket.socket(socket.AF_UNIX)
        s.connect(self.sock_path)
        self.sock = s
        r = _chat(s, {'type': 'create_session', 'username': USER})
        # Most PAM stacks reply with an auth_message asking for the
        # password. We ignore its text — our UI already says "Enter
        # Password" — and wait for the user to submit.
        if r['type'] not in ('auth_message', 'success'):
            self.sock.close()
            self.sock = None

    def submit(self, password):
        """Returns True iff login succeeded (caller should quit GTK)."""
        if not self.sock:
            self._open_session()
        if not self.sock:
            return False
        try:
            r = _chat(self.sock, {'type': 'post_auth_message_response',
                                  'response': password})
            # Defensive: PAM may emit additional info/error messages
            # before the verdict. We respond with empty strings since we
            # only have one input field.
            while r['type'] == 'auth_message':
                r = _chat(self.sock, {'type': 'post_auth_message_response',
                                      'response': ''})
            if r['type'] == 'success':
                _chat(self.sock, {'type': 'start_session',
                                  'cmd': SESSION_CMD})
                try: self.sock.close()
                except Exception: pass
                self.sock = None
                return True
            try:
                _chat(self.sock, {'type': 'cancel_session'})
            except Exception:
                pass
        except Exception:
            pass
        try: self.sock.close()
        except Exception: pass
        self.sock = None
        try: self._open_session()
        except Exception: pass
        return False


def _pick_monitor():
    """Prefer first external (HDMI/DP) output; fall back to internal."""
    display = Gdk.Display.get_default()
    if display is None:
        return 0
    n = display.get_n_monitors()
    external_idx = None
    internal_idx = 0
    for i in range(n):
        mon = display.get_monitor(i)
        name = (mon.get_model() or '') + ' ' + (mon.get_manufacturer() or '')
        # GDK doesn't expose connector names directly; use plug name via get_model
        # which on Wayland is typically the connector (e.g. "HDMI-A-1", "eDP-1").
        plug = (mon.get_model() or '').upper()
        if plug.startswith(('HDMI', 'DP-', 'DISPLAYPORT')):
            external_idx = i
            break
        if plug.startswith('EDP') or plug.startswith('LVDS'):
            internal_idx = i
    return external_idx if external_idx is not None else internal_idx


def build_ui(greeter):
    css = Gtk.CssProvider()
    css.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    win = Gtk.Window()
    win.set_decorated(False)
    win.fullscreen_on_monitor(Gdk.Screen.get_default(), _pick_monitor())

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.set_halign(Gtk.Align.CENTER)
    box.set_valign(Gtk.Align.CENTER)

    headline = Gtk.Label(label='Enter Password')
    headline.get_style_context().add_class('headline')

    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char('*')
    entry.set_alignment(0.5)
    entry.set_has_frame(False)
    entry.set_width_chars(20)
    entry.set_max_width_chars(20)
    entry.get_style_context().add_class('password')

    def on_activate(_e):
        password = entry.get_text()
        entry.set_text('')
        if greeter.submit(password):
            Gtk.main_quit()
        else:
            entry.grab_focus()

    entry.connect('activate', on_activate)

    box.pack_start(headline, False, False, 0)
    box.pack_start(entry, False, False, 0)
    win.add(box)

    # Smoke-test escape hatch: when running outside greetd (no socket),
    # Escape quits so we can iterate on the visuals.
    if not os.environ.get('GREETD_SOCK'):
        win.connect('key-press-event', lambda _w, e:
            Gtk.main_quit() if e.keyval == Gdk.KEY_Escape else None)

    win.connect('destroy', lambda *_: Gtk.main_quit())
    win.show_all()
    entry.grab_focus()
    return win


def main():
    greeter = Greeter()
    build_ui(greeter)
    Gtk.main()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if os.environ.get('GREETD_SOCK'):
            os.execvp('/usr/bin/agreety', ['agreety', '--cmd', 'Hyprland'])
        else:
            raise
