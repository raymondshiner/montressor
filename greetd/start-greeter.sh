#!/bin/sh
# Disable every output that isn't the laptop panel, then launch the greeter.
(
  for _ in 1 2 3 4 5; do
    wlr-randr >/dev/null 2>&1 && break
    sleep 0.2
  done
  wlr-randr 2>/dev/null | awk '/^[A-Za-z]/ && $1 != "eDP-1" {print $1}' \
    | while read -r o; do wlr-randr --output "$o" --off; done
) &
exec /usr/bin/python3 /etc/greetd/greeter.py
