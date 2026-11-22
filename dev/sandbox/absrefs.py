"""python absrefs.py <pe> <lo hex> <hi hex>  - every instruction in .text with an absolute imm/disp in [lo, hi)"""
import struct, sys, capstone
from disva import Img
im = Img(sys.argv[1]); d = im.d
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
vs, va, rs, rp = im.secs[0]
code = d[rp:rp + rs]; cva = im.base + va
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
hits = []
for i in range(len(code) - 4):
    v = struct.unpack_from('<I', code, i)[0]
    if lo <= v < hi:
        best = None
        for k in range(1, 9):
            ins = next(md.disasm(code[i - k:i - k + 16], cva + i - k), None)
            if ins and ins.size >= k + 4 and ('0x%x' % v) in ins.op_str:
                best = ins; break
        hits.append((cva + i, v, best))
for at, v, ins in hits:
    print('%x  val=%x  %s' % (at, v, ('%x: %s %s' % (ins.address, ins.mnemonic, ins.op_str)) if ins else '?? (no instruction decode)'))
print(len(hits), 'refs')
