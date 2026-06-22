#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

readonly service_user="lei1"
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

id "${service_user}" >/dev/null

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install --yes caddy

install -d -o root -g root -m 0755 /opt/visit-notify
install -o root -g root -m 0755 "${source_dir}/visit_notify.py" /opt/visit-notify/visit_notify.py
install -o root -g root -m 0644 "${source_dir}/visit-notify.service" /etc/systemd/system/visit-notify.service
install -o root -g root -m 0644 "${source_dir}/Caddyfile" /etc/caddy/Caddyfile

if [[ ! -e /etc/visit-notify.env ]]; then
  topic="dttutty-visit-$(openssl rand -hex 24)"
  {
    printf 'NTFY_TOPIC=%s\n' "${topic}"
    printf 'VISIT_ALLOWED_ORIGINS=https://dttutty.com,https://www.dttutty.com\n'
  } > /etc/visit-notify.env
  chmod 0600 /etc/visit-notify.env
fi

caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl daemon-reload
systemctl enable --now visit-notify.service
systemctl enable --now caddy.service
systemctl restart caddy.service

if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
  ufw allow 80/tcp
  ufw allow 443/tcp
fi

curl --fail --silent --show-error http://127.0.0.1:8787/healthz --output /dev/null

echo "Installation complete. Subscribe to this private-looking ntfy.sh topic:"
sed -n 's/^NTFY_TOPIC=//p' /etc/visit-notify.env
