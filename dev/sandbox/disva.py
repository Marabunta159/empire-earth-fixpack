"""Disassemble a PE file on disk by VA, with import names resolved.

  python disva.py <pe file> <va hex> <len>          plain range
  python disva.py <pe file> fn <va hex> [maxlen]    whole function containing va (prologue search backwards)
"""
import os, re, struct, sys
import capstone
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'crashfix'))
from mdmp import undname


class Img:
    def __init__(self, path):
        d = self.d = open(path, 'rb').read()
        e = struct.unpack_from('<I', d, 0x3c)[0]
        n = struct.unpack_from('<H', d, e + 6)[0]
        self.base = struct.unpack_from('<I', d, e + 52)[0]
        so = e + 24 + struct.unpack_from('<H', d, e + 20)[0]
        self.secs = [struct.unpack_from('<IIII', d, so + i * 40 + 8) for i in range(n)]
        self.imports = {}
        irva = struct.unpack_from('<I', d, e + 24 + 96 + 8)[0]
        if irva:
            o = self.off(self.base + irva)
            while True:
                oft, _, _, name, ft = struct.unpack_from('<IIIII', d, o)
                if not name:
                    break
                dll = self.cstr(self.base + name)
                t = self.off(self.base + (oft or ft)); k = 0
                while True:
                    v = struct.unpack_from('<I', d, t + k * 4)[0]
                    if not v:
                        break
                    nm = ('#%d' % (v & 0xffff)) if v & 0x80000000 else self.cstr(self.base + v + 2)
                    self.imports[self.base + ft + k * 4] = dll.split('.')[0][:12] + '!' + (undname(nm) if nm.startswith('?') else nm)
                    k += 1
                o += 20

    def off(self, va):
        rva = va - self.base
        for vs, a, rs, rp in self.secs:
            if a <= rva < a + max(vs, rs):
                return rva - a + rp
        raise SystemExit('va %x not mapped' % va)

    def cstr(self, va):
        o = self.off(va)
        return self.d[o:self.d.index(b'\0', o)].decode('latin1')

    def fn_start(self, va):
        o = self.off(va)
        for k in range(o, o - 0x4000, -1):
            if self.d[k:k + 3] == b'\x55\x8b\xec' and self.d[k - 1] in (0xc3, 0xcc, 0x90) or (self.d[k:k + 3] == b'\x55\x8b\xec' and self.d[k - 3] == 0xc2):
                return va - (o - k)
        return va

    def dis(self, va, ln, stop_at_ret=False):
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        o = self.off(va)
        out = []
        for i in md.disasm(self.d[o:o + ln], va):
            s = i.op_str
            m = re.search(r'dword ptr \[(0x[0-9a-f]+)\]', s)
            if m and int(m.group(1), 16) in self.imports:
                s += '      ; ' + self.imports[int(m.group(1), 16)]
            out.append('%x  %-7s %s' % (i.address, i.mnemonic, s))
        return out


if __name__ == '__main__':
    im = Img(sys.argv[1])
    if sys.argv[2] == 'fn':
        va = im.fn_start(int(sys.argv[3], 16))
        ln = int(sys.argv[4]) if len(sys.argv) > 4 else 0x600
    else:
        va = int(sys.argv[2], 16); ln = int(sys.argv[3])
    print('\n'.join(im.dis(va, ln)))
