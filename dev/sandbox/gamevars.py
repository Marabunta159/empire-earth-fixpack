"""players table / local player index of the running sandbox game (same lookup as cheat_test.py); prints JSON"""
import json, os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ee_cheat, sbx
def get():
    j = sbx.find()
    if not j: raise SystemExit('sandbox game not running')
    orig = {'ee': 'Empire Earth.exe', 'aoc': 'EE-AOC.exe'}[j['game']]
    pe = ee_cheat.PEFile(open(os.path.join(j['dir'], orig), 'rb').read())
    va0, _, rptr0, rsize0 = pe.sections[0]
    code = bytes(pe.d[rptr0:rptr0 + rsize0])
    m = re.search(rb'\x3B\x05(....)\x77\x14\xFF\x74\x24\x0C\x8B\x0C\x85(....)', code, re.S)
    players = struct.unpack('<I', m.group(2))[0]
    m = re.search(rb'\xA1(....)\x8B\x04\x85' + re.escape(m.group(2)), code, re.S)
    return dict(players=players, local=struct.unpack('<I', m.group(1))[0], game=j['game'])
if __name__ == '__main__':
    print(json.dumps(get()))
