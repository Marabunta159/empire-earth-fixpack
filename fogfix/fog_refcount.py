"""Empire Earth / Art of Conquest: fog of war reference count fix (Low-Level Engine.dll).

Defect (MODLOG.md, "Fog-Bug: Refcount-Patch")
  Every terrain tile has a 16 bit counter: 0 = never seen, 1 = explored (shadow), >= 2 = visible.
      GETerrainMesh::ReferenceTile:    if (rc == 0) rc = 2; else rc++;
      GETerrainMesh::DereferenceTile:  rc--;                       (unconditional)
  One Dereference too many takes the counter through 0 to -1; the renderer reads it unsigned
  (65535 = "visible"), the next Reference wraps it to 0 ("never seen") -> units flicker in
  and out of the fog.

Fix (same semantics as the patch Empire Earth got on 2026-10-09)
      ReferenceTile:    if (rc < 2) rc = 2; else rc++;
      DereferenceTile:  if (rc >= 2) rc--;
  Both functions are rewritten in place (the address calculation is 2 bytes shorter, which
  makes room for the checks) - no code cave, no header change, nothing position dependent.

Usage
  python fog_refcount.py status | install | uninstall   [--dll "<path to Low-Level Engine.dll>"]
  default: Art of Conquest.  Empire Earth already carries the older cave variant of this fix
  (reported as such, left alone).  Backup: backups/fogfix/<time>/, patch record next to the DLL.
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
DEFAULT_DLLS = [NEO + r'\Empire Earth - The Art of Conquest\Low-Level Engine.dll']
BACKUP_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', 'fogfix')
EXP_REF = b'?ReferenceTile@GETerrainMesh@@'
EXP_DEREF = b'?DereferenceTile@GETerrainMesh@@'

# original code (?? = offset of the tile row table inside GETerrainMesh, differs between EE and AoC)
CALC = '8B 89 ?? ?? ?? ?? 8B 44 24 08 8D 04 40 8D 04 81 8B 4C 24 04 2B 08 8B 40 08'
ORIG_DEREF = CALC + ' 66 FF 0C 88 8D 04 88 C2 08 00'
ORIG_REF = CALC + ' 8D 04 88 33 C9 66 8B 08 66 85 C9 76 06 41 66 89 08 EB 05 66 C7 00 02 00 C2 08 00'


def rx(pattern):
    out = b''
    for tok in pattern.split():
        out += b'(.)' if tok == '??' else re.escape(bytes.fromhex(tok))
    return re.compile(out, re.S)


def new_calc(off):
    return (bytes.fromhex('6B4424080C')                  # imul eax,[esp+8],12      ; y * sizeof(GETMTileRow)
            + b'\x03\x81' + off                           # add  eax,[ecx+rows]      ; -> row
            + bytes.fromhex('8B4C2404')                   # mov  ecx,[esp+4]         ; x
            + bytes.fromhex('2B08')                       # sub  ecx,[eax]           ; x - row.start_x
            + bytes.fromhex('8B4008')                     # mov  eax,[eax+8]         ; row.tiles
            + bytes.fromhex('8D0488'))                    # lea  eax,[eax+ecx*4]     ; -> tile


def new_deref(off):
    return (new_calc(off)
            + bytes.fromhex('66833802')                   # cmp  word [eax],2
            + bytes.fromhex('7C03')                       # jl   done
            + bytes.fromhex('66FF08')                     # dec  word [eax]
            + bytes.fromhex('C20800'))                    # done: ret 8


def new_ref(off, size):
    code = (new_calc(off)
            + bytes.fromhex('66833802')                   # cmp  word [eax],2
            + bytes.fromhex('7D08')                       # jge  inc
            + bytes.fromhex('66C7000200')                 # mov  word [eax],2
            + bytes.fromhex('C20800')                     # ret  8
            + bytes.fromhex('66FF00')                     # inc: inc word [eax]
            + bytes.fromhex('C20800'))                    # ret  8
    return code + b'\xCC' * (size - len(code))


class PE:
    def __init__(self, data):
        d = self.d = data
        pe = struct.unpack_from('<I', d, 0x3C)[0]
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        optsz = struct.unpack_from('<H', d, pe + 20)[0]
        self.opt = pe + 24
        self.sections = []
        for i in range(nsec):
            so = self.opt + optsz + i * 40
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', d, so + 8)
            self.sections.append((va, vsize, rptr, rsize))

    def off(self, rva):
        for va, _vs, rptr, rsize in self.sections:
            if va <= rva < va + rsize:
                return rptr + rva - va
        raise ValueError('RVA %X is not file backed' % rva)

    def export(self, prefix):
        o = self.off(struct.unpack_from('<I', self.d, self.opt + 96)[0])
        nnam = struct.unpack_from('<I', self.d, o + 24)[0]
        af, an, ao = struct.unpack_from('<III', self.d, o + 28)
        for i in range(nnam):
            no = self.off(struct.unpack_from('<I', self.d, self.off(an) + i * 4)[0])
            if self.d[no:no + len(prefix)] == prefix:
                ordi = struct.unpack_from('<H', self.d, self.off(ao) + i * 2)[0]
                return struct.unpack_from('<I', self.d, self.off(af) + ordi * 4)[0]
        raise RuntimeError('export %s not found' % prefix.decode())

    def relocs(self):
        rva, size = struct.unpack_from('<II', self.d, self.opt + 96 + 5 * 8)
        out = set()
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


def inspect(data):
    """-> ('pristine' | 'installed' | 'cave' | 'unknown', edits)"""
    pe = PE(data)
    rel = pe.relocs()
    edits, states = [], []
    for prefix, orig, make in ((EXP_DEREF, ORIG_DEREF, lambda off, n: new_deref(off)),
                               (EXP_REF, ORIG_REF, new_ref)):
        rva = pe.export(prefix)
        o = pe.off(rva)
        n = len(orig.split())
        cur = bytes(data[o:o + n])
        m = rx(orig).fullmatch(cur)
        if m:
            off = b''.join(m.groups())
            new = make(off, n)
            assert len(new) == n, (prefix, len(new), n)
            if any(rva - 3 <= r < rva + n for r in rel):
                raise RuntimeError('relocation inside %s' % prefix.decode())
            edits.append((o, cur, new))
            states.append('pristine')
        elif cur[:5] == bytes.fromhex('6B4424080C') and cur[5:7] == b'\x03\x81' and cur == make(cur[7:11], n):
            states.append('installed')
        elif cur[:1] == b'\xE9' and set(cur[5:]) <= {0x90, 0x00}:        # jmp cave + nops (EE, 2026-10-09)
            states.append('cave')
        else:
            states.append('unknown')
    if len(set(states)) != 1:
        return 'unknown', []
    return states[0], edits


def md5(b):
    return hashlib.md5(b).hexdigest().upper()


def record_path(dll):
    return dll + '.fogfix.json'


TEXT = {'pristine': 'not installed', 'installed': 'INSTALLED (in place)',
        'cave': 'fixed already (cave variant of 2026-10-09)', 'unknown': 'UNKNOWN code - not touched'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'install', 'uninstall'])
    ap.add_argument('--dll', action='append')
    a = ap.parse_args()
    rc = 0
    for dll in a.dll or DEFAULT_DLLS:
        if not os.path.exists(dll):
            print(dll, ': missing')
            rc = 1 if a.dll else rc
            continue
        data = open(dll, 'rb').read()
        try:
            state, edits = inspect(data)
        except RuntimeError as e:
            print('%s: %s' % (dll, e))
            rc = 1
            continue
        if a.cmd == 'status':
            print('%s : %s  md5 %s' % (dll, TEXT[state], md5(data)))
        elif a.cmd == 'install':
            if state != 'pristine':
                print('   %s: %s' % (dll, TEXT[state]))
                rc |= state == 'unknown'
                continue
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
            with open(record_path(dll), 'w') as f:
                json.dump(dict(dll=dll, md5_before=md5(data), md5_after=md5(bytes(out)), backup=bdir,
                               edits=[dict(off=off, old=old.hex(), new=new.hex()) for off, old, new in edits]), f, indent=1)
            print('   patched %s\n   md5 %s -> %s\n   backup %s' % (dll, md5(data), md5(bytes(out)), bdir))
        else:
            if state != 'installed' or not os.path.exists(record_path(dll)):
                print('   %s: %s - nothing to remove' % (dll, TEXT[state]))
                continue
            out = bytearray(data)
            for e in json.load(open(record_path(dll)))['edits']:
                new, old = bytes.fromhex(e['new']), bytes.fromhex(e['old'])
                if bytes(out[e['off']:e['off'] + len(new)]) != new:
                    print('   bytes changed since install - not touching', dll)
                    rc = 1
                    break
                out[e['off']:e['off'] + len(old)] = old
            else:
                tmp = dll + '.tmp'
                with open(tmp, 'wb') as f:
                    f.write(out)
                os.replace(tmp, dll)
                os.remove(record_path(dll))
                print('   restored %s  md5 %s' % (dll, md5(bytes(out))))
    return rc


if __name__ == '__main__':
    sys.exit(main())
