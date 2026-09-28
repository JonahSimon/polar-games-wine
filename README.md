# Polar Bowler & Polar Golfer on Linux (Wine): fixes and install scripts

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

**This kit contains no game files.** It is only scripts, Wine patches and this write-up. You need your own
copy of the game (the ISO or setup exe); the scripts read from it and patch the installed copy in place.

## Quick start

Requirements: `wine`, `7z` (p7zip), `python3`. Optional: `python-xlib`, which lets the scripts switch the
game out of fullscreen for you (see [Fullscreen](#fullscreen)).

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

## What's actually broken, and how each fix works

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
- `wine-patches/`: the upstream Wine patches (LGPL, like Wine)

The scripts are MIT licensed (see `LICENSE`). WildTangent, Polar Bowler and Polar Golfer belong to their owners; no game files are included.
