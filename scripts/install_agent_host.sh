#!/usr/bin/env bash
# Installe le service du poste de montage (scripts/agent_host.py serve) comme agent launchd de l'utilisateur :
# toujours actif, relancé s'il s'arrête, démarré à l'ouverture de session. Sans sudo.
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
