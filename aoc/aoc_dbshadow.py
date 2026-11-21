"""Art of Conquest: keep loose db files of the base game from breaking the add-on.

Root cause of "Empire Earth.cpp (989): Verification failure (theResult == keseOK)" at AoC start
  AoC also searches the data folder of the base game ("..\\Empire Earth\\data").  A loose file
  there wins against the same path inside AoC's own data.ssa.  A mod that puts a loose db file
  into the base game (the Samurai mod: data\\db\\dbtechtree.dat, EE format with 14 epochs) is
  therefore loaded by AoC too - and AoC's loader (15 epochs, other record layout) fails.

Fix
  For every loose  <EE>\\data\\db\\*.dat  that AoC does not have as a loose file itself, AoC's own
  version is extracted from  <AoC>\\Data\\data.ssa  into  <AoC>\\Data\\db\\  (AoC's own folder is
  searched first).  Run it again after installing another mod with loose db files into EE.

Usage
  python aoc_dbshadow.py status | install | uninstall   [--ee "<EE folder>"] [--aoc "<AoC folder>"]
  The files written are listed in <AoC>\\Data\\db\\_aoc_shadow.json; uninstall removes only those.
"""
import argparse
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ssa_unpack                                                     # noqa: E402

NEO = r'C:\Program Files (x86)\Neo Empire Earth'
RECORD = '_aoc_shadow.json'


def loose_db(folder):
    """{lower case name: real name} of the loose .dat files in <folder>\\data\\db"""
    d = os.path.join(folder, 'data', 'db')
    if not os.path.isdir(d):
        return {}
    return {n.lower(): n for n in os.listdir(d) if n.lower().endswith('.dat')}


def archive_db(aoc):
    """{lower case name: bytes} of db\\*.dat inside AoC's data.ssa (decompressed)"""
    ssa = ssa_unpack.parse_ssa(os.path.join(aoc, 'Data', 'data.ssa'))
    out = {}
    for e, blob in zip(ssa['entries'], ssa['blobs']):
        p = e['path'].replace('/', '\\').lower()
        if not (p.startswith('db\\') and p.endswith('.dat')):
            continue
        if blob[:4] == ssa_unpack.DCL_MAGIC:
            blob = ssa_unpack.explode(blob[12:], struct.unpack('<I', blob[4:8])[0])      # pure Python, no DLL needed
        out[p[3:]] = blob
    return out


def needed(ee, aoc):
    """names (lower case) loose in EE but not loose in AoC"""
    own = loose_db(aoc)
    return sorted(n for n in loose_db(ee) if n not in own)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['status', 'install', 'uninstall'])
    ap.add_argument('--ee', default=NEO + r'\Empire Earth')
    ap.add_argument('--aoc', default=NEO + r'\Empire Earth - The Art of Conquest')
    a = ap.parse_args()
    dbdir = os.path.join(a.aoc, 'Data', 'db')
    rec_path = os.path.join(dbdir, RECORD)
    rec = json.load(open(rec_path)) if os.path.exists(rec_path) else {'files': {}}
    if not os.path.isdir(a.aoc):
        print('Art of Conquest folder not found:', a.aoc)
        return 1
    if a.cmd == 'uninstall':
        for name in list(rec['files']):
            p = os.path.join(dbdir, name)
            if os.path.exists(p):
                os.remove(p)
                print('   removed', p)
        if os.path.exists(rec_path):
            os.remove(rec_path)
        return 0
    miss = needed(a.ee, a.aoc)
    if a.cmd == 'status':
        for name in sorted(rec['files']):
            print('   shadow copy present:', name)
        for name in miss:
            print('   MISSING: %s is loose in the base game, AoC would load that one' % name)
        if not miss:
            print('   ok - no loose base game db file reaches AoC')
        return 1 if miss else 0
    if not miss:
        print('   nothing to do')
        return 0
    arch = archive_db(a.aoc)
    os.makedirs(dbdir, exist_ok=True)
    rc = 0
    for name in miss:
        if name not in arch:
            print('   WARNING: %s is loose in the base game but not part of AoC\'s data.ssa - left alone' % name)
            rc = 1
            continue
        p = os.path.join(dbdir, name)
        with open(p, 'wb') as f:
            f.write(arch[name])
        rec['files'][name] = hashlib.md5(arch[name]).hexdigest().upper()
        print('   wrote %s  (%d bytes, AoC\'s own version from data.ssa)' % (p, len(arch[name])))
    with open(rec_path, 'w') as f:
        json.dump(rec, f, indent=1)
    return rc


if __name__ == '__main__':
    sys.exit(main())
