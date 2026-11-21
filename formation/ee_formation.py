"""Empire Earth / Art of Conquest: new single player games start with the formation "long line".

Normally every player starts with "short line" (formation kind 0).  This patch makes the game do, at the
end of the EEHumanPlayer constructor, exactly what the "long line" button does (EEMChangeFormation::Execute
with kind 1) - for human players and in single player sessions only.  Computer players and network games
keep the original default, so nothing can get out of sync.  Saved games keep whatever was saved.

It is an add-on for the cheat executable built by ee_cheat.py (same code cave area in the PE header).

  apply(exe bytes, comm, mp_off) -> patched bytes        (comm / mp_off: ee_cheat.locate() of the original)
  python ee_formation.py status|install|uninstall --exe <cheat exe> --orig <original exe>
"""
import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cheat'))
import ee_cheat                                                           # noqa: E402

MARK = b'EEFORM1\0'
KIND = 1            # 0 short line, 1 long line, 2 loose line, 3 staggered line, 4 wedge, 5 blunt wedge, 6 / 7 circle


def u32(v):
    return struct.pack('<I', v & 0xFFFFFFFF)


def locate(pe):
    """addresses taken from the game's own "change formation" code and the human player constructors"""
    d = bytes(pe.d)
    L = {}
    ex = pe.u32(pe.rtti_vtable('EEMChangeFormation') + 10 * 4)                 # EEMChangeFormation::Execute
    o = pe.off(ex)
    m = re.compile(rb'\xFF\x76\x10\x8B\xB8(....)\xE8(....)\x8B\xD8\x8A\x46\x14\x59\x53\x8B\xCF\x88\x43(.)\xE8(....)'
                   rb'\x8B\x4F(.)\x85\xC9\x74\x06\x53\xE8(....)\x8B\xCB\xFF\x15(....)', re.S).search(d, o, o + 0x60)
    if not m:
        raise RuntimeError('EEMChangeFormation::Execute looks different')
    va = pe.base + (m.start() - o) + (ex - pe.base)                            # VA of the match
    L['group'] = struct.unpack('<I', m.group(1))[0]                            # player -> selection group
    L['factory'] = va + m.start(2) - m.start() + 4 + struct.unpack('<i', m.group(2))[0]
    L['flag_off'] = m.group(3)[0]
    L['setform'] = va + m.start(4) - m.start() + 4 + struct.unpack('<i', m.group(4))[0]
    L['sub_off'] = m.group(5)[0]
    if va + m.start(6) - m.start() + 4 + struct.unpack('<i', m.group(6))[0] != L['setform']:
        raise RuntimeError('second SetFormation call differs')
    L['deref_iat'] = struct.unpack('<I', m.group(7))[0]
    vt = pe.rtti_vtable('EEHumanPlayer')
    hooks = []
    for c in re.finditer(re.escape(b'\xC7\x06' + u32(vt)), d):                 # mov dword [esi], vtable  (2 ctors + dtor)
        t = re.compile(rb'\x89\x86(....)\x5F\x8B\xC6\x5E', re.S).search(d, c.end(), c.end() + 0x40)
        if t:                                                                  # mov [esi+X], eax / pop edi / mov eax, esi / pop esi
            hooks.append((t.start(), t.group(0)[:6]))
    if len(hooks) != 2:
        raise RuntimeError('EEHumanPlayer constructors: %d hook sites (expected 2)' % len(hooks))
    L['hooks'] = hooks
    return L


def build_cave(L, org, comm, mp_off, displaced):
    a = ee_cheat.Asm(org)
    a.raw(MARK)
    entry = a.here
    a.raw(displaced)                                         # mov [esi+X], eax          (the instruction the hook replaced)
    a.emit('60')                                             # pushad
    a.emit('A1', comm)                                       # mov eax, [comm]
    a.emit('85 C0')                                          # test eax, eax
    a.j8(0x74, 'done')
    a.emit('80 78').raw(bytes([mp_off, 0]))                  # cmp byte [eax+mp], 0
    a.j8(0x75, 'done')                                       # network game: keep the original default
    a.emit('8B BE', L['group'])                              # mov edi, [esi+group]
    a.emit('85 FF')                                          # test edi, edi
    a.j8(0x74, 'done')
    a.raw(bytes([0x6A, KIND]))                               # push kind
    a.rel32(0xE8, L['factory'])                              # call CreateFormation
    a.emit('59')                                             # pop ecx
    a.emit('85 C0')                                          # test eax, eax
    a.j8(0x74, 'done')
    a.emit('8B D8')                                          # mov ebx, eax
    a.emit('53 8B CF')                                       # push ebx / mov ecx, edi
    a.rel32(0xE8, L['setform'])                              # call EEGroup::SetFormation
    a.emit('8B 4F').raw(bytes([L['sub_off']]))               # mov ecx, [edi+3Ch]
    a.emit('85 C9')                                          # test ecx, ecx
    a.j8(0x74, 'skip')
    a.emit('53')                                             # push ebx
    a.rel32(0xE8, L['setform'])                              # call EEGroup::SetFormation
    a.label('skip')
    a.emit('8B CB')                                          # mov ecx, ebx
    a.emit('FF 15', L['deref_iat'])                          # call [UReferenceCounter::Dereference]
    a.label('done')
    a.emit('61')                                             # popad
    a.emit('C3')                                             # ret
    return a.finish(), entry


def is_installed(data):
    return MARK in data[:0x1000]


def apply(data, comm, mp_off):
    """cheat executable bytes -> bytes with the formation default.  Raises RuntimeError when the exe looks different."""
    if is_installed(data):
        raise RuntimeError('already installed')
    pe = ee_cheat.PEFile(data)
    if ee_cheat.MARK not in bytes(pe.d[:pe.size_of_headers]):
        raise RuntimeError('not a cheat executable built by ee_cheat.py')
    L = locate(pe)
    used = max(i for i in range(pe.size_of_headers) if pe.d[i])            # last byte of the cheat code cave
    cave_off = (used + 1 + 0x1F) & ~0xF
    displaced = L['hooks'][0][1]
    if any(h[1] != displaced for h in L['hooks']):
        raise RuntimeError('the two constructors differ')
    cave, entry = build_cave(L, pe.base + cave_off, comm, mp_off, displaced)
    if cave_off + len(cave) > pe.size_of_headers:
        raise RuntimeError('no room in the PE header')
    pe.d[cave_off:cave_off + len(cave)] = cave
    for off, _ in L['hooks']:
        at = pe.va(off)
        pe.d[off:off + 6] = b'\xE8' + struct.pack('<i', entry - (at + 5)) + b'\x90'      # call cave / nop
    return bytes(pe.d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'install', 'uninstall'])
    ap.add_argument('--exe', required=True, help='cheat executable (EE-Cheats.exe / EE-AOC-Cheats.exe)')
    ap.add_argument('--orig', required=True, help='original game executable it was built from')
    a = ap.parse_args()
    cur = open(a.exe, 'rb').read()
    if a.cmd == 'status':
        print('%s : %s' % (a.exe, 'INSTALLED' if is_installed(cur) else 'not installed'))
        return 0
    orig = open(a.orig, 'rb').read()
    Lc = ee_cheat.locate(ee_cheat.PEFile(orig))
    plain = ee_cheat.patch(orig)[0]
    if a.cmd == 'install':
        if is_installed(cur):
            print('   already installed')
            return 0
        if cur != plain:
            print('   NOT patched: %s is not the plain cheat executable of this version (other add-ons applied?)' % a.exe)
            return 1
        out = apply(cur, Lc['comm'], Lc['mp_off'])
    else:
        if not is_installed(cur):
            print('   not installed')
            return 0
        if cur != apply(plain, Lc['comm'], Lc['mp_off']):
            print('   NOT removed: file differs from what this tool writes')
            return 1
        out = plain
    with open(a.exe, 'wb') as f:
        f.write(out)
    print('   %s: %s' % (a.exe, 'long line is the default formation now' if a.cmd == 'install' else 'removed'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
