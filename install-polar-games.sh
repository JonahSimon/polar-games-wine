#!/bin/bash
# Install Polar Bowler + Polar Golfer (WildTangent, 2005, "Polar Games" double pack CD) under Wine, as the full
# licensed retail versions, from the disc image alone. The disc's own HTML installer can't run under Wine, so
# this does its job directly: extract files, install the disc's Web Driver 4.1.1.28 + DRM, register them,
# install the retail licenses. Tested with Wine 11.18 (WoW64). Usage:
#   ./install-polar-games.sh polar-games.iso [prefix]      (default prefix: ~/.wine-polargames)
# Then: ./play.sh bowler | ./play.sh golfer
set -euo pipefail
ISO=$(realpath "$1"); HERE=$(cd "$(dirname "$0")" && pwd); T="python3 $HERE/polar_tools.py"
export WINEPREFIX=${2:-$HOME/.wine-polargames} WINEDEBUG=-all
for c in wine 7z python3; do command -v $c >/dev/null || { echo "missing: $c"; exit 1; }; done
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT; cd "$W"

echo "== extracting disc"
7z e -y "$ISO" pb.exe pg.exe >/dev/null
for g in pb pg; do 7z x -y -o$g-outer $g.exe >/dev/null; $T nsis-extract $g-outer/\$TEMP/*.exe $g >/dev/null; done
S=pg/e1/TMPSUPPORT
$T nsis-extract $S/WebdSetup.exe webd >/dev/null; $T nsis-extract $S/Drm0302Setup.exe drm >/dev/null

echo "== prefix $WINEPREFIX"
[ -d "$WINEPREFIX" ] || { wineboot -i >/dev/null 2>&1; wineserver -w; }
C=$WINEPREFIX/drive_c; WT="$C/Program Files (x86)/WildTangent"
mkdir -p "$C/Games" "$WT/WebDriver" "$WT/Apps" "$WT/Licenses"
rm -rf "$C/Games/Polar Bowler" "$C/Games/Polar Golfer"
cp -a pb/e1 "$C/Games/Polar Bowler"; cp -a pg/e1 "$C/Games/Polar Golfer"

echo "== Web Driver 4.1.1.28 + DRM 3.2.0.19 (patched for Wine)"
cp -a webd/*/files/. "$WT/WebDriver/"; rm -f "$WT/WebDriver/webdriver.dll.orig"
$T patch-webdriver "$WT/WebDriver/webdriver.dll"
cp drm/*/files/DRM0302.dll "$WT/Apps/"; rm -f "$WT/Apps/DRM0302.dll.orig"; $T patch-drm "$WT/Apps/DRM0302.dll"

echo "== registry"
r(){ wine reg add "$1" /v "$2" /d "$3" /f /reg:32 >/dev/null; }
rd(){ wine reg add "$1" /ve /d "$2" /f /reg:32 >/dev/null; }
WDW='C:\Program Files (x86)\WildTangent\WebDriver'
K='HKLM\Software\Classes\CLSID\{FA13A9FA-CA9B-11D2-9780-00104B242EA3}'   # WildTangent Web Driver (IWT)
rd "$K" 'WebDriver'; rd "$K\InprocServer32" "$WDW\webdriver.dll"; r "$K\InprocServer32" ThreadingModel Apartment
L='HKLM\Software\Classes\TypeLib\{FA13AA2E-CA9B-11D2-9780-00104B242EA3}\1.0'   # without it: white window forever
rd "$L" 'WebDriver 1.0 Type Library'; rd "$L\0\win32" "$WDW\webdriver.dll"; rd "$L\FLAGS" 0; rd "$L\HELPDIR" "$WDW"
r 'HKLM\SOFTWARE\WildTangent' wtRoot 'C:\Program Files (x86)\WildTangent\'
r 'HKLM\SOFTWARE\WildTangent' Apps 'C:\Program Files (x86)\WildTangent\Apps\'
r 'HKLM\SOFTWARE\WildTangent\LicenseStores' WT 'C:\Program Files (x86)\WildTangent\Licenses\'   # trailing \ required

echo "== retail licenses"
for g in "Polar Bowler" "Polar Golfer"; do
  cd "$C/Games/$g"; lic=$(ls TMPLICENSE/*.wtlic); guid=$(basename "$lic" .wtlic)
  $T fix-sto TMPLICENSE/wt.sto TMPLICENSE/wt-wine.sto >/dev/null
  wine 'TMPLICENSE\WDRM3InstallLicense.exe' /q WT 'TMPLICENSE\wt-wine.sto' "$guid" "./$lic" 0302 \
    && echo "   $g: license installed" || { echo "   $g: license install FAILED"; exit 1; }
done
wineserver -w; echo "done. Play with: $HERE/play.sh bowler   or   $HERE/play.sh golfer"
