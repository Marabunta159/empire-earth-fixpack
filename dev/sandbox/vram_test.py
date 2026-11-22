"""What video memory size does the game see for a dgVoodoo VRAM setting?  Sandbox copy only.

  python vram_test.py 8192 4096 2048 1024 256      (values for "VRAM =" in the sandbox dgVoodoo.conf; restored afterwards)
"""
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sbx                                                                # noqa: E402

conf = os.path.join(sbx.GAMES['ee'][0], 'dgVoodoo.conf')
orig = open(conf, encoding='latin1').read()
try:
    for v in sys.argv[1:]:
        open(conf, 'w', encoding='latin1').write(re.sub(r'(?m)^(VRAM\s*=\s*).*$', lambda m: m.group(1) + v, orig))
        sbx.start('ee', 'EE-Cheats.exe')
        time.sleep(26)
        if not sbx.find():
            print('VRAM = %-6s game did not start' % v)
            continue
        r = subprocess.run([sys.executable, os.path.join(HERE, 'sbx.py'), 'run', os.path.join(HERE, 'vram.js'), 'null', '20'], capture_output=True, text=True).stdout.strip()
        print('VRAM = %-6s %s' % (v, r[-230:]))
        print('   ', subprocess.run([sys.executable, os.path.join(HERE, 'closegame.py')], capture_output=True, text=True).stdout.strip())
        time.sleep(2)
finally:
    open(conf, 'w', encoding='latin1').write(orig)
