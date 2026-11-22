"""Sandbox check of the rebuilt first-person add-on: install it through the fix pack code into the sandbox copy,
start EE-Cheats.exe, enter a random map, ask the DLL for its state, toggle the mode once without a selected unit
(must answer with a message, not crash), close the game."""
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
pack = f.Pack({'ee': ee, 'aoc': ''}, shortcuts=False, touch_shortcuts=False)
print('fps state before:', pack.state('fps', 'ee')[0], '| cheats:', pack.state('cheats', 'ee')[0], pack.state('units_cheat', 'ee')[0])
if pack.state('fps', 'ee')[0] != 'on':
    pack.install('fps', 'ee')
print('fps state now   :', pack.state('fps', 'ee')[0])
log = os.path.join(ee, 'ee_fps.log')
size0 = os.path.getsize(log) if os.path.exists(log) else 0


def ui(arg, tmo=40):
    return subprocess.run([sys.executable, os.path.join(ROOT, 'cheat', 'sbx.py'), 'run', os.path.join(ROOT, 'cheat', 'ui.js'), arg, str(tmo)],
                          capture_output=True, text=True).stdout


sbx.start('ee', 'EE-Cheats.exe')
time.sleep(28)
j = sbx.find()
if not j:
    raise SystemExit('GAME DID NOT START / exited early')
ui('{"click":{"id":350},"wait":2500,"dump":false}')
ui('{"click":{"id":360},"wait":4000,"dump":false}')
out = ui('{"click":{"id":2511},"wait":25000,"dump":true}', 60)
print('in game:', '"formId": 11' in out or '"formId":11' in out)
s = frida.attach(j['pid'])
sc = s.create_script("""
const m = Process.findModuleByName('ee_fps.dll');
rpc.exports = {
  st() { if (!m) return 'ee_fps.dll NOT LOADED'; return new NativeFunction(m.getExportByName('fps_state'), 'pointer', [])().readCString(); },
  toggle() { const sim = new NativeFunction(m.getExportByName('fps_sim'), 'void', ['int','int','int','int','int','int']); sim(0, 0, 0x29, 1, -1, 0); },
  release() { const sim = new NativeFunction(m.getExportByName('fps_sim'), 'void', ['int','int','int','int','int','int']); sim(0, 0, 0x29, 0, -1, 0); }
};""")
sc.load()
print('state :', sc.exports_sync.st()[:160])
sc.exports_sync.toggle()
time.sleep(1.0)
sc.exports_sync.release()
time.sleep(1.0)
print('state after toggle without a selected unit:', sc.exports_sync.st()[:160])
s.detach()
print(subprocess.run([sys.executable, os.path.join(ROOT, 'cheat', 'closegame.py')], capture_output=True, text=True).stdout.strip())
time.sleep(1)
if os.path.exists(log):
    with open(log, 'rb') as fh:
        fh.seek(size0)
        print('new log lines:')
        for line in fh.read().decode('latin1', 'replace').splitlines()[-8:]:
            print('   ', line[:150])
