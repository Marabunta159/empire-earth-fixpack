"""Empire Earth / Art of Conquest: fix for the "second load" crash.

Root cause (details: MODLOG.md, section "Crash beim zweiten Laden"):
  FSPath::AddArchive closes and re-opens *every* mounted archive whenever one more
  archive is mounted (campaign .ssa, scenario ...).  FSArchive::Open maps the whole
  archive with MapViewOfFile - for data.ssa that is one contiguous 163 MB block.
  After a game session the 2 GB address space of the 32-bit process is fragmented,
  MapViewOfFile fails with ERROR_NOT_ENOUGH_MEMORY, the return value is ignored and
  the next file read dereferences  NULL + file_offset  -> access violation.

Fix (Low-Level Engine.dll):
  1. FSArchive::Open no longer maps the whole archive (the mapping *object* is kept).
  2. FSArchive::ReadFATFile is wrapped: it maps just the 64K-aligned range of the one
     file being read, runs the original code on it and unmaps it again.
  The game therefore never needs a 163 MB hole again (and gains 163 MB address space).

Usage:
  python ssa_mapfix.py status
  python ssa_mapfix.py install
  python ssa_mapfix.py uninstall
  optional: --dll "<path to Low-Level Engine.dll>"   (default: both NeoEE installs)
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import struct
import sys

DEFAULT_DLLS = [
    r'C:\Program Files (x86)\Neo Empire Earth\Empire Earth\Low-Level Engine.dll',
    r'C:\Program Files (x86)\Neo Empire Earth\Empire Earth - The Art of Conquest\Low-Level Engine.dll',
]
BACKUP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', 'crashfix')
MARK = b'EEMAPFIX1'          # marker placed in front of the cave code

EXP_OPEN = b'?Open@FSArchive@@QAEJXZ'
EXP_READ = b'?ReadFATFile@FSArchive@@AAEJABUArchivedFile@1@AAPAVFSMemoryFile@@@Z'


class PEFile:
    def __init__(self, data):
        self.d = bytearray(data)
        d = self.d
        self.pe = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[self.pe:self.pe + 4] == b'PE\0\0'
        self.nsec = struct.unpack_from('<H', d, self.pe + 6)[0]
        optsz = struct.unpack_from('<H', d, self.pe + 20)[0]
        self.opt = self.pe + 24
        assert struct.unpack_from('<H', d, self.opt)[0] == 0x10B, 'PE32 expected'
        self.image_base = struct.unpack_from('<I', d, self.opt + 28)[0]
        self.sec_off = self.opt + optsz
        self.sections = []
        for i in range(self.nsec):
            so = self.sec_off + i * 40
            name = bytes(d[so:so + 8]).rstrip(b'\0').decode('latin1')
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', d, so + 8)
            chars = struct.unpack_from('<I', d, so + 36)[0]
            self.sections.append(dict(i=i, hdr=so, name=name, va=va, vsize=vsize, rptr=rptr, rsize=rsize, chars=chars))

    def rva2off(self, rva):
        for s in self.sections:
            if s['va'] <= rva < s['va'] + s['rsize']:
                return s['rptr'] + rva - s['va']
        raise ValueError('rva %X not in file' % rva)

    def off2rva(self, off):
        for s in self.sections:
            if s['rptr'] <= off < s['rptr'] + s['rsize']:
                return s['va'] + off - s['rptr']
        raise ValueError('offset %X not in a section' % off)

    def cstr(self, rva):
        o = self.rva2off(rva)
        return bytes(self.d[o:self.d.index(b'\0', o)])

    def exports(self):
        rva = struct.unpack_from('<I', self.d, self.opt + 96)[0]
        o = self.rva2off(rva)
        nfun, nnam, afun, anam, aord = struct.unpack_from('<IIIII', self.d, o + 20)
        fo, no, oo = self.rva2off(afun), self.rva2off(anam), self.rva2off(aord)
        out = {}
        for i in range(nnam):
            name = self.cstr(struct.unpack_from('<I', self.d, no + i * 4)[0])
            idx = struct.unpack_from('<H', self.d, oo + i * 2)[0]
            out[name] = struct.unpack_from('<I', self.d, fo + idx * 4)[0]
        return out

    def imports(self):
        """name -> RVA of the IAT slot"""
        rva = struct.unpack_from('<I', self.d, self.opt + 96 + 8)[0]
        o = self.rva2off(rva)
        out = {}
        while True:
            oft, _ts, _fc, name, ft = struct.unpack_from('<IIIII', self.d, o)
            if not name:
                break
            t = self.rva2off(oft or ft)
            i = 0
            while True:
                v = struct.unpack_from('<I', self.d, t + i * 4)[0]
                if not v:
                    break
                if not v & 0x80000000:
                    out[self.cstr(v + 2)] = ft + i * 4
                i += 1
            o += 20
        return out


def rel32(src_after, dst):
    return struct.pack('<i', dst - src_after)


def build_cave(cave_rva, read_rva, iat_map, iat_unmap):
    """Position independent wrapper + trampoline. Returns (bytes, wrapper_rva)."""
    code = bytearray()
    labels = {}
    fix8 = []    # (pos_of_rel8, label)

    def emit(b):
        code.extend(b)

    def here():
        return cave_rva + len(code)

    def jcc8(opcode, label):
        emit(bytes([opcode, 0]))
        fix8.append((len(code) - 1, label))

    def call_iat(iat_rva):
        emit(b'\xE8\x00\x00\x00\x00')          # call $+5
        pop_rva = here()
        emit(b'\x58')                          # pop eax        ; eax = VA of this instruction
        emit(b'\xFF\x90' + struct.pack('<i', iat_rva - pop_rva))   # call [eax + disp32]

    emit(MARK + b'\0' * (16 - len(MARK)))
    wrapper = here()
    emit(b'\x55')                              # push ebp
    emit(b'\x8B\xEC')                          # mov ebp, esp
    emit(b'\x83\xEC\x10')                      # sub esp, 10h   ; -10 fake.off  -C fake.end  -8 fake.size  -4 view base
    emit(b'\x56')                              # push esi
    emit(b'\x57')                              # push edi
    emit(b'\x8B\x75\x08')                      # mov esi, [ebp+8]      ; ArchivedFile*
    emit(b'\x8B\xF9')                          # mov edi, ecx          ; this
    emit(b'\x83\x65\xFC\x00')                  # and dword [ebp-4], 0
    emit(b'\x8B\x06')                          # mov eax, [esi]        ; file offset in archive
    emit(b'\x8B\xD0')                          # mov edx, eax
    emit(b'\x81\xE2\xFF\xFF\x00\x00')          # and edx, 0FFFFh       ; delta inside the 64K block
    emit(b'\x89\x55\xF0')                      # mov [ebp-10h], edx
    emit(b'\x8B\x4E\x04')                      # mov ecx, [esi+4]
    emit(b'\x89\x4D\xF4')                      # mov [ebp-0Ch], ecx
    emit(b'\x8B\x4E\x08')                      # mov ecx, [esi+8]      ; stored size
    emit(b'\x89\x4D\xF8')                      # mov [ebp-8], ecx
    emit(b'\x85\xC9')                          # test ecx, ecx
    jcc8(0x74, 'call_inner')                   # jz  call_inner        ; empty file: nothing to map
    emit(b'\x03\xCA')                          # add ecx, edx          ; bytes to map
    emit(b'\x25\x00\x00\xFF\xFF')              # and eax, 0FFFF0000h   ; aligned offset
    emit(b'\x51')                              # push ecx              ; dwNumberOfBytesToMap
    emit(b'\x50')                              # push eax              ; dwFileOffsetLow
    emit(b'\x6A\x00')                          # push 0                ; dwFileOffsetHigh
    emit(b'\x6A\x04')                          # push 4                ; FILE_MAP_READ
    emit(b'\xFF\x77\x64')                      # push dword [edi+64h]  ; mapping handle
    call_iat(iat_map)                          # call MapViewOfFile
    emit(b'\x85\xC0')                          # test eax, eax
    jcc8(0x75, 'mapped')                       # jnz mapped
    emit(b'\x8B\x45\x0C')                      # mov eax, [ebp+0Ch]    ; mapping failed: *out = NULL, return 1
    emit(b'\x83\x20\x00')                      # and dword [eax], 0
    emit(b'\x6A\x01')                          # push 1
    emit(b'\x5E')                              # pop esi
    jcc8(0xEB, 'done')                         # jmp done
    labels['mapped'] = len(code)
    emit(b'\x89\x45\xFC')                      # mov [ebp-4], eax
    labels['call_inner'] = len(code)
    emit(b'\xFF\x75\x0C')                      # push dword [ebp+0Ch]  ; FSMemoryFile*& out
    emit(b'\x8D\x45\xF0')                      # lea eax, [ebp-10h]
    emit(b'\x50')                              # push eax              ; fake ArchivedFile {delta, end, size}
    emit(b'\x8D\x4D\x94')                      # lea ecx, [ebp-6Ch]    ; fake this: [ecx+68h] == view base
    emit(b'\xE8\x00\x00\x00\x00')              # call trampoline (fixed below)
    call_tramp_pos = len(code) - 4
    emit(b'\x8B\xF0')                          # mov esi, eax          ; keep result
    emit(b'\x8B\x45\xFC')                      # mov eax, [ebp-4]
    emit(b'\x85\xC0')                          # test eax, eax
    jcc8(0x74, 'done')                         # jz done
    emit(b'\x50')                              # push eax
    call_iat(iat_unmap)                        # call UnmapViewOfFile
    labels['done'] = len(code)
    emit(b'\x8B\xC6')                          # mov eax, esi
    emit(b'\x5F')                              # pop edi
    emit(b'\x5E')                              # pop esi
    emit(b'\xC9')                              # leave
    emit(b'\xC2\x08\x00')                      # ret 8
    while len(code) % 4:
        emit(b'\xCC')
    tramp = here()
    emit(b'\x55')                              # push ebp          ; displaced prologue of ReadFATFile
    emit(b'\x8B\xEC')                          # mov ebp, esp
    emit(b'\x83\xEC\x0C')                      # sub esp, 0Ch
    emit(b'\xE9' + rel32(here() + 5, read_rva + 6))   # jmp ReadFATFile+6
    for pos, label in fix8:
        d = labels[label] - (pos + 1)
        assert -128 <= d <= 127
        code[pos] = d & 0xFF
    code[call_tramp_pos:call_tramp_pos + 4] = rel32(cave_rva + call_tramp_pos + 4, tramp)
    return bytes(code), wrapper


READ_PROLOGUE = bytes.fromhex('558bec83ec0c')                 # push ebp / mov ebp,esp / sub esp,0Ch
READ_VIEWUSE = bytes.fromhex('8b7968033e')                    # mov edi,[ecx+68h] / add edi,[esi]   (at +10h)


def plan(pe):
    """Returns list of (file_offset, old_bytes, new_bytes) or raises."""
    exp = pe.exports()
    imp = pe.imports()
    open_rva, read_rva = exp[EXP_OPEN], exp[EXP_READ]
    iat_map, iat_unmap = imp[b'MapViewOfFile'], imp[b'UnmapViewOfFile']
    d = pe.d
    edits = []

    # --- FSArchive::ReadFATFile entry hook
    ro = pe.rva2off(read_rva)
    if bytes(d[ro:ro + 6]) != READ_PROLOGUE or bytes(d[ro + 0x10:ro + 0x15]) != READ_VIEWUSE:
        raise RuntimeError('ReadFATFile: unexpected bytes %s' % bytes(d[ro:ro + 0x15]).hex())

    # --- FSArchive::Open: skip the whole-file MapViewOfFile
    oo = pe.rva2off(open_rva)
    pat = bytes.fromhex('5353536a0450ff15') + struct.pack('<I', pe.image_base + iat_map) + bytes.fromhex('3bc38946687542')
    body = bytes(d[oo:oo + 0x100])
    p = body.find(pat)
    if p < 0:
        raise RuntimeError('Open: MapViewOfFile call pattern not found')
    edits.append((oo + p, pat[:2], b'\xEB\x53'))               # jmp -> "mapped ok" label (target of the jne)

    # --- cave in the slack behind .text (same page as the last code byte)
    text = pe.sections[0]
    assert text['chars'] & 0x20000000, 'first section is not code'
    slack_start = text['rptr'] + text['vsize']
    slack_end = text['rptr'] + text['rsize']
    last = slack_start
    for o in range(slack_end - 1, slack_start - 1, -1):
        if d[o]:
            last = o + 1
            break
    cave_off = (last + 16 + 15) & ~15
    cave_rva = pe.off2rva(cave_off)
    code, wrapper_rva = build_cave(cave_rva, read_rva, iat_map, iat_unmap)
    if cave_off + len(code) > slack_end:
        raise RuntimeError('not enough slack for the cave')
    if (cave_rva + len(code) - 1) >> 12 != (text['va'] + text['vsize'] - 1) >> 12:
        raise RuntimeError('cave would leave the last mapped code page')
    if any(d[cave_off:cave_off + len(code)]):
        raise RuntimeError('cave area not empty')
    edits.append((cave_off, bytes(len(code)), code))

    # --- make the cave an official part of .text (VirtualSize covers it)
    need_vsize = cave_off + len(code) - text['rptr']
    if text['vsize'] < need_vsize:
        edits.append((text['hdr'] + 8, struct.pack('<I', text['vsize']), struct.pack('<I', need_vsize)))

    edits.append((ro, READ_PROLOGUE, b'\xE9' + rel32(read_rva + 5, wrapper_rva) + b'\x90'))
    info = dict(open_rva=open_rva, read_rva=read_rva, cave_rva=cave_rva, wrapper_rva=wrapper_rva,
                cave_len=len(code), image_base=pe.image_base)
    return edits, info


def md5(b):
    return hashlib.md5(b).hexdigest().upper()


def record_path(dll):
    return dll + '.mapfix.json'


def is_installed(data):
    return MARK in data


def status(dll):
    data = open(dll, 'rb').read()
    st = 'INSTALLED' if is_installed(data) else 'not installed'
    print('%-9s md5=%s  %s' % (st.upper() if st == 'INSTALLED' else st, md5(data), dll))
    return is_installed(data)


def install(dll):
    data = open(dll, 'rb').read()
    if is_installed(data):
        print('already installed:', dll)
        return
    pe = PEFile(data)
    edits, info = plan(pe)
    for off, old, new in edits:
        assert bytes(pe.d[off:off + len(old)]) == old, 'pre-image mismatch at %X' % off
        assert len(old) == len(new)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    game = os.path.basename(os.path.dirname(dll))
    bdir = os.path.join(BACKUP_ROOT, stamp, game)
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(dll, os.path.join(bdir, os.path.basename(dll)))
    for off, old, new in edits:
        pe.d[off:off + len(new)] = new
    out = bytes(pe.d)
    tmp = dll + '.mapfix.tmp'
    with open(tmp, 'wb') as f:
        f.write(out)
    os.replace(tmp, dll)
    rec = dict(installed=stamp, md5_before=md5(data), md5_after=md5(out), backup=os.path.join(bdir, os.path.basename(dll)),
               info={k: '0x%X' % v for k, v in info.items()},
               edits=[dict(offset=off, old=old.hex(), new=new.hex()) for off, old, new in edits])
    with open(record_path(dll), 'w') as f:
        json.dump(rec, f, indent=1)
    print('installed:', dll)
    print('   md5 %s -> %s' % (rec['md5_before'], rec['md5_after']))
    print('   backup:', rec['backup'])
    for k, v in rec['info'].items():
        print('   %-12s %s' % (k, v))


def uninstall(dll):
    data = bytearray(open(dll, 'rb').read())
    if not is_installed(data):
        print('not installed:', dll)
        return
    rp = record_path(dll)
    if not os.path.exists(rp):
        raise SystemExit('patch record %s missing - restore the DLL from the backup folder instead' % rp)
    rec = json.load(open(rp))
    for e in rec['edits']:
        off, old, new = e['offset'], bytes.fromhex(e['old']), bytes.fromhex(e['new'])
        if bytes(data[off:off + len(new)]) != new:
            raise SystemExit('bytes at 0x%X changed since install - not touching the file' % off)
    for e in rec['edits']:
        off, old = e['offset'], bytes.fromhex(e['old'])
        data[off:off + len(old)] = old
    tmp = dll + '.mapfix.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, dll)
    os.remove(rp)
    print('uninstalled:', dll, ' md5 now', md5(bytes(data)), '(before install: %s)' % rec['md5_before'])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'install', 'uninstall', 'plan'])
    ap.add_argument('--dll', action='append')
    a = ap.parse_args()
    for dll in (a.dll or DEFAULT_DLLS):
        if not os.path.exists(dll):
            print('missing:', dll)
            continue
        if a.cmd == 'status':
            status(dll)
        elif a.cmd == 'install':
            install(dll)
        elif a.cmd == 'uninstall':
            uninstall(dll)
        else:
            pe = PEFile(open(dll, 'rb').read())
            if is_installed(pe.d):
                print('already installed:', dll)
                continue
            edits, info = plan(pe)
            print(dll)
            for k, v in info.items():
                print('   %-12s 0x%X' % (k, v))
            for off, old, new in edits:
                print('   @0x%06X  %s -> %s' % (off, old.hex() if any(old) else '(%d zero bytes)' % len(old), new.hex()))


if __name__ == '__main__':
    main()
