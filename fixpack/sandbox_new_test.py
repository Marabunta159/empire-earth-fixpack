"""Sandbox checks for the two newer entries of the fix pack.

  python sandbox_new_test.py filter      dgVoodoo "Filtering": same saved game with the old value and with 16 -> two screenshots + sharpness
  python sandbox_new_test.py formation   cheat exe with the formation add-on, new random map (EE and AoC): formation class of every player
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
mode = sys.argv[1]
sys.argv = ['x']
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'cheat'))
import ee_fixpack as f                                                   # noqa: E402
import frida                                                             # noqa: E402
import sbx                                                               # noqa: E402

CHEAT = os.path.join(ROOT, 'cheat')
EE = os.path.join(ROOT, 'sandbox', 'Empire Earth')
AOC = os.path.join(ROOT, 'sandbox', 'Empire Earth - The Art of Conquest')
pack = f.Pack({'ee': EE, 'aoc': AOC}, shortcuts=False, touch_shortcuts=False)


def py(*a):
    return subprocess.run([sys.executable] + list(a), capture_output=True, text=True).stdout.strip()


def ui(arg, tmo=40):
    return py(os.path.join(CHEAT, 'sbx.py'), 'run', os.path.join(CHEAT, 'ui.js'), arg, str(tmo))


def start(game, exe):
    import psutil
    names = {'empire earth.exe', 'ee-aoc.exe', 'ee-cheats.exe', 'ee-aoc-cheats.exe'}
    busy = [p.info['name'] for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() in names]
    if busy:                                     # never start a test game next to a game the user is playing
        raise SystemExit('NOT STARTED: a game is already running (%s)' % ', '.join(busy))
    sbx.start(game, exe)
    time.sleep(30 if game == 'aoc' else 27)
    if not sbx.find():
        raise SystemExit('GAME DID NOT START: ' + exe)


def close():
    print('   ', py(os.path.join(CHEAT, 'closegame.py')))
    time.sleep(3)


if mode == 'filter':
    import cv2
    shots = os.path.join(CHEAT, 'shots')
    conf = os.path.join(EE, 'dgVoodoo.conf')
    res = {}
    for tag in ('before', 'after'):
        if tag == 'after':
            print('dgvoodoo state:', pack.state('dgvoodoo', 'ee'))
            pack.install('dgvoodoo', 'ee')
        print(tag, 'Filtering =', f.dgv_read(conf).get(('DirectX', 'filtering')))
        start('ee', 'EE-Cheats.exe')
        ui('{"click":{"id":350},"wait":2500,"dump":false}')
        ui('{"click":{"id":361},"wait":3000,"dump":false}')
        out = ui('{"click":{"id":393},"wait":25000,"dump":true}', 60)
        print('   in game:', '"formId": 11' in out or '"formId":11' in out)
        png = os.path.join(shots, 'filter_%s.png' % tag)
        print('   ', py(os.path.join(CHEAT, 'shot.py'), png, '1'))
        img = cv2.imread(png)
        if img is not None:
            h, w = img.shape[:2]
            crop = img[int(h * 0.05):int(h * 0.45), int(w * 0.2):int(w * 0.8)]          # far part of the terrain
            res[tag] = cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
            cv2.imwrite(os.path.join(shots, 'filter_%s_crop.png' % tag), crop[::1, ::1])
        close()
    print('sharpness (variance of the Laplacian, far terrain):', {k: round(v, 1) for k, v in res.items()})
    print('uninstall:', pack.uninstall('dgvoodoo', 'ee'), '| Filtering =', f.dgv_read(conf).get(('DirectX', 'filtering')))

if mode == 'formation3':
    # v3 of the formation add-on: new random map, formation button, loaded game - state read with ReadProcessMemory
    import re
    import shutil
    import struct
    AOC_SAVE = r'C:\Program Files (x86)\Neo Empire Earth\Empire Earth - The Art of Conquest\Data\Saved Games\Start.ees'
    COUNT_JS = """
let n = 0, zero = 0;
Interceptor.attach(ptr('%s'), { onEnter() { n++; if (this.context.esp.add(4).readU32() === 0) zero++; } });
rpc.exports = { get() { return [n, zero]; } };"""

    def peek(game):
        out = py(os.path.join(CHEAT, 'peek_form.py'), str(sbx.find()['pid']), game)
        for line in out.splitlines():
            if 'Computer' not in line:
                print('      ' + line)

    def read_hook(path):
        d = open(path, 'rb').read()
        base = struct.unpack_from('<I', d, struct.unpack_from('<I', d, 0x3C)[0] + 52)[0]
        m = re.search(rb'\x83\x7D\xFC\x08\x74.\xFF\x75\xFC\xE8(....)\x8B\xD8\x85\xDB\x59', d, re.S)
        pe = f.ee_cheat.PEFile(d)
        va = pe.va(m.start(1)) + 4 + struct.unpack('<i', m.group(1))[0]
        assert base <= va < base + 0x1000, hex(va)
        return va

    def counter(va):
        s = frida.attach(sbx.find()['pid'])
        sc = s.create_script(COUNT_JS % hex(va))
        sc.load()
        return s, sc

    only = sys.argv[1:] if False else []
    for game, exe in (('ee', 'EE-Cheats.exe'), ('aoc', 'EE-AOC-Cheats.exe')):
        gdir = EE if game == 'ee' else AOC
        want = {(c, game): True for c in ('cheats', 'formation', 'units_cheat')}
        failed = pack.apply(want, log=lambda s: None)
        print(game, 'cheat exe:', {c: pack.state(c, game)[0] for c in ('cheats', 'formation', 'units_cheat')}, 'failed', failed)
        hook = read_hook(os.path.join(gdir, exe))
        print('   read hook at %x' % hook)
        if game == 'aoc' and os.path.isfile(AOC_SAVE):
            os.makedirs(os.path.join(gdir, 'Data', 'Saved Games'), exist_ok=True)
            shutil.copyfile(AOC_SAVE, os.path.join(gdir, 'Data', 'Saved Games', 'Start.ees'))

        print('  1) new random map')
        start(game, exe)
        s, sc = counter(hook)
        ui('{"click":{"id":350},"wait":2500,"dump":false}')
        ui('{"click":{"id":360},"wait":4000,"dump":false}')
        out = ui('{"click":{"id":2511},"wait":25000,"dump":true}', 60)
        if '"formId": 7' in out or '"formId":7' in out:
            out = ui('{"click":{"id":212},"wait":3000,"dump":true}')
        print('      in game:', '"formId": 11' in out or '"formId":11' in out, '| EEGroup::Read calls (all, short line):', sc.exports_sync.get())
        peek(game)
        print('  2) formation button 3108 (short line), 8 s later')
        ui('{"click":{"id":3108},"wait":8000,"dump":false}')
        print('      EEGroup::Read calls:', sc.exports_sync.get())
        peek(game)
        s.detach()
        close()

        print('  3) saved game')
        start(game, exe)
        s, sc = counter(hook)
        ui('{"click":{"id":350},"wait":2500,"dump":false}')
        ui('{"click":{"id":361},"wait":3000,"dump":false}')
        out = ui('{"click":{"id":393},"wait":25000,"dump":true}', 60)
        print('      in game:', '"formId": 11' in out or '"formId":11' in out, '| EEGroup::Read calls (all, short line):', sc.exports_sync.get())
        peek(game)
        s.detach()
        close()

if mode == 'formation':
    JS = """
function rtti(p) { try { return p.readPointer().sub(4).readPointer().add(12).readPointer().add(8).readCString(); } catch (e) { return '?'; } }
rpc.exports = { r(players, local, group) { const out = ['local=' + ptr(local).readU32()];
  for (let i = 0; i < 9; i++) { const p = ptr(players + i * 4).readPointer(); if (p.isNull()) continue;
    const g = p.add(group).readPointer(), u = p.add(group + 4).readPointer();
    out.push('player[' + i + '] ' + rtti(p) + ' -> internal ' + (g.isNull() ? '-' : rtti(g.add(0x34).readPointer())) + ' | interface ' + (u.isNull() ? '-' : rtti(u.add(0x34).readPointer()))); }
  return out; } };"""
    for game, exe, group in (('ee', 'EE-Cheats.exe', 0x9bc), ('aoc', 'EE-AOC-Cheats.exe', 0x9ac)):
        for comp in ('cheats', 'formation', 'units_cheat'):
            if pack.state(comp, game)[0] != 'on':
                pack.install(comp, game)
        print(game, 'cheat exe:', {c: pack.state(c, game)[0] for c in ('cheats', 'formation', 'units_cheat')})
        start(game, exe)
        ui('{"click":{"id":350},"wait":2500,"dump":false}')
        ui('{"click":{"id":360},"wait":4000,"dump":false}')
        out = ui('{"click":{"id":2511},"wait":25000,"dump":true}', 60)
        if '"formId": 7' in out or '"formId":7' in out:
            out = ui('{"click":{"id":212},"wait":3000,"dump":true}')
        print('   in game:', '"formId": 11' in out or '"formId":11' in out)
        v = json.loads(py(os.path.join(CHEAT, 'gamevars.py')))
        s = frida.attach(sbx.find()['pid'])
        sc = s.create_script(JS)
        sc.load()
        for line in sc.exports_sync.r(v['players'], v['local'], group):
            print('   ', line)
        s.detach()
        close()
