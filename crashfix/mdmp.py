"""Minimal x86 minidump reader + heuristic stack walker for Empire Earth crash dumps.

Usage:  python mdmp.py <dump.dmp> [--stack N] [--raw]
No third-party deps except capstone (optional, for disassembly).
"""
import ctypes
import os
import struct
import sys

try:
    import capstone
    _CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
except Exception:  # pragma: no cover
    _CS = None


class PE:
    """Maps a PE file by RVA and exposes its export table."""

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.d = f.read()
        d = self.d
        pe = struct.unpack_from('<I', d, 0x3C)[0]
        self.nsec = struct.unpack_from('<H', d, pe + 6)[0]
        self.timestamp = struct.unpack_from('<I', d, pe + 8)[0]
        optsz = struct.unpack_from('<H', d, pe + 20)[0]
        opt = pe + 24
        self.magic = struct.unpack_from('<H', d, opt)[0]
        self.image_base = struct.unpack_from('<I', d, opt + 28)[0]
        self.size_of_image = struct.unpack_from('<I', d, opt + 56)[0]
        self.dirs = []
        ddoff = opt + 96
        for i in range(16):
            self.dirs.append(struct.unpack_from('<II', d, ddoff + i * 8))
        self.sections = []
        so = opt + optsz
        for i in range(self.nsec):
            name = d[so:so + 8].rstrip(b'\0').decode('latin1')
            vsize, va, rsize, rptr = struct.unpack_from('<IIII', d, so + 8)
            chars = struct.unpack_from('<I', d, so + 36)[0]
            self.sections.append((name, va, vsize, rptr, rsize, chars))
            so += 40
        self._exports = None

    def rva2off(self, rva):
        for name, va, vsize, rptr, rsize, _ in self.sections:
            if va <= rva < va + max(vsize, rsize):
                o = rva - va
                if o < rsize:
                    return rptr + o
                return None
        return None

    def off2rva(self, off):
        for name, va, vsize, rptr, rsize, _ in self.sections:
            if rptr <= off < rptr + rsize:
                return va + off - rptr
        return None

    def read(self, rva, n):
        o = self.rva2off(rva)
        if o is None:
            return b''
        return self.d[o:o + n]

    def is_code(self, rva):
        for name, va, vsize, rptr, rsize, chars in self.sections:
            if va <= rva < va + max(vsize, rsize):
                return bool(chars & 0x20000000)
        return False

    def cstr(self, rva):
        o = self.rva2off(rva)
        if o is None:
            return ''
        e = self.d.index(b'\0', o)
        return self.d[o:e].decode('latin1')

    @property
    def exports(self):
        if self._exports is None:
            ex = []
            rva, size = self.dirs[0]
            if rva:
                o = self.rva2off(rva)
                if o is not None:
                    (nfun, nnam, afun, anam, aord) = struct.unpack_from('<IIIII', self.d, o + 20)
                    base = struct.unpack_from('<I', self.d, o + 16)[0]
                    fo = self.rva2off(afun)
                    no = self.rva2off(anam)
                    oo = self.rva2off(aord)
                    names = {}
                    for i in range(nnam):
                        nrva = struct.unpack_from('<I', self.d, no + i * 4)[0]
                        idx = struct.unpack_from('<H', self.d, oo + i * 2)[0]
                        names[idx] = self.cstr(nrva)
                    for i in range(nfun):
                        frva = struct.unpack_from('<I', self.d, fo + i * 4)[0]
                        if frva:
                            ex.append((frva, names.get(i, 'ord%d' % (i + base))))
            ex.sort()
            self._exports = ex
        return self._exports

    def sym(self, rva):
        ex = self.exports
        if not ex:
            return None
        lo, hi = 0, len(ex)
        while lo < hi:
            mid = (lo + hi) // 2
            if ex[mid][0] <= rva:
                lo = mid + 1
            else:
                hi = mid
        if lo == 0:
            return None
        frva, name = ex[lo - 1]
        return '%s+0x%X' % (undname(name), rva - frva)


_dbghelp = None


def undname(name):
    global _dbghelp
    if not name.startswith('?'):
        return name
    try:
        if _dbghelp is None:
            _dbghelp = ctypes.WinDLL('dbghelp')
        buf = ctypes.create_string_buffer(1024)
        # UNDNAME_NAME_ONLY = 0x1000
        n = _dbghelp.UnDecorateSymbolName(name.encode('latin1'), buf, 1024, 0x1000)
        if n:
            return buf.value.decode('latin1')
    except Exception:
        pass
    return name


CTX = dict(gs=140, fs=144, es=148, ds=152, edi=156, esi=160, ebx=164, edx=168, ecx=172,
           eax=176, ebp=180, eip=184, cs=188, eflags=192, esp=196, ss=200)


class Dump:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.d = f.read()
        d = self.d
        sig, ver, nstreams, dir_rva, _, self.time, self.flags = struct.unpack_from('<IIIIIIQ', d, 0)
        assert sig == 0x504D444D, 'not a minidump'
        self.streams = {}
        for i in range(nstreams):
            t, size, rva = struct.unpack_from('<III', d, dir_rva + i * 12)
            self.streams[t] = (rva, size)
        self.modules = []
        self.mem = []      # (start, size, file_off)
        self.threads = []
        self.exc = None
        self._pe = {}
        self._parse()

    def _str(self, rva):
        n = struct.unpack_from('<I', self.d, rva)[0]
        return self.d[rva + 4:rva + 4 + n].decode('utf-16le')

    def _parse(self):
        d = self.d
        if 4 in self.streams:
            rva, _ = self.streams[4]
            n = struct.unpack_from('<I', d, rva)[0]
            for i in range(n):
                o = rva + 4 + i * 108
                base, size, chk, ts, name_rva = struct.unpack_from('<QIIII', d, o)
                self.modules.append(dict(base=base, size=size, ts=ts, name=self._str(name_rva)))
        if 5 in self.streams:
            rva, _ = self.streams[5]
            n = struct.unpack_from('<I', d, rva)[0]
            for i in range(n):
                start, size, off = struct.unpack_from('<QII', d, rva + 4 + i * 16)
                self.mem.append((start, size, off))
        if 9 in self.streams:
            rva, _ = self.streams[9]
            n, base = struct.unpack_from('<QQ', d, rva)
            off = base
            for i in range(n):
                start, size = struct.unpack_from('<QQ', d, rva + 16 + i * 16)
                self.mem.append((start, size, off))
                off += size
        self.mem.sort()
        if 3 in self.streams:
            rva, _ = self.streams[3]
            n = struct.unpack_from('<I', d, rva)[0]
            for i in range(n):
                o = rva + 4 + i * 48
                tid, susp, pc, prio, teb, sstart, ssize, srva, csize, crva = struct.unpack_from('<IIIIQQIIII', d, o)
                self.threads.append(dict(tid=tid, teb=teb, stack_start=sstart, stack_size=ssize,
                                         stack_rva=srva, ctx_rva=crva, ctx_size=csize))
        if 6 in self.streams:
            rva, _ = self.streams[6]
            tid, _a = struct.unpack_from('<II', d, rva)
            code, flags, rec, addr, nparam, _u = struct.unpack_from('<IIQQII', d, rva + 8)
            params = struct.unpack_from('<15Q', d, rva + 8 + 32)
            csize, crva = struct.unpack_from('<II', d, rva + 8 + 152)
            self.exc = dict(tid=tid, code=code, flags=flags, addr=addr, params=params[:nparam],
                            ctx_rva=crva, ctx_size=csize)

    def ctx(self, rva):
        return {k: struct.unpack_from('<I', self.d, rva + o)[0] for k, o in CTX.items()}

    def read(self, addr, n):
        """Read process memory from the dump; falls back to module files on disk."""
        import bisect
        i = bisect.bisect_right(self.mem, (addr, 0xFFFFFFFFFFFF, 0)) - 1
        if i >= 0:
            start, size, off = self.mem[i]
            if start <= addr < start + size:
                m = min(n, start + size - addr)
                return self.d[off + addr - start: off + addr - start + m]
        m = self.module_at(addr)
        if m:
            pe = self.pe(m)
            if pe:
                return pe.read(addr - m['base'], n)
        return b''

    def in_dump(self, addr):
        import bisect
        i = bisect.bisect_right(self.mem, (addr, 0xFFFFFFFFFFFF, 0)) - 1
        if i >= 0:
            start, size, off = self.mem[i]
            return start <= addr < start + size
        return False

    def u32(self, addr):
        b = self.read(addr, 4)
        return struct.unpack('<I', b)[0] if len(b) == 4 else None

    def module_at(self, addr):
        for m in self.modules:
            if m['base'] <= addr < m['base'] + m['size']:
                return m
        return None

    def pe(self, m):
        p = m['name']
        if p not in self._pe:
            cand = [p]
            low = p.lower()
            if '\\system32\\' in low:
                cand.insert(0, p[:low.index('\\system32\\')] + '\\SysWOW64\\' + p[low.index('\\system32\\') + 10:])
            pe = None
            for c in cand:
                if os.path.exists(c):
                    try:
                        pe = PE(c)
                        break
                    except Exception:
                        pe = None
            self._pe[p] = pe
        return self._pe[p]

    def describe(self, addr):
        m = self.module_at(addr)
        if not m:
            return '%08X' % addr
        name = os.path.basename(m['name'])
        rva = addr - m['base']
        s = '%08X %s+0x%X' % (addr, name, rva)
        pe = self.pe(m)
        if pe:
            sy = pe.sym(rva)
            if sy:
                s += '  [%s]' % sy
        return s

    def is_code(self, addr):
        m = self.module_at(addr)
        if not m:
            return False
        pe = self.pe(m)
        if not pe:
            return True
        return pe.is_code(addr - m['base'])

    def looks_like_ret(self, addr):
        """True if the bytes before addr decode as a call instruction."""
        b = self.read(addr - 7, 7)
        if len(b) < 7:
            return False
        if b[2] == 0xE8:
            return True
        if b[5] == 0xFF and (b[6] & 0x38) == 0x10:   # call r/m (2 bytes)
            return True
        if b[4] == 0xFF and (b[5] & 0x38) == 0x10:   # 3 bytes
            return True
        if b[3] == 0xFF and (b[4] & 0x38) == 0x10:   # 4 bytes
            return True
        if b[1] == 0xFF and (b[2] & 0x38) == 0x10:   # 6 bytes
            return True
        if b[0] == 0xFF and (b[1] & 0x38) == 0x10:   # 7 bytes
            return True
        return False

    def disasm(self, addr, before=24, after=24):
        if not _CS:
            return ['(capstone missing)']
        out = []
        # try to sync: start decoding from several offsets before and pick one that lands on addr
        best = None
        for back in range(before, 0, -1):
            code = self.read(addr - back, back + after)
            ins = list(_CS.disasm(code, addr - back))
            if any(i.address == addr for i in ins):
                best = ins
                break
        if best is None:
            best = list(_CS.disasm(self.read(addr, after), addr))
        for i in best:
            mark = '=>' if i.address == addr else '  '
            out.append('%s %08X  %-22s %s %s' % (mark, i.address, i.bytes.hex(), i.mnemonic, i.op_str))
        return out

    def stack_scan(self, esp, limit=400, stack_end=None):
        out = []
        a = esp
        n = 0
        while n < 6000 and len(out) < limit:
            v = self.u32(a)
            if v is None:
                break
            if self.module_at(v) and self.is_code(v) and self.looks_like_ret(v):
                out.append((a, v))
            a += 4
            n += 1
        return out


def report(path, nstack=40, raw=False):
    dm = Dump(path)
    print('=' * 100)
    print('DUMP', path, 'flags=0x%X' % dm.flags, 'streams=%s' % sorted(dm.streams))
    e = dm.exc
    if not e:
        print('no exception stream')
        return dm
    c = dm.ctx(e['ctx_rva'])
    print('EXC code=%08X addr=%s tid=%d params=%s' % (e['code'], dm.describe(e['addr']), e['tid'],
                                                      ['%X' % p for p in e['params']]))
    if e['code'] == 0xC0000005 and len(e['params']) >= 2:
        kind = {0: 'READ', 1: 'WRITE', 8: 'EXECUTE'}.get(e['params'][0], '?')
        print('    access violation: %s of %08X' % (kind, e['params'][1]))
    print('    eax=%08X ebx=%08X ecx=%08X edx=%08X esi=%08X edi=%08X' % (
        c['eax'], c['ebx'], c['ecx'], c['edx'], c['esi'], c['edi']))
    print('    eip=%08X esp=%08X ebp=%08X efl=%08X' % (c['eip'], c['esp'], c['ebp'], c['eflags']))
    print('  code:')
    for l in dm.disasm(c['eip']):
        print('   ', l)
    print('  stack (heuristic return addresses):')
    for a, v in dm.stack_scan(c['esp'], nstack):
        print('    [%08X] %s' % (a, dm.describe(v)))
    if raw:
        print('  raw stack:')
        for i in range(0, 64):
            a = c['esp'] + i * 4
            v = dm.u32(a)
            if v is None:
                break
            print('    [%08X] %08X %s' % (a, v, dm.describe(v) if dm.module_at(v) else ''))
    return dm


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    n = 40
    if '--stack' in sys.argv:
        n = int(sys.argv[sys.argv.index('--stack') + 1])
        args = [a for a in args if a != str(n)]
    for p in args:
        report(p, n, '--raw' in sys.argv)
