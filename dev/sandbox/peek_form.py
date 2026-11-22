"""Passive look at the formation state of a running game: ReadProcessMemory only - no injection, no thread, no window.

  python peek_form.py <pid> ee|aoc

Prints for every player the three selection groups, the non-empty hotkey groups and the formation groups
(the groups that are actually moving), each with unit count and formation class / kind.
"""
import ctypes
import struct
import sys
from ctypes import wintypes

pid, game = int(sys.argv[1]), sys.argv[2]
V = {'ee': dict(players=0x918374, local=0x918E84, sel=0x9BC, hot=0x964, fg=0x844),
     'aoc': dict(players=0x930DB4, local=0x9318C4, sel=0x9AC, hot=0x954, fg=0x844)}[game]
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
h = k32.OpenProcess(0x0410, False, pid)          # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
if not h:
    raise SystemExit('OpenProcess failed: %d' % ctypes.get_last_error())


def rd(a, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(a), buf, n, ctypes.byref(got)) or got.value != n:
        raise OSError('read %x' % a)
    return buf.raw


def u32(a):
    return struct.unpack('<I', rd(a, 4))[0]


def rtti(obj):
    try:
        td = u32(u32(u32(obj) - 4) + 12)
        return rd(td + 8, 48).split(b'\0')[0].decode('latin1').replace('.?AV', '').replace('@@', '')
    except OSError:
        return '?'


def form(g):
    f = u32(g + 0x34)
    if not f:
        return 'no formation'
    return '%s kind=%d flag=%d' % (rtti(f), u32(f + 0x58), rd(f + 0x5C, 1)[0])


def count(g):
    b, e = u32(g + 0x24), u32(g + 0x28)
    return (e - b) // 4 if b else 0


print('local player index', u32(V['local']))
for i in range(16):
    p = u32(V['players'] + i * 4)
    if not p:
        continue
    cls = rtti(p)
    print('player[%d] %s' % (i, cls))
    if 'Human' not in cls:                       # computer players: one line (same group fields)
        try:
            g = u32(p + V['sel'])
            hk = set(rtti(u32(u32(p + V['hot'] + n * 4) + 0x34)) for n in range(20) if u32(p + V['hot'] + n * 4))
            print('   internal %s | hotkey groups %s' % (form(g) if g else '-', ', '.join(sorted(hk)) or '-'))
        except OSError:
            print('   (no groups)')
        continue
    for name, off in (('internal ', 0), ('interface', 4), ('third    ', 8)):
        g = u32(p + V['sel'] + off)
        if g:
            print('   %s %08x %-22s units=%-3d %s   link=%08x' % (name, g, rtti(g), count(g), form(g), u32(g + 0x3C)))
    kinds = {}
    for n in range(20):
        g = u32(p + V['hot'] + n * 4)
        if not g:
            continue
        name = rtti(u32(g + 0x34)) if u32(g + 0x34) else 'none'
        kinds[name] = kinds.get(name, 0) + 1
        if count(g):
            print('   hotkey %2d %08x units=%-3d %s' % (n, g, count(g), form(g)))
    print('   hotkey groups: %s' % ', '.join('%d x %s' % (c, k) for k, c in sorted(kinds.items())))
    b, e = u32(p + V['fg'] + 4), u32(p + V['fg'] + 8)
    n = (e - b) // 4 if b else 0
    print('   formation groups: %d' % n)
    for j in range(min(n, 40)):
        g = u32(b + j * 4)
        try:
            print('      %08x %-22s units=%-3d %s' % (g, rtti(g), count(g), form(g)))
        except OSError:
            print('      %08x unreadable' % g)
k32.CloseHandle(h)
