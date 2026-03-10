#!/bin/sh
set -eu

mkdir -p \
  /homelab-data/config/bind9/zones \
  /homelab-data/state/bind9/cache

if [ ! -f /homelab-data/config/bind9/named.conf ]; then
  cp /defaults/named.conf /homelab-data/config/bind9/named.conf
fi

if [ ! -f /homelab-data/config/bind9/zones/db.homelab.local ]; then
  cp /defaults/db.homelab.local /homelab-data/config/bind9/zones/db.homelab.local
fi

exec named -g -c /homelab-data/config/bind9/named.conf
