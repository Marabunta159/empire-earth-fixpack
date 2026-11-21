# Empire Earth / Art of Conquest (NeoEE) - Fix-Paket

Ein Installer, sieben einzeln waehlbare Bausteine. Gepatcht wird die eigene Installation; Spieldateien sind
nicht enthalten. Jeder Baustein prueft seine Zieldatei per Signatur (passt sie nicht, wird nichts veraendert),
legt ein Backup unter `backups\` an und laesst sich einzeln wieder entfernen.

*English summary: seven independent fixes for the NeoEE build of Empire Earth / The Art of Conquest. Run
`install_ee_fixes.cmd` (all), `install_ee_fixes.cmd menu` (pick), `install_ee_fixes.cmd uninstall`. Needs
Python 3.8+. The original game executables are not modified.*

## Voraussetzungen

- Windows, NeoEE-Installation von Empire Earth und/oder The Art of Conquest
- Python 3.8 oder neuer (python.org, Haken bei "Add to PATH"); keine weiteren Pakete
- Paket in einen normalen Ordner entpacken (nicht nach `Program Files`)

## Benutzung

| Aufruf | Wirkung |
|---|---|
| `install_ee_fixes.cmd` | alle Bausteine fuer beide Spiele (fragt per UAC nach Adminrechten) |
| `install_ee_fixes.cmd menu` | Bausteine per Nummer waehlen |
| `install_ee_fixes.cmd install units net` | nur die genannten Bausteine |
| `install_ee_fixes.cmd status` | was ist installiert |
| `install_ee_fixes.cmd uninstall` | alles entfernen (oder: `uninstall units`) |
| `install_ee_fixes.cmd noaoc` | alles, aber nur Empire Earth |

Liegt das Spiel woanders als unter `C:\Program Files (x86)\Neo Empire Earth`:
`install_ee_fixes.cmd install --ee "<Ordner mit Empire Earth.exe>" --aoc "<Ordner mit EE-AOC.exe>"`

Vor dem Start das Spiel beenden.

## Bausteine

| Name | Behebt | Geaenderte Datei |
|---|---|---|
| `crash` | Absturz beim zweiten Laden einer Karte, eines Spielstands oder einer Kampagne ("alles geht nur einmal") | `Low-Level Engine.dll` |
| `net` | NeoEE-Netzwerktest (Port-Check, UPnP) bei Zufallskarte / Spiel laden im Einzelspieler; Multiplayer-Hosting unveraendert | `TCP Protocol.dll` |
| `fog` | Fog-of-War-Zaehler laeuft nicht mehr unter null (Einheiten flackern im Schatten) | `Low-Level Engine.dll` |
| `aocstart` | AoC bricht beim Start ab (`Empire Earth.cpp (989)`), wenn eine EE-Mod lose `data\db\*.dat` mitbringt | Kopien in `AoC\Data\db\` |
| `cheats` | zweite EXE: eingebaute Cheats auch in Kampagnen (nur Einzelspieler), neu `buerger [1-50]`, `doughboys [1-50]` | `EE-Cheats.exe`, `EE-AOC-Cheats.exe` (neu) |
| `units` | Einheiten verschwinden, sobald mehr als 512 Objekte im Bild sind: Limit 512 -> 4096 (einfache Objekte 1536 -> 8192) | Cheat-EXE |
| `fps` | Ego-Shooter-Modus fuer Empire Earth (eigene Fernkampf-Einheit waehlen, Taste `^`) | `ee_fps.dll`, `ee_fps.ini` |

Abhaengigkeiten: `units` und `fps` wirken in der Cheat-EXE und brauchen deshalb `cheats`. Alle anderen sind
unabhaengig.

## Hinweise

- **Originalspiel:** `Empire Earth.exe` und `EE-AOC.exe` bleiben unveraendert. Die DLL-Fixes (`crash`, `net`,
  `fog`) gelten fuer beide EXEs, `cheats` / `units` / `fps` nur fuer die Cheat-EXE (Desktop-Verknuepfung
  "Empire Earth (Cheats)" bzw. "Empire Earth AoC (Cheats)").
  Wer das hoehere Einheiten-Limit auch im Originalspiel will: `install_ee_fixes.cmd install units --original-exe`
  (auf eigenes Risiko, mit NeoEE-Online-Spielen nicht getestet).
- **Mehrspieler:** Die Cheats sind im Netzwerkspiel abgeschaltet. `units` aendert nur die Anzeige, nicht die
  Simulation.
- **Nach einer neuen EE-Mod** mit losen `data\db`-Dateien: `install_ee_fixes.cmd install aocstart` erneut.
- **Nach einem NeoEE-Update:** `install_ee_fixes.cmd` erneut starten (geaenderte Dateien werden neu gepatcht,
  unbekannte Versionen bleiben unangetastet).
- **Bildrate mit sehr vielen Einheiten:** Das Zeichnen kostet pro Einheit Zeit. Gemessen (2560x1440, dgVoodoo):
  rund 650 Einheiten im Bild 100 fps, 860 Einheiten 77 fps, 2000 Einheiten 24 fps.

## Getestet mit

| Datei | MD5 |
|---|---|
| `Empire Earth.exe` (NeoEE) | `D531B5F8E6A66DB640DD5CCCFD0B3CA6` |
| `EE-AOC.exe` (NeoEE) | `6385D59E4B7C2BA9FD0BB30F15CB86F0` |

Andere Versionen: Die Patcher suchen ihre Stellen per Signatur. Finden sie sie nicht eindeutig, melden sie
das und aendern nichts.

## Einzelne Werkzeuge

Jeder Baustein ist auch direkt aufrufbar (`status | plan | install | uninstall`, Hilfe mit `-h`):
`crashfix\ssa_mapfix.py`, `net\sp_nonet.py`, `fogfix\fog_refcount.py`, `aoc\aoc_dbshadow.py`,
`cheat\ee_cheat.py`, `unitcap\ee_unitcap.py`. Der Quelltext des Ego-Modus liegt unter `fps\src\`.
