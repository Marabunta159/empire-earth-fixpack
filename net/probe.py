"""persistent Frida probe on the sandbox game: python probe.py <script.js> <logfile>   (runs until the game exits)"""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cheat'))
import frida, sbx, ee_cheat
j = sbx.find()
if not j: raise SystemExit('sandbox game not running')
orig = {'ee': 'Empire Earth.exe', 'aoc': 'EE-AOC.exe'}[j['game']]
L = ee_cheat.locate(ee_cheat.PEFile(open(os.path.join(j['dir'], orig), 'rb').read()))
log = open(sys.argv[2], 'a', encoding='utf-8')
def out(s):
    log.write('%s %s\n' % (time.strftime('%H:%M:%S'), s)); log.flush()
session = frida.attach(j['pid'])
alive = [1]
session.on('detached', lambda *a: alive.clear())
script = session.create_script('const ARG = %s;\n' % json.dumps(dict(json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}, comm=L['comm'], mp_off=L['mp_off'])) + open(sys.argv[1], encoding='utf-8').read())
script.on('message', lambda m, d: out(m['payload'] if m['type'] == 'send' else 'ERR ' + str(m.get('description'))))
script.load()
while alive: time.sleep(0.5)
out('detached')
