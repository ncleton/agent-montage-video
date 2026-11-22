#!/usr/bin/env bash
# Installe le service du poste de montage (scripts/agent_host.py serve), toujours actif et relancé s'il s'arrête :
# - Mac : agent launchd de l'utilisateur, démarré à l'ouverture de session, sans sudo ;
# - Linux (VPS des agents, 22/11/2026) : service systemd rossini-agent-host, démarré avec le serveur (compte root).
#   scripts/install_agent_host.sh            installe ou met à jour, puis redémarre le service
#   scripts/install_agent_host.sh --check    dit si le service tourne et si le poste redémarre seul après une coupure
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.rossinienergy.agent-host"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PYTHON="$(command -v python3)"
check() {
  if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    echo "service $LABEL : chargé ($(launchctl print "gui/$(id -u)/$LABEL" | awk '/state =/{print $3; exit}'))"
  else
    echo "service $LABEL : absent ; lancez scripts/install_agent_host.sh"
  fi
  restart="$(pmset -g | awk '/ autorestart /{print $2}')"
  sleep_value="$(pmset -g | awk '/^ sleep /{print $2}')"
  if [ "$sleep_value" = "0" ]; then echo "veille du poste : désactivée"; else echo "veille du poste : $sleep_value min (le service bloque la veille pendant un travail)"; fi
  if [ "$restart" = "1" ]; then
    echo "redémarrage après coupure de courant : activé"
  else
    echo "redémarrage après coupure de courant : DÉSACTIVÉ. Un administrateur du Mac le règle une fois : sudo pmset -a autorestart 1"
  fi
  python3 "$ROOT/scripts/agent_host.py" status || true
}
if [ "$(uname -s)" = Linux ]; then
  UNIT="/etc/systemd/system/rossini-agent-host.service"
  linux_check() {
    echo "service rossini-agent-host : $(systemctl is-active rossini-agent-host 2>/dev/null || true) ($(systemctl is-enabled rossini-agent-host 2>/dev/null || true) au démarrage du serveur)"
    python3 "$ROOT/scripts/agent_host.py" status || true
  }
  if [ "${1:-}" = "--check" ]; then linux_check; exit 0; fi
  [ "$(id -u)" = 0 ] || { echo "Sous Linux, le service systemd s'installe avec le compte root." >&2; exit 1; }
  cat > "$UNIT" <<EOF
[Unit]
Description=Poste de montage Rossini (Oscar) : commandes vidéo de l'ERP
After=network-online.target voicestudio.service
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
Environment=HOME=$HOME
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
ExecStart=$PYTHON $ROOT/scripts/agent_host.py serve
# Arrêter le service ne coupe pas un montage en cours : il est repris au redémarrage (adopt).
KillMode=process
Restart=always
RestartSec=30
StandardOutput=append:/var/log/rossini-agent-host.log
StandardError=append:/var/log/rossini-agent-host.log

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable rossini-agent-host >/dev/null
  systemctl restart rossini-agent-host
  linux_check
  exit 0
fi
if [ "${1:-}" = "--check" ]; then check; exit 0; fi
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PYTHON</string><string>$ROOT/scripts/agent_host.py</string><string>serve</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/rossini-agent-host.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/rossini-agent-host.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"
check
