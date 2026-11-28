#!/usr/bin/env bash
# Voix off d'Oscar sur un poste sans carte graphique (VPS des agents, 22/11/2026) : ouvre un tunnel SSH permanent
# 127.0.0.1:3900 du poste -> VoiceStudio du Mac mini de Tony (127.0.0.1:3900), service systemd voix-mac-tunnel.
# Seules la voix et la transcription passent par là (skill voix-sur-le-mac).
#   scripts/install_voice_tunnel.sh            installe ou met à jour, puis redémarre le tunnel
#   scripts/install_voice_tunnel.sh --check    dit si le tunnel tourne et ce qui répond sur 127.0.0.1:3900
# Pré-requis : l'hôte SSH macmini-tony dans ~/.ssh/config (clé sans phrase de passe, Tailscale).
set -euo pipefail
UNIT=/etc/systemd/system/voix-mac-tunnel.service
check() {
  echo "service voix-mac-tunnel : $(systemctl is-active voix-mac-tunnel 2>/dev/null || true)"
  echo "VoiceStudio sur 127.0.0.1:3900 : $(curl -s -m 5 http://127.0.0.1:3900/health || echo 'aucune réponse')"
}
if [ "${1:-}" = "--check" ]; then check; exit 0; fi
[ "$(id -u)" = 0 ] || { echo "Le service systemd s'installe avec le compte root." >&2; exit 1; }
ssh -o BatchMode=yes -o ConnectTimeout=8 macmini-tony true || { echo "SSH vers macmini-tony impossible : régler ~/.ssh/config et la clé." >&2; exit 1; }
cat > "$UNIT" <<EOF
[Unit]
Description=Voix d'Oscar : tunnel vers VoiceStudio du Mac mini de Tony (127.0.0.1:3900 -> Mac 127.0.0.1:3900)
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
Environment=HOME=$HOME
ExecStart=/usr/bin/ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:3900:127.0.0.1:3900 macmini-tony
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable voix-mac-tunnel >/dev/null
systemctl restart voix-mac-tunnel
sleep 5
check
