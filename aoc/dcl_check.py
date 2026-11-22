"""Compare the pure-Python DCL decompressor (ssa_unpack.explode) with libDCL.dll on real archive entries.

  python dcl_check.py "<data.ssa>" [...]      all db\\*.dat entries plus every 40th other compressed entry
"""
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ssa_unpack as su                                                   # noqa: E402

dcl = su.DCLDecompressor(su.find_dll())
for path in sys.argv[1:]:
    ssa = su.parse_ssa(path)
    n = ok = bad = big = 0
    t0 = time.time()
    for e, blob in zip(ssa['entries'], ssa['blobs']):
        p = e['path'].replace('/', os.sep).lower()
        if blob[:4] != su.DCL_MAGIC:
            continue
        n += 1
        if not (p.startswith('db' + os.sep) or n % 40 == 0):
            continue
        size = struct.unpack('<I', blob[4:8])[0]
        if size > 600000:
            big += 1
            continue
        ref = dcl.decompress(blob[12:], size)
        try:
            got = su.explode(blob[12:], size)
        except Exception as ex:
            got = None
            print('  ERR', p, ex)
        if got == ref:
            ok += 1
        else:
            bad += 1
            print('  MISMATCH', p)
    print('%s: compared %d (identical %d, different %d, skipped large %d) of %d compressed entries, %.1f s'
          % (path, ok + bad, ok, bad, big, n, time.time() - t0))
