"""Empire Earth / Art of Conquest (NeoEE): no network test for single player sessions.

What happens without this patch
  NeoEE hooks the socket bind inside NPIMPublish ("TCP Protocol.dll") and calls
  punch_hole() from neoee.dll for EVERY session the game creates: port check against the
  NeoEE server (3 s timeout), UPnP, UDP hole punching, the "ball" window.  The game also
  creates such a session for single player (random map setup, loading a saved game,
  campaign, scenario, editor test) - the engine marks those as local (session name
  "EEName", NESynchronousServer ctor bool -> NPIMPublish arg 8 -> record+0x55 = 1, the
  flag that also keeps the session out of LAN searches).  NeoEE ignores that flag.

What the patch does
  The hook first looks at the local flag of the session record:
    local session  -> the game's original code runs (plain bind of the UDP port), neoee.dll
                      is not even loaded
    anything else  -> NeoEE's hook exactly as before (multiplayer hosting unchanged)
  All new code is position independent (the DLL gets relocated); the one relocated
  instruction of the original code (call [bind]) is reused in place.

Usage
  python sp_nonet.py status | plan | install | uninstall   [--dll "<path to TCP Protocol.dll>"]
  default: both NeoEE installs.  Backup: backups/netfix/<time>/, patch record next to the DLL.
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
DEFAULT_DLLS = [NEO + r'\Empire Earth\TCP Protocol.dll',
                NEO + r'\Empire Earth - The Art of Conquest\TCP Protocol.dll']
BACKUP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', 'netfix')
MARK = b'EESPNET1'
LOCAL_FLAG = 0x55          # session record: "local session" byte (NPIMPublish argument 8)
SAVED_ESI = -0x1C          # bind helper frame: NPIMPublish's esi (= session record)


def sig(pattern):
    out = b''
    for tok in pattern.split():
        out += b'.' if tok == '??' else re.escape(bytes.fromhex(tok))
    return re.compile(out, re.S)


# NeoEE's hook site inside the bind helper:  mov eax,0 / jmp +0C / <left over: mov word [ebp-18h],2 /
# call [bind]> / jmp cave / nop nop / push eax / lea eax,[ebp-18h] / push eax / push esi / call [getsockname]
SIG_HOOK = sig('B8 00 00 00 00 EB 0C 66 C7 45 E8 02 00 FF 15 ?? ?? ?? ?? E9 ?? ?? ?? ?? 90 90 50 8D 45 E8 50 56 FF 15')
SIG_HELPER = bytes.fromhex('558BEC83EC185657')                       # push ebp / mov ebp,esp / sub esp,18h / push esi / push edi
SIG_CAVE = bytes.fromhex('609C89F05589E5')                           # pushad / pushfd / mov eax,esi / push ebp / mov ebp,esp
SIG_CAVE_TAIL = sig('5D 9D 61 85 C0 0F 85 ?? ?? ?? ?? 8D 45 F8 E9 ?? ?? ?? ??')
SIG_FLAG = bytes.fromhex('8A4D24830EFF834E04FF')                     # mov cl,[ebp+24h] / or [esi],-1 / or [esi+4],-1
SIG_FLAG2 = bytes.fromhex('884E55')                                  # mov [esi+55h],cl


class PE:
    def __init__(self, data):
        self.d = bytearray(data)
        d = self.d
        pe = struct.unpack_from('<I', d, 0x3C)[0]
        assert d[pe:pe + 4] == b'PE\0\0'
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        optsz = struct.unpack_from('<H', d, pe + 20)[0]
        self.opt = pe + 24
        self.base = struct.unpack_from('<I', d, self.opt + 28)[0]
        self.sections = []
        for i in range(nsec):
            so = self.opt + optsz + i * 40
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', d, so + 8)
            self.sections.append((d[so:so + 8].rstrip(b'\0').decode(), va, vsize, rptr, rsize))

    def off(self, rva):
        for _n, va, _vs, rptr, rsize in self.sections:
            if va <= rva < va + rsize:
                return rptr + rva - va
        raise ValueError('RVA %X is not file backed' % rva)

    def rva(self, off):
        for _n, va, _vs, rptr, rsize in self.sections:
            if rptr <= off < rptr + rsize:
                return va + off - rptr
        raise ValueError('offset %X is not in a section' % off)

    def section_of(self, rva):
        for s in self.sections:
            if s[1] <= rva < s[1] + s[4]:
                return s
        raise ValueError('RVA %X is not in a section' % rva)

    def import_at(self, slot_rva):
        """(dll, name or ordinal) of the IAT slot"""
        o = self.off(struct.unpack_from('<I', self.d, self.opt + 96 + 8)[0])
        while True:
            oft, _ts, _fc, name, ft = struct.unpack_from('<IIIII', self.d, o)
            if not name:
                return None
            no = self.off(name)
            dll = bytes(self.d[no:self.d.index(b'\0', no)]).decode().lower()
            t = self.off(oft or ft)
            i = 0
            while True:
                v = struct.unpack_from('<I', self.d, t + i * 4)[0]
                if not v:
                    break
                if ft + i * 4 == slot_rva:
                    if v & 0x80000000:
                        return dll, v & 0xFFFF
                    vo = self.off(v) + 2
                    return dll, bytes(self.d[vo:self.d.index(b'\0', vo)]).decode()
                i += 1
            o += 20

    def relocs(self):
        rva, size = struct.unpack_from('<II', self.d, self.opt + 96 + 5 * 8)
        out = set()
        if not rva:
            return out
        o = self.off(rva)
        end = o + size
        while o < end:
            page, bs = struct.unpack_from('<II', self.d, o)
            if not bs:
                break
            for i in range((bs - 8) // 2):
                e = struct.unpack_from('<H', self.d, o + 8 + i * 2)[0]
                if e >> 12 == 3:
                    out.add(page + (e & 0xFFF))
            o += bs
        return out


def rel32(at_rva, target_rva, length=5):
    return struct.pack('<i', target_rva - (at_rva + length))


def plan(data):
    """-> list of (file offset, old bytes, new bytes) + info dict.  Raises RuntimeError if the DLL is not the expected one."""
    pe = PE(data)
    d = bytes(pe.d)
    if MARK in d:
        raise RuntimeError('already patched')
    _n, tva, _vs, trptr, trsize = pe.sections[0]
    code = d[trptr:trptr + trsize]
    ms = list(SIG_HOOK.finditer(code))
    if len(ms) != 1:
        raise RuntimeError('NeoEE bind hook not found (%d hits) - not a NeoEE "TCP Protocol.dll"?' % len(ms))
    h_off = trptr + ms[0].start()
    hook = pe.rva(h_off)                                   # mov eax,0
    b = ms[0].group(0)
    if pe.import_at(struct.unpack_from('<I', b, 15)[0] - pe.base) != ('ws2_32.dll', 2):
        raise RuntimeError('left over call is not bind()')
    if code.rfind(SIG_HELPER, 0, ms[0].start()) < ms[0].start() - 0x90:
        raise RuntimeError('bind helper prologue not found')
    if code.count(SIG_FLAG) != 1 or SIG_FLAG2 not in code:
        raise RuntimeError('NPIMPublish local flag code not found')
    cave1 = hook + 0x13 + 5 + struct.unpack_from('<i', b, 0x14)[0]
    c_off = pe.off(cave1)
    if d[c_off:c_off + len(SIG_CAVE)] != SIG_CAVE:
        raise RuntimeError('NeoEE cave looks different')
    m = SIG_CAVE_TAIL.search(d, c_off, c_off + 0x100)
    if not m:
        raise RuntimeError('NeoEE cave tail not found')
    t = m.group(0)
    t_rva = pe.rva(m.start())
    err = t_rva + 5 + 6 + struct.unpack_from('<i', t, 7)[0]              # jne <bind failed>
    back = t_rva + 14 + 5 + struct.unpack_from('<i', t, 15)[0]            # jmp back
    if back != hook + 0x1A:
        raise RuntimeError('NeoEE cave returns to an unexpected place')
    jne8 = err - (hook + 0x15 + 2)
    if not -128 <= jne8 <= 127:
        raise RuntimeError('error path too far for a short jump')
    # our cave: free bytes behind NeoEE's first cave, same section
    sec = pe.section_of(cave1)
    my_off = (m.end() + 0x1F) & ~0xF
    my = pe.rva(my_off)
    cave = bytearray()
    cave += bytes([0x8B, 0x45, SAVED_ESI & 0xFF])                         # mov eax,[ebp-1Ch]      ; session record
    cave += b'\x85\xC0'                                                   # test eax,eax
    cave += b'\x74\x06'                                                   # jz   neo
    cave += bytes([0x80, 0x78, LOCAL_FLAG, 0x00])                         # cmp byte [eax+55h],0
    cave += b'\x75\x0A'                                                   # jne  local
    cave += b'\xB8\x00\x00\x00\x00'                                       # neo: mov eax,0         (displaced)
    cave += b'\xE9' + rel32(my + len(cave), cave1)                        # jmp  NeoEE cave
    cave += b'\x6A\x10'                                                   # local: push 10h
    cave += b'\x8D\x45\xE8'                                               # lea eax,[ebp-18h]
    cave += b'\x50\x56'                                                   # push eax / push esi
    cave += b'\xE9' + rel32(my + len(cave), hook + 7)                     # jmp  mov word [ebp-18h],2 / call [bind]
    while len(cave) % 4:
        cave += b'\xCC'
    cave += MARK
    if my_off + len(cave) > sec[3] + sec[4] or any(d[my_off - 8:my_off + len(cave) + 8]):
        raise RuntimeError('no free room behind the NeoEE cave')
    new_hook = b'\xE9' + rel32(hook, my) + b'\x90\x90'
    new_tail = b'\x85\xC0\x75' + bytes([jne8 & 0xFF]) + b'\x8D\x45\xF8'   # test eax,eax / jne err / lea eax,[ebp-8]
    edits = [(h_off, d[h_off:h_off + 7], new_hook),
             (h_off + 0x13, d[h_off + 0x13:h_off + 0x1A], new_tail),
             (my_off, d[my_off:my_off + len(cave)], bytes(cave))]
    rel = pe.relocs()
    for off, old, new in edits:
        r = pe.rva(off)
        hit = [x for x in rel if r - 3 <= x < r + len(new)]
        if hit:
            raise RuntimeError('relocation inside patched bytes at RVA %X' % hit[0])
    if hook + 15 not in rel:
        raise RuntimeError('call [bind] has no relocation entry')
    info = dict(hook=pe.base + hook, neo_cave=pe.base + cave1, my_cave=pe.base + my, bind_error=pe.base + err)
    return edits, info


def md5(b):
    return hashlib.md5(b).hexdigest().upper()


def record_path(dll):
    return dll + '.spnonet.json'


def status(dll):
    if not os.path.exists(dll):
        return 'missing'
    data = open(dll, 'rb').read()
    return ('INSTALLED' if MARK in data else 'not installed') + '  md5 ' + md5(data)


def install(dll):
    data = open(dll, 'rb').read()
    if MARK in data:
        print('   already installed:', dll)
        return 0
    edits, info = plan(data)
    out = bytearray(data)
    for off, old, new in edits:
        out[off:off + len(new)] = new
    bdir = os.path.join(BACKUP_ROOT, datetime.datetime.now().strftime('%Y%m%d-%H%M%S'),
                        os.path.basename(os.path.dirname(dll)))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(dll, os.path.join(bdir, os.path.basename(dll)))
    tmp = dll + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(out)
    os.replace(tmp, dll)
    rec = dict(dll=dll, md5_before=md5(data), md5_after=md5(bytes(out)), backup=bdir,
               edits=[dict(off=off, old=old.hex(), new=new.hex()) for off, old, new in edits],
               info={k: '%08X' % v for k, v in info.items()})
    with open(record_path(dll), 'w') as f:
        json.dump(rec, f, indent=1)
    print('   patched %s\n   md5 %s -> %s\n   backup %s' % (dll, rec['md5_before'], rec['md5_after'], bdir))
    return 0


def uninstall(dll):
    if not os.path.exists(dll):
        return 0
    data = bytearray(open(dll, 'rb').read())
    if MARK not in data:
        print('   not installed:', dll)
        return 0
    rp = record_path(dll)
    if not os.path.exists(rp):
        print('   patch record missing - restore %s from backups/netfix by hand' % dll)
        return 1
    rec = json.load(open(rp))
    for e in rec['edits']:
        new = bytes.fromhex(e['new'])
        if bytes(data[e['off']:e['off'] + len(new)]) != new:
            print('   bytes changed since install - not touching', dll)
            return 1
    for e in rec['edits']:
        old = bytes.fromhex(e['old'])
        data[e['off']:e['off'] + len(old)] = old
    tmp = dll + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, dll)
    os.remove(rp)
    print('   restored %s  md5 %s' % (dll, md5(bytes(data))))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'plan', 'install', 'uninstall'])
    ap.add_argument('--dll', action='append')
    a = ap.parse_args()
    rc = 0
    for dll in a.dll or DEFAULT_DLLS:
        if not os.path.exists(dll):
            if a.dll:
                print(dll, ': missing')
                rc = 1
            continue
        try:
            if a.cmd == 'status':
                print(dll, ':', status(dll))
            elif a.cmd == 'plan':
                edits, info = plan(open(dll, 'rb').read())
                print(dll)
                for k, v in info.items():
                    print('   %-11s %08X' % (k, v))
                for off, old, new in edits:
                    print('   off %05X  %s\n          -> %s' % (off, old.hex(), new.hex()))
            elif a.cmd == 'install':
                rc |= install(dll)
            else:
                rc |= uninstall(dll)
        except RuntimeError as e:
            print('%s: %s' % (dll, e))
            rc = 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
