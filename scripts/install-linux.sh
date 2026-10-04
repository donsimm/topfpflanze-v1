#!/usr/bin/env bash
# Installiert Topfpflanze als normales Programm (Programmmenü, optional Autostart).
# Aufruf im Projektordner:  bash scripts/install-linux.sh [--autostart]
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$DIR/.venv/bin/python"
if [ ! -x "$PY" ]; then
    echo "Virtuelle Umgebung fehlt. Zuerst im Projektordner ausführen:" >&2
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[linux-keys]\"" >&2
    exit 1
fi

BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons"
mkdir -p "$BIN" "$APPS" "$ICONS"

cp "$DIR/src/topfpflanze/icons/topfpflanze.png" "$ICONS/topfpflanze.png"

# Startskript: löst sich vom Terminal, schreibt Meldungen in eine Logdatei
cat > "$BIN/topfpflanze" <<LAUNCH
#!/usr/bin/env bash
mkdir -p "\$HOME/.local/share/topfpflanze"
exec "$PY" -m topfpflanze "\$@" >>"\$HOME/.local/share/topfpflanze/topfpflanze.log" 2>&1
LAUNCH
chmod +x "$BIN/topfpflanze"

cat > "$APPS/topfpflanze.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Topfpflanze
Comment=Desktop-Pflanzen, die durch Klicks und Tastaturanschläge wachsen
Exec=$BIN/topfpflanze
Icon=$ICONS/topfpflanze.png
Terminal=false
Categories=Game;
DESKTOP

if [ "${1:-}" = "--autostart" ]; then
    mkdir -p "$HOME/.config/autostart"
    cp "$APPS/topfpflanze.desktop" "$HOME/.config/autostart/topfpflanze.desktop"
    echo "Autostart eingerichtet (startet beim Anmelden)."
fi

echo "Fertig. Topfpflanze steht jetzt im Programmmenü (Suche: «Topfpflanze»)."
echo "Im Terminal: topfpflanze   (falls nicht gefunden: abmelden und neu anmelden)"
echo "Aktualisieren: im Projektordner «git pull», dann das Spiel neu starten."
