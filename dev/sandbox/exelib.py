"""Shared helpers for static analysis of the EE / AoC executables."""
import os, re, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'crashfix'))
from mdmp import PE, undname
import pedis, capstone

NEO = r'C:\Program Files (x86)\Neo Empire Earth'
GAMES = {'ee': (NEO + r'\Empire Earth', 'Empire Earth.exe'),
         'aoc': (NEO + r'\Empire Earth - The Art of Conquest', 'EE-AOC.exe')}
cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
cs.detail = False


class Exe:
    def __init__(self, game):
        self.dir, self.name = GAMES[game]
        self.pe = PE(os.path.join(self.dir, self.name))
        self.d = self.pe.d
        self.base = self.pe.image_base
        self.imps = pedis.imports(self.pe)
        self._strs = None
        # code lives in the first section (section names are scrambled by the NeoEE build)
        s = self.pe.sections[0]
        self.code_va = self.base + s[1]
        self.code_end = self.code_va + s[4]

    @property
    def strs(self):
        if self._strs is None:
            import langstr
            self._strs = langstr.strings(os.path.join(self.dir, 'Language.dll'), 0, 70000)
        return self._strs

    def off(self, va):
        return self.pe.rva2off(va - self.base)

    def va(self, off):
        return self.base + self.pe.off2rva(off)

    def read(self, va, n):
        return self.pe.read(va - self.base, n)

    def u32(self, va):
        return struct.unpack('<I', self.read(va, 4))[0]

    def find_bytes(self, pat, lo=None, hi=None):
        """all VAs of a byte pattern inside the code section"""
        lo = lo or self.code_va
        hi = hi or self.code_end
        blob = self.read(lo, hi - lo)
        out, i = [], 0
        while True:
            i = blob.find(pat, i)
            if i < 0:
                break
            out.append(lo + i)
            i += 1
        return out

    def refs_abs(self, addr):
        """VAs in code where the absolute 32-bit value `addr` appears"""
        return self.find_bytes(struct.pack('<I', addr))

    def calls_to(self, target):
        blob = self.read(self.code_va, self.code_end - self.code_va)
        out = []
        for m in re.finditer(b'\xE8', blob):
            i = m.start()
            if i + 5 <= len(blob):
                t = (self.code_va + i + 5 + struct.unpack_from('<i', blob, i + 1)[0]) & 0xFFFFFFFF
                if t == target:
                    out.append(self.code_va + i)
        return out

    def func_start(self, va, maxback=0x4000):
        """nearest preceding address that looks like a function start (after ret/int3/nop padding or called)"""
        blob = self.read(va - maxback, maxback)
        for i in range(len(blob) - 1, 2, -1):
            a = va - maxback + i
            b = blob[i]
            p1 = blob[i - 1]
            # push ebp; mov ebp, esp  |  preceded by ret / ret n / int3 / nop / jmp
            if b == 0x55 and blob[i + 1:i + 3] == b'\x8b\xec' if i + 3 <= len(blob) else False:
                if p1 in (0xC3, 0xCC, 0x90) or blob[i - 3] == 0xC2 or blob[i - 5] == 0xE9 or blob[i - 2] == 0xEB:
                    return a
        return None

    def dis(self, va, n=200, stop_ret=True, maxins=400):
        out = []
        code = self.read(va, n)
        cnt = 0
        for i in cs.disasm(code, va):
            note = ''
            op = i.op_str
            if i.mnemonic == 'push' and op.startswith('0x'):
                v = int(op, 16)
                if 1000 < v < 70000 and v in self.strs:
                    note = '  ; STR %d %r' % (v, self.strs[v][:40])
            m = re.search(r'ptr \[(0x[0-9a-f]+)\]', op)
            if m:
                t = int(m.group(1), 16)
                if t in self.imps:
                    note = '  ; ' + self.imps[t]
            out.append('%08X  %-20s %-6s %s%s' % (i.address, i.bytes.hex(), i.mnemonic, op, note))
            cnt += 1
            if cnt >= maxins:
                break
            if stop_ret and i.mnemonic == 'ret':
                break
        return out


def rtti_vtables(e, classname):
    """[(vtable_va, offset_in_object)] for a class name like 'EEMCheatCode'"""
    name = ('.?AV%s@@' % classname).encode() + b'\0'
    out = []
    pos = 0
    while True:
        pos = e.d.find(name, pos)
        if pos < 0:
            break
        try:
            td = e.va(pos) - 8
        except ValueError:
            pos += 1
            continue
        tdb = struct.pack('<I', td)
        p = 0
        while True:
            p = e.d.find(tdb, p)
            if p < 0:
                break
            if p >= 12 and e.d[p - 12:p - 8] == b'\0\0\0\0':
                try:
                    col = e.va(p - 12)
                except ValueError:
                    p += 1
                    continue
                off = struct.unpack_from('<I', e.d, p - 8)[0]
                colb = struct.pack('<I', col)
                q = 0
                while True:
                    q = e.d.find(colb, q)
                    if q < 0:
                        break
                    try:
                        out.append((e.va(q) + 4, off))
                    except ValueError:
                        pass
                    q += 1
            p += 1
        pos += 1
    return out


def vtable_entries(e, vt, maxn=64):
    out = []
    for i in range(maxn):
        try:
            v = e.u32(vt + i * 4)
        except Exception:
            break
        if not (e.code_va <= v < e.code_end) and v not in e.imps and not (e.base + 0x72F000 <= v < e.base + 0xB70000 and False):
            # allow import thunk pointers (IAT values are not code); stop at first non-code value
            break
        out.append(v)
    return out
