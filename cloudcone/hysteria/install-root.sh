#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

readonly service_user="hysteria"
readonly service_group="hysteria"
readonly service_version="v2.11.0"
readonly binary_sha256="d1b7996bff679f084c52541886ba2804dc582d237d6cbc820e0d6bf2393958bf"
readonly binary_url="https://github.com/apernet/hysteria/releases/download/app/${service_version}/hysteria-linux-amd64"
readonly managed_marker="/etc/hysteria/.dttutty-managed"
readonly server_name="hy2.dttutty.com"
readonly client_user="lei1"

source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
caddy_source="$(cd "${source_dir}/.." && pwd)/Caddyfile"
download_dir="$(mktemp -d)"

cleanup() {
  rm -rf -- "${download_dir}"
}
trap cleanup EXIT

if [[ -e /etc/hysteria && ! -e "${managed_marker}" ]]; then
  echo "Refusing to overwrite an unrecognized /etc/hysteria installation." >&2
  exit 1
fi
if [[ -e /etc/systemd/system/hysteria-server.service && ! -e "${managed_marker}" ]]; then
  echo "Refusing to overwrite an unrecognized hysteria-server.service." >&2
  exit 1
fi

id "${client_user}" >/dev/null
if ! getent group "${service_group}" >/dev/null; then
  groupadd --system "${service_group}"
fi
if ! id "${service_user}" >/dev/null 2>&1; then
  useradd --system --gid "${service_group}" --home-dir /var/lib/hysteria \
    --shell /usr/sbin/nologin "${service_user}"
fi

curl --fail --silent --show-error --location "${binary_url}" \
  --output "${download_dir}/hysteria"
printf '%s  %s\n' "${binary_sha256}" "${download_dir}/hysteria" \
  | sha256sum --check --status
install -o root -g root -m 0755 "${download_dir}/hysteria" /usr/local/bin/hysteria

install -d -o root -g "${service_group}" -m 0750 /etc/hysteria
install -d -o "${service_user}" -g "${service_group}" -m 0750 /var/lib/hysteria/acme

if [[ ! -e /etc/hysteria/config.yaml ]]; then
  auth_password="$(openssl rand -hex 24)"
  obfs_password="$(openssl rand -hex 24)"
  cat > /etc/hysteria/config.yaml <<EOF
listen: :443

acme:
  domains:
    - ${server_name}
  email: dttutty@gmail.com
  ca: letsencrypt
  listenHost: 127.0.0.1
  dir: /var/lib/hysteria/acme
  type: http
  http:
    altPort: 5080

auth:
  type: password
  password: ${auth_password}

obfs:
  type: salamander
  salamander:
    password: ${obfs_password}

masquerade:
  type: proxy
  proxy:
    url: https://dttutty.github.io/
    rewriteHost: true
EOF
fi
if grep -Fqx '    url: https://dttutty.com/' /etc/hysteria/config.yaml; then
  sed -i 's|^    url: https://dttutty\.com/$|    url: https://dttutty.github.io/|' \
    /etc/hysteria/config.yaml
fi
chown root:"${service_group}" /etc/hysteria/config.yaml
chmod 0640 /etc/hysteria/config.yaml
touch "${managed_marker}"
chown root:root "${managed_marker}"
chmod 0644 "${managed_marker}"

install -o root -g root -m 0644 "${source_dir}/hysteria-server.service" \
  /etc/systemd/system/hysteria-server.service
install -o root -g root -m 0644 "${caddy_source}" /etc/caddy/Caddyfile

cat > /etc/sysctl.d/99-hysteria.conf <<'EOF'
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
EOF
sysctl --system >/dev/null

caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl daemon-reload
systemctl enable caddy.service
systemctl restart caddy.service
systemctl enable hysteria-server.service
systemctl restart hysteria-server.service

if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
  ufw allow 443/udp
fi

client_dir="/home/${client_user}/hy2-client"
install -d -o "${client_user}" -g "${client_user}" -m 0700 "${client_dir}"
auth_password="$(sed -n 's/^[[:space:]]*password:[[:space:]]*//p' /etc/hysteria/config.yaml | sed -n '1p')"
obfs_password="$(sed -n 's/^[[:space:]]*password:[[:space:]]*//p' /etc/hysteria/config.yaml | sed -n '2p')"

cat > "${client_dir}/stash.yaml" <<EOF
proxies:
  - name: CloudCone-HY2
    type: hysteria2
    server: ${server_name}
    port: 443
    auth: ${auth_password}
    fast-open: true
    obfs: salamander
    obfs-password: ${obfs_password}
    sni: ${server_name}
    skip-cert-verify: false
EOF

cat > "${client_dir}/mihomo.yaml" <<EOF
proxies:
  - name: CloudCone-HY2
    type: hysteria2
    server: ${server_name}
    port: 443
    password: ${auth_password}
    obfs: salamander
    obfs-password: ${obfs_password}
    sni: ${server_name}
    skip-cert-verify: false
    alpn:
      - h3
EOF

cat > "${client_dir}/native.yaml" <<EOF
server: ${server_name}:443
auth: ${auth_password}

tls:
  sni: ${server_name}
  insecure: false

obfs:
  type: salamander
  salamander:
    password: ${obfs_password}

socks5:
  listen: 127.0.0.1:1080
EOF

cat > "${client_dir}/share-uri.txt" <<EOF
hysteria2://${auth_password}@${server_name}:443/?obfs=salamander&obfs-password=${obfs_password}&sni=${server_name}#CloudCone-HY2
EOF

chown "${client_user}:${client_user}" "${client_dir}"/*
chmod 0600 "${client_dir}"/*

for attempt in {1..20}; do
  if systemctl is-active --quiet hysteria-server.service; then
    break
  fi
  sleep 1
done
systemctl is-active --quiet hysteria-server.service
ss -lun | grep -Eq '(^|[[:space:]])\*:443([[:space:]]|$)|(^|[[:space:]])0\.0\.0\.0:443([[:space:]]|$)'

echo "Hysteria 2 ${service_version} is running on UDP 443."
echo "Client files: ${client_dir}"
