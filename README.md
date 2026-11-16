# Kindle dashboard

Weather + Google Calendar on a jailbroken Kindle Paperwhite 4 (1072×1448).

- `render.py` draws the dashboard PNG (weather from Open-Meteo, events from Google Calendar iCal links).
- `.github/workflows/render.yml` runs it every 30 minutes and publishes the image on GitHub Pages.
- `kindle/` holds the on-device files: copy `kindle/dashboard/` to the Kindle's root and
  `kindle/documents/Start Dashboard.sh` into its `documents` folder.

## Setup

1. **Secrets** (Settings → Secrets and variables → Actions → *Secrets*):
   - `CAL_ICS_URLS`: one or more calendar ICS links, separated by commas. Optionally put a
     short label and `|` in front of each to tag its events, e.g. `M|https://…,J|https://…`.
     - Google Calendar: calendar settings → *Secret address in iCal format*.
     - Outlook.com / Hotmail: Settings → Calendar → Shared calendars → *Publish a calendar* → ICS link.
   - `DASH_NAME`: the image file name (an unguessable string; the Pages site is public).
2. Optional **variables** (same page, *Variables* tab): `LAT`, `LON` (default State College, PA).
3. **Pages**: Settings → Pages → Source: *GitHub Actions*.
4. Actions tab → *Render dashboard* → *Run workflow*. The image appears at
   `https://<user>.github.io/<repo>/<DASH_NAME>.png`.
5. On the Kindle, set `DASH_URL` in `dashboard/config.sh` to that address (and optionally
   `WIFI_SSID` / `WIFI_PSK`), then tap **Start Dashboard** in the library.

**Extras:**
- Weather alerts from the National Weather Service appear as a banner when active.
- Start a calendar event's title with `*` (e.g. `*Thanksgiving`) to get a countdown chip.
- Sunrise, sunset and moon phase sit under the date.
- The Kindle draws its own battery level bottom-right (`SHOW_BATTERY=0` in config.sh to hide).

**Exit:** hold the power button ~40 s until the Kindle restarts. Nothing starts on boot.

**Preview locally:** `python render.py --mock` writes `out/dashboard.png` with sample data.

## Credits

`kindle/dashboard/loop.sh` and `start.sh` are adapted from
[dalager/kindle-todo](https://github.com/dalager/kindle-todo) (MIT), whose Paperwhite 4
power and Wi-Fi handling they reuse. Fonts: Inter (SIL Open Font License).
