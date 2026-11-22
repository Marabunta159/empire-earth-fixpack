#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema-driven parser for Empire Earth / Art of Conquest .dat DB files.
Schemas: EEEditorData/{Vanilla,AOC}/<file>dats (tab-separated field definitions).

Usage:
  python dat_dump.py <schema_dir> <file.dat> [--search NAME] [--json out.json] [--entry N]

Format (per DatFileManager.java, Forlini91 DB Editor):
  - group: if defineNumEntries: u32 numEntries (+adjustNumEntries), then N entries
  - entry: fields per FieldStruct; STRING size bytes; DYNAMIC_STRING size from
           field[indexSize]; FLOAT 4 bytes; else 1 or 4 byte int
  - extra fields: if indexExtraFields>=0: u32 numExtra = values[indexExtraFields],
           then numExtra u32 (links)
"""
import os
import sys
import struct
import json
import re

# per-file metadata: defineNumEntries, adjustNumEntries, indexExtraFields_mode
# mode: None (none), "last" (fieldStructs.length-1)
FILE_META = {
    "dbobjects.dat":        {"count": True,  "adjust": 0, "extra": None},
    "dbtechtree.dat":       {"count": True,  "adjust": 1, "extra": "last"},
    "dbeffects.dat":        {"count": False, "adjust": 0, "extra": None},
    "dbevents.dat":         {"count": False, "adjust": 0, "extra": "last"},
    "dbbuttons.dat":        {"count": True,  "adjust": 0, "extra": None},
    "dbgraphics.dat":       {"count": True,  "adjust": 0, "extra": None},
    "dbsounds.dat":         {"count": True,  "adjust": 0, "extra": None},
    "dbupgrade.dat":        {"count": True,  "adjust": 0, "extra": None},
    "dbfamily.dat":         {"count": True,  "adjust": 0, "extra": None},
    "dbgfxeffects.dat":     {"count": True,  "adjust": 0, "extra": None},
    "dbcivilization.dat":   {"count": True,  "adjust": 0, "extra": None},
    "dbunitset.dat":        {"count": True,  "adjust": 0, "extra": None},
    "dbareaeffect.dat":     {"count": True,  "adjust": 0, "extra": None},
    "dbcalamity.dat":       {"count": True,  "adjust": 0, "extra": None},
    "dbweapontohit.dat":    {"count": True,  "adjust": 0, "extra": None},
    "dbanimals.dat":        {"count": True,  "adjust": 0, "extra": None},
    "dbunitbehavior.dat":   {"count": True,  "adjust": 0, "extra": None},
    "dbaiunittargeting.dat": {"count": True, "adjust": 0, "extra": None},
    "dbcpbehavior.dat":     {"count": True,  "adjust": 0, "extra": None},
    "dbambientsounds.dat":  {"count": True,  "adjust": 0, "extra": None},
    "dbpremadecivs.dat":    {"count": True,  "adjust": 0, "extra": None},
    "dbmusic.dat":          {"count": True,  "adjust": 0, "extra": None},
    "dbworld.dat":          {"count": True,  "adjust": 0, "extra": None},
    "dbgamevariant.dat":    {"count": True,  "adjust": 0, "extra": None},
    "dbstartingresources.dat": {"count": True, "adjust": 0, "extra": None},
    "dbcivpowers.dat":      {"count": True,  "adjust": 0, "extra": None},
}


class Field:
    def __init__(self, size, type_, extra, name, index_size=-1):
        self.size = size
        self.type = type_
        self.extra = extra
        self.name = name
        self.index_size = index_size  # for DYNAMIC_STRING


def load_common(common_path):
    """Map KEY -> (size, type, extra, name, index_size)."""
    out = {}
    with open(common_path, encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            key = parts[0].strip()
            if key.startswith("FIELD") or key.startswith("#") or len(parts) < 3 or not parts[1].strip():
                continue
            try:
                size = int(parts[1].strip())
            except ValueError:
                continue
            type_ = parts[2].strip()
            extra = parts[3].strip() if len(parts) > 3 else ""
            name = parts[4].strip() if len(parts) > 4 else key
            idx_size = -1
            if type_ == "DYNAMIC_STRING" and extra:
                try:
                    idx_size = int(extra)
                except ValueError:
                    pass
            out[key] = Field(size, type_, extra, name, idx_size)
    return out


def load_schema(dats_path, common):
    fields = []
    with open(dats_path, encoding="latin-1") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            size_tok = parts[1].strip()
            if size_tok.startswith("@"):
                key = size_tok[1:]
                if key not in common:
                    raise KeyError(f"common field @{key} not found")
                fd = common[key]
                fields.append(Field(fd.size, fd.type, fd.extra, fd.name, fd.index_size))
                continue
            size = int(size_tok)
            type_ = parts[2].strip()
            extra = parts[3].strip() if len(parts) > 3 else ""
            name = parts[4].strip() if len(parts) > 4 else f"field{len(fields)}"
            idx_size = -1
            if type_ == "DYNAMIC_STRING" and extra:
                idx_size = int(extra)
            fields.append(Field(size, type_, extra, name, idx_size))
    return fields


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self):
        return len(self.data) - self.pos

    def u8(self):
        v = self.data[self.pos]
        self.pos += 1
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.data, self.pos)[0]
        self.pos += 4
        return v

    def raw(self, n):
        v = self.data[self.pos:self.pos + n]
        self.pos += n
        return v


def parse_dat(data: bytes, fields, meta):
    r = Reader(data)
    groups = []
    while r.remaining() > 0:
        if meta.get("count"):
            n = r.u32() + meta.get("adjust", 0)
        else:
            n = None
        entries = []
        i = 0
        while (n is None and r.remaining() > 0) or (n is not None and i < n):
            vals = []
            for fd in fields:
                if fd.type in ("STRING", "DYNAMIC_STRING"):
                    size = fd.size
                    if fd.index_size >= 0:
                        size = int(vals[fd.index_size])
                    if size > 0:
                        raw = r.raw(size)
                        vals.append(raw.split(b"\x00")[0].decode("latin-1", "replace"))
                    else:
                        vals.append("")
                elif fd.type == "FLOAT":
                    vals.append(r.f32())
                elif fd.size == 1:
                    vals.append(r.u8())
                else:
                    vals.append(r.i32())
            # extra fields
            if meta.get("extra") == "last":
                num_extra = int(vals[-1])
                extras = [r.i32() for _ in range(num_extra)]
                vals.append(extras)
            entries.append(vals)
            i += 1
        groups.append(entries)
    return groups


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a: None for a in sys.argv[1:] if a.startswith("--")}
    for a in sys.argv[1:]:
        if a.startswith("--search="):
            flags["--search"] = a.split("=", 1)[1]
        elif a.startswith("--entry="):
            flags["--entry"] = int(a.split("=", 1)[1])
        elif a.startswith("--json="):
            flags["--json"] = a.split("=", 1)[1]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    schema_dir, dat_path = args[0], args[1]
    fname = os.path.basename(dat_path)
    meta = FILE_META.get(fname, {"count": True, "adjust": 0, "extra": None})
    common = load_common(os.path.join(schema_dir, "common.dats"))
    fields = load_schema(os.path.join(schema_dir, fname + "s"), common)
    data = open(dat_path, "rb").read()
    groups = parse_dat(data, fields, meta)
    print(f"# {fname}: {len(groups)} group(s), fields={len(fields)}, "
          f"entry_base_size={sum(f.size for f in fields)}")
    for gi, entries in enumerate(groups):
        print(f"# group {gi}: {len(entries)} entries")
        for ei, vals in enumerate(entries):
            name = str(vals[0]) if vals else ""
            if "--search" in flags and flags["--search"]:
                if not re.search(flags["--search"], name, re.I):
                    continue
            if "--entry" in flags and flags["--entry"] is not None and ei != flags["--entry"]:
                continue
            print(f"--- group {gi} entry {ei} ---")
            for j, (fd, v) in enumerate(zip(fields, vals)):
                print(f"  [{j:3d}] {fd.name:28s} ({fd.type:14s} {fd.size:3d}) = {v!r}")
            if len(vals) > len(fields):
                print(f"  [extra] = {vals[-1]!r}")
    if "--json" in flags and flags["--json"]:
        out = []
        for gi, entries in enumerate(groups):
            for ei, vals in enumerate(entries):
                out.append({"group": gi, "entry": ei,
                            "fields": {fd.name: v for fd, v in zip(fields, vals)}})
        with open(flags["--json"], "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=str)
        print(f"# wrote {flags['--json']}")


if __name__ == "__main__":
    main()
