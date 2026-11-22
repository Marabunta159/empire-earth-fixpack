Empire Earth Fix Pack 1.0
=========================

Fixes for the NeoEE version of Empire Earth and The Art of Conquest - one small program that installs
them and removes them again.

How to use
----------
1. Close the game.
2. Start EE-FixPack.exe. Windows asks for administrator rights because the game is installed under
   "Program Files".
3. The program finds both games by itself. If it does not, press "Browse..." and choose the folder
   that contains "Empire Earth.exe" / "EE-AOC.exe".
4. Tick the fixes you want - separately for Empire Earth and The Art of Conquest - and press
   "Apply changes". "Info" explains every fix.

To remove a fix start the program again, untick it and press "Apply changes" - or press
"Remove all fixes...". The original files are restored.

The fixes
---------
Crash fix: loading a second game
    No crash any more when you load a second map, saved game or campaign in one session.
No network test in single player
    No NeoEE port check when you open a random map or load a game. Multiplayer hosting is unchanged.
Fog of war fix
    Units no longer flicker in the fog (the visibility counter of a tile could run below zero).
Art of Conquest start fix (mods)
    AoC starts again when a mod has put loose database files into the Empire Earth folder
    ("Empire Earth.cpp (989): Verification failure"). Only offered when it is needed.
Graphics settings (dgVoodoo)
    Sharper picture: native resolution, 8x antialiasing, 16x anisotropic filtering, window without
    "always on top". Settings that are already fine are left alone; removing restores the old values.
Cheat executable (single player)
    A second game exe next to the original one. Built-in cheat codes also work in campaigns and
    scenarios; new codes "citizens [1-50]" and "doughboys [1-50]". Network games are not affected.
Long line as default formation
    Single player games use the formation "long line" instead of "short line" (cheat executable),
    also for the groups on the number keys. A game saved with "short line" continues with "long
    line"; any other saved formation is kept and shown correctly after loading. Computer players
    and network games are not affected.
More units on screen - cheat executable / original game
    The game can draw only 512 objects per frame; in big battles units disappear. The limit is
    raised to 4096. Two entries: one for the cheat executable, one for the normal game executable.
    The second one has not been tested in NeoEE online games - use it at your own risk.
First-person mode (unfinished experiment, Empire Earth only)
    Control one ranged unit like in a shooter (cheat executable, key left of "1").
    UNFINISHED and no longer developed, no support. The source code is included - press
    "Source code..." in the program if you want to continue it. Have fun.

Good to know
------------
- Every fix first checks the file it is going to change. Files it does not recognise (other game
  versions) are left alone and shown as "not supported".
- Before a game file is changed a backup is stored in C:\ProgramData\EE-FixPack\backups.
- No game files are included. Only your own installation is patched.
- The program is not signed. Windows SmartScreen may show "Windows protected your PC" - choose
  "More info" and "Run anyway". Some virus scanners are suspicious of small unsigned programs that
  modify other programs; the complete source code is inside ("Source code...") if you want to check.
- After a NeoEE update or reinstall just start the program again and apply the fixes again.
- Updates: at start the program asks GitHub once whether a newer version exists and shows a line
  with the download link if so. Nothing else is sent, nothing is downloaded or installed by itself
  (switch it off with the command line option --no-update-check). After downloading a new version,
  start it and press "Apply changes" - entries marked "update available" are rebuilt.
- After installing another Empire Earth mod, start the program again: the "Art of Conquest start
  fix" may be offered then.
- Frame rate with very many units: every unit costs drawing time. Measured at 2560x1440:
  about 650 units in view 100 fps, 860 units 77 fps, 2000 units 24 fps.

Tested with NeoEE v2.0.0.5 (Setup v1.7.2), Windows 11.

Source code, updates and more Empire Earth mods:
https://github.com/Marabunta159/empire-earth-fixpack
