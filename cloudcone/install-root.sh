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
if ! command -v caddy >/dev/null; then
  apt-get update
  apt-get install --yes caddy
fi

if [[ ! -e /etc/visit-notify.env ]]; then
  topic="dttutty-visit-$(openssl rand -hex 24)"
  {
    printf 'NTFY_TOPIC=%s\n' "${topic}"
    printf 'VISIT_ALLOWED_ORIGINS=https://dttutty.com,https://www.dttutty.com\n'
  } > /etc/visit-notify.env
  chmod 0600 /etc/visit-notify.env
fi

if ! grep -Eq '^OPENAI_API_KEY=sk-[^[:space:]]+$' /etc/visit-notify.env; then
  read -r -s -p "Enter a NEW OpenAI API key: " openai_api_key </dev/tty
  printf '\n' >/dev/tty
  if [[ "${openai_api_key}" != sk-* || "${openai_api_key}" =~ [[:space:]] ]]; then
    echo "Invalid OpenAI API key format." >&2
    exit 1
  fi
  env_tmp="$(mktemp)"
  trap 'rm -f -- "${env_tmp:-}"' EXIT
  sed '/^OPENAI_API_KEY=/d' /etc/visit-notify.env > "${env_tmp}"
  printf 'OPENAI_API_KEY=%s\n' "${openai_api_key}" >> "${env_tmp}"
  install -o root -g root -m 0600 "${env_tmp}" /etc/visit-notify.env
  rm -f -- "${env_tmp}"
  trap - EXIT
  unset openai_api_key
fi
if ! grep -q '^OPENAI_MODEL=' /etc/visit-notify.env; then
  printf 'OPENAI_MODEL=gpt-5.6-luna\n' >> /etc/visit-notify.env
fi
chown root:root /etc/visit-notify.env
chmod 0600 /etc/visit-notify.env

install -d -o root -g root -m 0755 /opt/visit-notify
install -o root -g root -m 0755 "${source_dir}/visit_notify.py" /opt/visit-notify/visit_notify.py
install -o root -g root -m 0644 "${source_dir}/visit-notify.service" /etc/systemd/system/visit-notify.service
install -o root -g root -m 0644 "${source_dir}/Caddyfile" /etc/caddy/Caddyfile

caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl daemon-reload
systemctl enable visit-notify.service
systemctl restart visit-notify.service
systemctl enable caddy.service
systemctl restart caddy.service

if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
  ufw allow 80/tcp
  ufw allow 443/tcp
fi

curl --fail --silent --show-error http://127.0.0.1:8787/healthz --output /dev/null

echo "Installation complete. The private ntfy topic remains in /etc/visit-notify.env."
