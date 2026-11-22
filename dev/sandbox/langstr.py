"""Dump string-table entries of a Language.dll:  python langstr.py <dll> [regex]"""
import ctypes, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32', use_last_error=True)
k32.LoadLibraryExW.restype = ctypes.c_void_p
k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint]
u32.LoadStringW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_int]
def strings(path, lo=0, hi=70000):
    h = k32.LoadLibraryExW(path, None, 0x22)   # AS_DATAFILE | AS_IMAGE_RESOURCE
    if not h: raise OSError(ctypes.get_last_error())
    buf = ctypes.create_unicode_buffer(4096)
    out = {}
    for i in range(lo, hi):
        n = u32.LoadStringW(h, i, buf, 4096)
        if n: out[i] = buf.value
    return out
if __name__ == '__main__':
    st = strings(sys.argv[1])
    pat = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
    for i, s in sorted(st.items()):
        if not pat or pat.search(s): print(i, repr(s))
