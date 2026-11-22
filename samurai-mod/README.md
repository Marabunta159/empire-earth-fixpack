# Samurai for Empire Earth (base)

Unlocks the **Samurai** — the Japan-unique melee unit from *Empire Earth: The Art
of Conquest* — as a normal buildable unit in **base Empire Earth**, for every
civilization.

* Barracks → Row 3, Position 7 → **Samurai**
* Available in all epochs (0–14), 30 food + 30 iron, build time 32 s
* 400 HP, 29 attack, 6 arrow armour, speed 0.6, upgrade class `Swordsman`

## Why this is only 9 bytes

Base Empire Earth already ships the Samurai's entire payload as disabled cut
content inside `data/data.ssa`:

| piece | where |
|---|---|
| object `x06 Samurai` (id 438) | `db/dbobjects.dat` |
| tech `xSP06 Samurai` (id 6100) | `db/dbtechtree.dat` |
| button `xSP Samurai` (id 922) | `db/dbbuttons.dat` |
| graphic `x Samurai` (id 639) | `db/dbgraphics.dat` |
| model | `models/men_samurai_06.cem` |
| textures | `textures/but_samurai_00t.sst`, `textures/men_samurai_06t.sst` |
| voices | `dbsounds` → `sounds/dv0sam1..4.wav` |
| name | `Language.dll` slot 2066 = "Samurai" |

The Barracks (object 34) already lists tech 6100 in its build queue. The only
thing keeping the unit out of normal gameplay is tech 6100's **Only in
scenario** flag. This mod writes a loose `data/db/dbtechtree.dat` with that
tech made buildable (and its epoch window widened to 0–14 so it is easy to
find). Loose files in `data/db/` override the same path inside `data.ssa` —
NeoEE/dreXmod already ship four other db files that way.

Nothing is redistributed here: `samurai_mod.py` only pokes nine bytes in a
file the user already owns.

## Install

```bat
python samurai_mod.py install --game "C:\Program Files (x86)\Neo Empire Earth\Empire Earth"
```

On a vanilla install with no loose `data/db/dbtechtree.dat` yet, add
`--from-scratch`. That rebuilds the file from `data/data.ssa` and needs
`libDCL.dll` from [Empire Earth Studio II](https://github.com/EE-modders/empire-earth-studio-2)
(`set LIBDCL=C:\path\to\libDCL.dll`).

If the patched file is already in place (as shipped in a mod pack as a
pre-patched `dbtechtree.dat`), just copy it to `data/db/`.

## Check / remove

```bat
python samurai_mod.py status    --game "..."
python samurai_mod.py uninstall --game "..."
```

`uninstall` only removes the override if tech 6100 is in the expected patched
state, and keeps a copy as `dbtechtree.dat.samurai-removed`.

## Verified with

NeoEE build of Empire Earth (base) + Art of Conquest, 2026-10-09. Random map,
cheat-advanced to the Middle Ages, Samurai built from a Barracks. Base game
version 1.0.4.0-era binaries (`Empire Earth.exe`, `data.ssa` md5
`277617B2A5E17381731480084163B870`).

## Credits

* DB file layouts: [Forlini91/Empire-Earth---DB-Editor](https://github.com/forlini91/empire-earth---db-editor)
  (`EEEditorData/Vanilla/*.dats`, GPL-3.0)
* SSA/DCL formats: [EE-modders](https://github.com/ee-modders/empire-earth-toolbox/wiki/SSA-v1.0)
  and [Empire Earth Studio II](https://github.com/ee-modders/empire-earth-studio-2)
  by zocker_160 (GPL-3.0)
* Built with [universal-modder](https://github.com/rehan-remade/universal-modder) —
  AI-assisted, verified by hand in the running game.
