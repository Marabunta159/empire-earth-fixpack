"""Screenshot of the sandbox game window without focus or input (PrintWindow, PW_RENDERFULLCONTENT).

  python shot.py <out.png> [scale=0.5] [crop=x0,y0,x1,y1 in window pixels]
"""
import ctypes, os, sys
import win32gui, win32ui, win32process
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sbx

ctypes.windll.user32.SetProcessDPIAware()


def window(pid):
    best = []
    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32process.GetWindowThreadProcessId(h)[1] == pid:
            l, t, r, b = win32gui.GetClientRect(h)
            best.append((r * b, h))
    win32gui.EnumWindows(cb, None)
    if not best:
        raise SystemExit('no window for pid %d' % pid)
    return max(best)[1]


def grab(h):
    l, t, r, b = win32gui.GetClientRect(h)
    w, hh = r - l, b - t
    hdc = win32gui.GetWindowDC(h)
    src = win32ui.CreateDCFromHandle(hdc)
    mem = src.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(src, w, hh)
    mem.SelectObject(bmp)
    ok = ctypes.windll.user32.PrintWindow(h, mem.GetSafeHdc(), 3)      # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    info = bmp.GetInfo()
    img = Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']), bmp.GetBitmapBits(True), 'raw', 'BGRX', 0, 1)
    win32gui.DeleteObject(bmp.GetHandle()); mem.DeleteDC(); src.DeleteDC(); win32gui.ReleaseDC(h, hdc)
    return ok, img


if __name__ == '__main__':
    j = sbx.find()
    if not j:
        raise SystemExit('sandbox game not running')
    out = sys.argv[1]
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    ok, img = grab(window(j['pid']))
    if len(sys.argv) > 3:
        img = img.crop(tuple(int(v) for v in sys.argv[3].split(',')))
    if scale != 1:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    img.save(out)
    print('ok' if ok else 'PrintWindow failed', img.size, out)
