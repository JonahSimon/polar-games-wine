# Polar Bowler & Polar Golfer on Linux (Wine) and 64-bit Windows: fixes and install scripts

WildTangent's **Polar Bowler** and **Polar Golfer** (2004–2006) don't work under Wine out of the box. They
freeze on the first frame of gameplay, the disc installer never gets past "Installing", and the DRM refuses
to install the retail license. This kit fixes all of it. Every game below was tested from the original
downloads, in a fresh Wine prefix, through to actual gameplay.

| Release | Result | Script |
|---|---|---|
| **Polar Games double pack CD** (`polar-games.iso`): Polar Bowler + Polar Golfer | ✅ both play, **full licensed retail versions** (no demo timer) | `install-polar-games.sh` |
| **Polar Bowler Classic** (standalone, `Polar Bowler Classic_setup.exe`) | ✅ plays | `install-polar-bowler-classic.sh` |

Tested on Arch-based Linux with **Wine 11.18** (the default WoW64 build), KDE Plasma on Wayland (XWayland).
Nothing here needs a 32-bit Wine or a Windows VM.

**On 64-bit Windows?** The disc's installer freezes at 90% there. The fix is one registry file, and none of
the Wine steps below are needed. Polar Bowler Classic works on Windows as is: see [64-bit Windows](#64-bit-windows-the-disc-installer-freezes-at-90).

**This kit contains no game files.** It is only scripts, Wine patches and this write-up. You need your own
copy of the game (the ISO or setup exe); the scripts read from it and patch the installed copy in place.

## Quick start

Requirements: `wine`, `7z` (p7zip), `python3`. Optional: `python-xlib`, which lets the scripts switch the
game out of fullscreen for you (see [Fullscreen](#fullscreen)).

Get the scripts first (or use **Code > Download ZIP** at the top of this page and unzip it):
```sh
git clone https://github.com/JonahSimon/polar-games-wine
cd polar-games-wine
```
Then point them at your own copy of the game:

**Double pack disc (Bowler + Golfer):**
```sh
./install-polar-games.sh polar-games.iso        # creates ~/.wine-polargames
./play.sh bowler
./play.sh golfer
```

**Polar Bowler Classic:**
```sh
./install-polar-bowler-classic.sh "Polar Bowler Classic_setup.exe"   # creates ~/.wine-polarclassic
./play.sh classic
```

Both installers take an optional second argument with a different prefix path. They make their own
prefix, so any other Wine setup you have is left alone.

### Files these were tested with
| File | Size | MD5 | SHA-1 |
|---|---|---|---|
| `polar-games.iso` | 623017984 | `c793456e546b9a000d48073cf7b609db` | `b2aeb7bd00ba5ff9f66b54dfdfac22ac6e9e5c6f` |
| `Polar Bowler Classic_setup.exe` | 13566343 | `6210f3b3bc05ec0b8ea3a157291d19e9` | `246589fd9f1093a92679bf3aa9abf86a5b0a58db` |

Other copies should work as long as they carry the same WildTangent components. The patch tool checks the
exact bytes it expects before changing anything, and stops with an error if they don't match.

---

## 64-bit Windows: the disc installer freezes at 90%

The disc games install and play on 32-bit Windows (XP era), but on 64-bit Windows (7, 8, 10, 11) the
installer stops at **90% ("Verifying Web Driver...")** and never finishes. You may first see a box saying
**"Unable to locate kernel component: wtKernel"**. The disc menu also stays on top of everything, so the
installer window can be hidden behind it and the whole thing looks frozen.

### How to fix it, step by step

You don't need Linux or any of the scripts for this. You need the disc (or `polar-games.iso`) and one small
file from this page.

1. **Download this kit.** Near the top of this page, click the green **Code** button, then
   **Download ZIP**.
2. **Unzip it.** Open your Downloads folder, right-click `polar-games-wine-main.zip`, choose
   **Extract All...**, then click **Extract**.
3. **Apply the fix.** In the extracted folder, open the `windows` folder and double-click
   `polar-games-64bit-fix.reg`. Windows asks a few questions ("Do you want to allow this app...",
   "Are you sure you want to continue?"). Answer **Yes** each time, then click **OK** when it says the keys
   were added.
4. **Open the disc.** Put the CD in, or double-click `polar-games.iso` (Windows 8 and later open ISO files
   like a CD). If the game's menu pops up, close it: it can hide the installer and make it look frozen.
   Then open **This PC** and open the disc drive to see its files.
5. **Install a game.** Right-click `polarbowler_install.exe` (or `polargolfer_install.exe` for Golfer),
   choose **Run as administrator**, click **Yes**, and go through the installer as normal. Do the same with
   the other one if you want both games.
6. **Play.** Use the shortcuts the installer puts on your desktop or Start menu.

If you already tried installing before this fix, just do steps 1 to 5. You don't need to uninstall first.

<details>
<summary>Prefer a command? (same fix, no download)</summary>

Search the Start menu for `cmd`, right-click **Command Prompt**, choose **Run as administrator**, and paste:

    reg add HKLM\SOFTWARE\WildTangent /v wtRoot /d "C:\WildTangent\\" /f /reg:32

It should say "The operation completed successfully." Then continue from step 4.
</details>

### What the fix changes

The file sets one value, which tells WildTangent's installer to use `C:\WildTangent` instead of
`C:\Program Files (x86)\WildTangent`:

    [HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\WildTangent]
    "wtRoot"="C:\\WildTangent\\"

**Why it breaks.** The disc installer runs a WildTangent sub-installer, `CDASilentInstall.exe` (an NSIS
installer from 2005). It loads its own DLLs through NSIS's `System` plugin with calls written like
`C:\...\CDA\cdaEngine0500.dll::cdaInstallerEngineInit(...)`. That old plugin treats the first `(` in the
string as the start of the argument list. On 64-bit Windows the path is `C:\Program Files (x86)\...`, so it
splits at the `(` of `(x86)`, misreads the rest, and crashes (access violation in `System.dll` at offset
`0x1b08`). The sub-installer dies silently. WildTangent's engine components, including `wtKernel`, never get
registered, and the main installer waits forever at the "Verifying Web Driver" step. 32-bit Windows has
plain `C:\Program Files\`, with no parentheses, which is why it worked there.

Tested on Windows 10 22H2 x64 (in a VM), starting from a clean install each time:

| | Result |
|---|---|
| Disc installer, no fix | `CDASilentInstall.exe` crashes (`0xC0000005`, `System.dll+0x1b08`), stuck at 90% after the wtKernel message. Every time. XP compatibility mode doesn't help. |
| Same, with the `.reg` fix | Both installers finish. The disc's retail licenses install by themselves (no demo timer). Polar Bowler bowls and Polar Golfer plays a hole, with the original unpatched files. |

**Polar Bowler Classic** (`Polar Bowler Classic_setup.exe`) needs no fix on 64-bit Windows. It's a later
repack with a normal Inno Setup installer that installs to `C:\Games` and doesn't use the CDA installer.
Tested on the same Windows 10 x64 machine, it installed and bowled.

The Wine problems in the next section don't apply to Windows: real Windows accepts the DirectInput call and
the certificate store as they are.

Two things came up only because the test machine was a VM with no GPU and no sound card. You probably won't
hit them on a real PC:
- "Sorry, Polar Bowler requires 3D hardware acceleration", or a crash in `d3d10warp.dll`: Windows has no
  real 3D driver. If this happens on real hardware, [dgVoodoo2](https://github.com/dege-diosg/dgVoodoo2)
  fixes it: copy `MS\x86\DDraw.dll` and `D3DImm.dll` (plus `dgVoodoo.conf`) next to `Polar.exe`/`golf.exe`.
- "FMOD Init Failed!" (Golfer only): there's no audio output device.

The installer also sets up WildTangent's background "Persistent" service to run at login, which triggers a
UAC prompt. The games don't need it; you can say No.

---

## What's broken under Wine, and how each fix works

There are five separate problems. **All three games** hit #1. **The disc games** hit all five.

### 1. The freeze on the first frame of gameplay (all three games)

The menus work, you click Play, and the lane or course appears for one frame and never moves again. The
process stays alive; there's no crash dialog.

The cause is in WildTangent's engine, the **Web Driver** (`webdriver.dll`). Every game here uses it (3.3.1.3
in Classic, 4.1.1.28 on the disc). To read the mouse, it calls

    DirectInputCreateA(hinst = NULL, version = 0x0300, ...)

Windows accepts a `NULL` instance handle for DirectX 3. **Wine rejects it** with `DIERR_INVALIDPARAM`. Wine's
own test suite knows Windows allows it; the checks are marked `todo_wine`. From there it falls apart:

1. Mouse setup fails, so the engine's `pollMouse()` returns `E_FAIL`.
2. The game's COM wrapper throws a C++ `_com_error` from inside its per-frame window message (`WM_USER+1002`).
3. Wine can't pass a C++ exception out of a window procedure. It swallows it (in a `+seh` log you'll see
   `err:seh:dispatch_user_callback ignoring exception e06d7363`).
4. The handler never reaches the `SetEvent` the render thread is waiting on. **The render thread waits forever.**

**Fix:** `polar_tools.py patch-webdriver` patches `webdriver.dll` to pass `GetModuleHandleA(NULL)` instead
of `NULL`. It finds the single call site by its byte pattern, adds a 27-byte stub in unused space at the end
of the code section, and jumps to it. Both Web Driver versions have exactly one such site. The original is
kept as `webdriver.dll.orig`.

Control test: put the original `webdriver.dll` back and the game freezes on the first frame again, with the
swallowed exception in the log.

### 2. The disc installer never finishes (disc only)

`pb.exe` and `pg.exe` on the CD are NSIS installer stubs. Run them wrong and they deadlock on their own
internal lock (`RtlpWaitForCriticalSection section 0040B468`). That's the error people have reported
online for years, and it isn't the game. The stub insists on "the original disc": it walks drive letters
with `GetDriveTypeA` and **stops at the first letter that doesn't exist**. So the disc has to be **D:** and
typed CD-ROM (`HKLM\Software\Wine\Drives`, `d:`=`cdrom`). Also set `DBUS_SYSTEM_BUS_ADDRESS=unix:path=/nonexistent`,
or Wine's mount manager may hand D: to a real device and delete your mapping.

Even then, the **second-stage installer can't run under Wine.** Its wizard is HTML pages shown in an embedded
browser (`wtInstallerUI0200.dll`). Under Wine-Gecko the page loads, but Gecko reports `DoContent failed`
and passes it to its "helper app" service. The page's JavaScript never runs, the window never appears, and
the installer waits forever. `/S` (silent) waits too. This one is **not fixed**. The kit skips the
installer instead:

- **`polar_tools.py nsis-extract`** reads the 2005-era NSIS format (stored and deflate) that 7-Zip can't
  open, and pulls out every file along with its install path.
- `install-polar-games.sh` then does what the installer's script does.

### 3. Web Driver registration (disc only): a white window, or "class not registered"

The disc games load the engine through COM, not from their own folder. The script registers:

- **CLSID `{FA13A9FA-CA9B-11D2-9780-00104B242EA3}`** → `webdriver.dll`. It must go in the **32-bit
  registry view** (`wine reg add ... /reg:32`). In the 64-bit view the game still says "not registered".
- **TypeLib `{FA13AA2E-CA9B-11D2-9780-00104B242EA3}` 1.0**. Without this, Golfer shows **a solid white
  window forever, with no error at all**. It's looping on `LoadRegTypeLib`.
- The disc's own Web Driver 4.1.1.28 files, extracted from `TMPSUPPORT/WebdSetup.exe`.

### 4. The DRM and the retail license (disc only)

The disc copies carry **full retail licenses** ("Polar Golfer full", unlimited play). Without the
WildTangent DRM the games run as a **demo with "0 minutes remaining"**. The script installs `DRM0302.dll`
(DRM 3.2.0.19, from `TMPSUPPORT/Drm0302Setup.exe`) into `C:\Program Files (x86)\WildTangent\Apps\`, sets
`HKLM\SOFTWARE\WildTangent` `Apps` and `LicenseStores\WT`, then runs the disc's own
`WDRM3InstallLicense.exe`. **The license-store path needs a trailing backslash**; without it the tool
writes `...\LicensesWT.sto`. That tool trips **two bugs in Wine's crypt32**:

- **The certificate store loads empty.** `WT.sto` is a certificate store saved by Windows, which writes each
  certificate's properties *before* the certificate itself. Wine does the same when saving, but its
  reader rejects that order (`prop id 2 before a context id`) and returns an empty store. The DRM then
  can't find its signing certificate: *"Could not encrypt license file (WT - …) - Error -1"*.
  **Fix:** `polar_tools.py fix-sto` rewrites the store certificate-first. The script feeds the rewritten
  copy to the license tool and leaves the original untouched.
- **Then it crashes on close.** The DRM calls `CertCloseStore(store, CERT_CLOSE_STORE_FORCE_FLAG)` while
  still holding the signing certificate. Windows allows this; Wine hits an assert and kills the process
  (`Assertion failed: !context->ref, file ../wine/dlls/crypt32/context.c, line 96`).
  **Fix:** `polar_tools.py patch-drm` changes that one `push 1` flag to `push 0`, a normal close. It's one
  byte, and the original is kept.

After that, the license installs and both games start as the full versions.

### 5. Fullscreen

All of these games start fullscreen at 640×480. Under Wine that shows up as the game in the top-left
corner of a black, desktop-sized window. The in-game "windowed" option doesn't stick between runs.
**Press Esc** (the game's own leave-fullscreen key) and it drops to a normal 640×480 window.
`play.sh` does that for you through `wt-unfullscreen.py` if `python-xlib` is installed.

---

## Doing it by hand (no scripts)

For the disc, in your prefix:
1. Extract `pb.exe` and `pg.exe` from the ISO. `7z x` each one to get `$TEMP/<GUID>.exe`, then run
   `polar_tools.py nsis-extract` on that to get the game files (the `e1/` folder = `$INSTDIR`).
2. Copy them to `C:\Games\Polar Bowler` and `C:\Games\Polar Golfer`.
3. Use `nsis-extract` on `TMPSUPPORT/WebdSetup.exe` and `TMPSUPPORT/Drm0302Setup.exe`. Copy the
   `files/` contents of the first to a Web Driver folder, and `DRM0302.dll` from the second to
   `C:\Program Files (x86)\WildTangent\Apps\`.
4. `patch-webdriver` the Web Driver's `webdriver.dll`; `patch-drm` the `DRM0302.dll`.
5. Add the registry keys in section 3 and section 4 (32-bit view). `install-polar-games.sh` has the exact
   values.
6. For each game: `fix-sto TMPLICENSE/wt.sto TMPLICENSE/wt-wine.sto`, then from the game folder run
   `wine 'TMPLICENSE\WDRM3InstallLicense.exe' /q WT 'TMPLICENSE\wt-wine.sto' <GUID> ./TMPLICENSE/<GUID>.wtlic 0302`,
   where `<GUID>` is the `.wtlic` file name (Bowler `6E19C296-…`, Golfer `5F7E059C-…`).
7. Run `Polar.exe` (Bowler) or `golf.exe` (Golfer) and press Esc.

For Classic: install `Polar Bowler Classic_setup.exe` normally under Wine (its Inno installer works), then
run `patch-webdriver` on `<install dir>\webdriver\webdriver.dll`.

## Troubleshooting

- **Freezes on the first gameplay frame:** `webdriver.dll` isn't patched, or the game loaded a different copy.
  Run with `WINEDEBUG=+seh` and look for `ignoring exception e06d7363`.
- **White window forever (disc games):** the TypeLib key is missing, or in the wrong registry view.
- **"0 minutes remaining in the Demo" / UNLOCK button:** the license didn't install. Rerun the license step
  and check for a new file in `C:\Program Files (x86)\WildTangent\Licenses\`.
- **`error: ... not found exactly once`:** your copy of the DLL is a different build from the tested ones.
  Nothing was changed.
- **Harmless log noise:** `class {a62fa99e-922e-4eca-a1d9-b54ef294a3cc} not registered` (WildTangent's
  long-dead ad/online service), `winebth` driver errors.
- Online features (leaderboards, "More Games", buy/unlock buttons) point at WildTangent servers that no
  longer exist.

## Proper fixes in Wine

The binary patches are workarounds. The real bugs are in Wine, and `wine-patches/` has three fixes written
against current Wine master, each with tests:

1. `dinput: Allow a NULL instance handle for DirectInput version 0x300.` (fixes #1 and removes three
   `todo_wine`s)
2. `crypt32: Don't free contexts still referenced on a forced store close.` (the assert in #4)
3. `crypt32: Read serialized store properties that precede their context.` (the empty store in #4, with a
   new round-trip test)

With those three applied, the **original, unpatched** `webdriver.dll`, `DRM0302.dll` and `WT.sto` all work.
That was checked with a fresh prefix on a patched Wine build: both disc games and Classic played. Wine's
dinput and crypt32 test suites pass with 0 failures on x86_64 and i386. Removing any one fix makes exactly
its own tests fail. Once these are in Wine, only the registry and license steps are needed.

## Files

- `install-polar-games.sh`: the disc, from ISO to playable
- `install-polar-bowler-classic.sh`: the standalone Classic installer + fix
- `play.sh`: launch a game and leave fullscreen
- `polar_tools.py`: NSIS extractor, the two DLL patches, the certificate-store fix (Python stdlib only)
- `wt-unfullscreen.py`: sends the Esc for `play.sh`
- `windows/polar-games-64bit-fix.reg`: the 64-bit Windows installer fix
- `wine-patches/`: the upstream Wine patches (LGPL, like Wine)

The scripts are MIT licensed (see `LICENSE`). WildTangent, Polar Bowler and Polar Golfer belong to their owners; no game files are included.
