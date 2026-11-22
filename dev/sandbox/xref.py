"""python xref.py <pe> <va hex> [...]  - direct call/jmp (E8/E9 rel32) and absolute dword references to the VAs"""
import struct, sys
from disva import Img
im = Img(sys.argv[1]); d = im.d
for a in sys.argv[2:]:
    t = int(a, 16); out = []
    for vs, va, rs, rp in im.secs[:1]:
        code = d[rp:rp + rs]; cva = im.base + va
        i = 0
        while True:
            i = code.find(b'\xe8', i)
            if i < 0: break
            if cva + i + 5 + struct.unpack_from('<i', code, i + 1)[0] == t: out.append('call@%x' % (cva + i))
            i += 1
        i = 0
        while True:
            i = code.find(b'\xe9', i)
            if i < 0: break
            if cva + i + 5 + struct.unpack_from('<i', code, i + 1)[0] == t: out.append('jmp@%x' % (cva + i))
            i += 1
    pat = struct.pack('<I', t); i = 0
    while True:
        i = d.find(pat, i)
        if i < 0: break
        for vs, va, rs, rp in im.secs:
            if rp <= i < rp + rs: out.append('abs@%x' % (im.base + va + i - rp))
        i += 1
    print(a, ' '.join(out[:40]), '(%d)' % len(out))
