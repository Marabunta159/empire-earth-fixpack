# MODLOG — Samurai (AOC) portiert nach Empire Earth (Base)

## Ziel
AOC-exklusive Einheit **Samurai** im Basisspiel Empire Earth baubar machen, für alle Zivilisationen.
Verifiziert im laufenden Spiel (Screenshot + Log).

## Route
**Data/Asset-Port** (mashup Pattern 1 "port the content"): DB-Einträge + Model/Texture/Sound
aus AOC in EE umhängen. Kein Code-Hook, keine Reimplementation.

## Installationen
- EE (Base): `C:\Program Files (x86)\Neo Empire Earth\Empire Earth`
  - `data\data.ssa` = 163.392.213 B (Stainless Steel Archive, Magic `rass`)
  - Loose Overrides: `data/db/` (4 Dateien), `data/Textures/` (240), `data/Models/amb_rock.cem`
  - `Language.dll` 249.856 B
- AOC: `C:\Program Files (x86)\Neo Empire Earth\Empire Earth - The Art of Conquest`
  - `data\data.ssa` = 45.554.167 B (Delta-Verdacht!)
  - `Language.dll` 270.336 B
  - + `dbcivpowers.dat`, `cachemap.dat` (aus Exe-Strings)
- Beide: NeoEE Build, dreXmod 3.4, dgVoodoo, natives x86 C++, DX7
- Anti-Cheat: keines. Safe to mod (SP/LAN + NeoEE Community-MP).

## Toolchain
- universal-modder (rehan-remade) — `um` CLI 0.2.0, Skills
- EESII (EE-modders/Empire-Earth-Studio-2) — SSA-Unpack + SST
- DB Editor (Forlini91/Empire-Earth---DB-Editor) v2.1 — db*.dat
- CEM-tool (EE-modders) — Blender .cem (nur falls nötig)

## Formate
- `data.ssa` = SSA v1.0: Header(16B: "rass", ver 1.0, data_start_offset) + FileEntry[]
  (path_length, path, start_offset, end_offset, size) + Intermediate (Attributes) +
  FileData (optional PK01/DCL compressed)
- DB-Dateien (binär): dbobjects.dat (Units/Buildings), dbtechtree.dat, dbbuttons.dat,
  dbeffects.dat (Limit 1565!), dbevents.dat (Limit 1500!), dbsounds.dat, dbgfxeffects.dat,
  dbupgrade.dat, dbgraphics.dat, dbcivilization.dat, dbfamily.dat, dbAnimals.dat,
  dbUnitBehavior.dat, dbweapontohit.dat, dbcalamity.dat, dbunitset.dat, dbareaeffect.dat,
  dbaiunittargeting.dat, dbcpbehavior.dat, dbambientsounds.dat, dbpremadecivs.dat,
  dbmusic.dat, dbworld.dat, dbterrain*.dat, dbrandommap.dat, dbfonts.dat, dbcliffterrain.dat,
  dbcolortable.dat, dbGameVariant.dat, dbStartingResources.dat, dbUIControls.dat
  AOC-exklusiv: dbcivpowers.dat
- Modelle: `.cem` (Computer Graphics Metadata)
- Textures: `.sst` (Slicer/Textures via EESII)
- Sounds: `.wav`
- Namen: `Language.dll` String-Tabelle (Slot-Nummer via dbeffects "Alter attribute → Name")

## Entscheidungen
- [2026-10-09] Einheit: **Samurai** (AOC/Japan-Unique, Land-Melee-Infanterie, Community-Tutorial vorhanden)
- [2026-10-09] Ziel-Civ: **alle Zivilisationen** (globaler Tech, kein Civ-Lock, kein dbcivilization-Eintrag nötig)
- Delivery: Loose Files in `EE\data\` (überschreiben SSA) statt SSA-Repack

## Status
- [x] Setup: Projektordner, universal-modder + um CLI 0.2.0
- [x] Toolchain: EESII 1.2.1 (SSA/SST), DB Editor v2.1 (Java, `.dats`-Schemata)
- [x] Backups: `%USERPROFILE%\.universal-modder\backups\ee-data-pristine\20261009-165140.zip`
      (1135 files, 436 MB) + `aoc-data-pristine\20261009-165207.zip` (859 files, 201 MB)
- [x] Unpack + Diff: EE `data.ssa` 3739 Dateien (163 MB) = Vollspiel;
      AOC `data.ssa` 826 Dateien (45 MB) = Delta auf eigenen db-Sätzen + neue Models
- [x] Samurai-Record + Cross-Links erfasst (s. Befunde)
- [x] Schema-Mapping: entfällt — Records waren in beiden Spielen identisch
- [x] Name: bereits vorhanden (Language.dll Slot 2066, UTF-16)
- [x] Assets: bereits vorhanden (cem/sst/wav in EE-SSA)
- [x] Verify in laufendem EE: **bestätigt** — Zufallskarte, Epochen per Cheat,
      Samurai in der Kaserne sichtbar und **baubar** (User-Check, 2026-10-09)
- [ ] Showcase-Clip (optional, ausgelassen)
- [x] Package: `release/` (samurai_mod.py + README), `um publish check` = PASS 0 failures
- [ ] Field Note (Draft liegt unter `FIELD-NOTE.md`, PR erst nach Freigabe)

## Befunde / Gotchas
1. **Der Samurai ist KEINE reine AOC-Neuschöpfung.** Base EE shippt den kompletten
   Satz als geschnittenen/„scenario"-Content: obj 438 `x06 Samurai`, tech 6100
   `xSP06 Samurai`, button 922, graphic 639, `models/men_samurai_06.cem`,
   `textures/but_samurai_00t.sst` + `men_samurai_06t.sst`, Sounds `dv0sam1..4.wav`,
   Language.dll Slot 2066 „Samurai". Der Barracks (obj 34) hat tech 6100 schon in
   der Build-Queue. AOC hat denselben Record (byte-identisch bis auf zwei
   Civ-Power-Bytes f39/f40).
2. **Der eigentliche Schalter** ist Tech 6100, Feld 38 „Only in scenario" = 1.
   Dazu Epoch-Fenster 5..6. Zusammen versteckt das die Einheit im normalen Spiel.
   Patch: f3 5→0, f4 6→14, f38 1→0 = 9 Bytes.
3. **Loose-Override-Mechanismus**: `data/db/*.dat` gewinnt gegen denselben Pfad in
   `data.ssa`. Beweis: NeoEE/dreXmod shippen dort bereits 4 abweichende db-Dateien
   (Hashvergleich loose vs. archiviert). Genau so wird der Patch ausgeliefert.
4. **dbtechtree.dat-Layout (Vanilla)**: 46 Felder, 268 B fix + `u32[num_tech_builders]`
   Array am Ende. Record-Header: pro Gruppe `u32 count`, dann `count+1` Records
   (`adjustNumEntries=1`, die Epoch-Zeile zählt nicht). Feld 38 ist ein 1-Byte-Bool
   bei Offset 245. Parser: `dat_dump.py`/`dat_patch.py` (schema-getrieben aus
   `EEEditorData/Vanilla/*.dats`).
5. **Effekt-/Event-Limits**: dbeffects 2000 Slots (958 undefined), dbevents 1500.
   Beim Hinzufügen nur undefined Slots überschreiben (KaktorKing-Tutorial) — hier
   aber nicht nötig, da kein neuer Effect/Event gebraucht wird.
6. **Button-Position 38 (Reihe 3, Pos. 7)** ist in der Barracks unbenutzt von
   anderen dort baubaren Techs (der Slot teilt sich nur den Rasterindex mit
   Buttons anderer Gebäude). Kein Umhängen nötig.
7. **AOC-Neuheiten** (zur Einordnung): 128 Namen nur in AOC, u.a. `Inf15 - Cyber Ninja`
   (obj 748), `Inf15 - Watchman` (788), `Sp15 - Space *`, `x Capital Ship Yamato`,
   `dbcivpowers.dat` (Japan/Korea + Civ Powers), `dbpremadecivs` +2 (Japan, Korea),
   `civilizations/japan.civ`, `korea.civ`, Epoch XV „Space".
8. **AOC-SSA ist 45 MB statt 163 MB**: kein fehlender Content, sondern eigenständige
   db-Sätze + nur die neuen Models. Delta-Verdacht war falsch Alarm — wichtig war der
   Dateilisten-Vergleich vor dem Record-Diff.
9. **`dbstartingresources.dat` hat einen 33.125er-Record** (Datei 1061 B für 8×132+4):
   ein hängendes Byte am Ende. Parser braucht eine Toleranz am Dateiende (bei
   `scan_records` als EOF-Guard). Kurzzeitig korrupt gesetzt (Stride 128 statt 132),
   aus Backup wiederhergestellt und verifiziert.
10. **`um win` braucht den BtbN-ffmpeg mit `gfxcapture`** — der chocolatey-ffmpeg
    hat den Filter nicht. `um win setup --force` lädt den richtigen herunter
    (`%LOCALAPPDATA%\universal-modder\ffmpeg\bin\ffmpeg.exe`).
11. **Spiel startet nicht per `um win launch`** ohne Working Directory —
    `Start-Process -WorkingDirectory <gamedir>` funktioniert. Fenster 1920×1080
    (borderless), dgVoodoo `FullScreenMode` fürs Driving auf false gesetzt und
    danach wieder auf true zurückgesetzt.

## Restore-Pfade
- `%USERPROFILE%\.universal-modder\backups\ee-data-pristine\20261009-165140.zip`
- `%USERPROFILE%\.universal-modder\backups\aoc-data-pristine\20261009-165207.zip`
- Mod entfernen: `python release/samurai_mod.py uninstall --game "<EE>"`

---

## Grafik-Modernisierung (09.10.2026)

### Frage
"Spiel grafisch im Sinne der Technik modernisieren, damit es mit modernen OS/Grafiktreibern
besser zusammenarbeitet. Community-Lösung ist dgVoodoo — geht es besser?"

### Befund Renderer
- **DirectDraw + Direct3D 1–7**, nicht D3D8. Beweis: PE-Imports der Renderer-DLLs
  (`DX7HRDisplay.dll`, `DX7HRTnLDisplay.dll`) → `DDRAW.dll`; `DX7HRGame.dll` → `d3dim700.dll`.
  `Empire Earth.exe`/`EE-AOC.exe` importieren `DDRAW.DLL`. Die `d3d8.dll` im String-Table ist
  ungenutzt (kein Import-Table-Eintrag).
- Ziel-API ist also exakt die von **DDrawCompat** ("DirectDraw and Direct3D 1-7 compatibility …").

### DDrawCompat getestet → scheitert
| Test | Ergebnis |
|---|---|
| v0.7.1, volle Config | rendert Menü sauber in 2560x1440, dann Exit nach ~2 s |
| v0.7.1, Minimal-Config | Exit nach ~4 s, Code 3 |
| v0.7.1, `GdiInterops = none` | Exit nach ~4 s, Code 0 |
| v0.7.1, Discord-Overlay deaktiviert + `WIN7RTM` entfernt | Exit nach ~4 s |
| v0.7.1, NeoEE-Netzwerk `Active: false` | Exit nach ~2 s |
| **v0.5.3** (hat expliziten NeoEE-Fix #251) | Exit nach ~3 s, Code 3 |

**Ursache (Windows Event Log):** `APPCRASH`, P4 = **`LOW-LEVEL ENGINE.DLL`** — der Engine-Kern
des Spiels bricht ab, nicht die Config. Damit ist DDrawCompat mit diesem NeoEE/dreXmod-Build
(3.4) grundsätzlich inkompatibel, egal welche Version.

Weitere gescheiterte Verdächtige: Discord-Overlay (`discord_game_sdk.dll`, `EEDiscord.dll`),
`WIN7RTM`-Compat-Flag, `HIGHDPIAWARE`, NeoEE-Netzwerk-Stack. Alle ohne Effekt.

### Ergebnis: dgVoodoo bleibt, Config wurde modernisiert
Die Community-Lösung war also richtig — aber die installierte Config war auf dieser Hardware
schlecht. Behobene Mängel (beide Verzeichnisse, `dgVoodoo.conf`):

| Schlüssel | vorher | nachher | warum |
|---|---|---|---|
| `VRAM` | 256 | 8192 | RTX 5070 Ti hat 16 GB; 256 MB verursacht Texture-Thrashing |
| `Resolution` | unforced | 2560x1440 | native Auflösung des LG UltraGear statt Skalierung |
| `Antialiasing` | (auskommentiert) | 8x | Kantenglättung |
| `Filtering` | — | forceanisotropic | Anisotrope Texturfilterung |
| `AppControlledScreenMode` | true | false | Wrapper kontrolliert den Modus (stabiler) |
| `WindowedAttributes` | Borderless, **AlwaysOnTop**, FullscreenSize | Borderless, FullscreenSize | AlwaysOnTop stört Alt-Tab |
| `FastVideoMemoryAccess` | — | false | sicherer bei modernen Treibern |

Game-Registry (beide Spiele): Fenster 2560x1440, 32 bpp, VSync an, Trilinear an.

### Verifikation
- Fenster liegt exakt bei (0,0) 2560x1440 auf **DISPLAY1 = LG UltraGear** (Primary, RTX 5070 Ti).
  BenQ RL2455 ist DISPLAY2 (1920x1080, AMD iGPU).
- Hauptmenü, „Einzelspieler-Options", „Spiel-Setup" alle sauber in 2560x1440 gerendert.
- Prozess stabil (14 s+), kein Crash, kein `0_Error.log`-Eintrag.
- Samurai-Mod weiterhin `INSTALLED`, AOC unverändert.

### Bekannte Limitierung (vorher schon so, nicht durch diese Änderung)
`um win drive`-Mausklicks erreichen das Spiel nicht (Exclusive-Fullscreen + SendInput). Per
A/B-Test mit Original-Config bestätigt. Tastatur (`key 0x0D`) funktioniert.

### Restore
- Backups: `%USERPROFILE%\.universal-modder\backups\ee-graphics-pre-ddrawcompat\20261009-194948\`
  (DDraw.dll, D3DImm.dll, dgVoodoo.conf, dgVoodooCpl.exe je Spiel + 4 .reg-Dateien).
- Für Rückkehr auf DDrawCompat: `ddraw.dll` (x86) ins Spielverzeichnis, `DDraw.dll`/`D3DImm.dll`
  von dgVoodoo entfernen/umbenennen. **Achtung:** Windows ist case-insensitive — `ddraw.dll`
  überschrieb beim Kopieren dgVoudoos `DDraw.dll`. Immer erst umbenennen, dann kopieren.

---

## Fog-Bug: Refcount-Patch (09.10.2026, abends)

### Repro-Material
- `data\Saved Games\nochok.ees` (92262 B, 21:22:43) / `nichtok.ees` (104052 B, 21:23:16)
- Live-Bug im laufenden Spiel (pid 21924), Screenshot `shot-bug.png` (2560x1440, 9.2 MB)

### Was die Saves gezeigt haben (negativ)
`GETerrainMesh::Save` (VA 0x1003F757) schreibt pro Tile **nur Byte +2 und +3**.
Der `short`-Refcount bei +0 wird **nie persistiert**. Der Bug ist also reiner
Laufzeit-Zustand — der Save-Diff war von vornherein ungeeignet (+11790 B sind
nur mehr Einheiten/erkundete Tiles). **Speichern/Laden heilt den Zustand.**

### Tile-Layout (aus `GETMTileRow::Initialize`, VA 0x10038968)
```
struct GETMTileRow { i32 start_x; i32 count; void* tiles; };   // 12 B, sparse rows
tiles = alloc((x1-x0+1) * 4)
pro Tile: 4 B = [i16 refcount][u8 +2][u8 +3]
```
Fog-Dekodierung (`UpdateFogOfWar`): `rc==0` -> dunkel, `rc==1` -> Schatten,
`rc>=2` -> sichtbar. **Als `ushort` gelesen** -> negative Werte lesen als
0xFFFF.. -> `>=2` -> **falsch sichtbar**.

### Der Paar-Defekt (vorher)
```c
ReferenceTile:   if (rc == 0) rc = 2;  else rc++;   // überspringt 1
DereferenceTile: rc--;                             // unbedingt, auch bei 0
```
Dekrementiert `rc` durch Null -> `-1` -> als `ushort` = sichtbar. Danach
`ReferenceTile` auf `-1` -> `65535+1` truncated auf **0** -> dunkel.
Genau das Flackern („Einheiten verschwinden im Schatten / tauchen kurz wieder auf").

### Live-Daten (pid 21924, 11400 Tiles)
`NEGATIVE=0, ZERO=0, 7431 bei rc=1 (Schatten), Rest 2..50+`
-> In *diesem* Snapshot war **kein** Refcount-Drift sichtbar. Die Asymmetrie ist
trotzdem ein realer Defekt (Refcounts sind Laufzeit-only, driftet über die Zeit).
**Ehrlich: der aktive Auslöser ist damit nicht final bewiesen.**
Zweiter Kandidat `bool[101][101]`-Overflow in `UpdateFogOfWar` war ebenfalls
**nicht aktiv** (Fenster 43x42 -> Loop 45x44 gegen 101).

### Gesetzter Patch (nur EE, `Low-Level Engine.dll`)
| | vorher | nachher |
|---|---|---|
| `ReferenceTile` | `if(rc==0) rc=2; else rc++` | `if(rc<2) rc=2; else rc++` |
| `DereferenceTile` | `rc--` | `if(rc>1) rc--` |

Semantik danach: `rc` bleibt in `{0} ∪ [2,∞)`; `0` = nie gesehen.
`rc==1` („aufgedeckt, nicht sichtbar") wird über den Seiteneffekt `2→(dec)→1`
erreicht und danach nicht mehr unterboten.

- VA `0x1000621B` (`DereferenceTile`) und `0x10006562` (`ReferenceTile`) sind
  `jmp`-Hooks in eine Code-Cave im `.text`-Tail-Slack (RVA `0x9361F`, 2529 B
  reines Padding).
- md5 vorher `544C44246DEA797C9B4E578D78A3AEE5` -> nachher s. `patch_engine.py`-Log.
- **AOC unverändert** (`40BD71D1E8662E7F1B972F1531DF34F5`): an denselben Offsets
  liegt völlig anderer Code -> AOC bräuchte eine eigene Offset-Analyse.

### Eigener Fehler, behoben
Erste Version der `ReferenceTile`-Cave hatte `jge +4` / `jmp +2` statt
`jge +5` / `jmp +3` -> Sprungziele mitten in Instruktionen. Per Capstone-
Rückdisassembly gefunden und korrigiert (`fix_refs.py`).

### Restore
`%USERPROFILE%\.universal-modder\backups\ee-engine-pristine\20261009-221558\`
(`Low-Level Engine.dll` + `Low-Level Engine-AOC.dll`). Einspielen, Spiel neu starten.

### Nebenbefunde
- `DereferenceTile`/`ReferenceTile` sind die einzigen Schreiber des Refcounts
  neben `SetTileReferenceCount` (VA 0x100065E2, setzt absolut).
- AOC-Engine hat andere Offsets -> jeder Patch braucht eine eigene Symbolliste.

---

## Crash beim zweiten Laden + Kampagnen-Cheat (10.11.2026)

### Crash "alles geht nur einmal" - Ursache (bewiesen)
- 10 WER-Dumps (`%LOCALAPPDATA%\CrashDumps\Empire Earth.exe.*.dmp`), alle dieselbe Wurzel:
  `FSArchive::ReadFATFile -> UDataCompression::GetIsCompressed -> memcmp` liest `NULL + Dateioffset`
  (z.B. `0x06F34926` = Start von `textures\formback_1_1.sst` in `data.ssa`); Folgecrashes in
  `GETexture::GetAllocatedSize(NULL)` / `GEModel::~GEModel`.
- `FSPath::AddArchive` schliesst bei JEDEM neu eingehaengten Archiv (Kampagnen-.ssa, Szenario, Editor)
  alle Archive und oeffnet sie neu. `FSArchive::Open` mappt das ganze Archiv per `MapViewOfFile`
  (data.ssa = 163 MB am Stueck). Nach einer Partie ist der 2-GB-Adressraum fragmentiert, das neue
  Archiv belegt die frei gewordene Luecke zuerst -> `MapViewOfFile` scheitert (Fehler 8,
  ERROR_NOT_ENOUGH_MEMORY, steht in 2 Dumps noch in `ESNativeError`), Rueckgabewert wird ignoriert,
  FAT bleibt geladen, View = NULL -> naechster Dateizugriff crasht.
- Nicht schuld: dgVoodoo-Einstellungen, Fog-Patch.

### Fix: `crashfix/ssa_mapfix.py` (Low-Level Engine.dll, EE + AoC per Signatur)
- `FSArchive::Open`: ganzes-Archiv-Mapping uebersprungen (Mapping-Objekt bleibt).
- `FSArchive::ReadFATFile`: Wrapper in der .text-Code-Cave mappt nur den 64K-ausgerichteten Bereich der
  einen Datei, ruft den Originalcode, unmappt wieder. Positionsunabhaengig (DLL wird gelegentlich
  umgeladen!). Nebenbei ~490 MB mehr freier Adressraum im Menue.
- `install | uninstall | status | plan`, Backup unter `backups/crashfix/<Zeit>/`, Patch-Record als
  `Low-Level Engine.dll.mapfix.json` neben der DLL (Uninstall setzt nur die eigenen Bytes zurueck,
  Fog-Patch bleibt).
- A/B-Test `crashfix/ab_test.py` (Frida, Sandbox): ohne Fix `access violation accessing 0x6f34926`
  (= Dump-Signatur), mit Fix liest dieselbe Datei fehlerfrei.

### Cheat: `cheat/ee_cheat.py` -> eigene `EE-Cheats.exe` (Original-EXE bleibt unveraendert)
- Cheat-Texte liegen in `Language.dll` (IDs 30622..30670). `ExecuteCheat` (EE `0x520339`) und die
  Chat-Funktion pruefen das Options-Flag `0x918E9A` ("Cheat-Codes"), in Kampagnen = 0.
  Patch: beide Pruefungen -> `flag != 0 || Einzelspieler` (`[[0x91984C]+0x2E] == 0`). Netzwerkspiel
  unveraendert.
- Neuer Cheat in freiem Slot 10: `buerger [1..50]` (Aliase `bürger`, `citizens`), Standard 5.
  Nutzt die spieleigene Editor-Nachricht `EEMHackANewUnit::Execute` (EE `0x4B7044`), Typ 32/480
  (Citizen / Female Citizen), Position = Kamera-Blickpunkt (`0x918CD0 + 0x40/0x44`) im 5er-Raster.
- Code-Cave im PE-Header (0x460), alle Adressen per Signatur/RTTI/Import -> gleicher Patcher fuer AoC.
- Getestet in Sandbox, Kampagne Griechenland Mission 1 (Flag 0): "all your base are belong to us"
  ueber die echte Chat-Zeile -> +100000 je Ressource; `buerger 4` -> +4 Buerger.

### Testmethode ohne Admin und ohne Maus/Tastatur
- Spiel verlangt Admin (HKCU-Layer RUNASADMIN), Spielordner nicht schreibbar -> Kopie unter
  `sandbox/` mit `__COMPAT_LAYER=RunAsInvoker DWM8And16BitMitigation HighDpiAware HeapClearAllocation
  Win7RTM`, dgVoodoo dort `FullScreenMode = false` (im Vollbild pausiert das Spiel ohne Fokus).
- Menues per Frida im Prozess bedient: `UIControl::FireTriggerEvent(ctrl, 0x3F0)` im Hook auf
  `UIManager::UpdateUI` (`cheat/sbx.py`, `ui.js`, `nav_campaign.sh`); Chat per
  `UIEditBox::SetText` + `ProcessEnterKey`.

### AoC
- Patcher finden alle Stellen (Code byte-identisch), aber AoC startet auf diesem Rechner gar nicht:
  `Empire Earth.cpp (989): Verification failure (theResult == keseOK)` ~5 s nach Start, auch ohne
  Patches. Deshalb dort nichts installiert und nichts im Spiel getestet.

### Installation
`install_ee_fixes.cmd` (UAC) / `install_ee_fixes.cmd uninstall`. rea-agents 3.2.1 -> 6.8.0 aktualisiert
(`rea doctor`: Ghidra ok, meldet aber java.exe ohne absoluten Pfad -> ggf. JAVA_HOME setzen).

---

## REA lauffähig + Machbarkeit Ego-Shooter-Modus (10.11.2026)

### REA
- Test: `rea decompile <LowLevelEngine.dll> 0x1001F081 --provider ghidra --snapshot rea/engine.snapshot`
  -> Pseudocode `FSArchive::ReadFATFile` in 50 s. Hopper/IDA/jadx/Kuna bleiben unkonfiguriert (nicht noetig).

### FPS-Machbarkeit (Sandbox, Kampagne Griechenland 1, alle Schritte live per Frida, Skripte in `fps/`)
| Baustein | Ergebnis | Wie |
|---|---|---|
| Kamera in Augenhoehe | **geht** | Hook `GEViewport::SetCamera` (1 Viewport `0x919470`, ~120/s), eigene `GETransformation`: Position = Einheit (`obj+0x130` ist ihre 4x4-Matrix, x/y/z bei +0x13C/+0x14C/+0x15C), `SetOrientationYPR(yaw, pitch, 0)`; Near-Clip 12.2 -> 0.05 (`SetFrontClippingDistance`). Blickrichtung = Y-Achse der Matrix. Screenshots `fps/fps_*.png` |
| Sicht | Gelaende/Baeume/Einheiten sauber; schwarz = Fog of War (mit aufgedeckter Karte voll sichtbar); kein Himmel (schwarz ueber Horizont) |
| Schuss | **geht mit echten Projektilen** | `EEMUnselectAllUnits::Execute` (0x4BF9C7) -> `EEMSelectUnit::Execute` (0x4BCF73, +0x0A Slot, +0x10 Einheiten-ID) -> `EEMAttackUnit::Execute` (0x4B3958, +0x10 Ziel-ID). Buerger wirft `Citizen Projectile` (Typ 656) |
| Staerke einstellbar | **geht** | Schadensfunktion `0x6172BC` (thiscall Ziel, arg1 = Projektil/Angreifer, arg2 = Schaden). Projektil `+0x1E0` = Schuetze. x10 -> 4 wird 40, Ziege (12 HP) stirbt mit einem Treffer |
| Einheiten-ID | `obj+0x24` (oberstes Byte = Spielerindex), Lookup `0x53B889` (this = 0x918300) |
| HP | `obj+0x3C` |

### Offen fuer einen echten Modus
- Eingabe: Spiel liest Maus/Tastatur per DirectInput (`ISMouse`/`ISKeyboard::Refresh`) -> im FPS-Modus abfangen.
- Bewegen (WASD): `EEMPathTo` pro Tick oder Position direkt schreiben (Wegfindung/Kachelbelegung pruefen).
- Zielen: Strahl aus Kamera gegen Einheiten-Positionen (oder `EEUnitPicker`), Fadenkreuz-HUD.
- Attack-Befehl laesst die Einheit erst in Reichweite laufen; "Schuss genau wohin gezielt" braucht direktes
  Spawnen eines Projektils (EEPMProjectile/EEUCProjectile - noch nicht untersucht).
- Adressen oben sind EE-Basis; fuer AoC per Signatur nachziehen (wie in ee_cheat.py).

---

## Ego-Shooter-Modus als native DLL (10.11.2026)

Lieferung: `fps/ee_fps.dll` (+ `fps/ee_fps.ini`), Quelle `fps/src/ee_fps.cpp`, Build `fps/src/build.cmd`
(VS 2019 BuildTools x86, `cl /O2 /MT /EHa`). Installation ueber `install_ee_fixes.cmd` (kopiert DLL + ini in den
EE-Ordner, ini nur wenn noch keine da ist; `uninstall` loescht beides). Nur Basisspiel, AoC bewusst nicht.

### Laden
- `cheat/ee_cheat.py` ruft jetzt am Anfang der Cheat-Registrierung (Code-Cave) `LoadLibraryA("ee_fps.dll")` auf.
  Fehlt die DLL, passiert nichts. (Eintrittspunkt in den Header verlegen ging NICHT: Prozess stirbt sofort,
  vermutlich weil die Kompatibilitaets-Shims den Einsprungpunkt patchen wollen.)
- **Falle:** Die Engine laedt beim Start jede DLL im Spielordner einmal als moegliches Plugin
  (`PIMModule::GetModule` in GE/SE/NEInitialize) und entlaedt sie wieder -> Hooks zeigten in freigegebenen Speicher.
  Loesung: DLL wird nur aktiv, wenn im PE-Header-Cave `0x400460` die Marke `EECHEAT1` steht (also nur in
  EE-Cheats.exe), und pinnt sich dann (`GetModuleHandleEx PIN`). Geprueft: normale `Empire Earth.exe` laedt die DLL,
  setzt keinen Hook, schreibt kein Log.
- Exe-Funktionen (Schaden) erst beim ersten UI-Frame pruefen/hooken - beim Laden passte die Signatur noch nicht.

### Bausteine (alle in der Sandbox verifiziert)
| Was | Wie |
|---|---|
| Kamera | Hook `GEViewport::SetCamera` (Engine-Inline-Hook 8 Byte). Eigene Matrix wird **in die uebergebene Transformation (0x91831C) geschrieben** - der Aufrufer zeichnet damit danach das Gelaende; nur den Zeiger zu tauschen liess Gelaende in RTS-Ansicht. Beim Verlassen Original zurueck. Kamera 0.35 vor die Augen (sonst Kopf im Bild) |
| Eingabe | `ISMouse/ISKeyboard::Refresh` hooken -> DirectInput-Device-vtable (Index 9 GetDeviceState, 10 GetDeviceData). Im Ego-Modus: Druck-Ereignisse fuer uns und aus dem Puffer entfernt, Loslass-Ereignisse durchgereicht (nichts bleibt haengen), Maus-X/Y/Rad aus GetDeviceState. Umschalttaste (DIK 0x29 = ^) |
| Fadenkreuz | Spiel-Cursor: oberstes UIForm (`UIManager+0x34` vector, letztes) `+0xE4` = Cursor x/y (float) -> Bildmitte |
| Zielen | Strahl aus Kamera (Matrix-Y-Spalte = Blick, X = rechts), Einheiten aller anderen Spieler, Radius 0.55 (+Gebaeude 1.2); aktuelles Ziel bleibt, solange es unter dem Fadenkreuz ist |
| Schiessen | `EEMAttackUnit::Execute` mit eigener Auswahl, solange LMB gehalten; Loslassen -> `EEMHaltSelectedGroup::Execute` (0x4B73C9) |
| Laufen | `EEMPathTo::Execute` (0x4B9D7B): +0x10 Winkel, +0x14 x, +0x18 y, +0x1C=1, +0x1D=1; neu nur bei Richtungswechsel >14 Grad oder Ziel fast erreicht |
| Held | Werte liegen pro Spieler+Typ in `EEUnitClassUpgrade` (0x164 Byte, Einheit +0x34 und +0x37C). Eigene Kopie: `operator new(0x164)` (0x683718) + Ctor 0x627765(db), Zahlen 0x84..0x153 vom Original, **Referenzzaehler +0x154/+0x158 = 1** (0 -> Einheit schiesst nicht, Original-Zaehler kopieren -> Absturz). Felder: Reichweite +0x9C, Sicht +0xA4, Angriff +0xD8, Ruestung +0xE0..0xF4, Nachladen ms +0x138, MaxHP +0x144. HP x10, erlittener Schaden x0.35, 1 %/s Regeneration |
| Verhalten | Einheit +0x208 = `EEUnitBehavior*` aus Tabelle `[0x8D2044][0..7]` (wie `EEMSetUnitBehavior`); Index 6 = laeuft nicht hinterher, schiesst aber |
| Waffen | 1 Standard (eigene Nachladezeit, Schaden x2), 2 AK-47 (250 ms, x1.2), 3 AWP (2600 ms, x12, 16 Felder), 4 Desert Eagle (700 ms, x3.5); Schaden ueber Hook 0x6172BC, Nachladezeit ueber +0x138 |
| Meldungen | Spiel-Chat: `0x661E91` thiscall (this=[0x91977C]; Spieler+0x438, Spieler+0x24, UWideString, [[0x917BB8]+0x2CC], 0) |
| Ende | Taste ^/ESC, Auswahl geaendert, Einheit tot -> Werte, Verhalten, Kamera, Clip-Distanzen zurueck, RTS-Kamera auf die Einheit |

Gemessen: Musketier-Held, AK-47 75 -> 90 je Treffer, ~5 Schuss/s, Langschwertkaempfer (400 HP) aus 8.1 Feldern in
0.6 s; AWP 75 -> 900; Abwaehlen -> 325/325 HP, Reichweite 5; Tod -> automatisch RTS-Ansicht, Spiel laeuft weiter.

### Grenzen / offen
- Echte Maus/Tastatur konnte ich nicht testen (Regel: Eingaben des Nutzers nicht fernsteuern); getestet wurde ueber
  den Debug-Export `fps_sim` (gleiche Zustandsvariablen). Der DirectInput-Pfad ist eingebaut und die Hooks greifen.
- Boegen/Schleudern/Speere: Projektile fliegen nicht weiter als die eigene Reichweite -> Modus stellt nach 6 s ohne
  Treffer auf die natuerliche Reichweite zurueck. Gewehre (Musketier, Schuetzen, MG, Scharfschuetze) haben >= 9.
- Laufen ist so schnell wie die Einheit (~0.7 Felder/s); `UCU+0xA8` beeinflusst das Tempo nicht.
- Kein HUD ausser Chat-Meldungen; Himmel schwarz; im Hintergrund zeichnet die Sandbox nur, wenn die Welt-Szene
  ohnehin neu gerendert wird (Screenshots ok).
- Fensternachrichten-Filter (`DispatchMessageA`-Import) fuehrte zum Absturz beim Betreten -> per ini abschaltbar,
  Standard aus (Spiel liest Hotkeys/Klicks ueber DirectInput, das ist gefiltert).
- Testskripte: `cheat/fpsctl.js` (Spawnen/Auswaehlen/Eingabe simulieren), `cheat/aimshoot.js`, `cheat/clone_test.js`.

### Korrektur nach erstem echten Test (10.11.2026, Nutzer-Rueckmeldung)
Rueckmeldung: kein Visier, Ego-Ansicht mit Vogelperspektive vermischt (Boden aus der Vogelperspektive, Objekte
schwebend), von 27 Klicks nur 1 Treffer (Log: `leave ... shots 27, hits 1`, Einheit Typ 512).

| Ursache | Fix |
|---|---|
| Renderer (0x503ad7..0x503b79) ruft `SetCamera` und die volle Boden-Transformation nur, wenn Byte `0x9128CB` = 0 ("Kamera geaendert"); sonst alle 100 ms Teil-Update mit alter Projektion | im Ego-Modus jedes Bild `0x9128CB = 0`, beim Verlassen nochmal (RTS-Bild wird neu aufgebaut) |
| Gelaende/Einheiten werden nur um den Blickpunkt der RTS-Kamera aufgebaut | RTS-Kamera Ziel `+0x40/+0x44` und aktuell `+0x78/+0x7C` = Einheit + 6 Felder in Blickrichtung (`WeltVorlauf`) |
| Fadenkreuz war der Spiel-Cursor in Bildschirmmitte (720), die 3D-Ansicht hat ihre Mitte bei y=672 (Leisten oben/unten) | eigenes Fadenkreuz: `DX7Rasterizer::BeginScene/DrawSky/EndScene` (DX7HRDisplay + DX7HRTnLDisplay) gehookt, Geraet = `[[rast+0x6C]+k*4]+0x1C` (IDirect3DDevice7), 3D-Viewport per `GetViewport` (vt 15) waehrend DrawSky, Zeichnen per `Clear` (vt 10) mit Rechtecken in EndScene; Spiel-Cursor nach (-200,-200), dgVoodoo-Zeiger: dessen `GetCursorPos`-Zeiger (in gepackter Sektion, kein Import-Eintrag) umgebogen |
| Kurzer Klick: Loslassen -> sofort `Halt`, Einheit hatte noch nicht gedreht/nachgeladen | Klick = ein Schuss: Angriff bleibt bis Treffer oder Nachladezeit+0.9 s; halten = Dauerfeuer |
| Altes Bild bleibt, wo nichts gezeichnet wird | nach BeginScene 3D-Bereich mit `Himmelfarbe` loeschen (Himmel wird zuletzt mit Tiefe 1 gezeichnet, daher nicht in DrawSky) |

Neu: HUD (Lebensbalken, Waffenplaetze), Treffer-Blinken des Fadenkreuzes, Zielfernrohr (rechte Maustaste, `Zoom=4` bei AWP).
Gemessen (Sandbox, Typ 512 als Held): 4 Einzelklicks -> 4 Treffer (66 -> 132); AK-47 gehalten 5 Schuss/s (44 -> 53);
AWP 44 -> 528. Zweimal starb die Sandbox (Zugriffsfehler in einem `TSThread`) kurz nach dem Betreten waehrend der
Missions-Einleitung, mit Ausnahme-Logger danach nicht mehr reproduzierbar (mehrere Laeufe, 90 s Stresstest ok).

---

## Kein Netzwerktest im Einzelspieler, Doughboy-Cheat, AoC lauffaehig (21.11.2026)

### Netzwerktest bei "Zufallskarte" / "Spiel laden" - Ursache (bewiesen)
- Das Spiel legt auch im Einzelspieler eine Sitzung an (`NESynchronousServer`-Konstruktor -> `NEProtocol::Publish`
  -> `NPIMPublish` in `TCP Protocol.dll`). NeoEE hat den `bind()` im Socket-Helfer (`0x100022D8`) durch einen Sprung
  in die Sektion `.neoee` ersetzt: `LoadLibrary("neoee.dll")` -> `punch_hole(socket)` -> Port-Check gegen
  titan.neoee.net (3 s Timeout), UPnP, Hole-Punching, Ball-Fenster. Beleg: `neoee.log` ("checking port 1 ...").
- Einzelspieler-Sitzungen heissen `EEName` und werden mit `bool1 = 1` angelegt (10 Aufrufstellen in der EXE; der
  Multiplayer-Host aus der Lobby `0x402D27` und `Migrated Server` uebergeben 0). Der Wert landet als Argument 8 in
  `NPIMPublish` und im Sitzungs-Record bei `+0x55` (dasselbe Flag haelt die Sitzung aus der LAN-Suche heraus).
  NeoEE wertet es nicht aus.
- Der Schalter `[[0x91984C]+0x2E]` (IsMultiplayerSession) taugt hier NICHT: Publish laeuft im Konstruktor, der
  globale Zeiger zeigt dann noch auf das alte Objekt.

### Fix: `net/sp_nonet.py` (`TCP Protocol.dll`, EE + AoC per Signatur, byte-identische Stellen)
- Hook prueft zuerst `record+0x55` (Record = gesichertes `esi` von `NPIMPublish`, `[ebp-1Ch]` im Helfer):
  lokal -> Originalcode des Spiels (`bind` auf UDP 33334), `neoee.dll` wird gar nicht geladen;
  sonst -> NeoEE-Cave wie bisher. 3 Edits: Hook (7 B), wiederhergestellter Original-Schwanz (7 B), 44 B Cave bei
  `.neoee+0x80`. Positionsunabhaengig (DLL wird umgeladen!); der einzige relozierte Befehl (`call [bind]`) bleibt
  an seiner Stelle - deshalb hatte NeoEE ihn stehen lassen und uebersprungen.
- `status | plan | install | uninstall`, Backup `backups/netfix/<Zeit>/`, Record `TCP Protocol.dll.spnonet.json`.
- Test (Sandbox, Frida-Probe `net/probe.js`): Zufallskarte und Spielstand laden -> "LOCAL path", `NPIMPublish -> 0`,
  `neoee.dll` nicht geladen, `neoee.log` unveraendert. Gegenprobe (Flag per Probe auf 0 gezwungen) -> NeoEE-Cave
  wird betreten. Echtes Multiplayer-Hosting konnte ich NICHT durchklicken: das Multiplayer-Menue (WON-Lobby) laeuft
  nicht ueber `UIManager::UpdateUI`, die In-Prozess-Bedienung greift dort nicht.

### Cheat `doughboys [1..50]` (Alias `doughboy`)
- `cheat/ee_cheat.py`: Tabelle `CHEATS` statt Einzelkonstanten; freier Slot 19 (10 = buerger). Jeder Cheat hat einen
  kleinen Einsprung (`push Typ ungerade / push Typ gerade / jmp`), der Rumpf liest die Typen vom Stack. Doughboy =
  dbobjects-ID 204 (`Inf10 - Doughboy`), in EE und AoC gleich. Weitere Einheiten = eine Zeile in `CHEATS`
  (frei ist danach kein Slot mehr -> dann Zahl-Parameter oder Slot teilen).
- Test EE (Sandbox, Spielstand): `doughboys` -> 5, `doughboy 7` -> 7, `doughboys 99` -> 50 (Typ 204); `buerger 4`
  -> 2x32 + 2x480.

### Art of Conquest startet wieder - Ursache war die Samurai-Mod, nicht dgVoodoo
- `Empire Earth.cpp (989): theResult == keseOK` = Techtree-Loader `0x5CBDF0` liefert Fehler 18 fuer `db\dbtechtree.dat`.
- AoC durchsucht auch den Datenordner des Basisspiels (Nachbarordner `Empire Earth\data`). Die lose
  `data\db\dbtechtree.dat` der Samurai-Mod (EE-Format, 14 Epochen) gewinnt gegen AoCs eigene Datei im `data.ssa`
  -> AoC-Loader (15 Epochen) scheitert. AoC lief am 09.10. um 16:38 noch (neoee.log), die Mod kam danach.
  dgVoodoo.conf, Kompatibilitaets-Flags und GPU-Wahl waren fuer AoC bereits identisch zu EE.
- Fix `aoc/aoc_dbshadow.py`: fuer jede lose `EE\data\db\*.dat`, die AoC nicht selbst lose hat, wird AoCs eigene
  Fassung aus `AoC\Data\data.ssa` nach `AoC\Data\db\` gelegt (eigener Ordner wird zuerst durchsucht). Liste in
  `_aoc_shadow.json`. **Nach jeder weiteren EE-Mod mit losen db-Dateien erneut ausfuehren.**
- AoC bekommt jetzt dieselben Verbesserungen wie EE: Crash-Fix (`ssa_mapfix`), Netz-Fix, Cheat-EXE
  (`EE-AOC-Cheats.exe`) und den Fog-of-War-Fix.
- Fog-Fix AoC: `fogfix/fog_refcount.py` schreibt `ReferenceTile`/`DereferenceTile` an Ort und Stelle um
  (Adressrechnung `imul eax,[esp+8],12 / add eax,[ecx+rows]` ist 2 Byte kuerzer -> Platz fuer die Pruefung; kein
  Cave, keine Header-Aenderung). Semantik wie der EE-Patch vom 09.10. EE selbst behaelt die Cave-Variante.
- Test AoC (Sandbox): Hauptmenue, Zufallskarte gestartet, lokaler Netzpfad, `doughboys 6` -> 6x Typ 204,
  `buerger 4` -> 2x32 + 2x480, Fog-Funktionen per Frida auf Testmesh (rc -1/0/1/2/5 -> Ref 2/2/2/3/6, Deref
  -1/0/1/1/4), Live-Mesh 11400 Kacheln ohne negative Zaehler. Deinstallation stellt die DLLs byte-genau wieder her.
- Nicht portiert: Ego-Shooter-Modus (`ee_fps.dll` hat feste EE-Adressen).
- Falle beim Testen: Ein Frida-Hook mit Schleife direkt in `GETerrainMesh::UpdateFogOfWar` (140 Aufrufe/s) hat die
  Sandbox beendet - Zeiger nur merken, ausserhalb des Hooks lesen (`aoc/fog_scan.js`). Solange der
  Zivilisations-Dialog (Form 7) offen ist, laeuft weder Fog-Update noch `ReferenceTile`.

### Installation
`install_ee_fixes.cmd` (UAC) installiert jetzt EE und - falls vorhanden - AoC; `noaoc` laesst AoC aus,
`uninstall` entfernt alles. Die im Spielordner liegende `ee_fps.dll` ist aelter (04:44) als der letzte Build
(12:12, Korrektur nach dem ersten echten Test) - der Lauf aktualisiert sie mit.

### Offene Punkte / moegliche TODOs
| # | Thema | Befund | Stand |
|---|---|---|---|
| 1 | Absturz 21.11. 02:16 (`EE-Cheats.exe.34052.dmp`) | AV in `RtlSizeHeap` aus `GETMTileRow::DeallocateInternalData` <- `~GETerrainMesh` (Partie verlassen), Virtual 1339 MB. Heap-Block einer Kachelzeile zerstoert. Verdacht: `Reference/DereferenceTile` pruefen x/y nicht gegen `start_x/count` -> Schreiben ausserhalb der Zeile (Sichtkreis ueber den Kartenrand; im Ego-Modus Sicht/`WeltVorlauf` vergroessert) | nur Dump gelesen, Ursache nicht bewiesen |
| 2 | Absturz 20.11. 22:33 (`EE-Cheats.exe.25860.dmp`) | AV Lesen `0x467` in `dreXmod.dll+0x6672C` auf einem `TSThread` (dreXmod 3.4, Fremdcode) | nicht untersucht |
| 3 | 32 Bit: 2 GB Adressraum | EXE und Engine ohne `LARGEADDRESSAWARE`; Abstuerze bei 1,0-1,3 GB Virtual. LAA-Flag gaebe 4 GB, aber Engine-Code auf vorzeichenbehaftete Zeigervergleiche pruefen (MSVC6-Aera) | offen |
| 4 | dgVoodoo `VRAM = 8192` | 32-Bit-Spiel: Speichergroessen sind DWORD/int - Werte ab 2048 MB koennen als negativ gelesen werden. Pruefen, was EE von `GetAvailableVidMem` liest und ob Texturbudget/Detailstufe davon abhaengt | Hypothese, nicht gemessen |
| 5 | Viele Einheiten gleichzeitig im Bild | noch nichts gemessen. Ansatz: Sandbox + `doughboys 50` mehrfach, Bildrate und fehlende Modelle beobachten, im Renderer nach festen Puffergroessen suchen (`DX7HRDisplay`/`DX7HRTnLDisplay`, Vertex-/Sortierpuffer) | offen |
| 6 | NeoEE-Test bei echtem Multiplayer-Host | unveraendert aktiv (gewollt); nicht per UI testbar gewesen | bei Gelegenheit im echten Spiel pruefen |
| 7 | Fog-Funktionen ohne Bereichspruefung | haengt mit #1 zusammen; in AoC bleiben in `ReferenceTile` 8 Byte frei, sonst Cave noetig | offen |
| 8 | Samurai-Mod | bricht AoC ohne Shadow-Kopie (siehe oben); README der Mod ergaenzen | offen |

---

## Einheiten verschwinden: festes Limit von 512 Objekten pro Bild (21.11.2026, nachmittags)

### Symptom
Ab ca. 300 Einheiten im Bild (im Gefecht frueher) verschwinden Einheiten; welche, haengt von der Kamera ab; nach
dem Ausduennen dauert es kurz, bis die Stelle wieder stimmt. Der Fog-Refcount-Patch half nicht.

### Ursache (gemessen, nicht vermutet)
- Reproduziert in der Sandbox mit `doughboys 50` x n: `DX7Rasterizer::Draw(GEModel*)` aus der Einheiten-Zeichenroutine
  (EE `0x50B4AC`) wird pro Bild **genau 512-mal** aufgerufen, egal ob 770 oder 1500 Einheiten im Bild sind.
- Das Spiel sammelt pro Bild alle Objekte der sichtbaren Kachelzeilen (`GETerrainMesh::GetVisibleTileRow`, EE `0x503B83`)
  in zwei festen Tabellen eines globalen Objekts (EE `0x8D2CB8`, AoC `0x8E9458`):
  `[512] x 0x148` Byte (Einheiten, Gebaeude, Leichen, Geschosse; Zaehler +0x3F880) und `[1536] x 0x3C` Byte
  (einfache Objekte, z.B. Baeume; Zaehler +0x3F884). Dritte Tabelle (Heap, 1536 x 0x50) fuer Maus-Picking und
  "schon eingetragen".
- Volle Tabelle -> `cmp [0x912538], 0x200 / jae` (EE `0x500996`) -> Objekt wird uebersprungen. Reihenfolge = Kachelzeilen,
  deshalb fehlen die Objekte der letzten Zeilen (kameraabhaengig). Leichen und Geschosse belegen ebenfalls Plaetze -
  daher die Verzoegerung nach einem Gefecht und die Grenze deutlich unter 512 lebenden Einheiten.
- Nicht schuld: dgVoodoo, Vertex-Puffer, Fog-Zaehler. dreXmod patcht im Speicher 115 Stellen, keine davon in diesem Code.

### Fix: `unitcap/ee_unitcap.py` (EE + AoC per Signatur, `status | plan | install | uninstall --exe`)
- Beide Tabellen ziehen in neuen, genullten Speicher hinter der letzten Sektion (`.neoee`: nur VirtualSize und
  SizeOfImage wachsen, +1792 KB Adressraum, Dateigroesse gleich). Neu: 4096 / 8192 Eintraege, Picking-Tabelle 12288.
- 21 Aenderungen je EXE: Konstruktor-/Destruktor-Schleifen des globalen Objekts, Init-Schleife, 12 absolute Verweise,
  4 Limit-Konstanten, Kapazitaet der Picking-Tabelle, 2 Header-Felder. Jeder Verweis muss eine bekannte Befehlsform
  haben und in erwarteter Anzahl vorkommen, sonst Abbruch.
- Ziel standardmaessig nur die Cheat-EXE; Original-EXE nur mit `--exe` bzw. `ee_fixes.py ... --original-exe`.

### Gemessen (Sandbox, 2560x1440, dgVoodoo, 8x AA)
| | ohne Patch | mit Patch |
|---|---|---|
| EE, 770 Einheiten, die meisten im Bild | 512 gezeichnet, ~100 fps | 801 gezeichnet |
| EE, ~650-670 im Bild | - | 100 fps |
| EE, ~865 im Bild | 512 | 864 gezeichnet, 77 fps |
| EE, ~2000 im Bild (3021 gesamt) | 512 | 2035 gezeichnet, 24 fps, stabil |
| AoC, 600 Doughboys | - | 611 gezeichnet, 92 fps |
Bildrate faellt linear mit der Zahl der Zeichenaufrufe (ca. 20 us je Einheit inkl. Schatten); minimiert 610 Durchlaeufe/s
bei 1830 Tabelleneintraegen - die Tabellenlogik selbst kostet also < 2 ms.
Deinstallation stellt die EXE byte-genau wieder her (md5). Beenden per Fenster-Schliessen: Exit-Code 0 mit und ohne Patch
(Menue, Partie, AoC mit 600 Einheiten).

### Cheat: Spawn-Positionen korrigiert (`ee_cheat.py`)
Zwei eigene Fehler, die wie "Einheiten fehlen" aussahen:
- Alle Einheiten eines Aufrufs lagen auf einem festen 5er-Raster am Kamerapunkt -> wiederholte Aufrufe ohne
  Kamerabewegung stapelten Einheiten deckungsgleich (gemessen: 2994 Doughboys auf 2158 Positionen, Stapel bis 44).
- Der benutzte Kamerapunkt (Kameraobjekt +0x40/+0x44) ist bis zur ersten Kamerabewegung (0,0) -> Einheiten landeten
  in der Kartenecke. Gueltig ab Spielstart ist die zweite Kopie +0x78/+0x7C.
Jetzt: jede Einheit bekommt einen Zufallsplatz (rdtsc-Startwert, LCG) in einem Quadrat der Seite n/4+3 Kacheln um
+0x78/+0x7C, `fabs` haelt sie rechts/unterhalb des Kartenursprungs. Test EE: 850 Doughboys direkt nach Spielstart,
850 verschiedene Positionen, Feld 29-44 x 32-47 um das Kapitol. AoC: 600 / 600 verschiedene.

### Paket zum Weitergeben
- `ee_fixes.py` = ein Installer mit einzeln waehlbaren Bausteinen `crash net fog aocstart cheats units fps`
  (`list | status | install | uninstall | menu`, `--ee/--aoc`, `--only`, `--original-exe`, `--no-shortcut`);
  `install_ee_fixes.cmd` ist nur noch die UAC-Huelle (ohne Argument: alles, wie bisher).
- `make_release.py` baut `release/EE-AoC-Fixes-<Datum>.zip` (14 Dateien, 139 KB, nur Patcher + eigene `ee_fps.dll`
  + `LIESMICH.md`, prueft auf private Pfade). Braucht nur Python 3.8+.
- `aoc_dbshadow.py` braucht `libDCL.dll` (EEStudio, Fremdcode) nicht mehr: `ssa_unpack.explode()` ist ein
  Python-Entpacker (PKWARE DCL, Verfahren wie blast.c), gegen libDCL auf 176 Archiveintraegen identisch.
- Ende-zu-Ende-Test des entpackten Pakets auf unveraenderten Dateien (EXE, Engine-DLL, TCP-DLL beider Spiele):
  Installation ergibt dieselben md5 wie die getesteten Sandbox-Staende; Deinstallation stellt alle sechs Dateien
  byte-genau wieder her. Fog-Fix laesst sich damit auch auf einer unveraenderten EE-Engine an Ort und Stelle setzen.

### Neue Werkzeuge
`cheat/shot.py` (Screenshot per PrintWindow ohne Fokus), `cheat/drawprobe.js`, `cheat/unitdraw.js`, `cheat/fpsmon.js`
(Bildrate + Tabellenfuellstand, ein Hook pro Bild), `cheat/posstat.js` (Stapel/Positionen), `cheat/disva.py`,
`cheat/xref.py`, `cheat/absrefs.py`, `cheat/immscan.py` (Disassembler/Verweissuche per VA), `cheat/memdiff.py`
(Laufzeit-Patches von dreXmod finden), `cheat/exit_test.py`, `cheat/closegame.py`, `cheat/gamevars.py`.
Falle: eine Datei `dis.py` im Skriptordner ueberdeckt das gleichnamige Standardmodul und bricht `capstone`.

### Nachtrag zu den offenen Punkten
| # | Thema | Befund | Stand |
|---|---|---|---|
| 5 | Viele Einheiten im Bild | Ursache gefunden und behoben (siehe oben) | erledigt in der Sandbox; echte Installation per `install_ee_fixes.cmd` |
| 9 | Exit-Code `0xC0000005` beim Schliessen einer Partie mit >= 2000 Einheiten | tritt mit und ohne Einheiten-Patch auf (A/B), kein WER-Dump, kein von Frida gesehener Zugriffsfehler -> passiert im Prozessabbau (statische Destruktoren / DLL-Detach). Fuer den Spieler ohne sichtbare Folge | nicht weiter untersucht; koennte mit #1 verwandt sein |
| 10 | Bildrate bei > 1500 Einheiten im Bild | 24 fps bei 2000; Zeit steckt in den Zeichenaufrufen (dgVoodoo/D3D11), nicht in der Spiel-Logik | offen (Ansatz: Schatten/LOD bei grosser Zahl reduzieren) |
| 11 | Zweite Instanz | AoC startet nicht, solange EE laeuft (beendet sich ohne Meldung) - beim Testen nur ein Spiel gleichzeitig | Hinweis |
| 12 | Einheiten-Limit im Originalspiel | Patch liegt nur in der Cheat-EXE; fuer `Empire Earth.exe`/`EE-AOC.exe` `--original-exe`. Wirkung auf NeoEE-Online-Spiele ungetestet | Entscheidung beim Nutzer |

---

## Fix Pack als GUI-EXE zum Weitergeben (21.11.2026, abends)

Vorgabe: Empfaenger sind keine Entwickler -> eine englische GUI als einzelne EXE, Spielordner automatisch finden
(aenderbar), Haekchen je Fix und Spiel, Infotexte, Deinstallation in derselben Oberflaeche. Upload auf die Mod-Seite
macht der Nutzer selbst.

### Ergebnis
- `release/EE-FixPack.exe` (10,5 MB, PyInstaller one-file, tkinter, kein Python noetig) + `release/EE-FixPack-README.txt`
  (englischer Text fuer die Mod-Seite). Quelle: `fixpack/ee_fixpack.py`, Bau: `python fixpack/build_exe.py`.
- Ordnersuche: `HKCU\Software\Neo\<Spiel>` ("Installed From Volume/Directory", schreibt das Spiel selbst), Inno-Setup-
  Eintrag von NeoEE (`...\Uninstall\{A24FCC7A-...}_is1`, InstallLocation), AppCompat-Layers (voller EXE-Pfad),
  uebliche Ordner, Nachbarordner; sonst "Browse...".
- 8 Zeilen x 2 Spiele: `crash`, `net`, `fog`, `aocstart` (nur AoC, nur wenn noetig), `cheats`, `units_cheat`,
  `units_orig` (Original-EXE, mit Hinweis "nicht online getestet"), `fps` (nur EE, als unfertiges Experiment
  gekennzeichnet). Zustand je Zelle wird aus den Dateien gelesen: installed / not installed / update available /
  already fixed / not supported / not needed. Haekchen = Sollzustand, "Apply changes" entfernt zuerst (umgekehrte
  Reihenfolge), installiert dann. "Remove all fixes...", "Select recommended" (crash, net, fog, aocstart), "Info"
  je Zeile + Tooltip, "Source code..." (gebuendeltes Quell-ZIP inkl. `ee_fps.cpp`), "Open backup folder".
- Backups der GUI: `C:\ProgramData\EE-FixPack\backups` (die Patcher-Module bekommen ihr `BACKUP_ROOT` gesetzt).
- Adminrechte: Start ohne Schreibrecht -> Neustart per `ShellExecuteW runas` (UAC), alle Argumente werden durchgereicht.
- Befehlszeile fuer Tests/unbeaufsichtigt: `--ee --aoc --select all|none|recommended|crash,net:ee,... --apply
  --report datei.json --exit --no-elevate --no-shortcuts`.
- Cheat-EXE wird immer aus den unveraenderten Bytes des Originals gebaut (auch wenn `units_orig` installiert ist) -
  dadurch sind die Zustaende der Cheat-EXE unabhaengig vom Original.

### Ego-Modus
Laut Nutzer unfertig und wird nicht weiterentwickelt -> in GUI, Readme, ini und Quell-README so gekennzeichnet,
Quelltext liegt bei. `ee_fps.dll` neu gebaut (md5 77FA843C...): Meldungen zweisprachig, `[Steuerung] Sprache=en`
schaltet auf Englisch (Standard ohne Schluessel: Deutsch, vorhandene ini bleibt also deutsch). Neue
`fps/ee_fps.en.ini` (englische Kommentare, Schluesselnamen bleiben deutsch, weil die DLL sie so liest).
Vorheriger Build: `fps/ee_fps.dll.bak-20261121`.

### Tests (alle auf Kopien, echte Installation unveraendert)
- Unveraenderte Kopie beider Spiele: "alles installieren" per Skript und per EXE -> 14/14 Zellen `on`, md5 wie die
  in der Sandbox gespielten Staende; Teil-Deinstallationen in verschiedener Reihenfolge; "alles entfernen" ->
  alle Dateien byte-gleich zum Ausgangszustand, keine Reste.
- Aelterer Cheat-EXE-Build + aeltere `ee_fps.dll` -> "update available", werden ersetzt, vorhandene ini bleibt.
- Fremde DLL als `TCP Protocol.dll` -> "not supported", unangetastet. Ordner ohne Schreibrecht -> Meldung, nichts geaendert.
- `units_orig` in der Sandbox: Original-`Empire Earth.exe` startet, Zufallskarte, Limits 4096/8192 im Speicher,
  Exit-Code 0, Entfernen stellt md5 D531B5F8... wieder her.
- Neue `ee_fps.dll` in der Sandbox: geladen (`fps_state` ok), Umschalten ohne gewaehlte Einheit ohne Absturz.
- `fixpack/scan_exe.py`: 1089 gepackte Elemente der EXE (inkl. komprimierter Module) ohne private Zeichenketten.

### Gefundene Fallen
- **PyInstaller one-file startet sich selbst neu** (UAC-Neustart): die neue Instanz erbt `_PYI_*`-Variablen und
  benutzt das Entpackverzeichnis der alten, das diese beim Beenden loescht -> Dateien fehlen (hier: `ee_fps.dll`
  "not supported"). Abhilfe: vor `ShellExecuteW` `PYINSTALLER_RESET_ENVIRONMENT=1` setzen und `_PYI_*` loeschen.
- "Schreibrecht pruefen" per `CreateFile(..., FILE_FLAG_BACKUP_SEMANTICS)` meldet in einer erhoehten Sitzung auch
  gesperrte Ordner als schreibbar -> wieder echte Probe (leere Datei anlegen und loeschen).
- Unbeaufsichtigter Lauf darf keine modalen Meldungsfenster oeffnen (haengt) -> mit `--exit` gehen Meldungen ins Log.
- Beim Aufraeumen eines haengenden Testfensters habe ich Prozesse ueber ein Kommandozeilen-Muster gesucht und damit
  auch sechs eigene `bash.exe`-Huellen beendet. Regel bleibt: nur die PID des selbst gestarteten Prozesses (`Popen.pid`).

### Stand echte Installation (nur gelesen)
crash EE: installiert | fog EE: bereits behoben (Cave-Variante) | cheats EE + fps EE: "update available" (alter Build)
| alles andere inkl. ganz AoC: nicht installiert | aocstart: noetig (`dbtechtree.dat`).

---

## Fix Pack 1.0: dgVoodoo-Eintrag, Standardformation, Repository (21.11.2026, spaet)

### dgVoodoo (`dgvoodoo`, je Spiel)
- NeoEE-Original (`dgVoodoo.conf` 2.82): `VRAM = 256`, `Resolution = unforced`, kein Antialiasing/Filtering,
  `AppControlledScreenMode = true`, Fenster mit `AlwaysOnTop`.
- **Korrektur zum 09.10.:** `Filtering = forceanisotropic` ist kein gueltiger Wert. Laut der in `dgVoodooCpl.exe`
  eingebetteten Vorlage: `appdriven | pointsampled | bilinear | pointmip | linearmip | trilinear` oder die Stufe
  `1-16`. Richtig ist `Filtering = 16`. Sandbox, selber Spielstand: Schaerfemass der fernen Bodentextur
  3708 -> 7068 (Kamera stand nicht exakt gleich, Unterschied im Bild aber deutlich; `cheat/shots/filter_compare.png`).
- **TODO #4 erledigt (VRAM):** `DX7Rasterizer::GetTotalVideoMemory` liefert dem Spiel bei `VRAM = 256 ... 8192`
  immer 256 MB gesamt / 223 MB frei (`cheat/vram_test.py`). Der Wert ist fuer das Spiel wirkungslos - weder das
  am 09.10. vermutete "Texture-Thrashing" noch der negative Wert bei 8192 treffen zu. Der Eintrag laesst VRAM in Ruhe.
- Der Eintrag setzt nur, was noch nicht passt: `Resolution = desktop` (nur wenn `unforced`), `Antialiasing = 8x`
  (4x/8x/16x gelten als ok), `Filtering = 16` (8-16 ok), `AppControlledScreenMode = false`, `WindowedAttributes`
  ohne `AlwaysOnTop`. Nur der Wert einer Zeile aendert sich (Abstaende und gemischte Zeilenenden bleiben);
  alte Werte in `dgVoodoo.conf.fixpack.json`, Entfernen stellt die Datei byte-genau wieder her.

### Standardformation "Lange Reihe" (`formation/ee_formation.py`, Zusatz zur Cheat-EXE)
- Formationsart = Argument der Fabrik `0x4D7CFC` (0 kurze, 1 lange, 2 lockere, 3 versetzte Reihe, 4/5 Keil, 6/7 Kreis);
  `EEMChangeFormation::Execute` (`0x4B49BC`) erzeugt das Objekt und setzt es in `[Spieler+0x9BC]` (EEGroup) und dessen
  Untergruppe. Standard: `EEGroup`-Konstruktor `push 0 / call 0x4D7CFC` (`0x5F61F0`).
- Den Konstruktor zu aendern traefe alle Spieler (auch Computer) und liefe im Netzwerkspiel auseinander. Deshalb:
  am Ende beider `EEHumanPlayer`-Konstruktoren (`0x4A017F`, `0x4A01D0`) fuehrt ein Cave genau das aus, was der Knopf
  tut (Art 1) - nur wenn `[[0x91984C]+0x2E] == 0` (Einzelspieler). AoC: Gruppe `+0x9AC`, Fabrik `0x4DDCC6`.
- Sandbox (EE + AoC, neue Zufallskarte): Mensch `EEFLongLine`, Computer `EEFShortLine`, Exit-Code 0.
  Geladene Spielstaende behalten die gespeicherte Formation (alte Staende also "Kurze Reihe") - so beabsichtigt.
- GUI: Cheat-EXE gibt es jetzt in vier festen Staenden (Formation x Einheiten-Limit); Zustand = Bytevergleich.

### GUI / Paket
- 10 Zeilen (neu `dgvoodoo`, `formation`), Kopfzeile mit Link `github.com/Marabunta159/empire-earth-fixpack`
  (Wunsch des Nutzers), auf kleinen Bildschirmen automatisch einzeilige Darstellung (`--compact`).
- `release/EE-FixPack.exe` (md5 A6F78E8B...), Volltest auf unveraenderten Kopien: 18/18 Zellen installiert,
  danach alles byte-gleich zum Ausgangszustand.

### Repository
- `make_repo.py` baut `..\empire-earth-fixpack` (138 Dateien: Quellen, Readme, Journal ohne private Pfade und ohne
  Notizen zum Rechner, Entwicklerhelfer unter `dev/`, Samurai-Mod; keine Spieldateien). Lokal ein Commit, Autor
  `Marabunta159 <...@users.noreply.github.com>`.
- **Noch nicht auf GitHub:** das gespeicherte `gh`-Token fuer Marabunta159 ist ungueltig -> `gh auth login`.
- Offen: Lizenzdatei (Entscheidung des Nutzers), Release mit der EXE.

### Veroeffentlicht (21.11.2026)
- `github.com/Marabunta159/empire-earth-fixpack` (oeffentlich), Release `v1.0` mit `EE-FixPack.exe` + Readme.

### Korrektur Standardformation (22.11.2026)
- Nutzer: neue AoC-Zufallskarte startete trotzdem mit "Kurze Reihe". Live gelesen: interne Gruppe `+0x9BC` (AoC `+0x9AC`) = LongLine, aber die Gruppe der Oberflaeche `+0x9C0` (AoC `+0x9B0`, die setzt der Formationsknopf direkt) = ShortLine. Mein Sandbox-Test hatte nur die erste geprueft.
- `ee_formation.py` v2 (Marker `EEFORM2`): setzt zusaetzlich die Oberflaechen-Gruppe; Offset per Signatur aus dem Knopf-Handler. Sandbox EE + AoC: Mensch intern + Oberflaeche LongLine, Computer ShortLine.
- GUI erkennt Cheat-EXEs der Vorversion (Marker / Patch-Record) als "update available" und baut sie mit denselben Zusaetzen neu. EXE im Release v1.0 ersetzt.

### Standardformation v3 + Update-Pruefung (22.11.2026, nachmittags)
- Nutzer: Anzeige "Lange Reihe", die Einheiten bilden trotzdem die kurze Reihe. Laufendes Spiel nur gelesen
  (`cheat/peek_form.py <pid> ee|aoc`, ReadProcessMemory, keine Injektion): Spieler 0 intern ShortLine / Oberflaeche
  LongLine, alle 20 Hotkey-Gruppen ShortLine, die aeltesten `EEActiveGroup` (= laufende Bewegungen, Vektor
  `Spieler+0x844`) ShortLine, die neueren LongLine. In der Sandbox (neue Zufallskarte) sind dagegen beide Gruppen
  LongLine -> das Spiel des Nutzers war geladen (`Start.ees` / AutoSave im Spielordner).
- Ursache: `EEGroup::Read` (EE `0x5F667D`, AoC Aufruf bei `0x606516`) liest beim Laden die Formationsart und ersetzt
  die Formation der Befehlsgruppe; die Oberflaechen-Gruppe steht nicht im Spielstand und behielt den Wert des
  Konstruktor-Hooks. Bewegungen nehmen die Formation der Befehlsgruppe `+0x9BC` (Handler `0x4B3958` ->
  `0x5DD18B` kopiert sie in die neue `EEActiveGroup`).
- Aufbau: je Spieler 3 x `EESelectedGroup` (`+0x9BC` Befehle, `+0x9C0` Oberflaeche, `+0x9C4` ungenutzt) und
  20 Hotkey-Gruppen (`+0x964`, AoC `+0x954`). Hotkey abrufen = `Befehlsgruppe.CopyFrom(Hotkey-Gruppe)` inkl.
  Formation (`0x5F93B0`) - eine nie belegte Zifferntaste setzte also "Kurze Reihe".
  Linienformationen: Basis `0x4D78E8(Art, Abstand, Abstand, Spalten, Reihen)`, kurz = 5 Spalten, lang = 10.
- `ee_formation.py` v3 (Marker `EEFORM3`): Konstruktor-Hook setzt alle 23 Gruppen; neuer Hook in `EEGroup::Read`
  (statt `call CreateFormation`): Einzelspieler + Gruppe eines `EEHumanPlayer` -> Art 0 wird 1, andere Arten bleiben,
  und die Oberflaechen-Gruppe bekommt die geladene Formation (das Original zeigt nach dem Laden immer "Kurze Reihe").
- GUI 1.1: fragt beim Start `api.github.com/.../releases/latest` (nur Tag, Hintergrund-Thread, 6 s) und zeigt eine
  orange Zeile mit Link zur Download-Seite; `--no-update-check`, unbeaufsichtigte Laeufe (`--exit`) fragen nie.
- Sandbox-Test v3 (`python fixpack/sandbox_new_test.py formation3`, Zustand per `peek_form.py`), EE und AoC:
  neue Zufallskarte -> alle 23 Gruppen der Menschen LongLine, 0 Aufrufe von `EEGroup::Read`; Formationsknopf 3108
  -> Befehls- und Oberflaechen-Gruppe ShortLine und bleiben es (waehrend des Spiels wird `Read` nie aufgerufen);
  Spielstand laden -> 147 `Read`-Aufrufe, Menschen LongLine, Computer unveraendert ShortLine, Exit-Code 0.
  Mit per Frida vorgetaeuschter Art 3 im Spielstand: Befehls- und Oberflaechen-Gruppe beide StaggeredLine.
  AoC-Ladebildschirm: Liste `394` hat keine Vorauswahl -> `cheat/listsel.js {"id":394,"index":0}`, dann Knopf 393.
- Update-Zeile in der gebauten EXE geprueft (`--pretend-version 0.9` -> "Version 1.0 is available").
- Veroeffentlicht als Version 1.1: Commit + `git push`, Release `v1.1` (eigenes Tag, damit die Update-Pruefung es meldet).
