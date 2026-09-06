#!/bin/zsh
# Deploy the DecaState Hub API on the OCI box (161.153.99.111).
# Static wall + seed data are rsynced separately; this script wires the dynamic API:
#   1. installs the hub server as a systemd service (port 8788, stdlib python only)
#   2. adds /api/* routing to the decastate.com Caddy block (backup first)
#   3. lets the Caddy container reach the host (host-gateway) + firewall rule
#   4. restarts only caddy, then verifies hub health + a test publish end-to-end
set -euo pipefail
KEY=~/ORACLE-CLOUD/ORACLE-ADITYA/ssh-key-2026-07-08.key
HOST=ubuntu@161.153.99.111

ssh -i "$KEY" "$HOST" '
set -e
# --- 1. systemd service ---
sudo tee /etc/systemd/system/decastate-hub.service >/dev/null <<EOF
[Unit]
Description=DecaState Hub (receipts API)
After=network.target
[Service]
User=ubuntu
Environment=DECASTATE_HUB_HOME=/home/ubuntu/decastate-hub
Environment=DECASTATE_SITE_DIR=/home/ubuntu/decastate-site
Environment=DECASTATE_HUB_PORT=8788
ExecStart=/usr/bin/python3 /home/ubuntu/decastate-hub/server.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now decastate-hub
sleep 2
curl -s http://127.0.0.1:8788/api/health && echo " ← hub healthy on host"

# --- 2. Caddyfile /api route for decastate.com (idempotent, backup first) ---
cd ~/agentcard/infra
cp Caddyfile Caddyfile.bak.hub
if ! grep -q "handle /api/\*" Caddyfile; then
python3 - <<PYEOF
text = open("Caddyfile").read()
old = """https://decastate.com, https://www.decastate.com {
	tls internal
	encode zstd gzip
	root * /srv/decastate
	file_server
}"""
new = """https://decastate.com, https://www.decastate.com {
	tls internal
	encode zstd gzip
	handle /api/* {
		reverse_proxy host.docker.internal:8788
	}
	handle {
		root * /srv/decastate
		file_server
	}
}"""
assert old in text, "decastate https block not found in expected form"
open("Caddyfile","w").write(text.replace(old, new))
print("Caddyfile: /api route added")
PYEOF
fi

# --- 3. caddy container can reach host + firewall allows docker nets to 8788 ---
grep -q "host-gateway" docker-compose.prod.yml || python3 - <<PYEOF2
t = open("docker-compose.prod.yml").read()
anchor = "  caddy:\n    image: caddy:2-alpine\n"
assert anchor in t, "caddy anchor not found"
t = t.replace(anchor, anchor + "    extra_hosts:\n      - \"host.docker.internal:host-gateway\"\n", 1)
open("docker-compose.prod.yml","w").write(t)
print("extra_hosts added at correct position")
PYEOF2
sudo docker compose -f docker-compose.prod.yml config >/dev/null && echo "compose validates"
sudo iptables -C INPUT -p tcp --dport 8788 -s 172.16.0.0/12 -j ACCEPT 2>/dev/null || \
  { sudo iptables -I INPUT -p tcp --dport 8788 -s 172.16.0.0/12 -j ACCEPT; sudo netfilter-persistent save; }

# --- 4. restart caddy only, verify everything ---
sudo docker compose -f docker-compose.prod.yml up -d caddy
sleep 4
echo "=== verify through Cloudflare-facing origin ==="
curl -sk https://127.0.0.1/api/health -H "Host: decastate.com" || true
echo
echo "=== agentsigned still healthy ==="
curl -sk -o /dev/null -w "%{http_code}\n" https://127.0.0.1/ -H "Host: agentsigned.com" || true
'
echo "=== public verification ==="
curl -s -o /dev/null -w "https://decastate.com/hub/       → %{http_code}\n" https://decastate.com/hub/
curl -s -w "\n" https://decastate.com/api/health
echo "=== test publish round-trip (tiny, labeled community) ==="
curl -s -X POST https://decastate.com/api/receipts -H "content-type: application/json" \
  -d '{"handle":"launch-test","saved_usd":0.01,"saved_pct":1,"requests":1,"top_models":["test"],"source":"deploy verification"}'
echo
echo "DONE — wall live at https://decastate.com/hub/"
