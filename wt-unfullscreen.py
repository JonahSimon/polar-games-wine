#!/usr/bin/env python3
"""WildTangent games start fullscreen; under Wine the 640x480 picture is drawn in the corner of a black
desktop-sized window. Wait for that window and send it Esc (the game's own 'leave fullscreen' key),
which drops it to a normal 640x480 window. Needs X11/XWayland and python-xlib (pip install python-xlib)."""
import time
from Xlib import display, X, XK
from Xlib.protocol import event

d = display.Display(); root = d.screen().root

def find(w):
    try:
        if w.get_wm_name() == 'WildTangent FullScreen' and w.get_attributes().map_state == X.IsViewable: return w
        for c in w.query_tree().children:
            r = find(c)
            if r: return r
    except Exception: pass

for _ in range(90):
    w = find(root)
    if w:
        time.sleep(2)
        kc = d.keysym_to_keycode(XK.string_to_keysym('Escape'))
        for cls in (event.KeyPress, event.KeyRelease):
            w.send_event(cls(time=X.CurrentTime, root=root, window=w, same_screen=1, child=X.NONE,
                             root_x=0, root_y=0, event_x=10, event_y=10, state=0, detail=kc), propagate=False)
            d.flush(); time.sleep(0.2)
        break
    time.sleep(1)
