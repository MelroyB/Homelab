#!/bin/sh
set -eu

mkdir -p \
  /homelab-data/config/caddy \
  /homelab-data/state/caddy/data \
  /homelab-data/state/caddy/config

if [ ! -f /homelab-data/config/caddy/Caddyfile ]; then
  cp /defaults/Caddyfile /homelab-data/config/caddy/Caddyfile
fi

exec caddy run --config /homelab-data/config/caddy/Caddyfile --adapter caddyfile
