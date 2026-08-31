#!/bin/zsh
# Deploy decastate.com static site on the AgentSigned OCI box (161.153.99.111).
# Site files are already rsynced to ~/decastate-site by the build step.
# This script: backs up configs, adds the Caddy vhost, mounts the site dir,
# recreates only the caddy container, and verifies BOTH domains at the origin.
set -euo pipefail
KEY=~/ORACLE-CLOUD/ORACLE-ADITYA/ssh-key-2026-07-08.key
HOST=ubuntu@161.153.99.111

ssh -i "$KEY" "$HOST" '
set -e
cd ~/agentcard/infra
cp Caddyfile Caddyfile.bak.decastate
cp docker-compose.prod.yml docker-compose.prod.yml.bak.decastate

if ! grep -q "decastate.com" Caddyfile; then
cat >> Caddyfile <<EOF

# decastate.com — static launch site + dashboard
https://decastate.com, https://www.decastate.com {
	tls internal
	encode zstd gzip
	root * /srv/decastate
	file_server
}
http://decastate.com, http://www.decastate.com {
	encode zstd gzip
	root * /srv/decastate
	file_server
}
EOF
fi

grep -q "decastate-site" docker-compose.prod.yml || \
  sed -i "s|- ./Caddyfile:/etc/caddy/Caddyfile:ro|- ./Caddyfile:/etc/caddy/Caddyfile:ro\n      - /home/ubuntu/decastate-site:/srv/decastate:ro|" docker-compose.prod.yml

sudo docker compose -f docker-compose.prod.yml up -d caddy
sleep 3
echo "=== decastate.com at origin ==="
curl -sk https://127.0.0.1/ -H "Host: decastate.com" | head -c 100; echo
echo "=== agentsigned.com still healthy ==="
curl -sk -o /dev/null -w "%{http_code}\n" https://127.0.0.1/ -H "Host: agentsigned.com"
'
echo "=== through Cloudflare ==="
curl -s -o /dev/null -w "https://decastate.com → %{http_code}\n" https://decastate.com
