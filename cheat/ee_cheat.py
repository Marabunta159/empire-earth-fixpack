"""Empire Earth / The Art of Conquest - single player cheat patch (offline use only).

What the patched executable does differently
  1. The built-in cheat codes ("all your base are belong to us", "asus drivers", ...) also work
     when the scenario / campaign has "Cheat-Codes" switched off - but ONLY in single player.
     In a network game the original check is used unchanged.
  2. New cheat codes (type them into the chat line like the others):
         buerger          -> 5 citizens appear around the point the camera is looking at
                             (each at its own random place in a small square)
         buerger 20       -> 20 citizens (1..50)        aliases: bürger, citizens
         doughboys        -> 5 doughboys (WW I infantry, "Inf10 - Doughboy")
         doughboys 20     -> 20 doughboys (1..50)       alias: doughboy
     Single player only.
     They use the game's own "place unit" message of the scenario editor (EEMHackANewUnit).

The original game executable is NOT modified: the patcher writes a second executable next to it
(Empire Earth: "EE-Cheats.exe", Art of Conquest: "EE-AOC-Cheats.exe").  Start that one for a
cheat session, start the normal one for everything else (NeoEE online play stays untouched).

Usage
  python ee_cheat.py info                     show what would be patched (both installs)
  python ee_cheat.py build                    write the cheat executables (needs write access)
  python ee_cheat.py remove                   delete them again
  options:  --dir "<game folder>"  (repeatable; default: both NeoEE installs)   --in-place
"""
import argparse
import hashlib
import os
import re
import struct
import sys

NEO = r'C:\Program Files (x86)\Neo Empire Earth'
DEFAULT_DIRS = [NEO + r'\Empire Earth', NEO + r'\Empire Earth - The Art of Conquest']
EXES = {'Empire Earth.exe': 'EE-Cheats.exe', 'EE-AOC.exe': 'EE-AOC-Cheats.exe'}
MARK = b'EECHEAT1'
# new cheats: (id = unused slot in the game's cheat table - 10 and 19 are free in EE and AoC,
#              code words, dbobjects ids for even / odd units - the same ids in EE and AoC)
CHEATS = [
    (10, [b'buerger', b'b\xfcrger', b'citizens'], (32, 480)),      # "Citizen" / "Female Citizen"
    (19, [b'doughboys', b'doughboy'], (204, 204)),                 # "Inf10 - Doughboy"
]
FPS_DLL = b'ee_fps.dll'          # optional first-person add-on next to the exe, loaded at start
CAM_X, CAM_Y = 0x78, 0x7C         # camera object: look-at point in tile coordinates (the copy at +40h/+44h stays 0
                                  # until the camera is moved for the first time, this one is valid from the start)
DEFAULT_COUNT, MAX_COUNT = 5, 50
LAYERS_KEY = r'Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
GPU_KEY = r'Software\Microsoft\DirectX\UserGpuPreferences'


class PEFile:
    def __init__(self, data):
        self.d = bytearray(data)
        d = self.d
        self.pe = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[self.pe:self.pe + 4] == b'PE\0\0'
        self.nsec = struct.unpack_from('<H', d, self.pe + 6)[0]
        optsz = struct.unpack_from('<H', d, self.pe + 20)[0]
        self.opt = self.pe + 24
        assert struct.unpack_from('<H', d, self.opt)[0] == 0x10B
        self.base = struct.unpack_from('<I', d, self.opt + 28)[0]
        self.dllchar = struct.unpack_from('<H', d, self.opt + 70)[0]
        self.size_of_headers = struct.unpack_from('<I', d, self.opt + 60)[0]
        self.sec_end = self.opt + optsz + self.nsec * 40
        self.sections = []
        for i in range(self.nsec):
            so = self.opt + optsz + i * 40
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', d, so + 8)
            self.sections.append((va, vsize, rptr, rsize))

    def off(self, va):
        rva = va - self.base
        for va_, vsize, rptr, rsize in self.sections:
            if va_ <= rva < va_ + rsize:
                return rptr + rva - va_
        raise ValueError('VA %08X is not file backed' % va)

    def va(self, off):
        for va_, vsize, rptr, rsize in self.sections:
            if rptr <= off < rptr + rsize:
                return self.base + va_ + off - rptr
        raise ValueError('offset %X is not in a section' % off)

    def cstr(self, va):
        o = self.off(va)
        return bytes(self.d[o:self.d.index(b'\0', o)])

    def u32(self, va):
        return struct.unpack_from('<I', self.d, self.off(va))[0]

    def imports(self):
        """mangled name -> VA of the IAT slot"""
        rva = struct.unpack_from('<I', self.d, self.opt + 96 + 8)[0]
        o = self.off(self.base + rva)
        out = {}
        while True:
            oft, _ts, _fc, name, ft = struct.unpack_from('<IIIII', self.d, o)
            if not name:
                break
            t = self.off(self.base + (oft or ft))
            i = 0
            while True:
                v = struct.unpack_from('<I', self.d, t + i * 4)[0]
                if not v:
                    break
                if not v & 0x80000000:
                    out[self.cstr(self.base + v + 2)] = self.base + ft + i * 4
                i += 1
            o += 20
        return out

    def rtti_vtable(self, classname):
        name = ('.?AV%s@@' % classname).encode() + b'\0'
        pos = self.d.find(name)
        if pos < 0:
            raise RuntimeError('RTTI name %s not found' % classname)
        td = struct.pack('<I', self.va(pos) - 8)
        p = 0
        while True:
            p = self.d.find(td, p)
            if p < 0:
                raise RuntimeError('RTTI locator of %s not found' % classname)
            if p >= 12 and self.d[p - 12:p - 4] == b'\0' * 8:      # signature 0, offset 0
                col = struct.pack('<I', self.va(p - 12))
                q = self.d.find(col)
                if q >= 0:
                    return self.va(q) + 4
            p += 1


def sig(pattern):
    out = b''
    for tok in pattern.split():
        out += b'.' if tok == '??' else re.escape(bytes.fromhex(tok))
    return re.compile(out, re.S)


SIG_EXEC = sig('55 8B EC 80 3D ?? ?? ?? ?? 00 53 56 57 8B F9 0F 84 ?? ?? ?? ?? 8B 45 08 48 83 F8 1A 0F 87 ?? ?? ?? ?? FF 24 85 ?? ?? ?? ??')
SIG_CHAT = sig('38 1D ?? ?? ?? ?? BE FF 00 00 00 74 ?? 8B 0D ?? ?? ?? ??')
SIG_REG = sig('68 CE 77 00 00 FF D6 53 6A 1B 8D 45 EC 50 8B CF E8 ?? ?? ?? ?? 8D 4D EC FF 15 ?? ?? ?? ?? 5F 5E 5B C9 C3')
SIG_COMM = sig('A1 ?? ?? ?? ?? 38 58 ?? 0F 85')
SIG_CAM = sig('D9 05 ?? ?? ?? ?? 8D 45 E8 50 51 BE ?? ?? ?? ?? D9 1C 24 8B CE E8')


def locate(pe):
    """Find every address the patch needs by signature (works for EE and AoC builds)."""
    va0, _vs, rptr0, rsize0 = pe.sections[0]            # the code lives in the first section
    code = bytes(pe.d[rptr0:rptr0 + rsize0])
    code_va = pe.base + va0

    def one(rx, name, same=None):
        ms = list(rx.finditer(code))
        if not ms:
            raise RuntimeError('signature %s not found - unsupported executable' % name)
        if len(ms) > 1 and (same is None or len({same(m) for m in ms}) != 1):
            raise RuntimeError('signature %s is ambiguous (%d hits)' % (name, len(ms)))
        return ms[0]

    L = {}
    m = one(SIG_EXEC, 'ExecuteCheat')
    b = m.group(0)
    L['exec'] = code_va + m.start()
    L['flag'] = struct.unpack_from('<I', b, 5)[0]
    L['exit'] = code_va + m.start() + 21 + struct.unpack_from('<i', b, 17)[0]
    L['table'] = struct.unpack_from('<I', b, 37)[0]
    m = one(SIG_CHAT, 'chat check')
    L['chat'] = code_va + m.start()
    if struct.unpack_from('<I', m.group(0), 2)[0] != L['flag']:
        raise RuntimeError('chat check uses a different flag')
    m = one(SIG_REG, 'cheat registration')
    b = m.group(0)
    L['reg_hook'] = code_va + m.start() + 21
    L['register'] = code_va + m.start() + 21 + struct.unpack_from('<i', b, 17)[0]
    L['dtor_iat'] = struct.unpack_from('<I', b, 26)[0]
    m = one(SIG_COMM, 'network object', same=lambda m: m.group(0)[1:5] + m.group(0)[7:8])
    L['comm'] = struct.unpack_from('<I', m.group(0), 1)[0]
    L['mp_off'] = m.group(0)[7]
    m = one(SIG_CAM, 'camera', same=lambda m: m.group(0)[12:16])
    L['cam'] = struct.unpack_from('<I', m.group(0), 12)[0]
    imp = pe.imports()
    L['assign_iat'] = imp[b'??4UWideString@@QAEAAV0@PBD@Z']        # UWideString::operator=(char const *)
    if imp[b'??1UWideString@@UAE@XZ'] != L['dtor_iat']:
        raise RuntimeError('unexpected destructor import')
    vt = pe.rtti_vtable('EEMHackANewUnit')
    L['hack_exec'] = pe.u32(vt + 10 * 4)                           # EEMHackANewUnit::Execute
    L['loadlib_iat'] = imp[b'LoadLibraryA']
    for cid, _names, _types in CHEATS:
        if pe.u32(L['table'] + (cid - 1) * 4) != L['exit']:
            raise RuntimeError('cheat slot %d is not free' % cid)
    return L


class Asm:
    def __init__(self, org):
        self.org = org
        self.b = bytearray()
        self.labels = {}
        self.fix8 = []

    @property
    def here(self):
        return self.org + len(self.b)

    def emit(self, hexstr, *vals):
        self.b += bytes.fromhex(hexstr.replace(' ', ''))
        for v in vals:
            self.b += struct.pack('<I', v & 0xFFFFFFFF)
        return self

    def raw(self, data):
        self.b += data
        return self

    def label(self, name):
        self.labels[name] = len(self.b)

    def j8(self, opcode, label):
        self.b += bytes([opcode, 0])
        self.fix8.append((len(self.b) - 1, label))

    def rel32(self, opcode, target):
        self.b += bytes([opcode]) + struct.pack('<i', target - (self.here + 5))

    def finish(self):
        for pos, label in self.fix8:
            d = self.labels[label] - (pos + 1)
            assert -128 <= d <= 127, label
            self.b[pos] = d & 0xFF
        return bytes(self.b)


def build_cave(L, org):
    a = Asm(org)
    a.raw(MARK.ljust(16, b'\0'))
    names_va = []                                            # (VA of the code word, cheat id)
    for cid, names, _types in CHEATS:
        for n in names:
            names_va.append((a.here, cid))
            a.raw(n + b'\0')
    dll_name = a.here
    a.raw(FPS_DLL + b'\0')
    while len(a.b) % 4:
        a.raw(b'\0')
    k_scale = a.here
    a.raw(struct.pack('<f', 1.0 / 32768))                    # random 15 bit value -> fraction of the spawn square

    # --- allowed(): ZF=0 when cheats may be used (option switched on, or single player game)
    allowed = a.here
    a.emit('80 3D', L['flag']).emit('00')                    # cmp byte [flag], 0
    a.j8(0x75, 'al_ret')                                     # jne -> allowed
    a.emit('50')                                             # push eax
    a.emit('A1', L['comm'])                                  # mov eax, [comm]
    a.emit('85 C0')                                          # test eax, eax
    a.j8(0x74, 'al_pop')                                     # jz  -> not allowed (ZF=1)
    a.emit('80 78').raw(bytes([L['mp_off'], 0]))             # cmp byte [eax+mp], 0
    a.emit('0F 94 C0')                                       # sete al        (1 = single player)
    a.emit('84 C0')                                          # test al, al    (ZF=0 if single player)
    a.label('al_pop')
    a.emit('58')                                             # pop eax
    a.label('al_ret')
    a.emit('C3')                                             # ret
    while len(a.b) % 4:
        a.raw(b'\xCC')

    # --- rnd(): st0 = random offset inside the spawn square, in tiles (edi = generator state; called from the loop
    #     below, so the caller's temp [esp+20h] / side [esp+24h] are 4 bytes further away here)
    rnd = a.here
    a.emit('69 FF 6D 4E C6 41')                              # imul edi, edi, 41C64E6Dh
    a.emit('81 C7 39 30 00 00')                              # add edi, 3039h
    a.emit('8B C7')                                          # mov eax, edi
    a.emit('C1 E8 10')                                       # shr eax, 10h
    a.emit('25 FF 7F 00 00')                                 # and eax, 7FFFh
    a.emit('2D 00 40 00 00')                                 # sub eax, 4000h            ; -16384 .. 16383
    a.emit('89 44 24 24')                                    # mov [esp+24h], eax
    a.emit('DB 44 24 24')                                    # fild dword [esp+24h]
    a.emit('DA 4C 24 28')                                    # fimul dword [esp+28h]     ; * side
    a.emit('D8 0D', k_scale)                                 # fmul dword [1/32768]
    a.emit('C3')                                             # ret
    while len(a.b) % 4:
        a.raw(b'\xCC')

    # --- cheats: spawn units (jump table targets inside ExecuteCheat; ebp frame: +0C player, +10 number)
    #     every unit gets its own random place in a square around the point the camera looks at (side n/4 + 3
    #     tiles), so repeated calls do not put units on exactly the same spot
    entries = {}
    for cid, _names, (even, odd) in CHEATS:
        entries[cid] = a.here
        a.emit('68', odd)                                    # push type of the odd units
        a.emit('68', even)                                   # push type of the even units
        a.j8(0xEB, 'c_common')                               # jmp common
    a.label('c_common')                                      # [esp] even type, [esp+4] odd type
    a.emit('A1', L['comm'])                                  # mov eax, [comm]
    a.emit('85 C0')                                          # test eax, eax
    a.j8(0x74, 'c_exit')
    a.emit('80 78').raw(bytes([L['mp_off'], 0]))             # cmp byte [eax+mp], 0
    a.j8(0x75, 'c_exit')                                     # network game: do nothing
    a.emit('8B 75 10')                                       # mov esi, [ebp+10h]     ; number typed after the code
    a.emit('85 F6')                                          # test esi, esi
    a.j8(0x7F, 'c_have')                                     # jg
    a.raw(bytes([0x6A, DEFAULT_COUNT, 0x5E]))                # push n / pop esi
    a.label('c_have')
    a.raw(bytes([0x83, 0xFE, MAX_COUNT]))                    # cmp esi, max
    a.j8(0x7E, 'c_ok')                                       # jle
    a.raw(bytes([0x6A, MAX_COUNT, 0x5E]))                    # push max / pop esi
    a.label('c_ok')
    a.emit('83 EC 28')                                       # sub esp, 28h           ; fake EEMHackANewUnit (20h) + 2 temps
    a.emit('8B C6')                                          # mov eax, esi
    a.emit('C1 E8 02')                                       # shr eax, 2
    a.emit('83 C0 03')                                       # add eax, 3
    a.emit('89 44 24 24')                                    # mov [esp+24h], eax     ; side of the spawn square
    a.emit('0F 31')                                          # rdtsc
    a.emit('8B F8')                                          # mov edi, eax           ; seed (edi is restored by the common exit)
    a.emit('33 DB')                                          # xor ebx, ebx           ; i
    a.label('c_loop')
    a.emit('C6 44 24 0A FF')                                 # mov byte [esp+0Ah], FFh   ; sender slot: none
    a.emit('8B 44 24 28')                                    # mov eax, [esp+28h]        ; even type
    a.emit('F6 C3 01')                                       # test bl, 1
    a.j8(0x74, 'c_even')
    a.emit('8B 44 24 2C')                                    # mov eax, [esp+2Ch]        ; odd type
    a.label('c_even')
    a.emit('89 44 24 10')                                    # mov [esp+10h], eax        ; object type
    a.rel32(0xE8, rnd)                                       # call rnd
    a.emit('D8 05', L['cam'] + CAM_X)                        # fadd dword [camera.x]
    a.emit('D9 E1')                                          # fabs                      ; never left of / above the map
    a.emit('D9 5C 24 14')                                    # fstp dword [esp+14h]      ; x
    a.rel32(0xE8, rnd)                                       # call rnd
    a.emit('D8 05', L['cam'] + CAM_Y)                        # fadd dword [camera.y]
    a.emit('D9 E1')                                          # fabs
    a.emit('D9 5C 24 18')                                    # fstp dword [esp+18h]      ; y
    a.emit('8A 45 0C')                                       # mov al, [ebp+0Ch]         ; player who typed the code
    a.emit('88 44 24 1C')                                    # mov [esp+1Ch], al         ; owner
    a.emit('8B CC')                                          # mov ecx, esp
    a.rel32(0xE8, L['hack_exec'])                            # call EEMHackANewUnit::Execute
    a.emit('43')                                             # inc ebx
    a.emit('3B DE')                                          # cmp ebx, esi
    a.j8(0x7C, 'c_loop')                                     # jl
    a.emit('83 C4 28')                                       # add esp, 28h
    a.label('c_exit')
    a.emit('83 C4 08')                                       # add esp, 8                ; the two types
    a.rel32(0xE9, L['exit'])                                 # jmp back into ExecuteCheat (common exit)
    while len(a.b) % 4:
        a.raw(b'\xCC')

    # --- registration of the new code words (called at the end of the game's own registration)
    reg = a.here
    # load the optional first-person add-on (ee_fps.dll next to the exe); without the file LoadLibraryA returns 0
    a.emit('68', dll_name)                                   # push "ee_fps.dll"
    a.emit('FF 15', L['loadlib_iat'])                        # call [LoadLibraryA]  (keeps ebx/esi/edi/ebp)
    for nva, cid in names_va:
        a.emit('68', nva)                                    # push name
        a.emit('8D 4D EC')                                   # lea ecx, [ebp-14h]
        a.emit('FF 15', L['assign_iat'])                     # call UWideString::operator=(char const*)
        a.emit('6A 00')                                      # push 0
        a.raw(bytes([0x6A, cid]))                            # push cheat id
        a.emit('8D 45 EC')                                   # lea eax, [ebp-14h]
        a.emit('50')                                         # push eax
        a.emit('8B CF')                                      # mov ecx, edi
        a.rel32(0xE8, L['register'])                         # call RegisterCheat
    a.emit('8D 4D EC')                                       # lea ecx, [ebp-14h]   (displaced)
    a.emit('FF 15', L['dtor_iat'])                           # call ~UWideString     (displaced)
    a.emit('C3')                                             # ret
    return a.finish(), dict(allowed=allowed, reg=reg, **{'cheat%d' % cid: va for cid, va in entries.items()})


def patch(data):
    """returns (patched bytes, info)"""
    pe = PEFile(data)
    if MARK in pe.d[:pe.size_of_headers]:
        raise RuntimeError('already patched')
    if pe.dllchar & 0x0140:
        raise RuntimeError('executable uses ASLR/NX - this patch expects the classic layout')
    L = locate(pe)
    # code cave: unused part of the PE header page (mapped at the image base; the game runs without NX anyway)
    cave_off = (pe.sec_end + 0x1F) & ~0xF
    cave_va = pe.base + cave_off
    cave, C = build_cave(L, cave_va)
    if cave_off + len(cave) > pe.size_of_headers or any(pe.d[pe.sec_end:pe.size_of_headers]):
        raise RuntimeError('no room in the PE header')
    edits = [(cave_off, cave)]

    def rel(op, at, target, pad):
        return bytes([op]) + struct.pack('<i', target - (at + 5)) + b'\x90' * pad

    o = pe.off(L['exec'] + 3)                                    # cmp byte [flag], 0  (7 bytes)
    assert bytes(pe.d[o:o + 2]) == b'\x80\x3D'
    edits.append((o, rel(0xE8, L['exec'] + 3, C['allowed'], 2)))
    o = pe.off(L['chat'])                                        # cmp byte [flag], bl (6 bytes)
    assert bytes(pe.d[o:o + 2]) == b'\x38\x1D'
    edits.append((o, rel(0xE8, L['chat'], C['allowed'], 1)))
    o = pe.off(L['reg_hook'])                                    # lea ecx,[ebp-14h] / call [dtor] (9 bytes)
    assert bytes(pe.d[o:o + 5]) == b'\x8D\x4D\xEC\xFF\x15'
    edits.append((o, rel(0xE8, L['reg_hook'], C['reg'], 4)))
    for cid, _names, _types in CHEATS:                           # jump table slots of the new cheats
        edits.append((pe.off(L['table'] + (cid - 1) * 4), struct.pack('<I', C['cheat%d' % cid])))
    for off, new in edits:
        pe.d[off:off + len(new)] = new
    info = dict(L)
    info.update(cave=cave_va, cave_len=len(cave), **{'cave_' + k: v for k, v in C.items()})
    return bytes(pe.d), info


def md5(b):
    return hashlib.md5(b).hexdigest().upper()


def find_games(dirs):
    for d in dirs:
        for exe, cheat in EXES.items():
            p = os.path.join(d, exe)
            if os.path.exists(p):
                yield d, exe, cheat


def set_layers(target, source):
    """give the cheat exe the same compatibility flags the original has (HKCU, no admin needed)"""
    import winreg
    flags = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, LAYERS_KEY) as k:
                v = winreg.QueryValueEx(k, source)[0]
                flags += [f for f in v.split() if f != '~']
        except OSError:
            pass
    if not flags:
        return None
    seen, uniq = set(), []
    for f in flags:
        if f.upper() not in seen:
            seen.add(f.upper())
            uniq.append(f)
    value = '~ ' + ' '.join(uniq)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, LAYERS_KEY) as k:
        winreg.SetValueEx(k, target, 0, winreg.REG_SZ, value)
    # same graphics card choice as the original (Windows "graphics settings" per exe)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, GPU_KEY) as k:
            gpu = winreg.QueryValueEx(k, source)[0]
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, GPU_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, target, 0, winreg.REG_SZ, gpu)
        value += '  | GPU: ' + gpu
    except OSError:
        pass
    return value


def clear_layers(target):
    import winreg
    for key in (LAYERS_KEY, GPU_KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, target)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['info', 'build', 'remove'])
    ap.add_argument('--dir', action='append')
    ap.add_argument('--in-place', action='store_true', help='patch the original exe instead of writing a copy (keeps a .pre-cheat.bak)')
    ap.add_argument('--no-layers', action='store_true', help='do not copy the compatibility flags to the cheat exe')
    a = ap.parse_args()
    rc = 0
    for d, exe, cheat in find_games(a.dir or DEFAULT_DIRS):
        src = os.path.join(d, exe)
        dst = src if a.in_place else os.path.join(d, cheat)
        if a.cmd == 'remove':
            if a.in_place:
                bak = src + '.pre-cheat.bak'
                if os.path.exists(bak):
                    os.replace(bak, src)
                    print('restored', src)
            elif os.path.exists(dst):
                os.remove(dst)
                clear_layers(dst)
                print('removed', dst)
            continue
        data = open(src, 'rb').read()
        try:
            out, info = patch(data)
        except RuntimeError as e:
            print('%s: %s' % (src, e))
            rc = 1
            continue
        print(src, ' md5', md5(data))
        if a.cmd == 'info':
            for k in sorted(info):
                print('   %-13s %08X' % (k, info[k]))
            print('   would write:', dst, ' md5', md5(out))
            continue
        if a.in_place:
            bak = src + '.pre-cheat.bak'
            if not os.path.exists(bak):
                with open(bak, 'wb') as f:
                    f.write(data)
        tmp = dst + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(out)
        os.replace(tmp, dst)
        print('   wrote', dst, ' md5', md5(out))
        if not a.in_place and not a.no_layers:
            v = set_layers(dst, src)
            print('   compatibility flags:', v)
    return rc


if __name__ == '__main__':
    sys.exit(main())
