"""Start the sandbox game, optionally enter a random map, close the window (WM_CLOSE) and report the exit code.

  python exit_test.py <ee|aoc> <exe name> <menu|game> [cheat calls of "doughboys 50" before closing] [dialog]
"""
import os, subprocess, sys, time
import psutil, win32api, win32con, win32gui, win32process
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sbx
game, exe, where = sys.argv[1], sys.argv[2], sys.argv[3]
here = os.path.dirname(os.path.abspath(__file__))
def ui(arg, tmo=40):
    return subprocess.run([sys.executable, os.path.join(here, 'sbx.py'), 'run', os.path.join(here, 'ui.js'), arg, str(tmo)], capture_output=True, text=True).stdout
sbx.start(game, exe)
time.sleep(28)
j = sbx.find()
if not j: raise SystemExit('game did not start / exited early')
pid = j['pid']
hp = win32api.OpenProcess(0x1000 | 0x100000, False, pid)
log = os.path.join(here, 'exit_exc.log')
if os.path.exists(log): os.remove(log)
probe = subprocess.Popen([sys.executable, os.path.join(here, '..', 'net', 'probe.py'), os.path.join(here, 'exc.js'), log])
time.sleep(3)
if where == 'game':
    ui('{"click":{"id":350},"wait":2500,"dump":false}')
    ui('{"click":{"id":360},"wait":4000,"dump":false}')
    out = ui('{"click":{"id":2511},"wait":25000,"dump":true}', 60)
    print('in game form:', 'formId": 11' in out or '"formId":11' in out)
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    for k in range(0, n, 10):
        r = subprocess.run([sys.executable, os.path.join(here, 'cheat_test.py')] + ['doughboys 50'] * min(10, n - k), capture_output=True, text=True).stdout
        m = __import__('re').findall(r'"objects": "(\d+ -> \d+)"', r)
        print('  spawned:', m[0] if m else r[-200:], '...', m[-1] if m else '')
    if n: time.sleep(5)
    if len(sys.argv) > 5:
        ui('{"click":{"id":250},"wait":1500,"dump":false}'); ui('{"click":{"id":2981},"wait":4000,"dump":false}')
hs = []
win32gui.EnumWindows(lambda h, _: hs.append(h) if win32process.GetWindowThreadProcessId(h)[1] == pid and win32gui.IsWindowVisible(h) else None, None)
print('alive before WM_CLOSE:', psutil.pid_exists(pid))
for h in hs: win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
t = time.time()
while psutil.pid_exists(pid) and time.time() - t < 30: time.sleep(0.25)
if psutil.pid_exists(pid):
    print('%s %s: still running 30 s after WM_CLOSE -> killing pid %d' % (exe, where, pid)); psutil.Process(pid).kill()
else:
    print('%s %s: exit code %#x after %.1f s' % (exe, where, win32process.GetExitCodeProcess(hp) & 0xffffffff, time.time() - t))
time.sleep(1.5)
try: probe.wait(5)
except Exception: probe.kill()
if os.path.exists(log): print(open(log, encoding='utf-8').read()[:3000])
