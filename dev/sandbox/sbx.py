"""Sandbox helpers: start the sandbox copy of the game / run a Frida script against it.

  python sbx.py start [ee|aoc]            -> starts the game (unelevated copy), prints pid, returns
  python sbx.py run <script.js> [json]    -> attach, run script, print its send() messages until {done:true} or timeout
  python sbx.py kill
"""
import json, os, subprocess, sys, time
import frida

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = {'ee': (os.path.join(ROOT, 'sandbox', 'Empire Earth'), 'Empire Earth.exe'),
         'aoc': (os.path.join(ROOT, 'sandbox', 'Empire Earth - The Art of Conquest'), 'EE-AOC.exe')}
PIDFILE = os.path.join(ROOT, 'sandbox', 'pid.json')


def find():
    if os.path.exists(PIDFILE):
        j = json.load(open(PIDFILE))
        try:
            import psutil
            if psutil.pid_exists(j['pid']) and psutil.Process(j['pid']).name().lower() == j['exe'].lower():
                return j
        except Exception:
            pass
    return None


def start(game, exe_override=None):
    gdir, exe = GAMES[game]
    if exe_override:
        exe = exe_override
    env = dict(os.environ)
    env['__COMPAT_LAYER'] = 'RunAsInvoker DWM8And16BitMitigation HighDpiAware HeapClearAllocation Win7RTM'
    p = subprocess.Popen([os.path.join(gdir, exe)], cwd=gdir, env=env,
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    json.dump({'pid': p.pid, 'exe': exe, 'game': game, 'dir': gdir}, open(PIDFILE, 'w'))
    print('started', exe, 'pid', p.pid)


def engine_syms(gdir, pattern):
    """{'Class::Method' (or 'Class::Method#n' for overloads): rva} for engine exports matching the regex"""
    import re
    sys.path.insert(0, os.path.join(ROOT, 'crashfix'))
    from mdmp import PE, undname
    pe = PE(os.path.join(gdir, 'Low-Level Engine.dll'))
    rx = re.compile(pattern)
    out, seen = {}, {}
    for rva, name in pe.exports:
        u = undname(name)
        if rx.search(u):
            k = seen.get(u, 0)
            seen[u] = k + 1
            out[u if k == 0 else '%s#%d' % (u, k)] = rva
    return out


def run(path, arg=None, timeout=60):
    j = find()
    if not j:
        raise SystemExit('sandbox game not running')
    session = frida.attach(j['pid'])
    src = open(path, encoding='utf-8').read()
    syms = {}
    first = src.split('\n', 1)[0]
    if first.startswith('// SYMS:'):
        syms = engine_syms(j['dir'], first[8:].strip())
    pre = 'const ARG = %s; const SYM = %s; const EXE = %s;\n' % (json.dumps(arg), json.dumps(syms), json.dumps(j['exe']))
    lib = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib.js')
    if os.path.exists(lib) and 'NOLIB' not in first:
        pre += open(lib, encoding='utf-8').read() + '\n'
    script = session.create_script(pre + src)
    done = []

    def on_message(m, data):
        if m['type'] == 'send':
            pl = m['payload']
            if isinstance(pl, dict) and pl.get('done'):
                done.append(1)
                if len(pl) > 1:
                    print(json.dumps(pl))
            else:
                print(pl if isinstance(pl, str) else json.dumps(pl))
        else:
            print('ERR', m.get('description'), m.get('stack', ''))
            done.append(1)
    script.on('message', on_message)
    script.load()
    t = time.time()
    while not done and time.time() - t < timeout:
        time.sleep(0.05)
    if not done:
        print('(timeout)')
    try:
        session.detach()
    except Exception:
        pass


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'start':
        start(sys.argv[2] if len(sys.argv) > 2 else 'ee', sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == 'run':
        arg = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        tmo = float(sys.argv[4]) if len(sys.argv) > 4 else 60
        run(sys.argv[2], arg, tmo)
    elif cmd == 'kill':
        j = find()
        if j:
            import psutil
            psutil.Process(j['pid']).kill()
            print('killed', j['pid'])
    elif cmd == 'pid':
        print(find())
