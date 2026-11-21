"""Search every file packed into a PyInstaller one-file exe (including the compressed Python modules) for
strings of the build machine.   python scan_exe.py <exe>   -> exit code 1 when something is found"""
import marshal
import os
import sys
import zlib

from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_exe import PRIVATE                                        # noqa: E402

exe = sys.argv[1]
PRIVATE = PRIVATE + [a.encode() for a in sys.argv[2:]]             # extra patterns (self test of the scanner)
hits = []


def check(name, data):
    low = data.lower()
    for p in PRIVATE:
        if p.lower() in low:
            i = low.index(p.lower())
            hits.append((name, p.decode(), data[max(0, i - 30):i + 50]))


arc = CArchiveReader(exe)
n = 0
for name in arc.toc:
    data = arc.extract(name)
    n += 1
    check(name, data)
    if name.lower().endswith('.pyz'):
        tmp = os.path.join(os.environ.get('TEMP', '.'), '_scan_pyz.pyz')
        open(tmp, 'wb').write(data)
        z = ZlibArchiveReader(tmp)
        for mod in z.toc:
            try:
                code = z.extract(mod)
            except Exception:
                continue
            n += 1
            if code is not None:
                check('PYZ:' + mod, marshal.dumps(code) if not isinstance(code, (bytes, bytearray)) else bytes(code))
        os.remove(tmp)
check('(raw exe)', open(exe, 'rb').read())
print('%s: %d packed items checked, %d hits' % (os.path.basename(exe), n, len(hits)))
for name, p, ctx in hits[:20]:
    print('  %s: %s  ...%r...' % (name, p, ctx))
sys.exit(1 if hits else 0)
