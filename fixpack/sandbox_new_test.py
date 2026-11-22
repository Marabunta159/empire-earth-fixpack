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
