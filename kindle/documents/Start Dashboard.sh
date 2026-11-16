#!/bin/sh
# Name: Start Dashboard
# Author: Matt
# DontUseFBInk

# Tap this "book" in the library to start the dashboard.
# To get back to the normal Kindle: hold power ~40 s until it restarts.

if [ ! -f /mnt/us/dashboard/start.sh ]; then
  /usr/sbin/eips 2 30 "Missing /mnt/us/dashboard folder" >/dev/null 2>&1
  exit 1
fi

if command -v setsid >/dev/null 2>&1; then
  setsid /bin/sh /mnt/us/dashboard/start.sh </dev/null >/dev/null 2>&1 &
else
  ( nohup /bin/sh /mnt/us/dashboard/start.sh </dev/null >/dev/null 2>&1 & )
fi

/usr/sbin/eips 2 30 "Starting dashboard..." >/dev/null 2>&1
exit 0
