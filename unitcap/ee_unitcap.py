"""Empire Earth / Art of Conquest: raise the number of objects the game can draw per frame.

What happens without this patch ("units disappear when many are on screen")
  Every frame the game collects the objects inside the view into two fixed tables that are
  part of one global object (EE 0x8D2CB8, AoC 0x8E9458):
      512  x 0x148 bytes   units, buildings, corpses, projectiles ...   (count: +0x3F880)
      1536 x 0x3C  bytes   simple objects (trees, ambient ...)            (count: +0x3F884)
  When a table is full the remaining objects are skipped ("cmp [count], 0x200 / jae").
  A third table (1536 entries, heap) holds one bounding volume per drawn object for
  picking with the mouse and for the "already added this frame" test.
  The view is walked tile row by tile row, so the objects of the rows that come last
  vanish - which ones depends on the camera.  With the NeoEE resolution / zoom far more
  objects are in view than in 2001, corpses and projectiles need a slot as well.

What the patch does
  The two tables move to new zero-initialised memory behind the last section of the
  executable (only the virtual size of that section and SizeOfImage grow, the file size
  stays the same) and get more entries (default 4096 / 8192).  Patched are the constructor
  and destructor loops of the global object, the init loop, every absolute reference to
  the tables and the four limit constants; the picking table gets units + simple entries.
  Lists, counters and everything else stay where they are.  Display only - the simulation
  is not touched.

Usage
  python ee_unitcap.py status | plan | install | uninstall
         [--exe "<path>"]...  [--units N] [--simple N] [--no-backup]
  default: the cheat executables of both NeoEE installs (the original executables stay
  untouched unless they are named with --exe).
  Backup: backups/unitcap/<time>/, patch record next to the executable.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import struct
import sys

NEO = r'C:\Program Files (x86)\Neo Empire Earth'
DEFAULT_EXES = [NEO + r'\Empire Earth\EE-Cheats.exe',
                NEO + r'\Empire Earth - The Art of Conquest\EE-AOC-Cheats.exe']
BACKUP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', 'unitcap')

STRIDE1, STRIDE2 = 0x148, 0x3C          # entry sizes
OLD1, OLD2 = 0x200, 0x600               # original capacities
OFF_BIG, OFF_SMALL, OFF_COUNT = 0x78, 0x29078, 0x3F880      # inside the global object
DEF1, DEF2 = 4096, 8192
PAGE = 0x1000


def u32(v):
    return struct.pack('<I', v & 0xFFFFFFFF)


class PE:
    def __init__(self, data):
        self.d = data
        e = self.e = struct.unpack_from('<I', data, 0x3C)[0]
        if data[e:e + 4] != b'PE\0\0':
            raise ValueError('not a PE file')
        self.n = struct.unpack_from('<H', data, e + 6)[0]
        self.base = struct.unpack_from('<I', data, e + 52)[0]
        self.size_of_image_off = e + 24 + 56
        self.size_of_image = struct.unpack_from('<I', data, self.size_of_image_off)[0]
        self.so = e + 24 + struct.unpack_from('<H', data, e + 20)[0]
        self.secs = [struct.unpack_from('<IIII', data, self.so + i * 40 + 8) for i in range(self.n)]   # vsize, va, rsize, rptr

    def va(self, off):
        for vs, va, rs, rp in self.secs:
            if rp <= off < rp + rs:
                return self.base + va + off - rp
        return None

    def off(self, va):
        rva = va - self.base
        for vs, a, rs, rp in self.secs:
            if a <= rva < a + rs:
                return rva - a + rp
        raise ValueError('va %x has no file data' % va)


def one(rx, data, name):
    m = list(re.finditer(rx, data, re.S))
    if len(m) != 1:
        raise ValueError('%s: %d matches (expected 1)' % (name, len(m)))
    return m[0]


# absolute references: value -> (how many, allowed instruction forms in front of the imm32)
FORMS = {
    'push': (b'\x68',), 'mov r32': tuple(bytes([b]) for b in range(0xB8, 0xC0)), 'add eax': (b'\x05',),
    'add r32': tuple(b'\x81' + bytes([b]) for b in range(0xC0, 0xC8)),
    'cmp r32': tuple(b'\x81' + bytes([b]) for b in range(0xF8, 0x100)),
}


def form_of(data, o):
    for name, pres in FORMS.items():
        for p in pres:
            if data[o - len(p):o] == p and (len(p) == 2 or data[o - 2:o - 1] != b'\x81'):
                return name
    return None


def plan(data, cap1=DEF1, cap2=DEF2):
    """-> dict(edits=[(file offset, old, new, what)], info=...) ; raises ValueError when the exe does not look as expected"""
    pe = PE(data)
    d = data
    m = one(rb'\x81\x3D(....)' + u32(OLD1) + rb'\x0F\x83', d, 'limit check 1')
    c1 = struct.unpack('<I', m.group(1))[0]
    edits = [(m.start() + 6, u32(OLD1), u32(cap1), 'limit check units')]
    m = one(rb'\x81\x3D' + re.escape(u32(c1 + 4)) + re.escape(u32(OLD2)), d, 'limit check 2')
    edits.append((m.start() + 6, u32(OLD2), u32(cap2), 'limit check simple objects'))
    obj = c1 - OFF_COUNT
    big, small = obj + OFF_BIG, obj + OFF_SMALL
    if small != big + OLD1 * STRIDE1 or small + OLD2 * STRIDE2 != c1 - 8:
        raise ValueError('table layout differs')

    # new home: behind the last section
    vs, va, rs, rp = pe.secs[-1]
    if max(s[1] for s in pe.secs) != va or va + ((max(vs, 1) + PAGE - 1) & ~(PAGE - 1)) != pe.size_of_image:
        raise ValueError('last section does not end at SizeOfImage')
    new1 = pe.base + pe.size_of_image
    end1 = new1 + cap1 * STRIDE1
    new2 = (end1 + 15) & ~15
    new_end = (new2 + cap2 * STRIDE2 + PAGE - 1) & ~(PAGE - 1)
    if new_end >= 0x10000000:
        raise ValueError('new tables would reach the DLL address range')
    last_hdr = pe.so + (pe.n - 1) * 40 + 8
    edits.append((last_hdr, u32(vs), u32(new_end - pe.base - va), 'last section: virtual size'))
    edits.append((pe.size_of_image_off, u32(pe.size_of_image), u32(new_end - pe.base), 'SizeOfImage'))

    # constructor of the global object: element loop + start of the small table loop (39 bytes)
    m = one(rb'\x8D\x7E\x78\xC7\x45\xF8' + re.escape(u32(OLD1)) + rb'\x8B\xCF\xE8(....)\x81\xC7' + re.escape(u32(STRIDE1)) +
            rb'\xFF\x4D\xF8\x75\xEE\x8D\x86' + re.escape(u32(OFF_SMALL)) + rb'\xB9' + re.escape(u32(OLD2)), d, 'constructor')
    rel = struct.unpack('<i', m.group(1))[0]
    new = (b'\xBF' + u32(new1) +                      # mov edi, new1
           b'\x8B\xCF' +                              # loop: mov ecx, edi
           b'\xE8' + struct.pack('<i', rel + 5) +     # call element ctor (5 bytes earlier than before)
           b'\x81\xC7' + u32(STRIDE1) +               # add edi, 0x148
           b'\x81\xFF' + u32(end1) +                  # cmp edi, end1
           b'\x75\xEB' +                              # jne loop
           b'\xB8' + u32(new2) +                      # mov eax, new2
           b'\xB9' + u32(cap2) +                      # mov ecx, cap2
           b'\x90\x90\x90')
    assert len(new) == m.end() - m.start() == 39
    edits.append((m.start(), m.group(0), new, 'constructor loops'))

    # destructor: lea edi,[esi+0x29078] / mov ebx,0x200 / sub edi,0x148 ...
    m = one(rb'\x8D\xBE' + re.escape(u32(OFF_SMALL)) + rb'\xBB' + re.escape(u32(OLD1)) + rb'\x81\xEF' + re.escape(u32(STRIDE1)), d, 'destructor')
    edits.append((m.start(), m.group(0)[:11], b'\xBF' + u32(end1) + b'\x90' + b'\xBB' + u32(cap1), 'destructor loop'))

    # limits handed to the "add with limit" helpers
    m = one(rb'\x68' + re.escape(u32(OLD1)) + rb'\x75.\x68' + re.escape(u32(obj)), d, 'limit argument 1')
    edits.append((m.start() + 1, u32(OLD1), u32(cap1), 'limit argument units'))
    m = one(rb'\x68' + re.escape(u32(OLD2)) + rb'\x68' + re.escape(u32(obj + 0x24)), d, 'limit argument 2')
    edits.append((m.start() + 1, u32(OLD2), u32(cap2), 'limit argument simple objects'))

    # third table: one entry (0x50 bytes, heap) per drawn object for picking / "already added" - capacity is a
    # constructor argument of the object right behind the counters (push 0x600 / mov ecx, obj2 / call ctor)
    m = one(rb'\x68' + re.escape(u32(OLD2)) + rb'\xB9' + re.escape(u32(c1 + 0xA0)) + rb'\xE8', d, 'pick table capacity')
    edits.append((m.start() + 1, u32(OLD2), u32(cap1 + cap2), 'pick table capacity'))

    # absolute references to the tables (anywhere in the file: every hit must be one of the known instructions)
    refs = [
        (big, new1, {'push': 3, 'mov r32': 1}, 'units table'),
        (big + 0x58, new1 + 0x58, {'mov r32': 1}, 'init loop start'),
        (small + 0x58, end1 + 0x58, {'cmp r32': 1}, 'init loop end'),
        (big + 0xFC, new1 + 0xFC, {'add eax': 1}, 'units table +0xFC'),
        (small, new2, {'push': 2, 'add eax': 1, 'add r32': 1}, 'simple table'),
        (small + 0x24, new2 + 0x24, {'add eax': 1}, 'simple table +0x24'),
    ]
    for old, newv, want, what in refs:
        got = {}
        i = 0
        while True:
            i = d.find(u32(old), i)
            if i < 0:
                break
            f = form_of(d, i)
            if f is None:
                raise ValueError('%s: unknown reference to %x at file offset %x' % (what, old, i))
            got[f] = got.get(f, 0) + 1
            edits.append((i, u32(old), u32(newv), what + ' (' + f + ')'))
            i += 1
        if got != want:
            raise ValueError('%s: references %r, expected %r' % (what, got, want))

    edits.sort()
    for (o1, a1, _, _), (o2, _, _, _) in zip(edits, edits[1:]):
        if o1 + len(a1) > o2:
            raise ValueError('edits overlap at %x' % o2)
    for o, old, new, what in edits:
        if d[o:o + len(old)] != old or len(old) != len(new):
            raise ValueError('internal: bad edit at %x (%s)' % (o, what))
    info = dict(object=obj, units_old=big, simple_old=small, units_new=new1, simple_new=new2, new_end=new_end,
                units=cap1, simple=cap2, extra_kb=(new_end - new1) // 1024, base=pe.base)
    return dict(edits=edits, info=info, pe=pe)


def md5(b):
    return hashlib.md5(b).hexdigest()


def record_path(exe):
    return exe + '.unitcap.json'


def state(exe):
    """-> ('missing' | 'installed' | 'pristine' | 'unknown', detail)"""
    if not os.path.exists(exe):
        return 'missing', ''
    d = open(exe, 'rb').read()
    rp = record_path(exe)
    if os.path.exists(rp):
        rec = json.load(open(rp))
        if all(d[o:o + len(bytes.fromhex(n))] == bytes.fromhex(n) for o, _, n, _ in rec['edits']):
            return 'installed', 'units %d, simple objects %d' % (rec['units'], rec['simple'])
    try:
        plan(d)
        return 'pristine', ''
    except ValueError as e:
        return 'unknown', str(e)


def show_plan(exe, cap1, cap2):
    p = plan(open(exe, 'rb').read(), cap1, cap2)
    i = p['info']
    print('   global object %x: units table %x -> %x (%d entries), simple table %x -> %x (%d entries), +%d KB address space'
          % (i['object'], i['units_old'], i['units_new'], i['units'], i['simple_old'], i['simple_new'], i['simple'], i['extra_kb']))
    for o, old, new, what in p['edits']:
        va = p['pe'].va(o)
        print('   %s  %-36s %s -> %s' % (('%08x' % va) if va else 'hdr %04x' % o, what, old.hex(), new.hex()))


def install(exe, cap1, cap2, backup=True):
    st, detail = state(exe)
    if st == 'missing':
        print('   not found:', exe); return 1
    if st == 'installed':
        print('   already installed (%s)' % detail); return 0
    if st == 'unknown':
        print('   NOT patched - executable does not look as expected:', detail); return 1
    d = open(exe, 'rb').read()
    p = plan(d, cap1, cap2)
    if backup:
        bdir = os.path.join(BACKUP_ROOT, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'), os.path.basename(os.path.dirname(exe)))
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(exe, bdir)
        print('   backup:', bdir)
    b = bytearray(d)
    for o, old, new, what in p['edits']:
        b[o:o + len(new)] = new
    rec = dict(md5_before=md5(d), md5_after=md5(bytes(b)), units=cap1, simple=cap2,
               edits=[[o, old.hex(), new.hex(), what] for o, old, new, what in p['edits']])
    with open(exe, 'wb') as f:
        f.write(b)
    with open(record_path(exe), 'w') as f:
        json.dump(rec, f, indent=1)
    print('   installed: %d units, %d simple objects per frame (%d edits, md5 %s)' % (cap1, cap2, len(p['edits']), rec['md5_after']))
    return 0


def uninstall(exe):
    rp = record_path(exe)
    st, _ = state(exe)
    if st == 'missing':
        if os.path.exists(rp):
            os.remove(rp)
        print('   not found (nothing to do):', exe); return 0
    if st != 'installed':
        if os.path.exists(rp):
            os.remove(rp)           # stale record (executable was rebuilt)
        print('   not installed'); return 0
    rec = json.load(open(rp))
    b = bytearray(open(exe, 'rb').read())
    for o, old, new, what in rec['edits']:
        b[o:o + len(old) // 2] = bytes.fromhex(old)
    if md5(bytes(b)) != rec['md5_before']:
        print('   NOT removed: result would not match the original (md5) - restore from backups/unitcap'); return 1
    with open(exe, 'wb') as f:
        f.write(b)
    os.remove(rp)
    print('   removed (md5 %s)' % rec['md5_before'])
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'plan', 'install', 'uninstall'])
    ap.add_argument('--exe', action='append')
    ap.add_argument('--units', type=int, default=DEF1)
    ap.add_argument('--simple', type=int, default=DEF2)
    ap.add_argument('--no-backup', action='store_true')
    a = ap.parse_args()
    if not (OLD1 <= a.units <= 16384 and OLD2 <= a.simple <= 32768):
        ap.error('--units 512..16384, --simple 1536..32768')
    rc = 0
    for exe in a.exe or DEFAULT_EXES:
        print(exe)
        try:
            if a.cmd == 'status':
                st, detail = state(exe)
                print('   ' + {'missing': 'not found', 'installed': 'INSTALLED (' + detail + ')', 'pristine': 'not installed (original limits 512 / 1536)',
                               'unknown': 'UNKNOWN: ' + detail}[st])
            elif a.cmd == 'plan':
                show_plan(exe, a.units, a.simple)
            elif a.cmd == 'install':
                rc |= install(exe, a.units, a.simple, not a.no_backup)
            else:
                rc |= uninstall(exe)
        except (ValueError, OSError) as e:
            print('   ERROR:', e)
            rc = 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
