#!/usr/bin/env python3
"""Tools for running WildTangent's Polar Bowler / Polar Golfer under Wine. Python 3 stdlib only.

  polar_tools.py nsis-extract <installer.exe> <outdir>   extract an early NSIS (2.0-era) installer, stored or
                                                         deflate, which 7-Zip cannot open. Files land in
                                                         <outdir>/<var>/..., <var> = hex code of the NSIS path
                                                         variable ($INSTDIR etc.)
  polar_tools.py patch-webdriver <webdriver.dll>         fix the DirectInput freeze (Web Driver 3.3.1.3 / 4.1.1.28)
  polar_tools.py patch-drm <DRM0302.dll>                 fix the license-install crash (DRM 3.2.0.19)
  polar_tools.py fix-sto <in.sto> <out.sto>              make WT.sto readable by Wine's crypt32

Each patch checks the exact original bytes first, keeps <file>.orig, and refuses to run twice.
"""
import os, shutil, struct, sys, zlib

def need(cond, msg):
    if not cond: sys.exit('error: ' + msg)

# ---------- minimal PE parsing ----------
def pe(buf):
    o = struct.unpack_from('<I', buf, 0x3c)[0]; need(buf[o:o+4] == b'PE\0\0', 'not a PE file')
    nsec, = struct.unpack_from('<H', buf, o + 6); optsz, = struct.unpack_from('<H', buf, o + 20)
    opt = o + 24; base, = struct.unpack_from('<I', buf, opt + 28)
    secs = []
    for i in range(nsec):
        s = opt + optsz + 40 * i
        name = buf[s:s+8].rstrip(b'\0').decode(); vsz, va, rsz, rptr = struct.unpack_from('<IIII', buf, s + 8)
        secs.append((name, va, vsz, rptr, rsz))
    imp_rva, = struct.unpack_from('<I', buf, opt + 104)
    return base, secs, imp_rva

def rva2off(secs, rva):
    for _, va, vsz, rptr, rsz in secs:
        if va <= rva < va + max(vsz, rsz): return rva - va + rptr
    raise ValueError(hex(rva))

def iat_slot(buf, dll, func):
    """VA of the import address table slot for dll!func."""
    base, secs, imp = pe(buf); d = rva2off(secs, imp)
    while True:
        oft, _, _, name, ft = struct.unpack_from('<IIIII', buf, d); d += 20
        if not name: break
        if buf[rva2off(secs, name):].split(b'\0', 1)[0].decode().lower() != dll.lower(): continue
        t, i = rva2off(secs, oft or ft), 0
        while True:
            ent, = struct.unpack_from('<I', buf, t + 4 * i)
            if not ent: break
            if not ent & 0x80000000 and buf[rva2off(secs, ent) + 2:].split(b'\0', 1)[0].decode() == func:
                return base + ft + 4 * i
            i += 1
    raise ValueError(f'{dll}!{func} not imported')

def backup_and_write(path, data):
    if os.path.exists(path + '.orig'): sys.exit(f'{path}.orig exists: already patched? (restore it first)')
    shutil.copy2(path, path + '.orig'); open(path, 'wb').write(data); print('patched', path, '(original kept as .orig)')

# ---------- patches ----------
def patch_webdriver(path):
    """Web Driver's mouse-poll object calls DirectInputCreateA(hinst=NULL, 0x300, ...). Windows accepts a NULL
    hinst for DirectX 3; Wine returns DIERR_INVALIDPARAM, pollMouse() fails, the game throws a C++ exception
    inside its frame handler, Wine swallows it, and the render thread waits forever (freeze on first frame).
    Patch: pass GetModuleHandleA(NULL) instead, via a 27-byte cave in .text padding."""
    need(not os.path.exists(path + '.orig'), f'{path}.orig exists: already patched')
    b = bytearray(open(path, 'rb').read()); base, secs, _ = pe(b)
    site_bytes = bytes.fromhex('6a00536800030000' '6a00ffd0')   # push 0; push ebx; push 0x300; push 0; call eax
    need(b.count(site_bytes) == 1, 'DirectInputCreate call site not found exactly once (unknown Web Driver version)')
    so = b.find(site_bytes)
    text = next(s for s in secs if s[0] == '.text'); _, va, vsz, rptr, rsz = text
    cave_off = rptr + ((vsz + 15) & ~15); need(cave_off + 32 <= rptr + rsz and not any(b[cave_off:cave_off+32]), 'no code cave')
    site_va = base + va + so - rptr; cave_va = base + va + cave_off - rptr; back_va = site_va + len(site_bytes)
    gmh = iat_slot(b, 'KERNEL32.dll', 'GetModuleHandleA')
    cave = (b'\x50' b'\x6a\x00' + b'\xff\x15' + struct.pack('<I', gmh) +         # push eax; push 0; call [GetModuleHandleA]
            b'\x59' b'\x6a\x00' b'\x53' b'\x68\x00\x03\x00\x00' b'\x50' b'\xff\xd1' +  # pop ecx; push 0; push ebx; push 0x300; push eax; call ecx
            b'\x68' + struct.pack('<I', back_va) + b'\xc3')                      # push back; ret
    b[cave_off:cave_off+len(cave)] = cave
    b[so:so+12] = b'\xe9' + struct.pack('<i', cave_va - (site_va + 5)) + b'\x90' * 7
    # the DLL has no ASLR flag and loads at its preferred base, so the absolute addresses above hold
    backup_and_write(path, bytes(b))

def patch_drm(path):
    """DRM0302.dll calls CertCloseStore(store, CERT_CLOSE_STORE_FORCE_FLAG) while still holding the signer
    certificate; Wine asserts '!context->ref' in crypt32 and the license installer dies. Close normally."""
    need(not os.path.exists(path + '.orig'), f'{path}.orig exists: already patched')
    b = bytearray(open(path, 'rb').read())
    pat = b'\x6a\x01\xff\x75\xfc\xff\x15' + struct.pack('<I', iat_slot(b, 'CRYPT32.dll', 'CertCloseStore'))
    need(b.count(pat) == 1, 'CertCloseStore(FORCE) site not found exactly once (unknown DRM version)')
    b[b.find(pat) + 1] = 0
    backup_and_write(path, bytes(b))

def fix_sto(src, dst):
    """A serialized cert store written by Windows puts each context's properties BEFORE the certificate.
    Wine's reader (11.x) rejects that and loads an empty store, so the DRM can't find its signer
    ('Could not encrypt license file ... Error -1'). Rewrite it certificate-first."""
    b = open(src, 'rb').read(); need(b[:8] == b'\0\0\0\0CERT', 'not a serialized store')
    out, pend, p, n = bytearray(b[:8]), [], 8, 0
    while p + 12 <= len(b):
        pid, _, sz = struct.unpack_from('<III', b, p); el = b[p:p+12+sz]; p += 12 + sz
        if pid in (0x20, 0x21, 0x22): out += el + b''.join(pend); pend = []; n += 1
        else: pend.append(el)
    out += b''.join(pend); open(dst, 'wb').write(out); print(f'{n} certificates reordered -> {dst}')

# ---------- early NSIS extraction ----------
def nsis_extract(exe_path, outdir):
    exe = open(exe_path, 'rb').read(); i = exe.find(b'NullsoftInst'); need(i > 8, 'not an NSIS installer')
    fh = i - 8; arclen, = struct.unpack_from('<i', exe, fh + 24); p = fh + 28; blocks = []
    while p < fh + arclen:
        L, = struct.unpack_from('<I', exe, p); c, L = L >> 31, L & 0x7fffffff
        blocks.append((p, c, L)); p += 4 + L
    def data(k):
        bp, c, L = blocks[k]; raw = exe[bp+4:bp+4+L]
        return zlib.decompress(raw, -15) if c else raw
    h = data(0); dstart = blocks[1][0]; byrel = {bp - dstart: k for k, (bp, c, L) in enumerate(blocks)}
    best = []
    for align in range(0, 24, 4):
        ents = [struct.unpack_from('<6i', h, o) for o in range(align, len(h) - 24, 24)]
        ex = [e for e in ents if e[0] == 21 and e[3] in byrel]
        if len(ex) > len(best): best, entries = ex, ents
    need(best, 'no file entries found (unsupported NSIS version)')
    base = next(bs for bs in range(len(h) - 1, 0, -1)
                if all(0 < bs + e[2] < len(h) and h[bs + e[2] - 1] == 0 and 32 < h[bs + e[2]] < 0x7f for e in best[:20]))
    def s(o):
        raw = h[base+o:h.index(b'\0', base+o)]; var = ''
        if raw and raw[0] >= 0x80: var, raw = f'{raw[0]:02x}', raw[1:]
        return var, raw.decode('latin-1').lstrip('\\')
    outvar, outpath, n = 'xx', '', 0
    for e in entries:
        if e[0] == 14 and e[2] == 1 and 0 <= e[1] < len(h) - base: outvar, outpath = s(e[1])
        if e[0] == 21 and e[3] in byrel:
            _, name = s(e[2]); dst = os.path.join(outdir, outvar or 'xx', *outpath.split('\\'), name)
            os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, 'wb').write(data(byrel[e[3]])); n += 1
    print(f'{n} files -> {outdir}')

if __name__ == '__main__':
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ('', [])
    {'nsis-extract': nsis_extract, 'patch-webdriver': patch_webdriver, 'patch-drm': patch_drm, 'fix-sto': fix_sto}.get(
        cmd, lambda *a: sys.exit(__doc__))(*args)
