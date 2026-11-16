#!/bin/sh
# Takes over the screen and runs the dashboard loop.
# Launched (detached) by the "Start Dashboard" scriptlet in /mnt/us/documents.
#
# Adapted from dalager/kindle-todo boot-image.sh (MIT License, (c) 2026 Christian Dalager).
#
# TO EXIT: hold the power button ~40 seconds until the Kindle restarts.
# Nothing auto-starts on boot, so a restart returns the normal Kindle UI.

DIR=/mnt/us/dashboard
LOG="$DIR/dashboard.log"

# Survive the display stack (which launched us) being stopped below.
trap '' HUP TERM INT

# Escape hatch: if a file named DISABLE exists in the dashboard folder, do nothing.
if [ -f "$DIR/DISABLE" ]; then
  echo "$(date) DISABLE present - not starting" >> "$LOG"
  exit 0
fi

set -a
[ -f "$DIR/config.sh" ] && . "$DIR/config.sh"
set +a

if [ -z "$DASH_URL" ]; then
  /usr/sbin/eips 2 30 "Set DASH_URL in dashboard/config.sh" >/dev/null 2>&1
  exit 1
fi

export FLINTENSITY="${FLINTENSITY:-0}"
export TZ="${TZ:-EST5EDT,M3.2.0,M11.1.0}"

# Make sure we're not in airplane mode (that flag persists across reboots).
lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null

# Let the scriptlet return and Wi-Fi settle.
sleep 10

# A dead battery resets the clock, which breaks HTTPS. Fix it from a plain-HTTP
# Date header if the year is obviously wrong.
fix_clock() {
  [ "$(date +%Y)" -ge 2024 ] && return 0
  d=$(curl -sI --max-time 5 http://cloudflare.com 2>/dev/null | tr -d '\r' | sed -n 's/^[Dd]ate: //p')
  set -- $d
  [ $# -ge 5 ] || return 1
  case "$3" in
    Jan) m=01;; Feb) m=02;; Mar) m=03;; Apr) m=04;; May) m=05;; Jun) m=06;;
    Jul) m=07;; Aug) m=08;; Sep) m=09;; Oct) m=10;; Nov) m=11;; Dec) m=12;;
    *) return 1;;
  esac
  date -u -s "$4.$m.$2-$5" >/dev/null 2>&1 || return 1
  hwclock -w 2>/dev/null
  echo "$(date) clock synced from HTTP Date header" >> "$LOG"
}
fix_clock

# Take over the panel: stop the whole display stack (framework, pillow,
# screensaver) so nothing repaints over the dashboard.
stop x 2>/dev/null
i=0
while [ $i -lt 20 ]; do
  ps -ef 2>/dev/null | grep -qE "[p]illow|[b]lanket|[a]wesome|[l]xinit" || break
  i=$((i + 1))
  sleep 1
done
sleep 3

lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
lipc-set-prop com.lab126.powerd flIntensity "$FLINTENSITY" 2>/dev/null

# 'ondemand' idles at low clock but avoids a Wi-Fi stall seen with 'powersave'.
echo "${GOVERNOR:-ondemand}" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null

exec /bin/sh "$DIR/loop.sh" "$DASH_URL" "${INTERVAL:-300}"
