"""Build the formation add-on for both games from the untouched sandbox executables and print what it found /
changed, plus a disassembly of the code cave.  Writes nothing.

  python check_build.py [--dis]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'cheat'))
import ee_cheat                                                           # noqa: E402
import ee_formation as F                                                  # noqa: E402

for exe in (os.path.join(ROOT, 'sandbox', 'Empire Earth', 'Empire Earth.exe'),
            os.path.join(ROOT, 'sandbox', 'Empire Earth - The Art of Conquest', 'EE-AOC.exe')):
    orig = open(exe, 'rb').read()
    Lc = ee_cheat.locate(ee_cheat.PEFile(orig))
    plain = ee_cheat.patch(orig)[0]
    pe = ee_cheat.PEFile(plain)
    L = F.locate(pe)
    print(os.path.basename(exe))
    print('  ', {k: (hex(v) if isinstance(v, int) else [hex(pe.va(h[0])) for h in v]) for k, v in L.items()})
    out = F.apply(plain, Lc['comm'], Lc['mp_off'])
    diff = [i for i in range(len(out)) if out[i] != plain[i]]
    hdr = [i for i in diff if i < pe.size_of_headers]
    print('   changed bytes: %d, cave %x..%x of header %x, read call at %x' % (
        len(diff), min(hdr), max(hdr), pe.size_of_headers, pe.va(L['read_call'])))
    if '--dis' in sys.argv:
        import capstone
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        start = out.index(F.MARK) + len(F.MARK)
        for ins in md.disasm(out[start:max(hdr) + 1], pe.base + start):
            print('      %x  %-6s %s' % (ins.address, ins.mnemonic, ins.op_str))
