#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Samurai for Empire Earth (base) — installer/uninstaller.

The Samurai is AOC's Japan-unique infantry unit. Base Empire Earth already
ships its whole payload (object 438, tech 6100, button 922, graphic 639,
model models/men_samurai_06.cem, textures, dv0sam*.wav voices, Language.dll
slot 2066) as disabled cut content. The only thing keeping it out of normal
gameplay is tech 6100's "Only in scenario" flag.

This script writes a loose override <game>/data/db/dbtechtree.dat with tech
6100 changed to be buildable everywhere:
    Starting epoch   5 -> 0
    Ending epoch     6 -> 14
    Only in scenario 1 -> 0

Loose files in data/db/ win over the same path inside data.ssa — that is how
NeoEE/dreXmod already ship 4 other overridden db files.

Usage:
  python samurai_mod.py install --game "C:\\...\\Empire Earth" [--from-scratch]
  python samurai_mod.py status   --game "C:\\...\\Empire Earth"
  python samurai_mod.py uninstall --game "C:\\...\\Empire Earth"

--from-scratch rebuilds dbtechtree.dat from data.ssa instead of patching the
existing loose file (needed on a vanilla install that has no loose override).

No game data is redistributed by this script: it only pokes 9 bytes in a file
the user already owns.
"""
import argparse
import hashlib
import os
import struct
import sys

TECH_ID = 6100
TECH_NAME = b"xSP06 Samurai"

# Vanilla Empire Earth dbtechtree.dat record layout (46 fields, 268 bytes fixed)
# plus a trailing u32[num_tech_builders] array. Verified against the DB Editor
# schema (Forlini91/Empire-Earth---DB-Editor, EEEditorData/Vanilla/dbtechtree.dats).
REC_FIXED = 268
OFF_NAME = 0
OFF_ID = 104
OFF_START_EP = 108
OFF_END_EP = 112
OFF_ONLY_SCEN = 245   # 1-byte BOOLEAN field 38
OFF_NUM_BUILDERS = 264
PATCHES = {
    OFF_START_EP: (0, "<i", "Starting epoch"),
    OFF_END_EP: (14, "<i", "Ending epoch"),
    OFF_ONLY_SCEN: (0, "<B", "Only in scenario"),
}


def walk_techs(buf: bytes):
    """Yield (record_offset, record_size, name, tech_id, start, end, only_scen)."""
    pos = 0
    n = len(buf)
    while pos + 4 <= n:
        (count,) = struct.unpack_from("<I", buf, pos)
        pos += 4
        entries = count + 1          # the game's counter skips the Epoch entry
        for _ in range(entries):
            if pos + REC_FIXED > n:
                raise ValueError("truncated dbtechtree.dat record table")
            name = bytes(buf[pos:OFF_NAME + 100]).split(b"\x00")[0]
            name = bytes(buf[pos + OFF_NAME:pos + OFF_NAME + 100]).split(b"\x00")[0]
            (tid,) = struct.unpack_from("<i", buf, pos + OFF_ID)
            (start,) = struct.unpack_from("<i", buf, pos + OFF_START_EP)
            (end,) = struct.unpack_from("<i", buf, pos + OFF_END_EP)
            only = buf[pos + OFF_ONLY_SCEN]
            (nb,) = struct.unpack_from("<I", buf, pos + OFF_NUM_BUILDERS)
            size = REC_FIXED + 4 * nb
            yield pos, size, name, tid, start, end, only
            pos += size


def find_tech(buf: bytes, tech_id: int):
    for rec in walk_techs(buf):
        if rec[3] == tech_id:
            return rec
    return None


def read_ssa_member(ssa_path: str, member: str) -> bytes:
    """Minimal Stainless Steel Archive (magic 'rass') reader. See EE-modders wiki."""
    data = open(ssa_path, "rb").read()
    if data[:4] != b"rass":
        raise ValueError("not an SSA archive")
    (dso,) = struct.unpack_from("<I", data, 12)
    pos = 16
    entries = []
    while pos < 16 + dso:
        (plen,) = struct.unpack_from("<I", data, pos)
        pos += 4
        path = data[pos:pos + plen].rstrip(b"\x00").decode("latin-1")
        pos += plen
        start, end, size = struct.unpack_from("<III", data, pos)
        pos += 12
        entries.append((path.replace("\\", "/").lower(), start, size))
    for path, start, size in entries:
        if path == member.lower():
            blob = data[start:start + size]
            if blob[:4] == b"PK01":
                return dcl_decompress(blob)
            return blob
    raise KeyError(f"{member} not in {ssa_path}")


def dcl_decompress(blob: bytes) -> bytes:
    """PKWARE DCL ('PK01') via libDCL.dll from Empire Earth Studio II (EE-modders)."""
    import ctypes
    (unc_size,) = struct.unpack_from("<I", blob, 4)
    payload = blob[12:]
    dll = os.environ.get("LIBDCL") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "libDCL.dll")
    if not os.path.isfile(dll):
        raise FileNotFoundError(
            "libDCL.dll not found. Set LIBDCL=<path to libDCL.dll> (ships with "
            "Empire Earth Studio II: github.com/EE-modders/Empire-Earth-Studio-2)")
    lib = ctypes.CDLL(dll)
    lib.decompressBytes.argtypes = [ctypes.c_char_p, ctypes.c_int,
                                    ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
    lib.decompressBytes.restype = ctypes.c_int
    out = ctypes.create_string_buffer(unc_size)
    out_len = ctypes.c_int(0)
    ret = lib.decompressBytes(payload, len(payload), out, ctypes.byref(out_len))
    if ret != 0:
        raise RuntimeError(f"DCL decompress failed with code {ret}")
    return out.raw[:unc_size]


def status(game: str) -> int:
    loose = os.path.join(game, "data", "db", "dbtechtree.dat")
    if not os.path.isfile(loose):
        print("status: UNMODIFIED (no loose data/db/dbtechtree.dat)")
        return 1
    buf = open(loose, "rb").read()
    rec = find_tech(buf, TECH_ID)
    if rec is None:
        print("status: BROKEN (tech 6100 missing)")
        return 2
    off, size, name, tid, start, end, only = rec
    ok = (start == 0 and end == 14 and only == 0 and name == TECH_NAME)
    print(f"status: {'INSTALLED' if ok else 'PARTIAL'}  "
          f"tech {tid} {name!r} start={start} end={end} onlyScen={only}")
    return 0 if ok else 3


def install(game: str, from_scratch: bool) -> int:
    game = os.path.abspath(game)
    loose = os.path.join(game, "data", "db", "dbtechtree.dat")
    if from_scratch or not os.path.isfile(loose):
        ssa = os.path.join(game, "data", "data.ssa")
        print(f"reading db/dbtechtree.dat from {ssa}")
        buf = bytearray(read_ssa_member(ssa, "db/dbtechtree.dat"))
    else:
        print(f"patching existing {loose}")
        buf = bytearray(open(loose, "rb").read())

    rec = find_tech(bytes(buf), TECH_ID)
    if rec is None:
        print("ERROR: tech 6100 (xSP06 Samurai) not found — wrong game version?")
        return 2
    off, size, name, tid, start, end, only = rec
    if name != TECH_NAME:
        print(f"ERROR: tech 6100 is {name!r}, expected {TECH_NAME!r}")
        return 2
    print(f"  record @{off} ({size} B) {name!r}")
    for rel, (value, fmt, label) in PATCHES.items():
        cur = buf[off + rel]
        if fmt == "<i":
            (cur,) = struct.unpack_from("<i", buf, off + rel)
        mark = "unchanged" if cur == value else f"{cur} -> {value}"
        print(f"  {label:22s} {mark}")
        struct.pack_into(fmt, buf, off + rel, value)

    os.makedirs(os.path.dirname(loose), exist_ok=True)
    open(loose, "wb").write(buf)
    print(f"wrote {loose}  md5 {hashlib.md5(buf).hexdigest()}")
    return status(game)


def uninstall(game: str) -> int:
    loose = os.path.join(game, "data", "db", "dbtechtree.dat")
    if not os.path.isfile(loose):
        print("nothing to do (no loose override)")
        return 0
    buf = open(loose, "rb").read()
    rec = find_tech(buf, TECH_ID)
    if rec is None or rec[3] != TECH_ID or rec[2] != TECH_NAME:
        print("refusing to delete: file does not look like the Samurai override")
        return 2
    if not (rec[4] == 0 and rec[5] == 14 and rec[6] == 0):
        print("refusing to delete: tech 6100 is not in the patched state")
        return 2
    bak = loose + ".samurai-removed"
    os.replace(loose, bak)
    print(f"removed override (kept a copy at {bak})")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("install", "status", "uninstall"):
        p = sub.add_parser(name)
        p.add_argument("--game", required=True, help="Empire Earth install dir (base game, not AoC)")
        if name == "install":
            p.add_argument("--from-scratch", action="store_true",
                           help="rebuild dbtechtree.dat from data.ssa instead of patching the loose file")
    a = ap.parse_args()
    if a.cmd == "install":
        sys.exit(install(a.game, a.from_scratch))
    if a.cmd == "status":
        sys.exit(status(a.game))
    sys.exit(uninstall(a.game))


if __name__ == "__main__":
    main()
