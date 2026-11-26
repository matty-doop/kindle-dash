# Dashboard settings. Edit DASH_URL (and optionally Wi-Fi) before first start.

# Where the dashboard image lives (from the GitHub Pages setup).
DASH_URL="https://matty-doop.github.io/kindle-dash/dash-daeaa084d03ce8b4.png"

# Optional but recommended: lets the dashboard rejoin Wi-Fi by itself if the
# Kindle drops its saved network after waking from sleep. 2.4 GHz network only.
WIFI_SSID=""
WIFI_PSK=""

# How often to check for a new image, in seconds.
INTERVAL=300               # on the charger (stays awake)
BATTERY_INTERVAL=1800      # on battery (sleeps in between)
BATTERY_LOW_INTERVAL=3600  # on battery below 20%

# Overnight: check once an hour.
NIGHT_START="23:00"
NIGHT_END="06:00"

# Frontlight (on the charger; always off on battery). Levels 0..24.
LIGHT=1              # 1 = follow the schedule below, 0 = fixed FLINTENSITY
EVENING_LIGHT=8      # sunset -> BEDTIME
NIGHT_LIGHT=2        # BEDTIME -> sunrise
BEDTIME="23:00"
LAT=40.8072          # for sunrise/sunset (Grays Woods)
LON=-77.9486
FLINTENSITY=0

TZ="EST5EDT,M3.2.0,M11.1.0"

# While on the charger: live clock, and a quote page for the last QUOTE_SECS
# seconds of every QUOTE_CYCLE seconds (default: dashboard :00-:29, quote
# :30-:59). Set CLOCK or QUOTES to 0 to turn either off.
CLOCK=1
QUOTES=1
QUOTE_CYCLE=60
QUOTE_SECS=30
TAP=1          # tap the screen to switch pages (on the charger)
TAP_HOLD=120   # a page you tap to stays up this many seconds
