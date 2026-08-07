#!/usr/bin/env bash
set -euo pipefail

domain="video-notes-8-135-44-86.sslip.io"
certificate_dir="/etc/letsencrypt/live/${domain}"
lego_dir="/root/.lego"
ip_address="8.135.44.86"
ip_lego_dir="/etc/lego-ip"
renew_before_seconds=$((30 * 24 * 60 * 60))
ip_renew_before_seconds=$((4 * 24 * 60 * 60))
renewed=0

exec 9>/run/video-to-notes-cert-renew.lock
flock -n 9 || exit 0

cleanup_redirect() {
  iptables -t nat -D PREROUTING -i eth0 -p tcp --dport 443 \
    -j REDIRECT --to-ports 8443 2>/dev/null || true
  iptables -D INPUT -i eth0 -p tcp --dport 8443 -j ACCEPT \
    2>/dev/null || true
}

prepare_redirect() {
  cleanup_redirect
  iptables -I INPUT 1 -i eth0 -p tcp --dport 8443 -j ACCEPT
  iptables -t nat -I PREROUTING 1 -i eth0 -p tcp --dport 443 \
    -j REDIRECT --to-ports 8443
}
trap cleanup_redirect EXIT

if ! openssl x509 -checkend "${renew_before_seconds}" -noout \
  -in "${certificate_dir}/fullchain.pem"; then
  prepare_redirect

  lego \
    --path "${lego_dir}" \
    --accept-tos \
    --email "admin@${domain}" \
    --domains "${domain}" \
    --tls \
    --tls.port :8443 \
    renew --days 30

  cleanup_redirect

  install -m 644 "${lego_dir}/certificates/${domain}.crt" \
    "${certificate_dir}/fullchain.pem"
  install -m 600 "${lego_dir}/certificates/${domain}.key" \
    "${certificate_dir}/privkey.pem"
  renewed=1
fi

if ! openssl x509 -checkend "${ip_renew_before_seconds}" -noout \
  -in "${ip_lego_dir}/certificates/${ip_address}.crt"; then
  prepare_redirect

  /usr/local/bin/lego-v5.2.1 run \
    --path "${ip_lego_dir}" \
    --accept-tos \
    --email "admin@${domain}" \
    --domains "${ip_address}" \
    --tls \
    --tls.address :8443 \
    --profile shortlived \
    --renew-days 4

  cleanup_redirect
  renewed=1
fi

if (( renewed )); then
  nginx -t
  systemctl reload nginx
fi
