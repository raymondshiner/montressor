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

PID_FILE = '/tmp/wifi-popup.pid'
POPUP_WIDTH = 360 + 16


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


def _signal_glyph(strength):
    try:
        s = int(strength)
    except (TypeError, ValueError):
        return '󰤯'
    if s >= 75: return '󰤨'
    if s >= 50: return '󰤥'
    if s >= 25: return '󰤢'
    if s > 0:   return '󰤟'
    return '󰤯'


def _signal_color_class(strength):
    try:
        s = int(strength)
    except (TypeError, ValueError):
        return 'sig-weak'
    if s >= 60: return 'sig-good'
    if s >= 35: return 'sig-mid'
    return 'sig-weak'


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
.net-row {
    background-color: rgba(42, 45, 58, 0.6);
    border-radius: 6px;
    padding: 8px 10px;
    margin-top: 6px;
}
.net-row.active {
    background-color: rgba(0, 232, 198, 0.10);
}
.net-glyph {
    font-family: "JetBrainsMono Nerd Font";
    font-size: 18px;
    margin-right: 10px;
}
.net-glyph.sig-good   { color: #A8FF60; }
.net-glyph.sig-mid    { color: #FFE66D; }
.net-glyph.sig-weak   { color: #EE5D43; }
.net-glyph.active     { color: #00E8C6; }
.net-name {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    font-weight: bold;
}
.net-meta {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.meta-active {
    color: #00E8C6;
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
.act-btn.forget {
    color: #B084EB;
    border-color: #B084EB;
}
.act-btn.forget:hover {
    background-color: rgba(176, 132, 235, 0.10);
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
.section-label {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
    margin-top: 10px;
    margin-bottom: 2px;
}
.pw-row {
    background-color: rgba(28, 30, 38, 0.95);
    border-radius: 6px;
    padding: 8px 10px;
    margin-top: 6px;
}
.pw-entry {
    background-color: rgba(42, 45, 58, 0.8);
    color: #D5CED9;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
}
.pw-entry:focus {
    border-color: #00E8C6;
}
.status {
    color: #FFE66D;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
    margin-top: 4px;
}
.status.err {
    color: #EE5D43;
}
.status.ok {
    color: #A8FF60;
}
scrolledwindow undershoot,
scrolledwindow overshoot { background-image: none; }
"""


def nmcli(*args, timeout=4):
    try:
        return subprocess.check_output(['nmcli', *args], text=True, timeout=timeout,
                                       stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        return e.output or ''
    except Exception:
        return ''


def get_radio():
    out = nmcli('-t', 'radio', 'wifi').strip()
    return out == 'enabled'


def set_radio(on):
    subprocess.Popen(['nmcli', 'radio', 'wifi', 'on' if on else 'off'],
                     start_new_session=True)


def get_wifi_device():
    for line in nmcli('-t', '-f', 'DEVICE,TYPE,STATE', 'device').splitlines():
        parts = line.split(':')
        if len(parts) >= 2 and parts[1] == 'wifi':
            return parts[0]
    return None


def _split_nmcli_terse(line):
    """nmcli -t escapes colons in field values as '\\:'. Split safely."""
    out, cur, i = [], [], 0
    while i < len(line):
        c = line[i]
        if c == '\\' and i + 1 < len(line):
            cur.append(line[i + 1])
            i += 2
        elif c == ':':
            out.append(''.join(cur))
            cur = []
            i += 1
        else:
            cur.append(c)
            i += 1
    out.append(''.join(cur))
    return out


def get_saved_connections():
    """Return {ssid_or_id: connection_name} for saved wifi profiles."""
    saved = {}
    out = nmcli('-t', '-f', 'NAME,TYPE', 'connection', 'show')
    for line in out.splitlines():
        parts = _split_nmcli_terse(line)
        if len(parts) >= 2 and parts[1] == '802-11-wireless':
            saved[parts[0]] = parts[0]
    return saved


def scan_networks():
    """Trigger a rescan and return list of dicts."""
    # Async rescan request — non-blocking.
    subprocess.Popen(['nmcli', 'device', 'wifi', 'rescan'],
                     start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = nmcli('-t', '-f', 'IN-USE,BSSID,SSID,SIGNAL,SECURITY', 'device', 'wifi',
                'list', '--rescan', 'no')
    nets = []
    seen = set()
    for line in out.splitlines():
        parts = _split_nmcli_terse(line)
        if len(parts) < 5:
            continue
        in_use, bssid, ssid, signal, security = parts[0], parts[1], parts[2], parts[3], parts[4]
        if not ssid or ssid in seen:
            # Keep strongest entry of each SSID (the list is already sorted by signal desc).
            continue
        seen.add(ssid)
        nets.append({
            'ssid': ssid,
            'bssid': bssid,
            'signal': signal,
            'security': security or '',
            'active': in_use.strip() == '*',
        })
    nets.sort(key=lambda n: (not n['active'], -int(n['signal'] or 0)))
    return nets


def connect_saved(ssid):
    return subprocess.Popen(['nmcli', 'connection', 'up', 'id', ssid],
                            start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_open(ssid):
    return subprocess.Popen(['nmcli', 'device', 'wifi', 'connect', ssid],
                            start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def connect_with_password(ssid, password):
    """Blocking: returns (ok, message)."""
    try:
        r = subprocess.run(['nmcli', 'device', 'wifi', 'connect', ssid,
                            'password', password],
                           capture_output=True, text=True, timeout=30)
        ok = r.returncode == 0
        msg = (r.stdout + r.stderr).strip().splitlines()
        return ok, (msg[-1] if msg else ('Connected' if ok else 'Failed'))
    except subprocess.TimeoutExpired:
        return False, 'Timed out'
    except Exception as e:
        return False, str(e)


def disconnect_active():
    dev = get_wifi_device()
    if not dev:
        return
    subprocess.Popen(['nmcli', 'device', 'disconnect', dev],
                     start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def forget(ssid):
    subprocess.Popen(['nmcli', 'connection', 'delete', 'id', ssid],
                     start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class WifiPopup(Gtk.Window):
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
        self._root.set_size_request(360, -1)
        blocker.add(self._root)

        self._status_text = ''
        self._status_kind = ''  # '', 'ok', 'err'
        self._pw_target = None   # ssid awaiting password
        self._render()
        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

    def _render(self):
        for child in self._root.get_children():
            self._root.remove(child)

        powered = get_radio()
        saved = get_saved_connections() if powered else {}
        nets = scan_networks() if powered else []

        # Header
        hdr_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr_row.set_margin_bottom(4)
        hdr = Gtk.Label(label='󰖩  Wi-Fi')
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

        if not powered:
            self._add_empty('Wi-Fi is off')
        elif not nets:
            self._add_empty('No networks in range')
        else:
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(min(420, 56 * max(1, len(nets))))
            scroller.set_max_content_height(420)
            scroller.set_propagate_natural_height(True)
            list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            for n in nets:
                list_box.pack_start(self._row(n, saved), False, False, 0)
                if self._pw_target == n['ssid']:
                    list_box.pack_start(self._password_row(n['ssid']), False, False, 0)
            scroller.add(list_box)
            self._root.pack_start(scroller, True, True, 0)

        if self._status_text:
            s = Gtk.Label(label=self._status_text)
            ctx = s.get_style_context()
            ctx.add_class('status')
            if self._status_kind:
                ctx.add_class(self._status_kind)
            s.set_xalign(0)
            self._root.pack_start(s, False, False, 0)

        # Refresh
        ref = Gtk.Button(label='󰑐  Rescan')
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

    def _row(self, n, saved):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        ctx_row = row.get_style_context()
        ctx_row.add_class('net-row')
        if n['active']:
            ctx_row.add_class('active')

        glyph = Gtk.Label(label=_signal_glyph(n['signal']))
        gctx = glyph.get_style_context()
        gctx.add_class('net-glyph')
        if n['active']:
            gctx.add_class('active')
        else:
            gctx.add_class(_signal_color_class(n['signal']))
        row.pack_start(glyph, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        info.set_hexpand(True)
        name = Gtk.Label(label=n['ssid'])
        name.get_style_context().add_class('net-name')
        name.set_xalign(0)
        name.set_ellipsize(3)
        info.pack_start(name, False, False, 0)

        sec = n['security'].strip() or 'Open'
        is_saved = n['ssid'] in saved
        meta_bits = [f"{n['signal']}%", sec]
        if n['active']:
            meta_bits.append('connected')
        elif is_saved:
            meta_bits.append('saved')
        meta = Gtk.Label(label='  ·  '.join(meta_bits))
        mctx = meta.get_style_context()
        mctx.add_class('net-meta')
        if n['active']:
            mctx.add_class('meta-active')
        meta.set_xalign(0)
        info.pack_start(meta, False, False, 0)
        row.pack_start(info, True, True, 0)

        # Action button(s)
        if n['active']:
            act = Gtk.Button(label='󰖪  Disconnect')
            act.get_style_context().add_class('act-btn')
            act.get_style_context().add_class('disconnect')
            act.connect('clicked', lambda _b: self._do_disconnect())
            _set_pointer_cursor(act)
            row.pack_start(act, False, False, 0)
        else:
            act = Gtk.Button(label='󰖩  Connect')
            act.get_style_context().add_class('act-btn')
            act.connect('clicked', lambda _b, ssid=n['ssid'], sec=sec, is_saved=is_saved:
                        self._on_connect(ssid, sec, is_saved))
            _set_pointer_cursor(act)
            row.pack_start(act, False, False, 0)
            if is_saved:
                fg = Gtk.Button(label='󰗨')
                fg.set_tooltip_text('Forget')
                fg.get_style_context().add_class('act-btn')
                fg.get_style_context().add_class('forget')
                fg.connect('clicked', lambda _b, ssid=n['ssid']: self._on_forget(ssid))
                _set_pointer_cursor(fg)
                row.pack_start(fg, False, False, 0)

        return row

    def _password_row(self, ssid):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class('pw-row')

        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_placeholder_text(f'Password for {ssid}')
        entry.get_style_context().add_class('pw-entry')
        entry.set_hexpand(True)
        entry.connect('activate', lambda _e: self._submit_password(ssid, entry.get_text()))
        box.pack_start(entry, True, True, 0)

        go = Gtk.Button(label='󰒃  Join')
        go.get_style_context().add_class('act-btn')
        go.connect('clicked', lambda _b: self._submit_password(ssid, entry.get_text()))
        _set_pointer_cursor(go)
        box.pack_start(go, False, False, 0)

        cancel = Gtk.Button(label='✕')
        cancel.get_style_context().add_class('act-btn')
        cancel.get_style_context().add_class('forget')
        cancel.connect('clicked', lambda _b: self._cancel_password())
        _set_pointer_cursor(cancel)
        box.pack_start(cancel, False, False, 0)

        GLib.timeout_add(50, lambda: (entry.grab_focus(), False)[1])
        return box

    # --- Actions ------------------------------------------------------

    def _refresh(self):
        self._render()
        self.show_all()

    def _set_status(self, text, kind=''):
        self._status_text = text
        self._status_kind = kind

    def _on_power(self, _btn, was_on):
        set_radio(not was_on)
        self._pw_target = None
        self._set_status('')
        GLib.timeout_add(900, lambda: (self._refresh(), False)[1])

    def _on_connect(self, ssid, sec, is_saved):
        if is_saved or sec == 'Open' or not sec:
            self._pw_target = None
            self._set_status(f'Connecting to {ssid}…')
            if is_saved:
                connect_saved(ssid)
            else:
                connect_open(ssid)
            GLib.timeout_add(2500, lambda: (self._refresh_and_clear(), False)[1])
            self._refresh()
        else:
            self._pw_target = ssid
            self._set_status('')
            self._refresh()

    def _submit_password(self, ssid, password):
        if not password:
            self._set_status('Password required', 'err')
            self._refresh()
            return
        self._set_status(f'Connecting to {ssid}…')
        self._refresh()

        def _do():
            ok, msg = connect_with_password(ssid, password)
            self._pw_target = None if ok else ssid
            self._set_status(msg, 'ok' if ok else 'err')
            self._refresh()
            return False
        GLib.idle_add(_do)

    def _cancel_password(self):
        self._pw_target = None
        self._set_status('')
        self._refresh()

    def _do_disconnect(self):
        disconnect_active()
        self._set_status('Disconnecting…')
        self._refresh()
        GLib.timeout_add(1500, lambda: (self._refresh_and_clear(), False)[1])

    def _on_forget(self, ssid):
        forget(ssid)
        self._set_status(f'Forgot {ssid}', 'ok')
        GLib.timeout_add(900, lambda: (self._refresh_and_clear(), False)[1])

    def _refresh_and_clear(self):
        self._set_status('')
        self._refresh()

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            if self._pw_target:
                self._cancel_password()
            else:
                self.destroy()


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, WifiPopup)
