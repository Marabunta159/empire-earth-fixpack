"""Close the running sandbox game with WM_CLOSE (no input injection) and print its exit code."""
import os, sys, time
import psutil, win32api, win32con, win32gui, win32process
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sbx
j = sbx.find()
if not j: raise SystemExit('sandbox game not running')
pid = j['pid']; hs = []
win32gui.EnumWindows(lambda h, _: hs.append(h) if win32process.GetWindowThreadProcessId(h)[1] == pid and win32gui.IsWindowVisible(h) else None, None)
hp = win32api.OpenProcess(0x1000 | 0x100000, False, pid)
for h in hs: win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
t = time.time()
while psutil.pid_exists(pid) and time.time() - t < 30: time.sleep(0.25)
if psutil.pid_exists(pid): print('still running after 30 s (pid %d)' % pid)
else: print('%s: exit code %#x after %.1f s' % (j['exe'], win32process.GetExitCodeProcess(hp) & 0xffffffff, time.time() - t))
