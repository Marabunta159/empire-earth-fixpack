"""python immscan.py <pe> <va lo> <va hi> <imm hex>...  - instructions in [lo,hi) using the given 32-bit immediates"""
import struct, sys, capstone
from disva import Img
im = Img(sys.argv[1]); d = im.d
lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
o0, o1 = im.off(lo), im.off(hi)
for a in sys.argv[4:]:
    v = int(a, 16); pat = struct.pack('<I', v); i = o0
    while True:
        i = d.find(pat, i, o1)
        if i < 0: break
        va = lo + i - o0
        for k in range(1, 8):
            ins = next(md.disasm(d[i - k:i - k + 16], va - k), None)
            if ins and ins.size == k + 4 and ('0x%x' % v) in ins.op_str:
                print('%x: %s %s' % (ins.address, ins.mnemonic, ins.op_str)); break
        i += 1
