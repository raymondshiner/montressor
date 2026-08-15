"""Shared layout language for the two `tower` popups (Minecraft + Torrenting).

They are siblings by design: same width, same header block, same section/row
grammar, same button treatment. Anything that must match between them lives
here so it cannot drift.
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

WIDTH = 330
POPUP_WIDTH = WIDTH + 16  # + .popup-inner CSS margin*2

OK = '#A8FF60'
WARN = '#FFE66D'
BAD = '#EE5D43'
CY = '#00E8C6'
DIM = '#677691'
TEXT = '#D5CED9'

GLOW = {OK: '168, 255, 96', WARN: '255, 230, 109',
        BAD: '238, 93, 67', CY: '0, 232, 198', DIM: '103, 118, 145'}

# {glow} is the state colour of the header icon — the popup's outline and halo
# always report the same thing the icon does.
CSS_TEMPLATE = """
window {{ background: transparent; }}
.popup-inner {{
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 10px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 24px 28px rgba(0, 0, 0, 0.8),
        0 0 0 1px rgba({glow}, 0.45),
        0 0 22px rgba({glow}, 0.38);
}}
.hdr-icon {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 22px;
    color: {state};
    margin-right: 10px;
}}
.hdr-state {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    font-weight: bold;
    color: {state};
    letter-spacing: 1px;
}}
.hdr-sub {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    color: #677691;
    margin-top: 2px;
}}
.section {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
    font-weight: bold;
    color: #677691;
    letter-spacing: 1.5px;
    margin-top: 12px;
    margin-bottom: 3px;
}}
.row-key {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    color: #677691;
}}
.row-val {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    color: #D5CED9;
}}
.v-ok   {{ color: #A8FF60; }}
.v-warn {{ color: #FFE66D; }}
.v-bad  {{ color: #EE5D43; font-weight: bold; }}
.v-cy   {{ color: #00E8C6; }}
.v-dim  {{ color: #677691; }}
.divider {{
    background-color: #2A2D3A;
    min-height: 1px;
    margin-top: 14px;
}}
.hint {{
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
    color: #677691;
    margin-top: 8px;
}}
.btn {{
    background: transparent;
    background-image: none;
    color: #677691;
    border: 1px solid #2A2D3A;
    border-radius: 4px;
    padding: 5px 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none;
    text-shadow: none;
}}
.btn:hover {{
    background-color: #2A2D3A;
    color: #D5CED9;
    border-color: #3A3D4A;
}}
.btn-open:hover {{
    color: #00E8C6;
    border-color: rgba(0, 232, 198, 0.5);
}}
/* Anything that stops a service or cuts the tunnel. Sits apart from the benign
   row and must be clicked twice — the first click only arms it. */
.btn-danger {{
    color: #EE5D43;
    border-color: rgba(238, 93, 67, 0.35);
}}
.btn-danger:hover {{
    background-color: rgba(238, 93, 67, 0.12);
    color: #EE5D43;
    border-color: rgba(238, 93, 67, 0.7);
}}
.btn-armed {{
    background-color: #EE5D43;
    color: #1C1E26;
    border-color: #EE5D43;
    font-weight: bold;
}}
.btn-armed:hover {{
    background-color: #EE5D43;
    color: #1C1E26;
}}
"""


def header(icon, state_text, sub_text, color):
    """Icon + state word + one muted subline. Returns (box, sub_label)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    ico = Gtk.Label(label=icon)
    ico.get_style_context().add_class('hdr-icon')
    st = Gtk.Label(label=state_text)
    st.get_style_context().add_class('hdr-state')
    st.set_xalign(0)
    top.pack_start(ico, False, False, 0)
    top.pack_start(st, False, False, 0)
    box.pack_start(top, False, False, 0)

    sub = Gtk.Label(label=sub_text)
    sub.get_style_context().add_class('hdr-sub')
    sub.set_xalign(0)
    sub.set_line_wrap(True)
    sub.set_max_width_chars(44)
    box.pack_start(sub, False, False, 0)
    return box, sub


def section(text):
    lbl = Gtk.Label(label=text.upper())
    lbl.get_style_context().add_class('section')
    lbl.set_xalign(0)
    return lbl


def row(key, value, tone=None):
    """key on the left (muted), value right-aligned, optionally state-toned."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    k = Gtk.Label(label=key)
    k.get_style_context().add_class('row-key')
    k.set_xalign(0)
    k.set_size_request(96, -1)
    v = Gtk.Label(label=str(value))
    v.get_style_context().add_class('row-val')
    if tone:
        v.get_style_context().add_class(tone)
    v.set_xalign(1)
    v.set_line_wrap(True)
    v.set_max_width_chars(32)
    v.set_justify(Gtk.Justification.RIGHT)
    box.pack_start(k, False, False, 0)
    box.pack_end(v, True, True, 0)
    return box


def divider():
    d = Gtk.Box()
    d.get_style_context().add_class('divider')
    return d


def button(label, *classes):
    b = Gtk.Button(label=label)
    ctx = b.get_style_context()
    ctx.add_class('btn')
    for c in classes:
        ctx.add_class(c)
    return b
