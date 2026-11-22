"""Start the fix pack GUI (script or exe), save a screenshot of its window (PrintWindow, no focus / input needed), close it.

  python gui_shot.py <out.png> <wait seconds> [--exe <EE-FixPack.exe>] -- <arguments for the GUI>
"""
import ctypes
import os
import subprocess
import sys
import time

import win32con
import win32gui
import win32process
import win32ui
from PIL import Image

ctypes.windll.user32.SetProcessDPIAware()
out, wait = sys.argv[1], float(sys.argv[2])
rest = sys.argv[3:]
exe = None
if rest and rest[0] == '--exe':
    exe, rest = rest[1], rest[2:]
if rest and rest[0] == '--':
    rest = rest[1:]
here = os.path.dirname(os.path.abspath(__file__))
cmd = ([exe] if exe else [sys.executable, os.path.join(here, 'ee_fixpack.py')]) + rest
p = subprocess.Popen(cmd)
time.sleep(wait)


def windows():
    res = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h).startswith('Empire Earth Fix Pack'):
            res.append(h)
    win32gui.EnumWindows(cb, None)
    return res


hs = windows()
if not hs:
    print('window not found (process alive: %s)' % (p.poll() is None))
    sys.exit(1)
h = hs[0]
l, t, r, b = win32gui.GetWindowRect(h)
w, hh = r - l, b - t
hdc = win32gui.GetWindowDC(h)
src = win32ui.CreateDCFromHandle(hdc)
mem = src.CreateCompatibleDC()
bmp = win32ui.CreateBitmap()
bmp.CreateCompatibleBitmap(src, w, hh)
mem.SelectObject(bmp)
ctypes.windll.user32.PrintWindow(h, mem.GetSafeHdc(), 2)
info = bmp.GetInfo()
img = Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']), bmp.GetBitmapBits(True), 'raw', 'BGRX', 0, 1)
img.save(out)
print('saved', out, img.size)
win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
try:
    p.wait(10)
except subprocess.TimeoutExpired:
    p.kill()
