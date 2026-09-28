#!/bin/bash
# Install "Polar Bowler Classic" (the standalone WildTangent release, "Polar Bowler Classic_setup.exe", Inno
# Setup) under Wine and fix its first-frame freeze. Tested with Wine 11.18 (WoW64). Usage:
#   ./install-polar-bowler-classic.sh "Polar Bowler Classic_setup.exe" [prefix]   (default ~/.wine-polarclassic)
# Then: ./play.sh classic [prefix]
set -euo pipefail
SETUP=$(realpath "$1"); HERE=$(cd "$(dirname "$0")" && pwd)
export WINEPREFIX=${2:-$HOME/.wine-polarclassic} WINEDEBUG=-all
[ -d "$WINEPREFIX" ] || { wineboot -i >/dev/null 2>&1; wineserver -w; }
wine "$SETUP" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /TASKS= '/DIR=C:\Games\Polar Bowler Classic'
wineserver -w
python3 "$HERE/polar_tools.py" patch-webdriver "$WINEPREFIX/drive_c/Games/Polar Bowler Classic/webdriver/webdriver.dll"
echo "done. Play with: $HERE/play.sh classic${2:+ $2}"
