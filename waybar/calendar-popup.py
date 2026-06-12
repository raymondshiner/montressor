#!/usr/bin/env python3
"""Calendar popup: month grid with event indicators + scrollable today timeline.

Events are pulled from one or more Google Calendar "Secret address in iCal
format" URLs listed in ~/.config/calendar-popup/feeds.conf (one per line).
Results are cached to /tmp/calendar-popup-cache.json for 5 min so the popup
opens instantly; a background refresh updates the cache on each open.
"""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import subprocess
import threading
import datetime
import calendar
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_lib

PID_FILE = '/tmp/calendar-popup.pid'
CACHE_FILE = '/tmp/calendar-popup-cache.json'
CACHE_TTL = 300  # seconds
FEEDS_FILE = os.path.expanduser('~/.config/calendar-popup/feeds.conf')

# Layout
MONTH_W = 440
TIMELINE_W = 240
POPUP_INNER_W = MONTH_W + TIMELINE_W + 16  # +gap
POPUP_WIDTH = POPUP_INNER_W + 32 + 16       # padding*2 + CSS margin*2
DAY_CELL_H = 56
TIMELINE_ROW_H = 56

# Andromeda
BG       = '#1C1E26'
BG_ALT   = '#23262E'
TEXT     = '#D5CED9'
MUTED    = '#677691'
CYAN     = '#00E8C6'
GREEN    = '#A8FF60'
YELLOW   = '#FFE66D'
RED      = '#EE5D43'
PURPLE   = '#B084EB'

# Cycle through these for distinct per-calendar coloring
EVENT_PALETTE = [PURPLE, CYAN, GREEN, YELLOW, '#7AA7FF', '#FFA17A']

CSS = """
window { background: transparent; }
.popup-inner {
    background-color: rgba(28, 30, 38, 0.97);
    border-radius: 12px;
    margin: 8px;
    padding: 16px;
    box-shadow:
        0 28px 28px rgba(0, 0, 0, 0.8),
        0 20px 20px rgba(176, 132, 235, 0.40),
        0 40px 40px rgba(176, 132, 235, 0.18);
}
.h-date {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 15px;
    font-weight: bold;
}
.h-sub {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
}
.month-title {
    color: #B084EB;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    font-weight: bold;
}
.nav-btn {
    background: transparent; background-image: none;
    color: #677691;
    border: none;
    border-radius: 4px;
    padding: 2px 8px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 14px;
    box-shadow: none; text-shadow: none;
    min-width: 0; min-height: 0;
}
.nav-btn:hover { color: #D5CED9; background-color: rgba(176, 132, 235, 0.15); }
.dow {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.day-cell {
    background-color: transparent;
    border-radius: 6px;
    padding: 3px 4px;
}
.day-cell:hover { background-color: rgba(176, 132, 235, 0.10); }
.day-cell.other-month .day-num { color: #3A3D4A; }
.day-cell.today { background-color: rgba(176, 132, 235, 0.18); }
.day-cell.selected {
    background-color: #B084EB;
}
.day-cell.selected .day-num,
.day-cell.selected .more-pill {
    color: #1C1E26;
}
.day-num {
    color: #D5CED9;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 12px;
    font-weight: bold;
}
.evt-bar {
    color: #1C1E26;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 9px;
    border-radius: 3px;
    padding: 1px 4px;
    margin-top: 1px;
}
.more-pill {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 9px;
    padding: 0 4px;
}
.timeline-title {
    color: #00E8C6;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 13px;
    font-weight: bold;
}
.timeline-sub {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.tl-scroll {
    background-color: rgba(35, 38, 46, 0.6);
    border-radius: 8px;
}
.tl-scroll undershoot, .tl-scroll overshoot { background: none; }
scrollbar slider {
    background-color: #3A3D4A;
    border-radius: 6px;
    min-width: 4px;
}
scrollbar slider:hover { background-color: #677691; }
.status-lbl {
    color: #677691;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 10px;
}
.open-btn {
    background: transparent; background-image: none;
    color: #B084EB;
    border: 1px solid #B084EB;
    border-radius: 6px;
    padding: 6px 14px;
    font-family: "JetBrainsMono Nerd Font";
    font-size: 11px;
    box-shadow: none; text-shadow: none;
}
.open-btn:hover { background-color: #B084EB; color: #1C1E26; }
"""


# ---------- Event store ----------

def _read_feeds():
    if not os.path.exists(FEEDS_FILE):
        return []
    out = []
    for ln in open(FEEDS_FILE):
        ln = ln.strip()
        if ln and not ln.startswith('#'):
            out.append(ln)
    return out


def _color_for_feed(idx):
    return EVENT_PALETTE[idx % len(EVENT_PALETTE)]


def _to_local_dt(val):
    """icalendar may give us datetime (tz-aware/naive) or date. Return a
    timezone-aware datetime in the local zone, plus an `all_day` flag."""
    if isinstance(val, datetime.datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=datetime.timezone.utc)
        return val.astimezone(), False
    if isinstance(val, datetime.date):
        return datetime.datetime.combine(
            val, datetime.time(0, 0), tzinfo=datetime.timezone.utc
        ).astimezone(), True
    return None, False


def fetch_events(window_days=45):
    """Fetch & expand events from all feeds. Returns a list of dicts:
        {title, start_iso, end_iso, all_day, color}
    Only events overlapping [now - 7d, now + window_days] are kept.
    Recurring events are expanded via icalendar.recurrence handling.
    """
    try:
        import requests
        from icalendar import Calendar
        try:
            from recurring_ical_events import of as recurring_of
        except ImportError:
            recurring_of = None
    except Exception as e:
        return {'error': f'missing deps: {e}', 'events': []}

    feeds = _read_feeds()
    if not feeds:
        return {'error': 'no feeds configured', 'events': []}

    now = datetime.datetime.now().astimezone()
    win_start = now - datetime.timedelta(days=7)
    win_end   = now + datetime.timedelta(days=window_days)
    out = []
    err = None

    for idx, url in enumerate(feeds):
        color = _color_for_feed(idx)
        try:
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            cal_obj = Calendar.from_ical(r.text)
        except Exception as e:
            err = f'feed {idx+1}: {e.__class__.__name__}'
            continue

        if recurring_of is not None:
            try:
                events = recurring_of(cal_obj).between(win_start, win_end)
            except Exception:
                events = [c for c in cal_obj.walk('VEVENT')]
        else:
            events = [c for c in cal_obj.walk('VEVENT')]

        for ev in events:
            try:
                s, all_day = _to_local_dt(ev.get('DTSTART').dt)
                end = ev.get('DTEND')
                e, _ = _to_local_dt(end.dt) if end else (s + datetime.timedelta(hours=1), False)
                if e <= win_start or s >= win_end:
                    continue
                out.append({
                    'title': str(ev.get('SUMMARY') or '(no title)'),
                    'start_iso': s.isoformat(),
                    'end_iso': e.isoformat(),
                    'all_day': bool(all_day),
                    'color': color,
                })
            except Exception:
                continue

    out.sort(key=lambda x: x['start_iso'])
    return {'error': err, 'events': out, 'fetched_at': now.isoformat()}


def load_cache():
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        return data
    except Exception:
        return None


def save_cache(data):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


def cache_is_fresh(data):
    if not data or 'fetched_at' not in data:
        return False
    try:
        t = datetime.datetime.fromisoformat(data['fetched_at'])
        return (datetime.datetime.now().astimezone() - t).total_seconds() < CACHE_TTL
    except Exception:
        return False


# ---------- Widgets ----------

class MonthGrid(Gtk.Box):
    """6-week month view. Each cell shows the day number + up to 3 event bars."""
    def __init__(self, on_day_selected):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._on_day_selected = on_day_selected
        self.events_by_day = {}     # date -> list of event dicts
        self.today = datetime.date.today()
        self.view = self.today.replace(day=1)
        self.selected = self.today

        # Header: < Month Year >
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._prev = Gtk.Button(label='‹')
        self._prev.get_style_context().add_class('nav-btn')
        self._prev.connect('clicked', lambda *_: self._shift(-1))
        self._next = Gtk.Button(label='›')
        self._next.get_style_context().add_class('nav-btn')
        self._next.connect('clicked', lambda *_: self._shift(1))
        self._title = Gtk.Label()
        self._title.get_style_context().add_class('month-title')
        self._title.set_xalign(0.5)
        self._title.set_hexpand(True)
        hdr.pack_start(self._prev, False, False, 0)
        hdr.pack_start(self._title, True, True, 0)
        hdr.pack_start(self._next, False, False, 0)
        self.pack_start(hdr, False, False, 0)

        # Day-of-week strip
        dow_row = Gtk.Grid()
        dow_row.set_column_homogeneous(True)
        for i, d in enumerate(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']):
            lbl = Gtk.Label(label=d)
            lbl.get_style_context().add_class('dow')
            lbl.set_xalign(0.5)
            dow_row.attach(lbl, i, 0, 1, 1)
        self.pack_start(dow_row, False, False, 0)

        # 6x7 grid of cells
        self._grid = Gtk.Grid()
        self._grid.set_column_homogeneous(True)
        self._grid.set_row_homogeneous(True)
        self._grid.set_row_spacing(2)
        self._grid.set_column_spacing(2)
        self._grid.set_size_request(MONTH_W, DAY_CELL_H * 6)
        self.pack_start(self._grid, True, True, 0)

        self._cells = []  # list of (event_box, container_box, date)
        self._build_cells()
        self._render()

    def _shift(self, months):
        m = self.view.month + months
        y = self.view.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        self.view = datetime.date(y, m, 1)
        self._render()

    def _build_cells(self):
        for r in range(6):
            for c in range(7):
                eb = Gtk.EventBox()
                eb.get_style_context().add_class('day-cell')
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                eb.add(inner)
                eb.connect('button-press-event', self._on_cell_click, r, c)
                self._grid.attach(eb, c, r, 1, 1)
                self._cells.append((eb, inner, None))

    def _on_cell_click(self, _w, _ev, r, c):
        d = self._cells[r * 7 + c][2]
        if d is None:
            return True
        self.selected = d
        self._render()
        self._on_day_selected(d)
        return True

    def set_events(self, events):
        """events: full list across all dates. Bin by local date."""
        by_day = {}
        for e in events:
            try:
                s = datetime.datetime.fromisoformat(e['start_iso']).date()
                by_day.setdefault(s, []).append(e)
            except Exception:
                continue
        for k in by_day:
            by_day[k].sort(key=lambda x: x['start_iso'])
        self.events_by_day = by_day
        self._render()

    def _render(self):
        self._title.set_text(self.view.strftime('%B %Y'))
        first = self.view
        # Find Sunday on/before first
        start_offset = (first.weekday() + 1) % 7  # Mon=0 → +1; Sun=6 → 0
        grid_start = first - datetime.timedelta(days=start_offset)

        for i, (eb, inner, _) in enumerate(self._cells):
            d = grid_start + datetime.timedelta(days=i)
            # rebuild cell
            for ch in inner.get_children():
                inner.remove(ch)

            ctx = eb.get_style_context()
            for cls in ('other-month', 'today', 'selected'):
                ctx.remove_class(cls)
            if d.month != self.view.month:
                ctx.add_class('other-month')
            if d == self.today:
                ctx.add_class('today')
            if d == self.selected:
                ctx.add_class('selected')

            num = Gtk.Label(label=str(d.day))
            num.get_style_context().add_class('day-num')
            num.set_xalign(0)
            inner.pack_start(num, False, False, 0)

            evs = self.events_by_day.get(d, [])
            shown = evs[:3]
            for ev in shown:
                bar = Gtk.Label()
                title = ev['title'][:18]
                if not ev['all_day']:
                    try:
                        st = datetime.datetime.fromisoformat(ev['start_iso'])
                        title = f"{st.strftime('%-I%p').lower().rstrip('m')} {title}"[:22]
                    except Exception:
                        pass
                bar.set_text(title)
                bar.set_xalign(0)
                bar.set_ellipsize(Pango.EllipsizeMode.END)
                bar.get_style_context().add_class('evt-bar')
                # Inline color: use Pango markup so bg matches the calendar
                color = ev['color']
                bar.set_markup(
                    f'<span background="{color}" foreground="#1C1E26"> {GLib.markup_escape_text(title)} </span>'
                )
                inner.pack_start(bar, False, False, 0)

            if len(evs) > 3:
                more = Gtk.Label(label=f'+{len(evs) - 3} more')
                more.get_style_context().add_class('more-pill')
                more.set_xalign(0)
                inner.pack_start(more, False, False, 0)

            self._cells[i] = (eb, inner, d)
        self.show_all()


class DayTimeline(Gtk.DrawingArea):
    """24-hour vertical timeline. Hour labels + ticks at :15/:30/:45. Events
    rendered as colored rounded blocks. The current time gets a cyan line."""
    def __init__(self):
        super().__init__()
        self.events = []
        self.day = datetime.date.today()
        self.set_size_request(TIMELINE_W, 24 * TIMELINE_ROW_H)
        self.connect('draw', self._draw)
        # Repaint the now-line every minute
        GLib.timeout_add_seconds(60, lambda: (self.queue_draw() or True))

    def set_day(self, day, events):
        self.day = day
        # Filter events on this day (in local tz)
        out = []
        for e in events:
            try:
                s = datetime.datetime.fromisoformat(e['start_iso'])
                en = datetime.datetime.fromisoformat(e['end_iso'])
            except Exception:
                continue
            if s.date() <= day <= en.date() or s.date() == day:
                out.append({
                    'title': e['title'],
                    'start': s,
                    'end': en,
                    'all_day': e['all_day'],
                    'color': e['color'],
                })
        self.events = out
        self.queue_draw()

    def _hex(self, h):
        h = h.lstrip('#')
        return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)

    def _draw(self, _w, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        gutter = 50  # left strip for hour labels

        # Background
        cr.set_source_rgba(*self._hex(BG_ALT), 0.7)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # Gutter divider
        cr.set_source_rgba(*self._hex(MUTED), 0.25)
        cr.set_line_width(1)
        cr.move_to(gutter + 0.5, 0)
        cr.line_to(gutter + 0.5, h)
        cr.stroke()

        # Hour rows
        for hr in range(24):
            y = hr * TIMELINE_ROW_H
            # Hour line
            cr.set_source_rgba(*self._hex(MUTED), 0.25)
            cr.set_line_width(1)
            cr.move_to(gutter, y + 0.5)
            cr.line_to(w, y + 0.5)
            cr.stroke()
            # Hour label
            label = datetime.time(hr).strftime('%-I %p') if hr else '12 AM'
            cr.set_source_rgba(*self._hex(TEXT), 0.85)
            cr.select_font_face('JetBrainsMono Nerd Font',
                                 0, 1)  # normal, bold
            cr.set_font_size(10)
            ext = cr.text_extents(label)
            cr.move_to(gutter - 6 - ext.width, y + 12)
            cr.show_text(label)
            # Sub-hour ticks
            for frac, length in ((0.25, 6), (0.5, 12), (0.75, 6)):
                ty = y + TIMELINE_ROW_H * frac
                cr.set_source_rgba(*self._hex(MUTED), 0.35)
                cr.set_line_width(1)
                cr.move_to(gutter + 1, ty + 0.5)
                cr.line_to(gutter + 1 + length, ty + 0.5)
                cr.stroke()

        # All-day strip at top? Render as compact rows in hour 0 area
        events_intraday = [e for e in self.events if not e['all_day']]
        events_allday = [e for e in self.events if e['all_day']]

        # Event blocks
        evt_x0 = gutter + 6
        evt_w  = w - evt_x0 - 6
        for ev in events_intraday:
            day_start = datetime.datetime.combine(
                self.day, datetime.time(0, 0)
            ).astimezone()
            s = ev['start'].astimezone()
            e = ev['end'].astimezone()
            mins_from_start = max(0, (s - day_start).total_seconds() / 60)
            mins_dur = max(15, (e - s).total_seconds() / 60)
            # Clip to day
            mins_from_start = min(mins_from_start, 24 * 60 - 10)
            mins_dur = min(mins_dur, 24 * 60 - mins_from_start)
            y = mins_from_start * TIMELINE_ROW_H / 60
            bh = mins_dur * TIMELINE_ROW_H / 60

            # Filled block w/ transparency + solid left bar
            r, g, b = self._hex(ev['color'])
            cr.set_source_rgba(r, g, b, 0.25)
            cr.rectangle(evt_x0, y + 1, evt_w, bh - 2)
            cr.fill()
            cr.set_source_rgba(r, g, b, 1.0)
            cr.rectangle(evt_x0, y + 1, 3, bh - 2)
            cr.fill()

            # Title text
            cr.set_source_rgba(*self._hex(TEXT), 0.95)
            cr.select_font_face('JetBrainsMono Nerd Font', 0, 0)
            cr.set_font_size(10)
            time_str = s.strftime('%-I:%M') if s.minute else s.strftime('%-I')
            title = ev['title']
            # Clip text to bh
            cr.move_to(evt_x0 + 8, y + 12)
            cr.show_text(time_str + '  ' + title[:24])
            if bh > 26:
                cr.set_source_rgba(*self._hex(MUTED), 0.95)
                cr.set_font_size(9)
                cr.move_to(evt_x0 + 8, y + 24)
                cr.show_text(
                    s.strftime('%-I:%M %p').lower() + ' – ' +
                    e.strftime('%-I:%M %p').lower()
                )

        # All-day events as pinned banners at top of timeline
        for i, ev in enumerate(events_allday[:2]):
            r, g, b = self._hex(ev['color'])
            cr.set_source_rgba(r, g, b, 0.4)
            cr.rectangle(evt_x0, 4 + i * 18, evt_w, 16)
            cr.fill()
            cr.set_source_rgba(*self._hex(BG), 1.0)
            cr.select_font_face('JetBrainsMono Nerd Font', 0, 1)
            cr.set_font_size(10)
            cr.move_to(evt_x0 + 6, 4 + i * 18 + 12)
            cr.show_text('all-day  ' + ev['title'][:20])

        # Now-line (only if viewing today)
        if self.day == datetime.date.today():
            now = datetime.datetime.now()
            mins = now.hour * 60 + now.minute
            ny = mins * TIMELINE_ROW_H / 60
            cr.set_source_rgba(*self._hex(CYAN), 1.0)
            cr.set_line_width(1.5)
            cr.move_to(gutter, ny + 0.5)
            cr.line_to(w, ny + 0.5)
            cr.stroke()
            cr.arc(gutter, ny, 3, 0, 6.283)
            cr.fill()


# ---------- Popup window ----------

class CalendarPopup(Gtk.Window):
    def __init__(self):
        super().__init__()
        popup_lib.setup_window(self)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        blocker = popup_lib.wrap_with_click_outside(self, POPUP_WIDTH, center=True)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.get_style_context().add_class('popup-inner')
        root.set_size_request(POPUP_INNER_W, -1)
        blocker.add(root)

        now = datetime.datetime.now()

        # ----- Top header -----
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        date_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        date_lbl = Gtk.Label(label='  ' + now.strftime('%A, %B %-d'))
        date_lbl.get_style_context().add_class('h-date')
        date_lbl.set_xalign(0)
        sub_lbl = Gtk.Label(label=now.strftime('%-I:%M %p  ·  Week %W  ·  %Y'))
        sub_lbl.get_style_context().add_class('h-sub')
        sub_lbl.set_xalign(0)
        date_box.pack_start(date_lbl, False, False, 0)
        date_box.pack_start(sub_lbl, False, False, 0)
        hdr.pack_start(date_box, True, True, 0)

        self._status = Gtk.Label(label='loading…')
        self._status.get_style_context().add_class('status-lbl')
        self._status.set_xalign(1)
        self._status.set_yalign(1)
        hdr.pack_start(self._status, False, False, 0)

        open_btn = Gtk.Button(label='Open Google Calendar')
        open_btn.get_style_context().add_class('open-btn')
        open_btn.connect('clicked', self._open_gcal)
        hdr.pack_start(open_btn, False, False, 0)
        root.pack_start(hdr, False, False, 0)

        # ----- Body: month grid + timeline -----
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        self._month = MonthGrid(on_day_selected=self._on_day_selected)
        self._month.set_size_request(MONTH_W, -1)
        body.pack_start(self._month, False, False, 0)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right.set_size_request(TIMELINE_W, -1)

        self._tl_title = Gtk.Label(label='Today')
        self._tl_title.get_style_context().add_class('timeline-title')
        self._tl_title.set_xalign(0)
        right.pack_start(self._tl_title, False, False, 0)

        self._tl_sub = Gtk.Label(label=now.strftime('%A, %b %-d'))
        self._tl_sub.get_style_context().add_class('timeline-sub')
        self._tl_sub.set_xalign(0)
        right.pack_start(self._tl_sub, False, False, 0)

        self._scroll = Gtk.ScrolledWindow()
        self._scroll.get_style_context().add_class('tl-scroll')
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_size_request(TIMELINE_W, 6 * TIMELINE_ROW_H + 24)
        self._timeline = DayTimeline()
        self._scroll.add(self._timeline)
        right.pack_start(self._scroll, True, True, 0)

        body.pack_start(right, False, False, 0)
        root.pack_start(body, True, True, 0)

        self.connect('key-press-event', self._on_key)
        self.show_all()
        self.present()

        # Initial data + scroll to current hour after layout
        self._load_initial()
        GLib.idle_add(self._scroll_to_now)

    def _on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.destroy()

    def _scroll_to_now(self):
        now = datetime.datetime.now()
        target = max(0, (now.hour - 1)) * TIMELINE_ROW_H
        adj = self._scroll.get_vadjustment()
        adj.set_value(min(adj.get_upper() - adj.get_page_size(), target))
        return False

    def _open_gcal(self, _btn):
        subprocess.Popen(
            ['xdg-open', 'https://calendar.google.com/'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.destroy()

    def _on_day_selected(self, day):
        self._tl_title.set_text('Today' if day == datetime.date.today() else 'Day')
        self._tl_sub.set_text(day.strftime('%A, %b %-d'))
        self._timeline.set_day(day, self._events)
        if day == datetime.date.today():
            GLib.idle_add(self._scroll_to_now)

    def _apply_events(self, data):
        self._events = data.get('events', [])
        self._month.set_events(self._events)
        self._timeline.set_day(self._month.selected, self._events)
        err = data.get('error')
        feeds = _read_feeds()
        if not feeds:
            self._status.set_text('add ICS URL to ~/.config/calendar-popup/feeds.conf')
        elif err:
            self._status.set_text(f'⚠ {err}')
        else:
            n = len(self._events)
            self._status.set_text(f'{n} events · {len(feeds)} cal{"s" if len(feeds) != 1 else ""}')

    def _load_initial(self):
        self._events = []
        cache = load_cache()
        if cache:
            self._apply_events(cache)
        if not _read_feeds():
            self._status.set_text('add ICS URL to ~/.config/calendar-popup/feeds.conf')
            return
        if cache_is_fresh(cache):
            return
        self._status.set_text('refreshing…')
        threading.Thread(target=self._bg_refresh, daemon=True).start()

    def _bg_refresh(self):
        data = fetch_events()
        if data.get('events') or not data.get('error'):
            save_cache(data)
        GLib.idle_add(self._apply_events, data)


if __name__ == '__main__':
    popup_lib.run_popup(PID_FILE, CalendarPopup)
