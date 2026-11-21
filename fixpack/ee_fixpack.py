"""Empire Earth Fix Pack - installer / uninstaller with a simple GUI (English).

Finds the NeoEE installs of Empire Earth and The Art of Conquest (registry, common folders, or chosen by
hand), shows per fix and per game whether it is installed, and installs / removes what is ticked.
The window shows the current state every time it is started, so the same program is the uninstaller.

Built into one executable with  python fixpack/build_exe.py  (PyInstaller).  Command line (for tests and
silent use):
  --ee DIR --aoc DIR        use these folders instead of the detected ones
  --select SPEC             all | none | recommended | comma list such as  crash,net:ee,units_cheat:aoc
  --apply                   apply the selection right away
  --report FILE             write the states (and the log of --apply) as JSON
  --exit                    close when done        --no-elevate   never ask for administrator rights
  --no-shortcuts            neither create nor remove desktop shortcuts
"""
import argparse
import ctypes
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser

APP = 'Empire Earth Fix Pack'
VERSION = '1.0'
REPO_URL = 'https://github.com/Marabunta159/empire-earth-fixpack'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FROZEN = getattr(sys, 'frozen', False)
RES = getattr(sys, '_MEIPASS', ROOT)                 # bundled data (ee_fps.dll, ini)
if not FROZEN:
    for _sub in ('crashfix', 'net', 'fogfix', 'aoc', 'cheat', 'unitcap', 'formation', ''):
        sys.path.insert(0, os.path.join(ROOT, _sub))

import ssa_mapfix          # noqa: E402
import sp_nonet            # noqa: E402
import fog_refcount        # noqa: E402
import aoc_dbshadow        # noqa: E402
import ee_cheat            # noqa: E402
import ee_formation        # noqa: E402
import ee_unitcap          # noqa: E402

NO_WINDOW = 0x08000000

GAMES = {
    'ee': dict(title='Empire Earth', exe='Empire Earth.exe', cheat='EE-Cheats.exe', shortcut='Empire Earth (Cheats)',
               reg='Empire Earth', sub='Empire Earth'),
    'aoc': dict(title='The Art of Conquest', exe='EE-AOC.exe', cheat='EE-AOC-Cheats.exe', shortcut='Empire Earth AoC (Cheats)',
                reg='Art of Conquest', sub='Empire Earth - The Art of Conquest'),
}

# key, title, one line, long text, games, requires, recommended
COMPONENTS = [
    ('crash', 'Crash fix: loading a second game',
     'No crash any more when you load a second map, saved game or campaign in one session.',
     'Without this fix the game often crashes the second time something is loaded in one session (second '
     'random map, loading a saved game after a match, switching campaigns).\n\n'
     'Cause: the game maps its whole data archive into memory again every time; after a match the 2 GB address '
     'space is too fragmented and the mapping fails silently.\n\n'
     'The fix maps only the one file that is being read. As a side effect about 490 MB more memory stay free.\n\n'
     'Changes: Low-Level Engine.dll (a backup is kept).',
     ('ee', 'aoc'), None, True),
    ('net', 'No network test in single player',
     'No NeoEE port check when you open a random map or load a game (multiplayer unchanged).',
     'NeoEE runs its network test (port check, UPnP, hole punching - the small "ball" window) for every session '
     'the game creates, also for single player: random map setup, loading a saved game, campaigns.\n\n'
     'With this fix single player sessions skip the test completely. Hosting a multiplayer game works exactly '
     'as before.\n\n'
     'Changes: TCP Protocol.dll (a backup is kept). Only available when the NeoEE network hook is found.',
     ('ee', 'aoc'), None, True),
    ('fog', 'Fog of war fix',
     'Units no longer flicker in the fog: the visibility counter of a tile cannot run below zero.',
     'Every map tile counts how many of your units can see it. The original code can count below zero; the tile '
     'then switches between visible and dark for no reason and units on it flicker or vanish for a moment.\n\n'
     'The fix keeps the counter in its valid range.\n\n'
     'Changes: Low-Level Engine.dll (a backup is kept).',
     ('ee', 'aoc'), None, True),
    ('aocstart', 'Art of Conquest start fix (mods)',
     'AoC starts again when a mod has put loose database files into the Empire Earth folder.',
     'The Art of Conquest also reads the data folder of the base game. If a mod places loose files in '
     '"Empire Earth\\data\\db", AoC loads them too - and stops right after the start with\n'
     '"Empire Earth.cpp (989): Verification failure".\n\n'
     'The fix extracts AoC\'s own versions of exactly those files into "The Art of Conquest\\Data\\db", where AoC '
     'looks first. Nothing in the base game is changed.\n\n'
     'Only offered when such loose files exist. Apply it again after you install another Empire Earth mod.',
     ('aoc',), None, True),
    ('dgvoodoo', 'Graphics settings (dgVoodoo)',
     'Sharper picture: native resolution, 8x antialiasing, 16x anisotropic filtering, friendlier Alt-Tab.',
     'NeoEE draws the game through dgVoodoo. Its default settings (dgVoodoo.conf in the game folder) leave quality '
     'unused. This entry sets:\n'
     '  - Resolution = desktop  (render at the native resolution of your monitor)\n'
     '  - Antialiasing = 8x  (smooth edges)\n'
     '  - Filtering = 16  (16x anisotropic texture filtering)\n'
     '  - AppControlledScreenMode = false  (dgVoodoo handles the screen mode)\n'
     '  - window without "AlwaysOnTop"  (Alt-Tab works normally)\n\n'
     'Settings that are already fine are left alone (for example a resolution you forced yourself). Removing '
     'the entry restores the previous values. If the game gets slow on an old graphics card, remove it again.',
     ('ee', 'aoc'), None, False),
    ('cheats', 'Cheat executable (single player)',
     'A second game exe: cheat codes also work in campaigns, plus "citizens" and "doughboys".',
     'Adds a second executable next to the game (EE-Cheats.exe / EE-AOC-Cheats.exe) and, if you want, a desktop '
     'shortcut. The original game executable is not modified.\n\n'
     'In the cheat executable:\n'
     '  - the built-in cheat codes also work in campaigns and scenarios that switch them off\n'
     '  - new code  citizens  (or  citizens 20): citizens appear where the camera looks, 1-50\n'
     '  - new code  doughboys  (or  doughboys 20): World War I infantry, 1-50\n\n'
     'Type the codes into the chat line (Enter). Single player only - in network games nothing changes.',
     ('ee', 'aoc'), None, False),
    ('formation', 'Long line as default formation',
     'New single player games start with the formation "long line" instead of "short line".',
     'Every game starts with the formation "short line". With this entry a new single player game starts with '
     '"long line" for you - exactly as if you had pressed the formation button right at the start. You can still '
     'choose any other formation in the game.\n\n'
     'Computer players and network games are not affected; saved games keep the formation that was saved.\n\n'
     'This entry patches the cheat executable (needs "Cheat executable").',
     ('ee', 'aoc'), 'cheats', False),
    ('units_cheat', 'More units on screen - cheat executable',
     'Units no longer disappear in big battles: the game can draw 4096 objects instead of 512.',
     'The game collects everything inside the view in a table with 512 places (units, buildings, corpses, '
     'projectiles). When the table is full the rest is simply not drawn - units disappear, depending on the '
     'camera, as soon as a battle gets big.\n\n'
     'The fix gives the table 4096 places (simple objects such as trees: 8192 instead of 1536). Display only, '
     'the simulation is not touched. Very large crowds cost frame rate because every unit has to be drawn.\n\n'
     'This entry patches the cheat executable (needs "Cheat executable").',
     ('ee', 'aoc'), 'cheats', False),
    ('units_orig', 'More units on screen - original game',
     'The same fix written into the normal game executable (not tested in online games).',
     'The same fix as above, but written into Empire Earth.exe / EE-AOC.exe, so it also works when you start '
     'the game the normal way.\n\n'
     'It only changes what is drawn, not the game rules. It has NOT been tested in NeoEE online games - use it '
     'at your own risk. A backup of the executable is kept and you can remove the fix here at any time.',
     ('ee', 'aoc'), None, False),
    ('fps', 'First-person mode (unfinished experiment)',
     'Control one ranged unit like in a shooter. Unfinished, no longer developed, source included.',
     'UNFINISHED EXPERIMENT. It works, but it is rough, it is not developed any further and there is no support. '
     'If you want to continue it: the complete source code is included - press "Source code..." in this window. '
     'Have fun.\n\n'
     'Select ONE of your own ranged units and press the key left of "1" (` on a US keyboard, ^ on a German one): '
     'the camera moves into the unit. Mouse = look, W/A/S/D = walk, left button = shoot, right button = scope, '
     '1-4 or wheel = weapons, ESC = back.\n\n'
     'Single player only, Empire Earth only, and only when the game is started with the cheat executable. '
     'Settings: ee_fps.ini in the game folder.\n\n'
     'Adds: ee_fps.dll and ee_fps.ini (needs "Cheat executable").',
     ('ee',), 'cheats', False),
]
ORDER = [c[0] for c in COMPONENTS]
COMP = {c[0]: dict(title=c[1], summary=c[2], info=c[3], games=c[4], requires=c[5], recommended=c[6]) for c in COMPONENTS}
STATE_TEXT = {'on': 'installed', 'off': 'not installed', 'old': 'update available', 'fixed': 'already fixed',
              'unknown': 'not supported', 'na': 'not needed', 'nogame': ''}


# ------------------------------------------------------------------------------------------------ helpers
def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def writable(folder):
    """may this process create files in the folder?  The only reliable test is to create one (empty, removed at once)."""
    probe = os.path.join(folder, '_ee_fixpack_write_test_%d.tmp' % os.getpid())
    try:
        open(probe, 'w').close()
    except OSError:
        return False
    try:
        os.remove(probe)
    except OSError:
        pass
    return True


def backup_base():
    for base in (os.environ.get('ProgramData'), os.environ.get('LOCALAPPDATA'), tempfile.gettempdir()):
        if not base:
            continue
        p = os.path.join(base, 'EE-FixPack', 'backups')
        try:
            os.makedirs(p, exist_ok=True)
            return p
        except OSError:
            pass
    return tempfile.gettempdir()


BACKUPS = backup_base()
ssa_mapfix.BACKUP_ROOT = os.path.join(BACKUPS, 'crashfix')
sp_nonet.BACKUP_ROOT = os.path.join(BACKUPS, 'netfix')
fog_refcount.BACKUP_ROOT = os.path.join(BACKUPS, 'fogfix')
ee_unitcap.BACKUP_ROOT = os.path.join(BACKUPS, 'unitcap')


def game_running():
    names = [g['exe'].lower() for g in GAMES.values()] + [g['cheat'].lower() for g in GAMES.values()]
    try:
        out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, creationflags=NO_WINDOW).stdout.lower()
    except OSError:
        return False
    return any('"%s"' % n in out for n in names)


def ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


def powershell(script):
    try:
        subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script],
                       capture_output=True, creationflags=NO_WINDOW, timeout=60)
    except (OSError, subprocess.SubprocessError):
        pass


def make_shortcut(name, target, workdir):
    ico = os.path.join(workdir, 'game.ico')
    powershell("$p=[Environment]::GetFolderPath('Desktop')+%s; $s=(New-Object -ComObject WScript.Shell).CreateShortcut($p); "
               "$s.TargetPath=%s; $s.WorkingDirectory=%s; $s.IconLocation=%s; $s.Save()"
               % (ps_quote('\\' + name + '.lnk'), ps_quote(target), ps_quote(workdir), ps_quote(ico if os.path.exists(ico) else target)))


def remove_shortcut(name, target):
    """only when the shortcut really points to this cheat executable"""
    powershell("$p=[Environment]::GetFolderPath('Desktop')+%s; if(Test-Path $p){$s=(New-Object -ComObject WScript.Shell).CreateShortcut($p); "
               "if($s.TargetPath -ieq %s){Remove-Item $p}}" % (ps_quote('\\' + name + '.lnk'), ps_quote(target)))


# ------------------------------------------------------------------------------------------------ detection
def _reg_values(root, path, names, flag=0):
    import winreg
    out = {}
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_READ | flag) as k:
            for n in names:
                try:
                    out[n] = str(winreg.QueryValueEx(k, n)[0])
                except OSError:
                    pass
    except OSError:
        pass
    return out


def detect():
    """-> ({'ee': folder or '', 'aoc': folder or ''}, NeoEE display name or '')"""
    import winreg
    cand = {'ee': [], 'aoc': []}
    neo_name = ''
    # 1. the game's own settings: HKCU\Software\Neo\<game>  (written by the game when it runs)
    for g, info in GAMES.items():
        for vendor in ('Neo', 'SSSI', 'Sierra'):
            v = _reg_values(winreg.HKEY_CURRENT_USER, 'Software\\%s\\%s' % (vendor, info['reg']),
                            ('Installed From Volume', 'Installed From Directory'))
            if v.get('Installed From Directory'):
                cand[g].append(os.path.normpath(v.get('Installed From Volume', 'C:') + v['Installed From Directory']))
    # 2. the NeoEE setup (Inno Setup uninstall entry)
    un = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall'
    for root, flag in ((winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY), (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
                       (winreg.HKEY_CURRENT_USER, 0)):
        try:
            k = winreg.OpenKey(root, un, 0, winreg.KEY_READ | flag)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(k, i)
            except OSError:
                break
            i += 1
            v = _reg_values(root, un + '\\' + sub, ('DisplayName', 'InstallLocation', 'Inno Setup: App Path'), flag)
            dn = v.get('DisplayName', '')
            if 'neoee' in dn.lower() or 'empire earth' in dn.lower():
                if 'neoee' in dn.lower() and not neo_name:
                    neo_name = dn
                for base in (v.get('InstallLocation'), v.get('Inno Setup: App Path')):
                    if base:
                        for g, info in GAMES.items():
                            cand[g] += [os.path.join(base, info['sub']), base]
    # 3. compatibility flags are stored under the full path of the exe
    layers = 'Software\\Microsoft\\Windows NT\\CurrentVersion\\AppCompatFlags\\Layers'
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, layers) as k:
                i = 0
                while True:
                    try:
                        name = winreg.EnumValue(k, i)[0]
                    except OSError:
                        break
                    i += 1
                    for g, info in GAMES.items():
                        if name.lower().endswith('\\' + info['exe'].lower()):
                            cand[g].append(os.path.dirname(name))
        except OSError:
            pass
    # 4. usual places
    pf = [os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), os.environ.get('ProgramFiles', r'C:\Program Files'), 'C:\\', 'D:\\']
    for base in pf:
        for top in ('Neo Empire Earth', 'NeoEE', 'Sierra', 'GOG Games\\Empire Earth Gold', 'Games\\Neo Empire Earth'):
            for g, info in GAMES.items():
                cand[g].append(os.path.join(base, top, info['sub']))
    found = {}
    for g, info in GAMES.items():
        found[g] = next((os.path.realpath(c) for c in cand[g] if c and os.path.isfile(os.path.join(c, info['exe']))), '')      # realpath: real upper / lower case
    # 5. the two games normally sit next to each other
    for g, other in (('ee', 'aoc'), ('aoc', 'ee')):
        if not found[g] and found[other]:
            c = os.path.join(os.path.dirname(found[other]), GAMES[g]['sub'])
            if os.path.isfile(os.path.join(c, GAMES[g]['exe'])):
                found[g] = c
    return found, neo_name


# ------------------------------------------------------------------------------------------------ dgVoodoo.conf
# (section, key, value we write, test "is the current value already fine?")
def _aniso(v):
    return v.strip().isdigit() and 8 <= int(v) <= 16


DGV_WANT = [
    ('DirectX', 'Resolution', 'desktop', lambda v: v.strip().lower() not in ('', 'unforced')),            # any forced resolution is fine
    ('DirectX', 'Antialiasing', '8x', lambda v: v.strip().lower() in ('4x', '8x', '16x')),
    ('DirectX', 'Filtering', '16', _aniso),                                                               # anisotropic level 1-16
    ('DirectX', 'AppControlledScreenMode', 'false', lambda v: v.strip().lower() == 'false'),
    ('GeneralExt', 'WindowedAttributes', 'Borderless, FullscreenSize', lambda v: 'alwaysontop' not in v.lower()),
]


def dgv_same(cur, want_value, ok=None):
    if cur is None:
        return False
    return ok(cur) if ok else cur.strip().lower() == want_value.strip().lower()


def _dgv_lines(path):
    """lines with their own line endings (the files in the wild mix LF and CR LF)"""
    return open(path, 'rb').read().decode('latin1').splitlines(keepends=True)


EOL_CHARS = chr(13) + chr(10)


def _eol(line):
    return line[len(line.rstrip(EOL_CHARS)):]


def dgv_read(path):
    """{(section, key in lower case): value}"""
    out, sec = {}, ''
    for line in _dgv_lines(path):
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            sec = s[1:-1]
        elif s and not s.startswith(';') and '=' in s:
            k, v = s.split('=', 1)
            out[(sec, k.strip().lower())] = v.strip()
    return out


def dgv_write(path, items):
    """items: [(section, key, value or None = remove the line)]  ->  {'Section|Key': previous value or None}
    Only the value of a line changes; everything else (spacing, line endings, comments) stays byte for byte."""
    lines = _dgv_lines(path)
    old = {}
    for sec, key, val in items:
        start = next((i for i, x in enumerate(lines) if x.strip().lower() == '[%s]' % sec.lower()), None)
        if start is None:
            old['%s|%s' % (sec, key)] = None
            if val is None:
                continue
            nl = (_eol(lines[-1]) if lines else '') or EOL_CHARS
            if lines and not _eol(lines[-1]):
                lines[-1] += nl
            lines += [nl, '[%s]%s' % (sec, nl)]
            start = len(lines) - 1
        end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith('[')), len(lines))
        hit = next((i for i in range(start + 1, end) if not lines[i].strip().startswith(';') and '=' in lines[i]
                    and lines[i].split('=', 1)[0].strip().lower() == key.lower()), None)
        if hit is not None:
            head, tail = lines[hit].split('=', 1)
            body = tail.rstrip(EOL_CHARS)
            old['%s|%s' % (sec, key)] = body.strip()
            if val is None:
                del lines[hit]
            else:                                           # keep the spacing around the value
                lead = body[:len(body) - len(body.lstrip())]
                trail = body[len(body.rstrip()):]
                lines[hit] = head + '=' + lead + val + trail + _eol(lines[hit])
        else:
            old['%s|%s' % (sec, key)] = None
            if val is not None:
                at = end
                while at > start + 1 and not lines[at - 1].strip():
                    at -= 1
                nl = _eol(lines[at - 1]) or EOL_CHARS
                if not _eol(lines[at - 1]):
                    lines[at - 1] += nl
                lines.insert(at, '%-36s= %s%s' % (key, val, nl))
    with open(path, 'wb') as f:
        f.write(''.join(lines).encode('latin1'))
    return old


# ------------------------------------------------------------------------------------------------ the fixes
class Pack:
    """state / install / uninstall of every fix for the chosen folders"""

    def __init__(self, dirs, shortcuts=True, touch_shortcuts=True):
        self.dirs = {g: (os.path.normpath(d) if d and os.path.isfile(os.path.join(d, GAMES[g]['exe'])) else '') for g, d in dirs.items()}
        self.shortcuts = shortcuts                     # create them when the cheat exe is installed
        self.touch_shortcuts = touch_shortcuts         # False: never create or remove (tests)
        self._builds = {}

    # --- files
    def f(self, g, name):
        return os.path.join(self.dirs[g], name)

    def orig(self, g):
        return self.f(g, GAMES[g]['exe'])

    def cheat(self, g):
        return self.f(g, GAMES[g]['cheat'])

    def ee_dir_for_aoc(self):
        if self.dirs.get('ee'):
            return self.dirs['ee']
        c = os.path.join(os.path.dirname(self.dirs['aoc']), GAMES['ee']['sub'])
        return c if os.path.isdir(c) else ''

    def builds(self, g):
        """the cheat executable this version of the tool would write: (plain, with unit limit fix, error text)"""
        p = self.orig(g)
        st = os.stat(p)
        key = (p, st.st_mtime_ns, st.st_size)
        if self._builds.get(g, (None,))[0] != key:
            data = bytearray(open(p, 'rb').read())
            rp = ee_unitcap.record_path(p)
            if os.path.exists(rp):                    # original carries the unit limit fix: build from its pristine bytes
                try:
                    rec = json.load(open(rp))
                    if all(bytes(data[o:o + len(n) // 2]) == bytes.fromhex(n) for o, _, n, _ in rec['edits']):
                        for o, old, _, _ in rec['edits']:
                            data[o:o + len(old) // 2] = bytes.fromhex(old)
                except (ValueError, KeyError, OSError):
                    pass
            try:
                Lc = ee_cheat.locate(ee_cheat.PEFile(bytes(data)))
                plain = ee_cheat.patch(bytes(data))[0]
                var = {(0, 0): plain, (1, 0): ee_formation.apply(plain, Lc['comm'], Lc['mp_off'])}
                for form in (0, 1):                     # the same two files with the unit limit fix on top
                    b = bytearray(var[(form, 0)])
                    for o, old, new, _ in ee_unitcap.plan(var[(form, 0)])['edits']:
                        b[o:o + len(new)] = new
                    var[(form, 1)] = bytes(b)
                self._builds[g] = (key, var, '')
            except Exception as e:                     # unsupported executable
                self._builds[g] = (key, None, str(e))
        return self._builds[g][1:]

    def cheat_flags(self, g):
        """(formation, unit limit) of the installed cheat executable, None when it is not one of our four builds"""
        var, err = self.builds(g)
        p = self.cheat(g)
        if var is None or not os.path.isfile(p):
            return None
        cur = open(p, 'rb').read()
        return next((k for k, v in var.items() if v == cur), None)

    def write_cheat(self, g, form, cap):
        """write the cheat executable with / without the two add-ons (the unit limit goes through ee_unitcap so
        that its patch record exists for the command line tools)"""
        var, err = self.builds(g)
        dst = self.cheat(g)
        self._write(dst, var[(form, 0)])
        self._drop_record(dst)
        if cap:
            return ee_unitcap.install(dst, ee_unitcap.DEF1, ee_unitcap.DEF2, backup=False)
        return 0

    # --- state
    def state(self, comp, g):
        """-> (state, detail)   state: nogame | na | off | on | old | fixed | unknown"""
        if g not in COMP[comp]['games']:
            return 'nogame', ''
        if not self.dirs.get(g):
            return 'nogame', GAMES[g]['title'] + ' was not found'
        try:
            return getattr(self, 'st_' + comp)(g)
        except Exception as e:
            return 'unknown', '%s: %s' % (type(e).__name__, e)

    def _dll(self, g, name):
        p = self.f(g, name)
        if not os.path.isfile(p):
            raise RuntimeError(name + ' not found')
        return p, open(p, 'rb').read()

    def st_crash(self, g):
        p, data = self._dll(g, 'Low-Level Engine.dll')
        if ssa_mapfix.is_installed(data):
            return 'on', ''
        try:
            ssa_mapfix.plan(ssa_mapfix.PEFile(data))
        except Exception as e:
            return 'unknown', 'This version of Low-Level Engine.dll is not supported (%s).' % e
        return 'off', ''

    def st_net(self, g):
        p, data = self._dll(g, 'TCP Protocol.dll')
        if sp_nonet.MARK in data:
            return 'on', ''
        try:
            sp_nonet.plan(data)
        except Exception as e:
            return 'unknown', 'No NeoEE network hook found in TCP Protocol.dll (%s).' % e
        return 'off', ''

    def st_fog(self, g):
        p, data = self._dll(g, 'Low-Level Engine.dll')
        st, _ = fog_refcount.inspect(data)
        if st == 'pristine':
            return 'off', ''
        if st == 'installed':
            return ('on', '') if os.path.exists(fog_refcount.record_path(p)) else ('fixed', 'Installed without a patch record - cannot be removed here.')
        if st == 'cave':
            return 'fixed', 'Fixed by an older variant of this patch - nothing to do.'
        return 'unknown', 'This version of Low-Level Engine.dll is not supported.'

    def st_aocstart(self, g):
        ee = self.ee_dir_for_aoc()
        aoc = self.dirs['aoc']
        rec = os.path.join(aoc, 'Data', 'db', aoc_dbshadow.RECORD)
        have = bool(json.load(open(rec)).get('files')) if os.path.exists(rec) else False
        miss = aoc_dbshadow.needed(ee, aoc) if ee else []
        if miss:
            return ('old' if have else 'off'), 'Loose base game files that AoC would load: ' + ', '.join(miss)
        if have:
            return 'on', ''
        return 'na', 'No mod with loose database files found in Empire Earth - nothing to fix.'

    def st_cheats(self, g):
        var, err = self.builds(g)
        if var is None:
            return 'unknown', 'This version of %s is not supported (%s).' % (GAMES[g]['exe'], err)
        p = self.cheat(g)
        if not os.path.isfile(p):
            return 'off', ''
        if self.cheat_flags(g) is not None:
            return 'on', ''
        if ee_cheat.MARK in open(p, 'rb').read(0x1000):
            return 'old', 'An older build of the cheat executable is installed - it will be replaced.'
        return 'unknown', 'A different file named %s exists - not touched.' % GAMES[g]['cheat']

    def _st_addon(self, g, index):
        var, err = self.builds(g)
        if var is None:
            return 'unknown', 'This version of %s is not supported (%s).' % (GAMES[g]['exe'], err)
        flags = self.cheat_flags(g)
        return ('on', '') if flags and flags[index] else ('off', '')

    def st_formation(self, g):
        return self._st_addon(g, 0)

    def st_units_cheat(self, g):
        return self._st_addon(g, 1)

    def st_dgvoodoo(self, g):
        p = self.f(g, 'dgVoodoo.conf')
        if not os.path.isfile(p):
            return 'unknown', 'dgVoodoo.conf not found - this does not look like a NeoEE install.'
        diff = self.dgv_todo(g)
        if not diff:
            return 'on', ''
        text = 'Would change  ' + ';  '.join('%s: %s -> %s' % (k, c if c is not None else '(not set)', v) for _, k, v, c in diff)
        return ('old' if len(diff) <= len(DGV_WANT) // 2 else 'off'), text

    def dgv_todo(self, g):
        """[(section, key, new value, current value)] for the settings that are not fine yet"""
        cur = dgv_read(self.f(g, 'dgVoodoo.conf'))
        return [(s, k, v, cur.get((s, k.lower()))) for s, k, v, ok in DGV_WANT if not dgv_same(cur.get((s, k.lower())), v, ok)]

    def st_units_orig(self, g):
        st, detail = ee_unitcap.state(self.orig(g))
        if st == 'installed':
            return 'on', detail
        if st == 'pristine':
            return 'off', ''
        return 'unknown', 'This version of %s is not supported (%s).' % (GAMES[g]['exe'], detail)

    def st_fps(self, g):
        p = self.f(g, 'ee_fps.dll')
        if not os.path.isfile(p):
            return 'off', ''
        same = open(p, 'rb').read() == open(os.path.join(RES, 'fps', 'ee_fps.dll'), 'rb').read()
        return ('on', '') if same else ('old', 'A different build of ee_fps.dll is installed - it will be replaced (your ee_fps.ini is kept).')

    # --- actions (print progress; raise or return non-zero on failure)
    def install(self, comp, g):
        return getattr(self, 'in_' + comp)(g)

    def uninstall(self, comp, g):
        return getattr(self, 'un_' + comp)(g)

    @staticmethod
    def _main(mod, *argv):
        old = sys.argv
        sys.argv = [mod.__name__] + list(argv)
        try:
            return mod.main() or 0
        finally:
            sys.argv = old

    def in_crash(self, g):
        ssa_mapfix.install(self.f(g, 'Low-Level Engine.dll'))

    def un_crash(self, g):
        ssa_mapfix.uninstall(self.f(g, 'Low-Level Engine.dll'))

    def in_net(self, g):
        return sp_nonet.install(self.f(g, 'TCP Protocol.dll'))

    def un_net(self, g):
        return sp_nonet.uninstall(self.f(g, 'TCP Protocol.dll'))

    def in_fog(self, g):
        return self._main(fog_refcount, 'install', '--dll', self.f(g, 'Low-Level Engine.dll'))

    def un_fog(self, g):
        return self._main(fog_refcount, 'uninstall', '--dll', self.f(g, 'Low-Level Engine.dll'))

    def in_aocstart(self, g):
        return self._main(aoc_dbshadow, 'install', '--ee', self.ee_dir_for_aoc(), '--aoc', self.dirs['aoc'])

    def un_aocstart(self, g):
        return self._main(aoc_dbshadow, 'uninstall', '--ee', self.ee_dir_for_aoc(), '--aoc', self.dirs['aoc'])

    def _write(self, path, data):
        tmp = path + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)

    def _drop_record(self, exe):
        rp = ee_unitcap.record_path(exe)
        if os.path.exists(rp):
            os.remove(rp)

    def in_cheats(self, g):
        dst = self.cheat(g)
        self.write_cheat(g, 0, 0)
        print('   wrote', dst)
        flags = ee_cheat.set_layers(dst, self.orig(g))
        if flags:
            print('   compatibility flags copied from the original:', flags)
        if self.shortcuts and self.touch_shortcuts:
            make_shortcut(GAMES[g]['shortcut'], dst, self.dirs[g])
            print('   desktop shortcut "%s"' % GAMES[g]['shortcut'])

    def un_cheats(self, g):
        dst = self.cheat(g)
        if os.path.exists(dst):
            os.remove(dst)
        self._drop_record(dst)
        ee_cheat.clear_layers(dst)
        if self.touch_shortcuts:
            remove_shortcut(GAMES[g]['shortcut'], dst)
        print('   removed', dst)

    def _addon(self, g, index, on, text):
        flags = self.cheat_flags(g)
        if flags is None:
            print('   the cheat executable is missing - tick "Cheat executable" as well')
            return 1
        new = list(flags)
        new[index] = 1 if on else 0
        rc = self.write_cheat(g, new[0], new[1])
        print('   %s: %s' % (self.cheat(g), text))
        return rc

    def in_formation(self, g):
        return self._addon(g, 0, True, 'new single player games start with the formation "long line"')

    def un_formation(self, g):
        return self._addon(g, 0, False, 'default formation is "short line" again')

    def in_units_cheat(self, g):
        return self._addon(g, 1, True, 'unit limit raised')

    def un_units_cheat(self, g):
        return self._addon(g, 1, False, 'unit limit fix removed')

    def in_dgvoodoo(self, g):
        p = self.f(g, 'dgVoodoo.conf')
        bdir = os.path.join(BACKUPS, 'dgvoodoo', time.strftime('%Y%m%d-%H%M%S'), os.path.basename(self.dirs[g]))
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(p, bdir)
        old = dgv_write(p, [(s, k, v) for s, k, v, _ in self.dgv_todo(g)])
        rec = p + '.fixpack.json'
        prev = json.load(open(rec)) if os.path.exists(rec) else {}
        for k, v in old.items():                       # keep the oldest known value of every key
            prev.setdefault(k, v)
        with open(rec, 'w') as f:
            json.dump(prev, f, indent=1)
        print('   %s updated (backup: %s)' % (p, bdir))

    def un_dgvoodoo(self, g):
        p = self.f(g, 'dgVoodoo.conf')
        rec = p + '.fixpack.json'
        if not os.path.exists(rec):
            print('   no record of the previous settings - dgVoodoo.conf left as it is (backups: %s)' % os.path.join(BACKUPS, 'dgvoodoo'))
            return 1
        prev = json.load(open(rec))
        dgv_write(p, [(k.split('|')[0], k.split('|')[1], v) for k, v in prev.items()])
        os.remove(rec)
        print('   previous settings restored in', p)

    def in_units_orig(self, g):
        return ee_unitcap.install(self.orig(g), ee_unitcap.DEF1, ee_unitcap.DEF2, backup=True)

    def un_units_orig(self, g):
        return ee_unitcap.uninstall(self.orig(g))

    def in_fps(self, g):
        shutil.copyfile(os.path.join(RES, 'fps', 'ee_fps.dll'), self.f(g, 'ee_fps.dll'))
        ini = self.f(g, 'ee_fps.ini')
        if not os.path.exists(ini):
            shutil.copyfile(os.path.join(RES, 'fps', 'ee_fps.en.ini'), ini)
        print('   ee_fps.dll and ee_fps.ini ->', self.dirs[g])

    def un_fps(self, g):
        for n in ('ee_fps.dll', 'ee_fps.ini', 'ee_fps.log'):
            if os.path.exists(self.f(g, n)):
                os.remove(self.f(g, n))
        print('   first-person add-on removed')

    # --- apply a selection
    def cells(self):
        return [(c, g) for c in ORDER for g in ('ee', 'aoc') if g in COMP[c]['games']]

    def all_states(self):
        return {(c, g): self.state(c, g) for c, g in self.cells()}

    def apply(self, want, log=print):
        """want: {(comp, game): bool}.  Removes first (reverse order), then installs.  -> number of failed steps"""
        failed = 0

        def step(verb, fn, c, g):
            nonlocal failed
            log('%s: %s - %s' % (verb, COMP[c]['title'], GAMES[g]['title']))
            try:
                rc = fn(c, g)
            except PermissionError as e:
                rc = 1
                log('   FAILED: no write access (%s). Is the game still running?' % e)
            except SystemExit as e:
                rc = 1 if e.code not in (None, 0) else 0
                if rc:
                    log('   FAILED: %s' % e.code)
            except Exception as e:
                rc = 1
                log('   FAILED: %s: %s' % (type(e).__name__, e))
            if rc:
                failed += 1
            return not rc

        for c in reversed(ORDER):
            for g in ('aoc', 'ee'):
                if (c, g) in want and not want[(c, g)] and self.state(c, g)[0] in ('on', 'old'):
                    step('Removing', self.uninstall, c, g)
        for c in ORDER:
            for g in ('ee', 'aoc'):
                if want.get((c, g)) and self.state(c, g)[0] in ('off', 'old'):
                    req = COMP[c]['requires']
                    if req and self.state(req, g)[0] != 'on':
                        log('Skipped: %s - %s (needs "%s")' % (COMP[c]['title'], GAMES[g]['title'], COMP[req]['title']))
                        failed += 1
                        continue
                    step('Installing', self.install, c, g)
        return failed


def parse_select(spec, pack):
    """'all' | 'none' | 'recommended' | 'crash,net:ee,...'  -> {(comp, game): bool} for every cell that can be changed"""
    states = pack.all_states()
    usable = {k for k, (s, _) in states.items() if s in ('on', 'off', 'old')}
    if spec == 'all':
        return {k: True for k in usable}
    if spec == 'none':
        return {k: False for k in usable}
    if spec == 'recommended':
        return {k: (COMP[k[0]]['recommended'] or states[k][0] in ('on', 'old')) for k in usable}
    chosen = set()
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        c, _, g = part.partition(':')
        if c not in COMP:
            raise SystemExit('unknown fix: ' + c)
        chosen |= {(c, x) for x in ((g,) if g else ('ee', 'aoc'))}
    return {k: (k in chosen) for k in usable}


# ------------------------------------------------------------------------------------------------ GUI
def run_gui(args, dirs, neo_name):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    class Tip:
        """small yellow info box while the mouse is over a widget"""

        def __init__(self, widget, text_fn):
            self.w, self.fn, self.top = widget, text_fn, None
            widget.bind('<Enter>', self.show, add='+')
            widget.bind('<Leave>', self.hide, add='+')

        def show(self, _e=None):
            text = self.fn() if callable(self.fn) else self.fn
            if not text or self.top:
                return
            self.top = t = tk.Toplevel(self.w)
            t.wm_overrideredirect(True)
            t.wm_geometry('+%d+%d' % (self.w.winfo_rootx() + 16, self.w.winfo_rooty() + self.w.winfo_height() + 4))
            tk.Label(t, text=text, justify='left', background='#ffffe1', relief='solid', borderwidth=1, wraplength=460,
                     padx=6, pady=4).pack()

        def hide(self, _e=None):
            if self.top:
                self.top.destroy()
                self.top = None

    root = tk.Tk()
    root.title('%s %s' % (APP, VERSION))
    try:
        root.iconbitmap(default=os.path.join(RES, 'fixpack', 'icon.ico'))
    except Exception:
        pass
    root.minsize(1010, 560)
    style = ttk.Style()
    base_font = ('Segoe UI', 9)
    style.configure('.', font=base_font)
    style.configure('Head.TLabel', font=('Segoe UI', 13, 'bold'))
    style.configure('Bold.TLabel', font=('Segoe UI', 9, 'bold'))
    style.configure('Gray.TLabel', foreground='#555555')
    style.configure('Col.TLabel', font=('Segoe UI', 9, 'bold'))
    COLORS = {'on': '#1a7f37', 'fixed': '#1a7f37', 'off': '#666666', 'old': '#b35900', 'unknown': '#b42318', 'na': '#666666', 'nogame': '#999999'}

    outer = ttk.Frame(root, padding=(10, 6, 10, 8))
    outer.pack(fill='both', expand=True)
    head = ttk.Frame(outer)
    head.pack(fill='x')
    ttk.Label(head, text=APP, style='Head.TLabel').pack(side='left')
    link = tk.Label(head, text=REPO_URL.replace('https://', ''), fg='#0b57d0', cursor='hand2', font=('Segoe UI', 9, 'underline'))
    link.pack(side='right')
    link.bind('<Button-1>', lambda _e: webbrowser.open(REPO_URL))
    Tip(link, 'Source code, updates and more Empire Earth mods on GitHub')
    ttk.Label(head, text='by Marabunta159  -', style='Gray.TLabel').pack(side='right', padx=(0, 4))
    ttk.Label(outer, style='Gray.TLabel',
              text='Fixes for the NeoEE version of Empire Earth and The Art of Conquest. Tick what you want, then press '
                   '"Apply changes". Untick to remove.' + ('   Detected: ' + neo_name if neo_name else '')).pack(anchor='w', pady=(0, 6))

    # --- folders
    ff = ttk.LabelFrame(outer, text='Game folders', padding=(8, 2, 8, 6))
    ff.pack(fill='x')
    ff.columnconfigure(1, weight=1)
    dir_var, dir_msg = {}, {}
    for r, g in enumerate(('ee', 'aoc')):
        ttk.Label(ff, text=GAMES[g]['title'] + ':').grid(row=r, column=0, sticky='w', padx=(0, 6), pady=2)
        dir_var[g] = tk.StringVar(value=os.path.normpath(dirs[g]) if dirs.get(g) else '')
        e = ttk.Entry(ff, textvariable=dir_var[g])
        e.grid(row=r, column=1, sticky='ew')
        e.bind('<Return>', lambda _e: refresh())
        e.bind('<FocusOut>', lambda _e: refresh())
        ttk.Button(ff, text='Browse...', command=lambda g=g: browse(g)).grid(row=r, column=2, padx=6)
        dir_msg[g] = ttk.Label(ff, width=34)
        dir_msg[g].grid(row=r, column=3, sticky='w')
    ttk.Button(ff, text='Detect again', command=lambda: redetect()).grid(row=0, column=4, rowspan=2, padx=(6, 0))

    # --- fixes
    lf = ttk.LabelFrame(outer, text='Fixes', padding=(8, 2, 8, 6))
    lf.pack(fill='x', pady=6)
    lf.columnconfigure(0, weight=1)
    ttk.Label(lf, text='Fix', style='Col.TLabel').grid(row=0, column=0, sticky='w')
    ttk.Label(lf, text='Empire Earth', style='Col.TLabel').grid(row=0, column=1, sticky='w', padx=10)
    ttk.Label(lf, text='The Art of Conquest', style='Col.TLabel').grid(row=0, column=2, sticky='w', padx=10)
    var, chk, lab, detail = {}, {}, {}, {}
    summaries = []
    for i, c in enumerate(ORDER):
        r = 1 + i * 2
        ttk.Separator(lf, orient='horizontal').grid(row=r, column=0, columnspan=4, sticky='ew', pady=2)
        cell = ttk.Frame(lf)
        cell.grid(row=r + 1, column=0, sticky='ew')
        t = ttk.Label(cell, text=COMP[c]['title'], style='Bold.TLabel')
        t.pack(anchor='w')
        s = ttk.Label(cell, text=COMP[c]['summary'], style='Gray.TLabel', wraplength=620, justify='left')
        s.pack(anchor='w')
        summaries.append(s)
        for w in (t, s):
            Tip(w, COMP[c]['info'])
        for col, g in ((1, 'ee'), (2, 'aoc')):
            fr = ttk.Frame(lf)
            fr.grid(row=r + 1, column=col, sticky='w', padx=10)
            if g not in COMP[c]['games']:
                ttk.Label(fr, text='-', style='Gray.TLabel').pack(anchor='w')
                continue
            var[(c, g)] = tk.BooleanVar(value=False)
            chk[(c, g)] = ttk.Checkbutton(fr, variable=var[(c, g)], command=lambda c=c, g=g: toggled(c, g))
            chk[(c, g)].pack(side='left')
            lab[(c, g)] = tk.Label(fr, text='', font=base_font, width=17, anchor='w')
            lab[(c, g)].pack(side='left')
            Tip(lab[(c, g)], lambda k=(c, g): detail.get(k, ''))
        ttk.Button(lf, text='Info', width=6, command=lambda c=c: messagebox.showinfo(COMP[c]['title'], COMP[c]['info'], parent=root)
                   ).grid(row=r + 1, column=3, padx=(6, 0))

    # --- options + buttons
    of = ttk.Frame(outer)
    of.pack(fill='x')
    shortcut_var = tk.BooleanVar(value=not args.no_shortcuts)
    sc = ttk.Checkbutton(of, text='Create desktop shortcuts for the cheat executables', variable=shortcut_var)
    sc.pack(side='left')
    if args.no_shortcuts:
        sc.state(['disabled'])
    admin_lbl = ttk.Label(of, text='', foreground='#b42318')
    admin_lbl.pack(side='right')

    bf = ttk.Frame(outer)
    bf.pack(fill='x', pady=6)
    apply_btn = ttk.Button(bf, text='Apply changes', command=lambda: start_apply(None))
    apply_btn.pack(side='left')
    rec_btn = ttk.Button(bf, text='Select recommended', command=lambda: select('recommended'))
    rec_btn.pack(side='left', padx=(12, 0))
    all_btn = ttk.Button(bf, text='Select all', command=lambda: select('all'))
    all_btn.pack(side='left', padx=6)
    rem_btn = ttk.Button(bf, text='Remove all fixes...', command=lambda: remove_all())
    rem_btn.pack(side='left', padx=6)
    ttk.Button(bf, text='Close', command=root.destroy).pack(side='right')
    ttk.Button(bf, text='About', command=lambda: about()).pack(side='right', padx=6)
    ttk.Button(bf, text='Source code...', command=lambda: save_source()).pack(side='right')
    ttk.Button(bf, text='Open backup folder', command=lambda: os.startfile(BACKUPS)).pack(side='right')

    log = ScrolledText(outer, height=5, font=('Consolas', 9), state='disabled', wrap='word')
    log.pack(fill='both', expand=True)

    q = queue.Queue()
    st = {'pack': None, 'states': {}, 'busy': False, 'first': True, 'loglines': [], 'failed': None}

    def say(text):
        st['loglines'].append(text)
        log.configure(state='normal')
        log.insert('end', text + '\n')
        log.see('end')
        log.configure(state='disabled')

    def pending():
        return {k: v.get() for k, v in var.items()
                if st['states'].get(k, ('',))[0] in ('on', 'off', 'old')
                and (v.get() != (st['states'][k][0] == 'on') or (v.get() and st['states'][k][0] == 'old'))}

    def update_buttons():
        n = len(pending())
        apply_btn.configure(text='Apply changes (%d)' % n if n else 'Apply changes')
        for b in (apply_btn, rec_btn, all_btn, rem_btn):
            b.state(['disabled'] if st['busy'] else ['!disabled'])
        if not n and not st['busy']:
            apply_btn.state(['disabled'])

    def toggled(c, g):
        if var[(c, g)].get():
            req = COMP[c]['requires']
            if req and (req, g) in var and st['states'].get((req, g), ('',))[0] in ('off', 'old', 'on'):
                var[(req, g)].set(True)
        else:
            for d in ORDER:
                if COMP[d]['requires'] == c and (d, g) in var and st['states'].get((d, g), ('',))[0] in ('off', 'old', 'on'):
                    var[(d, g)].set(False)
        update_buttons()

    def refresh(keep=False):
        if st['busy']:
            return
        old_want = {k: v.get() for k, v in var.items()} if keep else {}
        pack = st['pack'] = Pack({g: dir_var[g].get().strip().strip('"') for g in GAMES}, shortcut_var.get(), not args.no_shortcuts)
        for g in GAMES:
            typed = dir_var[g].get().strip()
            if pack.dirs[g]:
                dir_msg[g].configure(text='found', foreground='#1a7f37')
            else:
                dir_msg[g].configure(text=('%s not found here' % GAMES[g]['exe']) if typed else 'not found - choose the folder', foreground='#b42318')
        states = st['states'] = pack.all_states()
        any_installed = any(s in ('on', 'old') for s, _ in states.values())
        for k, (s, d) in states.items():
            lab[k].configure(text=STATE_TEXT[s] if s != 'nogame' else 'game not found', fg=COLORS[s])
            detail[k] = d
            usable = s in ('on', 'off', 'old')
            chk[k].state(['!disabled'] if usable else ['disabled'])
            if keep and usable and k in old_want:
                var[k].set(old_want[k])
            elif usable:
                var[k].set(s in ('on', 'old') or (st['first'] and not any_installed and COMP[k[0]]['recommended']))
            else:
                var[k].set(s == 'fixed')
        st['first'] = False
        locked = [d for d in pack.dirs.values() if d and not writable(d)]
        admin_lbl.configure(text='No write access to the game folder - start this program as administrator.' if locked else '')
        update_buttons()

    def browse(g):
        d = filedialog.askdirectory(parent=root, title='Folder that contains ' + GAMES[g]['exe'],
                                    initialdir=dir_var[g].get() or None, mustexist=True)
        if d:
            dir_var[g].set(os.path.normpath(d))
            refresh()

    def redetect():
        found, _ = detect()
        for g in GAMES:
            dir_var[g].set(found[g])
        refresh()

    def select(spec):
        for k, v in parse_select(spec, st['pack']).items():
            var[k].set(v)
        update_buttons()

    def remove_all():
        if messagebox.askyesno(APP, 'Remove every fix of this pack from both games?\n\nThe original files are restored.', parent=root):
            start_apply({k: False for k in var})

    def about():
        messagebox.showinfo('About', '%s %s\n\nFixes for the NeoEE version of Empire Earth and The Art of Conquest.\n\n'
                            '- Every fix checks the file it changes first; unknown versions are left alone.\n'
                            '- Before a game file is changed a backup is stored in\n  %s\n'
                            '- Start this program again to see what is installed or to remove it.\n'
                            '- No game files are included; only your own installation is patched.\n'
                            '- The source code of all fixes is included ("Source code..."). The first-person mode is an\n'
                            '  unfinished experiment that is no longer developed - feel free to continue it.\n\n'
                            'Tested with NeoEE v2.0.0.5.\n\n'
                            'Source code, updates and more Empire Earth mods:\n%s' % (APP, VERSION, BACKUPS, REPO_URL), parent=root)

    def save_source():
        src = os.path.join(RES, 'fixpack', 'EE-FixPack-source.zip')
        if not os.path.isfile(src):
            messagebox.showinfo(APP, 'The source code is not part of this build.', parent=root)
            return
        dst = filedialog.asksaveasfilename(parent=root, title='Save the source code of this pack', defaultextension='.zip',
                                           initialfile='EE-FixPack-source.zip', filetypes=[('ZIP archive', '*.zip')])
        if dst:
            shutil.copyfile(src, dst)
            say('Source code saved: ' + dst)

    def alert(kind, text):
        """message box - or, in unattended runs (--exit), a log line, the report and the end of the program"""
        if not args.exit:
            (messagebox.showerror if kind == 'error' else messagebox.showwarning)(APP, text, parent=root)
            return
        say(text)
        st['failed'] = 1
        if args.report:
            write_report(args.report, st['pack'], st['loglines'], 1)
        root.after(200, root.destroy)

    def start_apply(want):
        if st['busy']:
            return
        want = want if want is not None else pending()
        if not want:
            return
        pack = st['pack']
        targets = [d for d in pack.dirs.values() if d]
        if game_running():
            alert('warning', 'Please close the game first.')
            return
        if any(not writable(d) for d in targets):
            cur = ['--ee', dir_var['ee'].get().strip(), '--aoc', dir_var['aoc'].get().strip()] + (['--no-shortcuts'] if args.no_shortcuts else [])
            if not is_admin() and not args.no_elevate and relaunch_elevated(cur):
                root.destroy()
                return
            alert('error', 'No write access to the game folder. Start this program as administrator.')
            return
        pack.shortcuts = shortcut_var.get()
        st['busy'] = True
        update_buttons()

        def work():
            class W:
                def write(self, s):
                    if s:
                        q.put(s)

                def flush(self):
                    pass
            old = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = W()
            try:
                failed = pack.apply(want, log=lambda s: q.put(s + '\n'))
            except Exception:
                failed = 1
                q.put(traceback.format_exc())
            finally:
                sys.stdout, sys.stderr = old
            q.put(('done', failed))
        threading.Thread(target=work, daemon=True).start()

    buf = ['']

    def pump():
        try:
            while True:
                item = q.get_nowait()
                if isinstance(item, tuple):
                    if buf[0].strip():
                        say(buf[0].rstrip())
                    buf[0] = ''
                    st['busy'] = False
                    st['failed'] = item[1]
                    say('Done.' if not item[1] else 'Finished with %d problem(s) - see above.' % item[1])
                    say('')
                    refresh()
                    if args.report:
                        write_report(args.report, st['pack'], st['loglines'], item[1])
                    if args.exit:
                        root.after(200, root.destroy)
                    elif item[1]:
                        messagebox.showwarning(APP, 'Some steps could not be completed. See the log at the bottom.', parent=root)
                else:
                    buf[0] += item
                    while '\n' in buf[0]:
                        line, buf[0] = buf[0].split('\n', 1)
                        say(line.rstrip())
        except queue.Empty:
            pass
        root.after(80, pump)

    root.update_idletasks()
    if root.winfo_reqheight() > root.winfo_screenheight() - 90 or args.compact:      # small screen: one line per fix
        for w in summaries:
            w.pack_forget()
    refresh()
    say('Backups: ' + BACKUPS)
    for g in GAMES:
        if st['pack'].dirs[g]:
            say('%s: %s' % (GAMES[g]['title'], st['pack'].dirs[g]))
    if args.select:
        select(args.select)
    pump()
    if args.apply:
        root.after(300, lambda: start_apply(None) if pending() else (args.report and write_report(args.report, st['pack'], st['loglines'], 0),
                                                                    args.exit and root.destroy()))
    elif args.exit:
        root.after(1500, lambda: (args.report and write_report(args.report, st['pack'], st['loglines'], 0), root.destroy()))
    root.mainloop()
    return st['failed'] or 0


def write_report(path, pack, loglines, failed):
    data = dict(version=VERSION, dirs=pack.dirs, failed=failed, admin=is_admin(), frozen=FROZEN, backups=BACKUPS,
                states={'%s:%s' % k: list(v) for k, v in pack.all_states().items()}, log=loglines)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)


def relaunch_elevated(params):
    """start this program again with administrator rights (UAC prompt); True when the new instance was started"""
    params = [p for p in params if p not in ('--elevated', '--test-relaunch')] + ['--elevated']
    if FROZEN:
        exe, arg = sys.executable, subprocess.list2cmdline(params)
    else:
        exe, arg = sys.executable, subprocess.list2cmdline([os.path.abspath(__file__)] + params)
    # A one-file PyInstaller exe that starts itself would make the new instance reuse this instance's unpacked
    # files - which are deleted as soon as this instance exits.  Tell the bootloader to start from scratch.
    os.environ['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    for k in [k for k in os.environ if k.startswith('_PYI_') or k == '_MEIPASS2']:
        del os.environ[k]
    try:
        return ctypes.windll.shell32.ShellExecuteW(None, 'runas', exe, arg, None, 1) > 32
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ee')
    ap.add_argument('--aoc')
    ap.add_argument('--select')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--report')
    ap.add_argument('--exit', action='store_true')
    ap.add_argument('--no-elevate', action='store_true')
    ap.add_argument('--no-shortcuts', action='store_true')
    ap.add_argument('--compact', action='store_true', help='one line per fix (automatic on small screens)')
    ap.add_argument('--elevated', action='store_true', help=argparse.SUPPRESS)
    ap.add_argument('--test-relaunch', action='store_true', help=argparse.SUPPRESS)      # exercise the relaunch path
    args = ap.parse_args()
    found, neo_name = detect()
    dirs = {'ee': args.ee if args.ee is not None else found['ee'], 'aoc': args.aoc if args.aoc is not None else found['aoc']}
    # the game normally lives under "Program Files": ask for administrator rights once, right at the start
    need = [d for g, d in dirs.items() if d and os.path.isfile(os.path.join(d, GAMES[g]['exe'])) and not writable(d)]
    if ((need and not is_admin()) or args.test_relaunch) and not args.no_elevate and not args.elevated:
        if relaunch_elevated(sys.argv[1:]):
            return 0
    return run_gui(args, dirs, neo_name)


if __name__ == '__main__':
    sys.exit(main())
