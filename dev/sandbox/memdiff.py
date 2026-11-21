"""Compare the running sandbox game's code in memory with the exe on disk (finds runtime patches, e.g. by dreXmod).

  python memdiff.py [lo hex] [hi hex]     default: first section
"""
import os, sys, struct
import frida
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sbx
from disva import Img
j = sbx.find()
if not j: raise SystemExit('sandbox game not running')
im = Img(os.path.join(j['dir'], j['exe']))
vs, va, rs, rp = im.secs[0]
lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else im.base + va
hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else im.base + va + rs
s = frida.attach(j['pid'])
sc = s.create_script("rpc.exports = { rd(a, n) { return ptr(a).readByteArray(n); } };")
sc.load()
runs = []; a = lo
while a < hi:
    n = min(0x10000, hi - a)
    mem = sc.exports_sync.rd(a, n); disk = im.d[im.off(a):im.off(a) + n]
    for i in range(n):
        if mem[i] != disk[i]:
            if runs and runs[-1][1] >= a + i - 8: runs[-1][1] = a + i + 1
            else: runs.append([a + i, a + i + 1])
    a += n
s.detach()
print(len(runs), 'differing runs in %x..%x' % (lo, hi))
for b, e in runs[:80]:
    print('%x..%x (%d bytes)' % (b, e, e - b))
