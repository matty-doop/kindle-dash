#!/usr/bin/env python3
"""Render a weather + calendar dashboard PNG for a Kindle Paperwhite 4 (1072x1448).

Config (environment variables):
  CAL_ICS_URLS   One or more calendar iCal (ICS) links, separated by commas or
                 newlines. Prefix a link with a short label and "|" to tag its
                 events on screen, e.g.  M|https://...ics, J|https://...ics
  LAT, LON       Location for weather (default: Grays Woods, Patton Township, PA).
  TZ_NAME        Time zone (default: America/New_York).
  OUT            Output path (default: out/dashboard.png).

Countdowns: start a calendar event's title with "*" (e.g. "*Thanksgiving") and it
gets a countdown chip until the day arrives.

Run with --mock to render sample data without network access.
"""
import datetime as dt
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

W, H = 1072, 1448
M = 56                      # outer margin
BLACK, DARK, MID, LIGHT, WHITE = 0, 25, 70, 170, 255

TZ = ZoneInfo(os.environ.get("TZ_NAME") or "America/New_York")
LAT = float(os.environ.get("LAT") or "40.8072")
LON = float(os.environ.get("LON") or "-77.9486")
FONT_DIR = Path(__file__).parent / "fonts"


def font(weight, size):
    return ImageFont.truetype(str(FONT_DIR / f"Inter-{weight}.otf"), size)


# ---------------------------------------------------------------- weather

WMO = {  # code -> (label, icon)
    0: ("Clear", "sun"), 1: ("Mostly clear", "sun"), 2: ("Partly cloudy", "partly"),
    3: ("Overcast", "cloud"), 45: ("Fog", "fog"), 48: ("Freezing fog", "fog"),
    51: ("Light drizzle", "rain"), 53: ("Drizzle", "rain"), 55: ("Heavy drizzle", "rain"),
    56: ("Freezing drizzle", "sleet"), 57: ("Freezing drizzle", "sleet"),
    61: ("Light rain", "rain"), 63: ("Rain", "rain"), 65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "sleet"), 67: ("Freezing rain", "sleet"),
    71: ("Light snow", "snow"), 73: ("Snow", "snow"), 75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"), 80: ("Showers", "rain"), 81: ("Showers", "rain"),
    82: ("Heavy showers", "rain"), 85: ("Snow showers", "snow"), 86: ("Snow showers", "snow"),
    95: ("Thunderstorms", "storm"), 96: ("Thunderstorms", "storm"), 99: ("Thunderstorms", "storm"),
}


def fetch_weather():
    import time
    last = None
    for attempt in range(4):          # the free API sometimes rejects shared CI IPs; retry
        try:
            return _fetch_weather_once()
        except Exception as e:
            last = e
            print(f"weather attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise last


def _fetch_weather_once():
    import requests
    r = requests.get("https://api.open-meteo.com/v1/forecast", timeout=20, params={
        "latitude": LAT, "longitude": LON, "timezone": str(TZ),
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,is_day",
        "hourly": "temperature_2m,precipitation_probability,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
        "forecast_days": 6,
    })
    r.raise_for_status()
    return r.json()


def fetch_alerts():
    """Active National Weather Service alerts for the dashboard's location."""
    import requests
    r = requests.get("https://api.weather.gov/alerts/active", timeout=20,
                     params={"point": f"{LAT:.4f},{LON:.4f}"},
                     headers={"User-Agent": "kindle-dash (github.com/matty-doop/kindle-dash)",
                              "Accept": "application/geo+json"})
    r.raise_for_status()
    rank = {"Extreme": 0, "Severe": 1, "Moderate": 2, "Minor": 3}
    out, seen = [], set()
    for f in r.json().get("features", []):
        p = f.get("properties", {})
        ev = p.get("event")
        if not ev or ev in seen or p.get("status", "Actual") != "Actual":
            continue
        seen.add(ev)
        until = p.get("ends") or p.get("expires")
        out.append({"event": ev, "severity": p.get("severity", ""),
                    "until": dt.datetime.fromisoformat(until).astimezone(TZ) if until else None})
    out.sort(key=lambda a: rank.get(a["severity"], 4))
    print(f"alerts: {len(out)}")
    return out


def moon_phase(day):
    """Approximate moon phase name for a date (good to within about a day)."""
    age = ((dt.datetime.combine(day, dt.time(12)) - dt.datetime(2000, 1, 6, 18, 14)).total_seconds()
           / 86400) % 29.530588853
    names = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous",
             "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"]
    return names[int((age / 29.530588853) * 8 + 0.5) % 8]


# --------------------------------------------------------------- calendar

def fetch_events(now, days=180):
    import requests
    import icalendar
    import recurring_ical_events

    urls = [u.strip() for u in os.environ.get("CAL_ICS_URLS", "").replace("\n", ",").split(",") if u.strip()]
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + dt.timedelta(days=days)
    events = []
    for entry in urls:
        label, _, url = entry.rpartition("|") if "|" in entry else ("", "", entry)
        label = label.strip()
        url = url.strip().replace("webcal://", "https://", 1)
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        cal = icalendar.Calendar.from_ical(r.content)
        for ev in recurring_ical_events.of(cal).between(start, end):
            if str(ev.get("STATUS", "")).upper() == "CANCELLED":
                continue
            s = ev["DTSTART"].dt
            if ev.get("DTEND"):
                e = ev["DTEND"].dt
            elif ev.get("DURATION"):
                e = s + ev["DURATION"].dt
            else:
                e = None
            all_day = not isinstance(s, dt.datetime)
            if all_day:
                e = e or s + dt.timedelta(days=1)
                # expand multi-day all-day events onto each day they cover
                d = s
                while d < e:
                    if start.date() <= d < end.date():
                        events.append({"date": d, "start": None, "end": None, "label": label,
                                       "title": str(ev.get("SUMMARY", "(no title)")), "first_day": d == s})
                    d += dt.timedelta(days=1)
            else:
                s = s.astimezone(TZ) if s.tzinfo else s.replace(tzinfo=TZ)
                e = (e.astimezone(TZ) if e and e.tzinfo else e.replace(tzinfo=TZ)) if e else s
                if e <= now:          # already finished
                    continue
                events.append({"date": max(s.date(), start.date()), "start": s, "end": e, "label": label,
                               "title": str(ev.get("SUMMARY", "(no title)")), "first_day": True})
    # "*Title" marks a countdown event; strip the marker for display
    for ev in events:
        t = ev["title"].strip()
        ev["countdown"] = t.startswith("*")
        ev["title"] = t.lstrip("*").strip() if ev["countdown"] else t
    # de-duplicate (same event on two shared calendars)
    seen, out = {}, []
    for ev in sorted(events, key=lambda x: (x["date"], x["start"] is not None,
                                            x["start"] or dt.datetime.min.replace(tzinfo=TZ))):
        key = (ev["date"], ev["start"], ev["title"].strip().lower())
        if key in seen:   # same event on two calendars: show it once, with both labels
            first = seen[key]
            if ev["label"] and ev["label"] not in first["label"]:
                first["label"] = (first["label"] + ev["label"]) if first["label"] else ev["label"]
            continue
        seen[key] = ev
        out.append(ev)
    print(f"calendars: {len(urls)}, events: {len(out)}")
    return out, len(urls)


# ------------------------------------------------------------------ icons

def icon(d, kind, cx, cy, r):
    """Simple line-art weather icons sized to radius r."""
    lw = max(3, r // 9)

    def sun(x, y, rad):
        d.ellipse([x - rad, y - rad, x + rad, y + rad], outline=BLACK, width=lw)
        import math
        for i in range(8):
            a = i * math.pi / 4
            d.line([x + math.cos(a) * rad * 1.45, y + math.sin(a) * rad * 1.45,
                    x + math.cos(a) * rad * 1.9, y + math.sin(a) * rad * 1.9], fill=BLACK, width=lw)

    def cloud(x, y, s):
        # Build the cloud silhouette as a mask, then outline it by eroding.
        from PIL import ImageFilter
        pad = int(s * 1.2)
        ox, oy = int(x) - pad, int(y) - pad
        mask = Image.new("L", (pad * 2, pad * 2), 0)
        md = ImageDraw.Draw(mask)
        for px, py, pr in [(x - s * 0.55, y + s * 0.05, s * 0.42), (x + s * 0.05, y - s * 0.2, s * 0.55),
                           (x + s * 0.6, y + s * 0.1, s * 0.38)]:
            md.ellipse([px - pr - ox, py - pr - oy, px + pr - ox, py + pr - oy], fill=255)
        md.rounded_rectangle([x - s * 0.97 - ox, y + s * 0.05 - oy, x + s * 0.98 - ox, y + s * 0.48 - oy],
                             radius=s * 0.22, fill=255)
        inner = mask.filter(ImageFilter.MinFilter(lw * 2 + 1))
        d._image.paste(BLACK, (ox, oy), mask)
        d._image.paste(WHITE, (ox, oy), inner)

    def moon(x, y, rad):
        from PIL import ImageFilter
        pad = int(rad * 1.3)
        ox, oy = int(x) - pad, int(y) - pad
        mask = Image.new("L", (pad * 2, pad * 2), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([pad - rad, pad - rad, pad + rad, pad + rad], fill=255)
        md.ellipse([pad - rad * 0.45, pad - rad * 1.15, pad + rad * 1.45, pad + rad * 0.55], fill=0)
        inner = mask.filter(ImageFilter.MinFilter(lw * 2 + 1))
        d._image.paste(BLACK, (ox, oy), mask)
        d._image.paste(WHITE, (ox, oy), inner)

    if kind == "moon":
        moon(cx, cy, r * 0.62)
    elif kind == "partly-night":
        moon(cx - r * 0.3, cy - r * 0.3, r * 0.42)
        cloud(cx + r * 0.12, cy + r * 0.15, r * 0.72)
    elif kind == "sun":
        sun(cx, cy, r * 0.5)
    elif kind == "partly":
        sun(cx - r * 0.3, cy - r * 0.3, r * 0.36)
        cloud(cx + r * 0.12, cy + r * 0.15, r * 0.72)
    elif kind in ("cloud", "fog"):
        cloud(cx, cy - r * 0.1, r * 0.85)
        if kind == "fog":
            for i in range(2):
                y = cy + r * 0.6 + i * lw * 2.6
                d.line([cx - r * 0.8, y, cx + r * 0.8, y], fill=BLACK, width=lw)
    else:
        cloud(cx, cy - r * 0.3, r * 0.85)
        y0 = cy + r * 0.38
        for i, dx in enumerate((-0.5, 0, 0.5)):
            x = cx + dx * r
            if kind == "snow":
                d.text((x, y0 + r * 0.22), "*", font=font("Bold", int(r * 0.6)), fill=BLACK, anchor="mm")
            elif kind == "storm" and i == 1:
                d.line([x + r * 0.12, y0, x - r * 0.1, y0 + r * 0.3, x + r * 0.1, y0 + r * 0.3,
                        x - r * 0.12, y0 + r * 0.6], fill=BLACK, width=lw)
            else:
                d.line([x + r * 0.1, y0, x - r * 0.1, y0 + r * 0.45], fill=BLACK, width=lw)


# ------------------------------------------------------------------ helpers

def icon_kind(code, is_day=1):
    kind = WMO.get(code, ("", "cloud"))[1]
    if not is_day:
        kind = {"sun": "moon", "partly": "partly-night"}.get(kind, kind)
    return kind


def fmt_time(t):
    s = t.strftime("%I:%M").lstrip("0")
    return s.replace(":00", "") + ("a" if t.hour < 12 else "p")


def fit(d, text, f, maxw):
    if d.textlength(text, font=f) <= maxw:
        return text
    while text and d.textlength(text + "…", font=f) > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def day_label(day, today):
    if day == today:
        return "Today"
    if day == today + dt.timedelta(days=1):
        return "Tomorrow"
    return day.strftime("%A")


# ------------------------------------------------------------------- render

def draw_alerts(d, alerts, y):
    """Black banner for active weather alerts. Returns the new y."""
    if not alerts:
        return y
    top = y + 16
    d.rounded_rectangle([M, top, W - M, top + 64], radius=10, fill=BLACK)
    # warning triangle
    tx, ty = M + 34, top + 32
    d.polygon([(tx, ty - 17), (tx + 19, ty + 15), (tx - 19, ty + 15)], fill=WHITE)
    d.text((tx, ty + 3), "!", font=font("Bold", 24), fill=BLACK, anchor="mm")
    a = alerts[0]
    text = a["event"]
    if a["until"]:
        text += f"  ·  until {a['until'].strftime('%a')} {fmt_time(a['until'])}"
    if len(alerts) > 1:
        text += f"  ·  +{len(alerts) - 1} more"
    f = font("Bold", 32)
    d.text((M + 70, top + 32), fit(d, text, f, W - 2 * M - 90), font=f, fill=WHITE, anchor="lm")
    return top + 64


def render(now, wx, events, errors, note="", alerts=()):
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    today = now.date()

    # Header -------------------------------------------------------------
    d.text((M, 40), now.strftime("%A"), font=font("Bold", 84), fill=BLACK)
    d.text((M, 138), now.strftime("%B ") + str(now.day), font=font("Medium", 44), fill=DARK)
    sunline = moon_phase(today)
    if wx and wx["daily"].get("sunrise"):
        rise = dt.datetime.fromisoformat(wx["daily"]["sunrise"][0])
        sset = dt.datetime.fromisoformat(wx["daily"]["sunset"][0])
        sunline = f"Rise {fmt_time(rise)}  ·  Set {fmt_time(sset)}  ·  {sunline}"
    d.text((M, 196), fit(d, sunline, font("Medium", 28), 600), font=font("Medium", 28), fill=MID)

    # Current weather (top right) ---------------------------------------
    y = 236
    if wx:
        cur, daily = wx["current"], wx["daily"]
        label = WMO.get(cur["weather_code"], ("—", "cloud"))[0]
        kind = icon_kind(cur["weather_code"], cur.get("is_day", 1))
        temp = f"{round(cur['temperature_2m'])}°"
        tw = d.textlength(temp, font=font("Bold", 120))
        icon(d, kind, W - M - tw - 95, 125, 66)
        d.text((W - M, 60), temp, font=font("Bold", 120), fill=BLACK, anchor="ra")
        d.text((W - M, 192), label, font=font("SemiBold", 34), fill=DARK, anchor="ra")

        hi, lo = round(daily["temperature_2m_max"][0]), round(daily["temperature_2m_min"][0])
        pop = daily["precipitation_probability_max"][0]
        summary = (f"High {hi}°  ·  Low {lo}°  ·  Feels {round(cur['apparent_temperature'])}°"
                   f"  ·  Wind {round(cur['wind_speed_10m'])} mph")
        if pop:
            summary += f"  ·  {pop}% rain"
        d.line([M, y, W - M, y], fill=BLACK, width=3)
        y = draw_alerts(d, alerts, y)
        d.text((M, y + 20), fit(d, summary, font("SemiBold", 33), W - 2 * M), font=font("SemiBold", 33), fill=DARK)
        y += 80

        # Hourly strip: next 6 slots, every 2 hours
        times = [dt.datetime.fromisoformat(t).replace(tzinfo=TZ) for t in wx["hourly"]["time"]]
        idx = next((i for i, t in enumerate(times) if t >= now.replace(minute=0, second=0, microsecond=0)), 0)
        slots = [idx + 1 + 2 * k for k in range(5) if idx + 1 + 2 * k < len(times)]
        colw = (W - 2 * M) / max(len(slots), 1)
        for k, i in enumerate(slots):
            cx = M + colw * k + colw / 2
            d.text((cx, y + 6), fmt_time(times[i]), font=font("SemiBold", 32), fill=MID, anchor="ma")
            icon(d, icon_kind(wx["hourly"]["weather_code"][i], wx["hourly"].get("is_day", [1] * len(times))[i]),
                 cx, y + 86, 37)
            d.text((cx, y + 132), f"{round(wx['hourly']['temperature_2m'][i])}°", font=font("Bold", 44),
                   fill=BLACK, anchor="ma")
            p = wx["hourly"]["precipitation_probability"][i]
            if p and p >= 20:
                d.text((cx, y + 184), f"{p}%", font=font("SemiBold", 28), fill=MID, anchor="ma")
        y += 226

        # Next 4 days
        d.line([M, y, W - M, y], fill=LIGHT, width=2)
        y += 20
        colw = (W - 2 * M) / 4
        for k in range(1, 5):
            cx = M + colw * (k - 1) + colw / 2
            day = dt.date.fromisoformat(daily["time"][k])
            d.text((cx, y), day.strftime("%a"), font=font("Bold", 34), fill=DARK, anchor="ma")
            icon(d, icon_kind(daily["weather_code"][k]), cx, y + 82, 37)
            d.text((cx, y + 128), f"{round(daily['temperature_2m_max'][k])}° / "
                                  f"{round(daily['temperature_2m_min'][k])}°",
                   font=font("SemiBold", 34), fill=BLACK, anchor="ma")
        y += 186
    else:
        d.line([M, y, W - M, y], fill=BLACK, width=3)
        y = draw_alerts(d, alerts, y)
        d.text((M, y + 20), "Weather unavailable", font=font("SemiBold", 34), fill=MID)
        y += 80

    # Countdowns -----------------------------------------------------------
    counts, seen_c = [], set()
    for ev in events:
        if ev.get("countdown") and ev.get("first_day", True) and ev["date"] >= today \
                and ev["title"].lower() not in seen_c:
            seen_c.add(ev["title"].lower())
            counts.append(ev)
    if counts:
        d.line([M, y, W - M, y], fill=LIGHT, width=2)
        x, cy = M, y + 18
        nf, tf = font("Bold", 34), font("SemiBold", 32)
        for ev in counts[:4]:
            n = (ev["date"] - today).days
            num = "Today" if n == 0 else "Tomorrow" if n == 1 else f"{n} days"
            title = fit(d, ev["title"], tf, 360)
            wdt = d.textlength(num, font=nf) + 14 + d.textlength(title, font=tf) + 40
            if x + wdt > W - M:
                break
            d.rounded_rectangle([x, cy, x + wdt, cy + 58], radius=29, outline=BLACK, width=3)
            d.text((x + 20, cy + 29), num, font=nf, fill=BLACK, anchor="lm")
            d.text((x + 20 + d.textlength(num, font=nf) + 14, cy + 29), title, font=tf, fill=DARK, anchor="lm")
            x += wdt + 16
        y += 94

    # Calendar -------------------------------------------------------------
    events = [ev for ev in events if ev["date"] < today + dt.timedelta(days=7)]
    d.line([M, y, W - M, y], fill=BLACK, width=3)
    y += 26
    footer_top = H - 74
    title_f, time_f, head_f = font("SemiBold", 42), font("Bold", 38), font("Bold", 44)
    time_col = 215
    row = 60

    by_day = {}
    for ev in events:
        by_day.setdefault(ev["date"], []).append(ev)
    days = [today, today + dt.timedelta(days=1)] + sorted(k for k in by_day if k > today + dt.timedelta(days=1))

    hidden = 0
    for day in days:
        evs = by_day.get(day, [])
        if day > today + dt.timedelta(days=1) and not evs:
            continue
        need = 64 + max(len(evs), 1) * row
        if y + min(need, 64 + row) > footer_top:
            hidden += len(evs)
            continue
        label = day_label(day, today)
        d.text((M, y), label, font=head_f, fill=BLACK)
        if day > today + dt.timedelta(days=1) or day == today + dt.timedelta(days=1):
            d.text((M + d.textlength(label, font=head_f) + 18, y + 10), day.strftime("%b ") + str(day.day),
                   font=font("SemiBold", 32), fill=MID)
        y += 64
        if not evs:
            d.text((M + time_col, y), "Nothing scheduled", font=font("Medium", 36), fill=MID)
            y += row + 4
            continue
        for ev in evs:
            if y + row > footer_top:
                hidden += 1
                continue
            if ev["start"] is None:
                d.rounded_rectangle([M, y + 4, M + time_col - 30, y + 48], radius=8, fill=BLACK)
                d.text((M + (time_col - 30) / 2, y + 26), "ALL DAY", font=font("Bold", 25), fill=WHITE, anchor="mm")
            else:
                happening = ev["start"] <= now < ev["end"]
                t = "Now" if happening else fmt_time(ev["start"])
                d.text((M, y), t, font=time_f, fill=BLACK)
            tx = M + time_col
            if ev.get("label"):
                bf = font("Bold", 26)
                bw = max(44, d.textlength(ev["label"], font=bf) + 22)
                d.rounded_rectangle([tx, y + 5, tx + bw, y + 49], radius=22, outline=BLACK, width=3)
                d.text((tx + bw / 2, y + 27), ev["label"], font=bf, fill=BLACK, anchor="mm")
                tx += bw + 14
            d.text((tx, y), fit(d, ev["title"], title_f, W - M - tx), font=title_f, fill=BLACK)
            y += row
        y += 14

    if hidden:
        d.text((W - M, footer_top - 46), f"+{hidden} more", font=font("SemiBold", 32), fill=MID, anchor="ra")

    # Footer ---------------------------------------------------------------
    d.line([M, footer_top, W - M, footer_top], fill=LIGHT, width=2)
    stamp = f"Updated {now.strftime('%a')} {fmt_time(now)}" + (f"  ·  {note}" if note else "")
    if errors:
        stamp += "  ·  " + " / ".join(errors)
    d.text((M, footer_top + 18), fit(d, stamp, font("Medium", 28), W - 2 * M - 250), font=font("Medium", 28), fill=MID)
    return img


# --------------------------------------------------------------------- mock

def mock(now):
    base = now.replace(minute=0, second=0, microsecond=0)
    hours = [base + dt.timedelta(hours=h) for h in range(48)]
    codes = [3, 3, 2, 2, 61, 61, 63, 3, 2, 1, 0, 0] * 4
    days = [now.date() + dt.timedelta(days=k) for k in range(6)]
    wx = {
        "current": {"temperature_2m": 47.3, "apparent_temperature": 42.1, "weather_code": 2, "wind_speed_10m": 9},
        "hourly": {"time": [h.strftime("%Y-%m-%dT%H:%M") for h in hours],
                   "temperature_2m": [47 - (i % 12) * 0.8 for i in range(48)],
                   "precipitation_probability": [10, 10, 20, 40, 70, 80, 60, 30, 10, 0, 0, 0] * 4,
                   "weather_code": codes[:48],
                   "is_day": [1 if 7 <= h.hour < 17 else 0 for h in hours]},
        "daily": {"time": [x.isoformat() for x in days], "weather_code": [2, 63, 3, 71, 0, 1],
                  "temperature_2m_max": [51, 46, 41, 34, 38, 44], "temperature_2m_min": [36, 38, 29, 22, 21, 30],
                  "precipitation_probability_max": [40, 85, 20, 60, 0, 5],
                  "sunrise": [f"{x.isoformat()}T07:01" for x in days],
                  "sunset": [f"{x.isoformat()}T16:58" for x in days]},
    }
    t = lambda dd, h, m=0: dt.datetime.combine(now.date() + dt.timedelta(days=dd), dt.time(h, m), TZ)
    events = [
        {"date": now.date(), "start": None, "end": None, "title": "Trash & recycling", "label": "MJ"},
        {"date": now.date(), "start": t(0, 16), "end": t(0, 17), "title": "Piano lesson", "label": "J"},
        {"date": now.date(), "start": t(0, 18, 30), "end": t(0, 20), "title": "Dinner with the Hendersons", "label": "MJ"},
        {"date": now.date() + dt.timedelta(days=1), "start": t(1, 8), "end": t(1, 9), "title": "Dentist – Dr. Patel", "label": "M"},
        {"date": now.date() + dt.timedelta(days=1), "start": t(1, 15, 15), "end": t(1, 16), "title": "Early dismissal", "label": "J"},
        {"date": now.date() + dt.timedelta(days=2), "start": t(2, 19), "end": t(2, 21), "title": "School board meeting", "label": "M"},
        {"date": now.date() + dt.timedelta(days=4), "start": None, "end": None, "title": "Thanksgiving break begins"},
        {"date": now.date() + dt.timedelta(days=4), "start": t(4, 10), "end": t(4, 11), "title": "Flight to Atlanta"},
        {"date": now.date() + dt.timedelta(days=10), "start": None, "end": None, "title": "Thanksgiving",
         "countdown": True},
        {"date": now.date() + dt.timedelta(days=39), "start": None, "end": None, "title": "Christmas",
         "countdown": True},
    ]
    alerts = [{"event": "Winter Weather Advisory", "severity": "Moderate",
               "until": dt.datetime.combine(now.date() + dt.timedelta(days=1), dt.time(19), TZ)}]
    return wx, events, alerts


def main():
    now = dt.datetime.now(TZ)
    out = Path(os.environ.get("OUT", "out/dashboard.png"))
    errors, note, alerts = [], "", []
    if "--mock" in sys.argv:
        wx, events, alerts = mock(now)
        note = "2 calendars"
    else:
        try:
            wx = fetch_weather()
        except Exception as e:  # keep rendering with what we have
            print("weather error:", e, file=sys.stderr)
            wx, errors = None, errors + ["weather failed"]
        try:
            alerts = fetch_alerts()
        except Exception as e:  # alerts are a bonus; never block the render
            print("alerts error:", e, file=sys.stderr)
        try:
            events, ncal = fetch_events(now)
            note = "no calendars set" if ncal == 0 else f"{ncal} calendar{'s' if ncal > 1 else ''}"
        except Exception as e:
            print("calendar error:", e, file=sys.stderr)
            events, errors = [], errors + ["calendar failed"]
    img = render(now, wx, events, errors, note, alerts)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
