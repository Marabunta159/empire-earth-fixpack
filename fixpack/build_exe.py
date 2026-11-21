"""Build  release/EE-FixPack.exe  (one file, GUI, no console) with PyInstaller.

  python fixpack/build_exe.py

Steps: icon -> source zip (bundled, "Source code..." button) -> version resource -> PyInstaller.
Needs: pip install pyinstaller pillow
"""
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, 'build', 'fixpack')
sys.path.insert(0, HERE)
VERSION = '1.0'

SOURCES = [                                 # (file in the project, name in the source zip)
    ('fixpack/ee_fixpack.py', 'fixpack/ee_fixpack.py'),
    ('fixpack/build_exe.py', 'fixpack/build_exe.py'),
    ('crashfix/ssa_mapfix.py', 'crashfix/ssa_mapfix.py'),
    ('net/sp_nonet.py', 'net/sp_nonet.py'),
    ('fogfix/fog_refcount.py', 'fogfix/fog_refcount.py'),
    ('aoc/aoc_dbshadow.py', 'aoc/aoc_dbshadow.py'),
    ('ssa_unpack.py', 'ssa_unpack.py'),
    ('cheat/ee_cheat.py', 'cheat/ee_cheat.py'),
    ('unitcap/ee_unitcap.py', 'unitcap/ee_unitcap.py'),
    ('formation/ee_formation.py', 'formation/ee_formation.py'),
    ('fps/src/ee_fps.cpp', 'fps/src/ee_fps.cpp'),
    ('fps/src/build.cmd', 'fps/src/build.cmd'),
    ('fps/ee_fps.dll', 'fps/ee_fps.dll'),
    ('fps/ee_fps.en.ini', 'fps/ee_fps.en.ini'),
    ('fps/ee_fps.ini', 'fps/ee_fps.de.ini'),
]


def private_patterns():
    """strings that must never end up in a public file: user name, home / project path of the build machine,
    plus the lines of build/private.txt (not shipped)"""
    pats = {os.environ.get('USERNAME', ''), os.path.expanduser('~'), ROOT, ROOT.replace('\\', '/')}
    extra = os.path.join(ROOT, 'build', 'private.txt')
    if os.path.exists(extra):
        pats |= {line.strip() for line in open(extra, encoding='utf-8')}
    return [p.encode() for p in pats if len(p) >= 4]


PRIVATE = private_patterns()

README = """Empire Earth Fix Pack %s - source code
=========================================

Everything the installer does is in these files. Python 3.8+ is enough to run them; nothing else is needed.

  fixpack/ee_fixpack.py     the GUI (tkinter). Start it with:  python fixpack/ee_fixpack.py
  fixpack/build_exe.py      builds EE-FixPack.exe (needs: pip install pyinstaller pillow)
  crashfix/ssa_mapfix.py    crash fix (Low-Level Engine.dll): maps one archive file at a time
  net/sp_nonet.py           no NeoEE network test for single player sessions (TCP Protocol.dll)
  fogfix/fog_refcount.py    fog of war reference counter (Low-Level Engine.dll)
  aoc/aoc_dbshadow.py       Art of Conquest start fix (uses ssa_unpack.py to read data.ssa)
  cheat/ee_cheat.py         builds the cheat executable
  unitcap/ee_unitcap.py     512 -> 4096 objects per frame
  formation/ee_formation.py "long line" as the default formation of new single player games (cheat exe)
  fps/src/ee_fps.cpp        first-person mode (C++, 32 bit, build with fps/src/build.cmd / MSVC)

Each patcher also works alone on the command line:  python <file> status | install | uninstall  (see -h).
All of them locate their patch sites by signature and refuse files they do not recognise.

First-person mode: an UNFINISHED EXPERIMENT. It is not developed any further and there is no support.
Section and key names of ee_fps.ini are German (the DLL reads them that way). Addresses are fixed for the
NeoEE Empire Earth.exe; there is no Art of Conquest version. If you want to continue it - have fun.

No game files are included.  Project page: https://github.com/Marabunta159/empire-earth-fixpack
""" % VERSION


def make_icon(path):
    from PIL import Image, ImageDraw, ImageFont
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, size - 8, size - 8), radius=44, fill=(28, 38, 58, 255), outline=(201, 162, 39, 255), width=10)
    try:
        font = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 124)
        small = ImageFont.truetype(r'C:\Windows\Fonts\segoeuib.ttf', 46)
    except OSError:
        font = small = ImageFont.load_default()
    d.text((size // 2, 104), 'EE', font=font, fill=(232, 196, 78, 255), anchor='mm')
    d.text((size // 2, 196), 'FIX', font=small, fill=(120, 200, 120, 255), anchor='mm')
    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def make_source_zip(path):
    for src, _ in SOURCES:
        data = open(os.path.join(ROOT, src), 'rb').read()
        hit = [p.decode() for p in PRIVATE if p.lower() in data.lower()]
        if hit:
            raise SystemExit('NOT built: %s contains %s' % (src, ', '.join(hit)))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('EE-FixPack-source/README.txt', README)
        for src, name in SOURCES:
            z.write(os.path.join(ROOT, src), 'EE-FixPack-source/' + name)


def make_version_file(path):
    v = tuple(int(x) for x in (VERSION + '.0.0').split('.')[:4])
    open(path, 'w', encoding='utf-8').write("""VSVersionInfo(
  ffi=FixedFileInfo(filevers=%r, prodvers=%r, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Empire Earth community'),
      StringStruct('FileDescription', 'Empire Earth Fix Pack (NeoEE) - installer / uninstaller'),
      StringStruct('FileVersion', '%s'),
      StringStruct('InternalName', 'EE-FixPack'),
      StringStruct('OriginalFilename', 'EE-FixPack.exe'),
      StringStruct('ProductName', 'Empire Earth Fix Pack'),
      StringStruct('ProductVersion', '%s')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""" % (v, v, VERSION, VERSION))


def main():
    os.makedirs(BUILD, exist_ok=True)
    icon = os.path.join(BUILD, 'icon.ico')
    srczip = os.path.join(BUILD, 'EE-FixPack-source.zip')
    ver = os.path.join(BUILD, 'version.txt')
    make_icon(icon)
    make_source_zip(srczip)
    make_version_file(ver)
    cmd = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed', '--name', 'EE-FixPack',
           '--icon', icon, '--version-file', ver,
           '--distpath', os.path.join(ROOT, 'release'), '--workpath', os.path.join(BUILD, 'work'), '--specpath', BUILD,
           '--add-data', os.path.join(ROOT, 'fps', 'ee_fps.dll') + ';fps',
           '--add-data', os.path.join(ROOT, 'fps', 'ee_fps.en.ini') + ';fps',
           '--add-data', srczip + ';fixpack', '--add-data', icon + ';fixpack']
    for sub in ('crashfix', 'net', 'fogfix', 'aoc', 'cheat', 'unitcap', 'formation', ''):
        cmd += ['--paths', os.path.join(ROOT, sub)]
    for mod in ('numpy', 'PIL', 'frida', 'psutil', 'capstone', 'win32com', 'pywin32', 'cv2', 'matplotlib', 'pytest'):
        cmd += ['--exclude-module', mod]
    cmd.append(os.path.join(HERE, 'ee_fixpack.py'))
    rc = subprocess.call(cmd)
    out = os.path.join(ROOT, 'release', 'EE-FixPack.exe')
    if rc == 0 and os.path.exists(out):
        data = open(out, 'rb').read()
        hit = [p.decode() for p in PRIVATE if p.lower() in data.lower()]
        print('%s  %d KB%s' % (out, len(data) // 1024, ('   WARNING: contains ' + ', '.join(hit)) if hit else ''))
    return rc


if __name__ == '__main__':
    sys.exit(main())
