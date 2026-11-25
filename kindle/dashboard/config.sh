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

# Frontlight: 0 = off ... 24 = max. Forced off on battery.
FLINTENSITY=0

TZ="EST5EDT,M3.2.0,M11.1.0"

# While on the charger: live clock, and a quote page for QUOTE_FOR minute(s)
# out of every QUOTE_EVERY minutes. Set to 0 to turn either off.
CLOCK=1
QUOTES=1
QUOTE_EVERY=5
QUOTE_FOR=1
