#!/bin/sh
set -eu

mkdir -p \
  /homelab-data/config/dnsmasq/runtime \
  /homelab-data/state/dnsmasq

if [ ! -f /homelab-data/config/dnsmasq/dnsmasq.conf ]; then
  cp /defaults/dnsmasq.conf /homelab-data/config/dnsmasq/dnsmasq.conf
fi

if [ ! -f /homelab-data/config/dnsmasq/runtime/generated.conf ]; then
  : > /homelab-data/config/dnsmasq/runtime/generated.conf
fi

exec dnsmasq -k --conf-file=/homelab-data/config/dnsmasq/dnsmasq.conf
