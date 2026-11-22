#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surgical field patcher for Empire Earth / AOC .dat files.
Tracks absolute byte offsets of every record so fields can be poked in place
without rewriting the whole file (safer than a full reserialize).

Usage:
  python dat_patch.py <schema_dir> <file.dat> --find NAME --set FIELD=VALUE [--dry]
  python dat_patch.py <schema_dir> <file.dat> --find-id 6100 --set 38=0 --dry
  python dat_patch.py <schema_dir> <file.dat> --dump-off NAME
"""
import os
import sys
import struct

from dat_dump import load_common, load_schema, parse_dat, FILE_META, Reader


def field_offsets(fields):
    """Return list of byte offsets of each field within a record, and total size.

    DYNAMIC_STRING fields have size 0 in the schema; their real size comes from
    the referenced STRING_SIZE field. For offset math we need the *runtime* size,
    so this returns a callable... but for dbtechtree/dbobjects all fields are
    fixed-size. We assert that here to stay safe.
    """
    offs = []
    o = 0
    for f in fields:
        if f.size == 0 and f.type == "DYNAMIC_STRING":
            raise ValueError("dynamic-size fields need per-record offsets; use scan_records()")
        offs.append(o)
        o += f.size
    return offs, o


def scan_records(data, fields, meta):
    """Walk the file exactly like parse_dat but yield (abs_offset, values, entry_size)."""
    r = Reader(data)
    out = []
    while r.remaining() > 0:
        group_start = r.pos
        if meta.get("count"):
            n = r.u32() + meta.get("adjust", 0)
        else:
            n = None
        i = 0
        while (n is None and r.remaining() > 0) or (n is not None and i < n):
            rec_start = r.pos
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
            if meta.get("extra") == "last":
                num_extra = int(vals[-1])
                extras = [r.i32() for _ in range(num_extra)]
                vals.append(extras)
            rec_size = r.pos - rec_start
            out.append((rec_start, vals, rec_size))
            i += 1
    return out


def pack_field(fd, value):
    """Serialize a value for a fixed-size field."""
    if fd.type == "FLOAT":
        return struct.pack("<f", float(value))
    if fd.size == 1:
        return struct.pack("<B", int(value) & 0xFF)
    return struct.pack("<i", int(value))


def find_field_offset(fields, rec_vals, target_idx):
    """Byte offset of field target_idx inside a record, handling dynamic strings."""
    o = 0
    for i, fd in enumerate(fields):
        if i == target_idx:
            return o
        size = fd.size
        if fd.index_size >= 0:
            size = int(rec_vals[fd.index_size])
        o += size
    raise IndexError(target_idx)


def main():
    argv = sys.argv[1:]
    args = [a for a in argv if not a.startswith("--")]
    opts = {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            if "=" in key:
                k, v = key.split("=", 1)
                opts[k] = v
            else:
                opts[key] = True
        i += 1

    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    schema_dir, dat_path = args[0], args[1]
    fname = os.path.basename(dat_path)
    meta = FILE_META.get(fname, {"count": True, "adjust": 0, "extra": None})
    common = load_common(os.path.join(schema_dir, "common.dats"))
    fields = load_schema(os.path.join(fname + "s", ""), common) if False else load_schema(
        os.path.join(schema_dir, fname + "s"), common)

    data = bytearray(open(dat_path, "rb").read())
    records = scan_records(bytes(data), fields, meta)
    print(f"# {fname}: {len(records)} records, fields={len(fields)}")

    sel = []
    if "find" in opts and opts["find"]:
        for rec in records:
            if opts["find"].lower() in str(rec[1][0]).lower():
                sel.append(rec)
    if "find-id" in opts and opts["find-id"] is not None:
        fid = int(opts["find-id"])
        # ID field is at index 5 for dbobjects, 2 for dbtechtree, 3 for dbbuttons
        id_idx = {"dbobjects.dat": 5, "dbtechtree.dat": 2, "dbbuttons.dat": 3,
                  "dbgraphics.dat": 68, "dbeffects.dat": 1, "dbevents.dat": 1,
                  "dbsounds.dat": 4}.get(fname)
        if id_idx is None:
            for rec in records:
                if len(rec[1]) > 2 and rec[1][2] == fid:
                    sel.append(rec)
        else:
            for rec in records:
                if len(rec[1]) > id_idx and rec[1][id_idx] == fid:
                    sel.append(rec)
    if not sel:
        sel = records

    if opts.get("dump-off") or opts.get("dump"):
        for rec in sel:
            if opts.get("dump"):
                print(f"--- offset {rec[0]} ---")
                for j, (fd, v) in enumerate(zip(fields, rec[1])):
                    print(f"  [{j:3d}] @{rec[0] + find_field_offset(fields, rec[1], j):8d} {fd.name} = {v!r}")
        return

    sets = {k: v for k, v in opts.items() if k.startswith("set")}
    patches = []
    for k, v in opts.items():
        if k.isdigit():
            patches.append((int(k), v))
    if "set" in opts and opts["set"] and "=" in str(opts["set"]):
        for part in str(opts["set"]).split(","):
            fi, val = part.split("=", 1)
            patches.append((int(fi), val))

    if not patches:
        for rec in sel[:20]:
            nm = rec[1][0] if rec[1] else "?"
            print(f"  offset={rec[0]:8d} size={rec[2]:5d} name={str(nm)!r}")
        return

    dry = bool(opts.get("dry"))
    for rec in sel:
        for fi, val in patches:
            fd = fields[fi]
            off_in_rec = find_field_offset(fields, rec[1], fi)
            abs_off = rec[0] + off_in_rec
            blob = pack_field(fd, val)
            old = bytes(data[abs_off:abs_off + len(blob)])
            print(f"  rec@{rec[0]} {str(rec[1][0])!r} field[{fi}] {fd.name}: "
                  f"{rec[1][fi]!r} -> {val!r}  (abs {abs_off}, {len(blob)}B)")
            if not dry:
                data[abs_off:abs_off + len(blob)] = blob

    if not dry and patches:
        with open(dat_path, "wb") as f:
            f.write(data)
        print(f"# wrote {dat_path} ({len(data)} B)")
    else:
        print("# dry run, nothing written")


if __name__ == "__main__":
    main()
