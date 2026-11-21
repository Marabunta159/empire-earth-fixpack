"""Empire Earth / The Art of Conquest (NeoEE) - Fix-Paket: ein Installer, einzeln waehlbare Bausteine.

  python ee_fixes.py list
  python ee_fixes.py status    [Bausteine ...]
  python ee_fixes.py install   [Bausteine ...]      ohne Bausteine: alle
  python ee_fixes.py uninstall [Bausteine ...]      ohne Bausteine: alle
  python ee_fixes.py menu                           Auswahl per Nummer

  Optionen:  --ee "<Ordner Empire Earth>"   --aoc "<Ordner Art of Conquest>"   --only ee|aoc
             --original-exe   Baustein "units" zusaetzlich in die Original-EXE schreiben
                              (Standard: nur die Cheat-EXE, das Original bleibt unveraendert)
             --no-shortcut    Baustein "cheats" ohne Desktop-Verknuepfung und ohne Kompatibilitaets-Flags

Bausteine (Reihenfolge = Installationsreihenfolge):
  crash     kein Absturz mehr beim zweiten Laden / Kampagnenwechsel        (Low-Level Engine.dll)
  net       kein NeoEE-Netzwerktest im Einzelspieler                        (TCP Protocol.dll)
  fog       Fog-of-War-Zaehler korrigiert                                   (Low-Level Engine.dll)
  aocstart  AoC startet trotz loser db-Dateien einer EE-Mod                 (Kopien in AoC\\Data\\db)
  cheats    eigene Cheat-EXE: Cheats auch in Kampagnen, buerger / doughboys (EE-Cheats.exe, EE-AOC-Cheats.exe)
  units     bis 4096 statt 512 Einheiten pro Bild sichtbar                  (Cheat-EXE; braucht "cheats")
  fps       Ego-Shooter-Modus, nur Empire Earth                            (ee_fps.dll; braucht "cheats")

Jeder Baustein prueft die Zieldatei per Signatur, legt ein Backup unter backups\\ an und laesst sich
einzeln wieder entfernen.  Es werden keine Spieldateien mitgeliefert - gepatcht wird die eigene Installation.
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NEO = r'C:\Program Files (x86)\Neo Empire Earth'
ORDER = ['crash', 'net', 'fog', 'aocstart', 'cheats', 'units', 'fps']
TITLE = {
    'crash': 'Crash-Fix (zweites Laden)',
    'net': 'kein Netzwerktest im Einzelspieler',
    'fog': 'Fog-of-War-Fix',
    'aocstart': 'AoC-Start-Fix (lose db-Dateien des Basisspiels)',
    'cheats': 'Cheat-EXE (buerger / doughboys, Cheats in Kampagnen)',
    'units': 'Einheiten-Limit 512 -> 4096 pro Bild',
    'fps': 'Ego-Shooter-Modus (nur Empire Earth)',
}
GAMES = {'ee': ('Empire Earth', 'Empire Earth.exe', 'EE-Cheats.exe', 'Empire Earth (Cheats)'),
         'aoc': ('Art of Conquest', 'EE-AOC.exe', 'EE-AOC-Cheats.exe', 'Empire Earth AoC (Cheats)')}
EXE_NAMES = ['Empire Earth.exe', 'EE-AOC.exe', 'EE-Cheats.exe', 'EE-AOC-Cheats.exe']


def tool(script, *args):
    """run one of the patchers, show its output, return its exit code"""
    return subprocess.call([sys.executable, os.path.join(HERE, script)] + list(args))


def game_running():
    try:
        out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout.lower()
    except OSError:
        return False
    return any('"%s"' % n.lower() in out for n in EXE_NAMES)


def writable(folder):
    probe = os.path.join(folder, '_ee_fixes_write_test.tmp')
    try:
        open(probe, 'w').close()
        os.remove(probe)
        return True
    except OSError:
        return False


def shortcut(name, target, workdir, create):
    lnk = "[Environment]::GetFolderPath('Desktop')+'\\%s.lnk'" % name
    if create:
        ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(%s); $s.TargetPath='%s'; $s.WorkingDirectory='%s'; "
              "$s.IconLocation='%s\\game.ico'; $s.Save()" % (lnk, target, workdir, workdir))
    else:
        ps = "Remove-Item (%s) -ErrorAction SilentlyContinue" % lnk
    subprocess.call(['powershell', '-NoProfile', '-Command', ps])


class Ctx:
    def __init__(self, a):
        self.dirs = {}
        for g, folder in (('ee', a.ee), ('aoc', a.aoc)):
            if a.only and a.only != g:
                continue
            if os.path.exists(os.path.join(folder, GAMES[g][1])):
                self.dirs[g] = folder
        self.all = {'ee': a.ee, 'aoc': a.aoc}
        self.original = a.original_exe
        self.plain = a.no_shortcut

    def engine(self, g):
        return os.path.join(self.dirs[g], 'Low-Level Engine.dll')

    def cheat_exe(self, g):
        return os.path.join(self.dirs[g], GAMES[g][2])

    def unit_exes(self, g):
        exes = [self.cheat_exe(g)]
        if self.original:
            exes.append(os.path.join(self.dirs[g], GAMES[g][1]))
        return exes


def run(comp, cmd, c):
    """cmd: status | install | uninstall  -> exit code"""
    rc = 0
    for g in c.dirs:
        d = c.dirs[g]
        if comp == 'crash':
            rc |= tool(r'crashfix\ssa_mapfix.py', cmd, '--dll', c.engine(g))
        elif comp == 'net':
            rc |= tool(r'net\sp_nonet.py', cmd, '--dll', os.path.join(d, 'TCP Protocol.dll'))
        elif comp == 'fog':
            rc |= tool(r'fogfix\fog_refcount.py', cmd, '--dll', c.engine(g))
        elif comp == 'aocstart':
            if g == 'aoc':
                rc |= tool(r'aoc\aoc_dbshadow.py', cmd, '--ee', c.all['ee'], '--aoc', d)
        elif comp == 'cheats':
            if cmd == 'status':
                print('%s : %s' % (c.cheat_exe(g), 'vorhanden' if os.path.exists(c.cheat_exe(g)) else 'nicht vorhanden'))
            elif cmd == 'install':
                r = tool(r'cheat\ee_cheat.py', 'build', '--dir', d, *(['--no-layers'] if c.plain else []))
                if not r and not c.plain:
                    shortcut(GAMES[g][3], c.cheat_exe(g), d, True)
                rc |= r
            else:
                rc |= tool(r'cheat\ee_cheat.py', 'remove', '--dir', d)
                if not c.plain:
                    shortcut(GAMES[g][3], '', '', False)
        elif comp == 'units':
            for exe in c.unit_exes(g):
                if cmd == 'install' and not os.path.exists(exe):
                    print('%s fehlt - Baustein "units" braucht die Cheat-EXE (Baustein "cheats") oder --original-exe' % exe)
                    rc |= 1
                    continue
                extra = ['--no-backup'] if cmd == 'install' and exe == c.cheat_exe(g) else []      # the cheat exe can be rebuilt
                rc |= tool(r'unitcap\ee_unitcap.py', cmd, '--exe', exe, *extra)
            if cmd == 'uninstall' and not c.original:                                              # never leave a patched original behind
                rc |= tool(r'unitcap\ee_unitcap.py', cmd, '--exe', os.path.join(d, GAMES[g][1]))
        elif comp == 'fps':
            if g != 'ee':
                continue
            dll, ini = os.path.join(d, 'ee_fps.dll'), os.path.join(d, 'ee_fps.ini')
            if cmd == 'status':
                print('%s : %s' % (dll, 'vorhanden' if os.path.exists(dll) else 'nicht vorhanden'))
            elif cmd == 'install':
                shutil.copyfile(os.path.join(HERE, 'fps', 'ee_fps.dll'), dll)
                if not os.path.exists(ini):
                    shutil.copyfile(os.path.join(HERE, 'fps', 'ee_fps.ini'), ini)
                print('   ee_fps.dll + ee_fps.ini -> %s   (aktiv nur in EE-Cheats.exe, Taste ^)' % d)
            else:
                for f in (dll, ini, os.path.join(d, 'ee_fps.log')):
                    if os.path.exists(f):
                        os.remove(f)
                print('   ee_fps entfernt')
    return rc


def menu():
    print('Bausteine:')
    for i, k in enumerate(ORDER, 1):
        print('  %d  %-9s %s' % (i, k, TITLE[k]))
    s = input('Nummern mit Leerzeichen (leer = alle, q = Abbruch): ').strip().lower()
    if s == 'q':
        return None
    if not s:
        return list(ORDER)
    try:
        return [ORDER[int(x) - 1] for x in s.replace(',', ' ').split()]
    except (ValueError, IndexError):
        print('Ungueltige Eingabe.')
        return None


def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['list', 'status', 'install', 'uninstall', 'menu'])
    ap.add_argument('components', nargs='*', help=' '.join(ORDER))
    ap.add_argument('--ee', default=NEO + r'\Empire Earth')
    ap.add_argument('--aoc', default=NEO + r'\Empire Earth - The Art of Conquest')
    ap.add_argument('--only', choices=['ee', 'aoc'])
    ap.add_argument('--original-exe', action='store_true')
    ap.add_argument('--no-shortcut', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'list':
        for k in ORDER:
            print('%-9s %s' % (k, TITLE[k]))
        return 0
    bad = [k for k in a.components if k not in ORDER]
    if bad:
        ap.error('unbekannter Baustein: %s   (moeglich: %s)' % (' '.join(bad), ' '.join(ORDER)))
    cmd, comps = a.cmd, a.components or list(ORDER)
    if cmd == 'menu':
        comps = menu()
        if not comps:
            return 1
        cmd = 'install'
    c = Ctx(a)
    if not c.dirs:
        print('Kein Spiel gefunden. Ordner angeben:  --ee "<Ordner mit Empire Earth.exe>"  --aoc "<Ordner mit EE-AOC.exe>"')
        return 1
    if cmd != 'status':
        if game_running():
            print('Bitte zuerst das Spiel beenden.')
            return 1
        locked = [d for d in c.dirs.values() if not writable(d)]
        if locked:
            print('Kein Schreibzugriff auf %s - als Administrator starten (install_ee_fixes.cmd fragt per UAC).' % locked[0])
            return 1
    comps = [k for k in ORDER if k in comps]
    if cmd == 'uninstall':
        comps.reverse()
    rc = 0
    for k in comps:
        print('\n=== %s: %s ===' % (k, TITLE[k]))
        r = run(k, cmd, c)
        rc |= r
        if r and cmd == 'install':
            print('\nFEHLER bei "%s" - siehe Meldung oben. Es wurde nichts weiter veraendert.' % k)
            return 1
    if cmd == 'install' and not rc:
        print('\nFertig (%s).' % ', '.join('%s' % GAMES[g][0] for g in c.dirs))
        if 'cheats' in comps:
            if not c.plain:
                print('Cheat-Sitzung: Desktop-Verknuepfung "Empire Earth (Cheats)" bzw. "Empire Earth AoC (Cheats)".')
            print('Cheats (Chat-Zeile, nur Einzelspieler):  buerger [1-50]   doughboys [1-50]')
        if 'units' in comps and not c.original:
            print('Das Einheiten-Limit ist in der Cheat-EXE angehoben; das Originalspiel bleibt unveraendert (Option --original-exe).')
    return rc


if __name__ == '__main__':
    sys.exit(main())
