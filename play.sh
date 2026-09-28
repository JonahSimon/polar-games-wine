#!/bin/bash
# ./play.sh bowler|golfer|classic [prefix]   (classic defaults to ~/.wine-polarclassic)   -- start the game, then drop it from fullscreen to a normal window
[ "$1" = classic ] && def=$HOME/.wine-polarclassic || def=$HOME/.wine-polargames
export WINEPREFIX=${2:-$def}; HERE=$(cd "$(dirname "$0")" && pwd)
case "$1" in bowler) cd "$WINEPREFIX/drive_c/Games/Polar Bowler" && exe=Polar.exe ;;
             golfer) cd "$WINEPREFIX/drive_c/Games/Polar Golfer" && exe=golf.exe ;;
             classic) cd "$WINEPREFIX/drive_c/Games/Polar Bowler Classic" && exe="Polar Bowler Classic.exe" ;;
             *) echo "usage: $0 bowler|golfer|classic [prefix]"; exit 1 ;; esac
wine "$exe" & python3 "$HERE/wt-unfullscreen.py" 2>/dev/null || echo "(python-xlib missing: press Esc in the game to leave fullscreen)"
wait
