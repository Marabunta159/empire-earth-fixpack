"""Run cheat texts through the game's own cheat lookup in the running sandbox game and report the effect."""
import json, os, re, struct, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ee_cheat, sbx
j = sbx.find()
if not j: raise SystemExit('sandbox game not running')
orig = {'ee': 'Empire Earth.exe', 'aoc': 'EE-AOC.exe'}[j['game']]
data = open(os.path.join(j['dir'], orig), 'rb').read()          # locate on the unpatched original (same addresses)
pe = ee_cheat.PEFile(data)
L = ee_cheat.locate(pe)
va0, _, rptr0, rsize0 = pe.sections[0]
code = bytes(pe.d[rptr0:rptr0 + rsize0]); cva = pe.base + va0
def rel_target(at):       # at = VA of an E8 call
    o = at - cva
    assert code[o] == 0xE8, hex(at)
    return at + 5 + struct.unpack_from('<i', code, o + 1)[0]
o = L['chat'] - cva
L['cheatMgr'] = struct.unpack_from('<I', code, o + 15)[0]
k = code.index(b'\xE8', o + 19); L['lookup'] = rel_target(cva + k)
k = code.index(b'\x6A\x18\xE8', k); L['opnew'] = rel_target(cva + k + 2)
k = code.index(b'\xFF\x75\xFC\x8B\xC8\xFF\x75\x08\xE8', k); L['msgctor'] = rel_target(cva + k + 8)
m = re.search(rb'\x3B\x05(....)\x77\x14\xFF\x74\x24\x0C\x8B\x0C\x85(....)', code, re.S)
L['players'] = struct.unpack('<I', m.group(2))[0]
m = re.search(rb'\xA1(....)\x8B\x04\x85' + re.escape(m.group(2)), code, re.S)
L['local'] = struct.unpack('<I', m.group(1))[0]
L['defctor_iat'] = pe.imports()[b'??0UWideString@@QAE@XZ']
L['texts'] = sys.argv[1:] or ['buerger']
print({k: (hex(v) if isinstance(v, int) else v) for k, v in L.items()})
sbx.run(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cheat_test.js'), L, 60)
