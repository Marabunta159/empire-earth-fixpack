"""Sandbox check of "More units on screen - original game": patch the sandbox copy of Empire Earth.exe through
the fix pack code, start it, enter a random map, read the limit from the running process, close it, remove
the patch again (the file must be byte-identical afterwards)."""
import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.argv = ['x']
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'cheat'))
import ee_fixpack as f                                                   # noqa: E402
import frida                                                             # noqa: E402
import sbx                                                               # noqa: E402

ee = os.path.join(ROOT, 'sandbox', 'Empire Earth')
exe = os.path.join(ee, 'Empire Earth.exe')
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
before = md5(exe)
pack = f.Pack({'ee': ee, 'aoc': ''}, shortcuts=False, touch_shortcuts=False)
print('state before:', pack.state('units_orig', 'ee')[0], before)
print('install rc:', pack.install('units_orig', 'ee'))
print('state after :', pack.state('units_orig', 'ee'), '| cheat exe still:', pack.state('cheats', 'ee')[0], pack.state('units_cheat', 'ee')[0])


def ui(arg, tmo=40):
    return subprocess.run([sys.executable, os.path.join(ROOT, 'cheat', 'sbx.py'), 'run', os.path.join(ROOT, 'cheat', 'ui.js'), arg, str(tmo)],
                          capture_output=True, text=True).stdout


try:
    sbx.start('ee', 'Empire Earth.exe')
    time.sleep(28)
    j = sbx.find()
    if not j:
        print('GAME DID NOT START / exited early')
    else:
        ui('{"click":{"id":350},"wait":2500,"dump":false}')
        ui('{"click":{"id":360},"wait":4000,"dump":false}')
        out = ui('{"click":{"id":2511},"wait":25000,"dump":true}', 60)
        print('in game:', '"formId": 11' in out or '"formId":11' in out)
        s = frida.attach(j['pid'])
        sc = s.create_script("rpc.exports={r(){return [ptr(0x50099c).readU32(), ptr(0x500bbc).readU32(), ptr(0x912538).readU32(), ptr(0x91253c).readU32(), ptr(0x503ed0).readU32()];}};")
        sc.load()
        mx = [0, 0]
        for _ in range(20):
            v = sc.exports_sync.r()
            mx = [max(mx[0], v[2]), max(mx[1], v[3])]
            time.sleep(0.1)
        print('limits in the running original exe: units %d, simple %d | table base %#x | objects in view %d / %d' % (v[0], v[1], v[4], mx[0], mx[1]))
        s.detach()
        print(subprocess.run([sys.executable, os.path.join(ROOT, 'cheat', 'closegame.py')], capture_output=True, text=True).stdout.strip())
finally:
    time.sleep(2)
    print('uninstall rc:', pack.uninstall('units_orig', 'ee'))
    print('restored:', md5(exe) == before, md5(exe))
