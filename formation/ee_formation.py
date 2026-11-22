"""Empire Earth / Art of Conquest: new single player games start with the formation "long line".

Normally every player starts with "short line" (formation kind 0).  This patch gives every group of a human
player the formation "long line" (kind 1) - in single player sessions only.  Computer players and network
games keep the original default, so nothing can get out of sync.

Two hooks:
  * end of the EEHumanPlayer constructors: the three selection groups (the one the orders use, the one the
    interface shows, a spare one) and the 20 hotkey groups get "long line".
  * EEGroup::Read (loading / restarting a game): a group saved with "short line" becomes "long line"; any
    other saved formation is kept, and the interface group follows the loaded one (the original shows
    "short line" after loading no matter what was saved).

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

MARK = b'EEFORM3\0'
# v1 only set the internal group (+0x9BC) - the interface kept "short line"; v2 missed loaded games and the
# hotkey groups (the display said "long line", the units formed a short line)
OLD_MARKS = [b'EEFORM1\0', b'EEFORM2\0']
HOTKEYS = 20        # hotkey groups per player
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
    # the group the interface uses for the player's selection (the formation buttons set it directly)
    rx = re.compile(rb'\xC6\x47\x5C\x01\xA1(....)\x8B\x04\x85(....)\x8B\x88(....)\x57\xE8', re.S)
    ms = list(rx.finditer(d))
    if len(ms) != 1:
        raise RuntimeError('formation button handler: %d matches (expected 1)' % len(ms))
    L['selgroup'] = struct.unpack('<I', ms[0].group(3))[0]
    # EEGroup constructor: player pointer and formation of a group
    m = re.compile(rb'\x8B\x45\x08\x6A\x00\xC7\x06....\x89\x46(.)\xE8(....)\x83\x66.\x00\x89\x46(.)', re.S).search(d)
    if not m or pe.va(m.start(2)) + 4 + struct.unpack('<i', m.group(2))[0] != L['factory']:
        raise RuntimeError('EEGroup constructor looks different')
    L['g_player'], L['g_form'] = m.group(1)[0], m.group(3)[0]
    # the 20 hotkey groups (the "assign group" message) and the spare selection group (allocated right before them)
    ms = list(re.finditer(rb'\x0F\xB6\x47\x10\xFF\x36\x8B\x8C\x83(....)', d, re.S))
    if len(ms) != 1:
        raise RuntimeError('hotkey group handler: %d matches (expected 1)' % len(ms))
    L['hot'] = struct.unpack('<I', ms[0].group(1))[0]
    m = re.compile(rb'\x8D\x86' + re.escape(u32(L['hot'])) + rb'\x89\xBE(....)\x33\xFF', re.S).search(d)
    if not m:
        raise RuntimeError('player group setup looks different')
    third = struct.unpack('<I', m.group(1))[0]
    if not (L['selgroup'] == L['group'] + 4 and third == L['group'] + 8 and L['hot'] + HOTKEYS * 4 <= L['group']):
        raise RuntimeError('unexpected group layout')
    # EEGroup::Read: "if (kind != 8) formation = CreateFormation(kind)"
    rx = re.compile(rb'\x83\x7D\xFC\x08\x74.\xFF\x75\xFC\xE8(....)\x8B\xD8\x85\xDB\x59\x74.\x8B\x4F' + bytes([L['g_form']]), re.S)
    ms = [m for m in rx.finditer(d) if pe.va(m.start(1)) + 4 + struct.unpack('<i', m.group(1))[0] == L['factory']]
    if len(ms) != 1:
        raise RuntimeError('EEGroup::Read: %d matches (expected 1)' % len(ms))
    L['read_call'] = ms[0].start(1) - 1                                        # file offset of the E8
    vt = pe.rtti_vtable('EEHumanPlayer')
    L['human_vt'] = vt
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
    """-> (bytes, entry of the constructor hook, entry of the EEGroup::Read hook)"""
    a = ee_cheat.Asm(org)
    a.raw(MARK)

    def single_player(label):                                # falls through in a single player session
        a.emit('A1', comm)                                   # mov eax, [comm]
        a.emit('85 C0')                                      # test eax, eax
        a.j8(0x74, label)
        a.emit('80 78').raw(bytes([mp_off, 0]))              # cmp byte [eax+mp], 0
        a.j8(0x75, label)                                    # network game: keep the original default

    # --- set_range: edi = first group pointer, ebp = count, ebx = formation
    a.label('set_range')
    set_range = a.here
    a.emit('8B 0F')                                          # mov ecx, [edi]
    a.emit('85 C9')                                          # test ecx, ecx
    a.j8(0x74, 'sr_next')
    a.emit('53')                                             # push ebx
    a.rel32(0xE8, L['setform'])                              # call EEGroup::SetFormation
    a.label('sr_next')
    a.emit('83 C7 04')                                       # add edi, 4
    a.emit('4D')                                             # dec ebp
    a.j8(0x75, 'set_range')
    a.emit('C3')                                             # ret

    # --- end of the EEHumanPlayer constructors (esi = player)
    entry = a.here
    a.raw(displaced)                                         # mov [esi+X], eax          (the instruction the hook replaced)
    a.emit('60')                                             # pushad
    single_player('done')
    a.raw(bytes([0x6A, KIND]))                               # push kind
    a.rel32(0xE8, L['factory'])                              # call CreateFormation
    a.emit('59')                                             # pop ecx
    a.emit('85 C0')                                          # test eax, eax
    a.j8(0x74, 'done')
    a.emit('8B D8')                                          # mov ebx, eax
    a.emit('8D BE', L['hot'])                                # lea edi, [esi+hotkey groups]
    a.raw(bytes([0x6A, HOTKEYS, 0x5D]))                      # push 20 / pop ebp
    a.rel32(0xE8, set_range)
    a.emit('8D BE', L['group'])                              # lea edi, [esi+selection groups]   (orders, interface, spare)
    a.raw(bytes([0x6A, 3, 0x5D]))                            # push 3 / pop ebp
    a.rel32(0xE8, set_range)
    a.emit('8B CB')                                          # mov ecx, ebx
    a.emit('FF 15', L['deref_iat'])                          # call [UReferenceCounter::Dereference]
    a.label('done')
    a.emit('61')                                             # popad
    a.emit('C3')                                             # ret

    # --- EEGroup::Read, in place of "call CreateFormation" ([esp+4] = saved kind, edi = group)
    read_entry = a.here
    single_player('r_orig')
    a.emit('8B 57').raw(bytes([L['g_player']]))              # mov edx, [edi+player]
    a.emit('85 D2')                                          # test edx, edx
    a.j8(0x74, 'r_orig')
    a.emit('81 3A', L['human_vt'])                           # cmp dword [edx], EEHumanPlayer vtable
    a.j8(0x75, 'r_orig')
    a.emit('83 7C 24 04 00')                                 # cmp dword [esp+4], 0      (short line = the old default)
    a.j8(0x75, 'r_keep')
    a.emit('C7 44 24 04', KIND)                              # mov dword [esp+4], kind
    a.label('r_keep')
    a.emit('FF 74 24 04')                                    # push dword [esp+4]
    a.rel32(0xE8, L['factory'])                              # call CreateFormation
    a.emit('59')                                             # pop ecx
    a.emit('85 C0')                                          # test eax, eax
    a.j8(0x74, 'r_out')
    a.emit('8B 57').raw(bytes([L['g_player']]))              # mov edx, [edi+player]
    a.emit('3B BA', L['group'])                              # cmp edi, [edx+order group]
    a.j8(0x75, 'r_out')
    a.emit('8B 8A', L['selgroup'])                           # mov ecx, [edx+interface group]
    a.emit('85 C9')                                          # test ecx, ecx
    a.j8(0x74, 'r_out')
    a.emit('50 50')                                          # push eax (keep) / push eax (argument)
    a.rel32(0xE8, L['setform'])                              # call EEGroup::SetFormation   -> the interface shows what was loaded
    a.emit('58')                                             # pop eax
    a.label('r_out')
    a.emit('C3')                                             # ret
    a.label('r_orig')
    a.rel32(0xE9, L['factory'])                              # jmp CreateFormation
    return a.finish(), entry, read_entry


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
    cave, entry, read_entry = build_cave(L, pe.base + cave_off, comm, mp_off, displaced)
    if cave_off + len(cave) > pe.size_of_headers:
        raise RuntimeError('no room in the PE header')
    pe.d[cave_off:cave_off + len(cave)] = cave
    for off, _ in L['hooks']:
        at = pe.va(off)
        pe.d[off:off + 6] = b'\xE8' + struct.pack('<i', entry - (at + 5)) + b'\x90'      # call cave / nop
    off = L['read_call']
    pe.d[off + 1:off + 5] = struct.pack('<i', read_entry - (pe.va(off) + 5))             # call CreateFormation -> call cave
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
