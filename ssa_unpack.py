#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSA (Stainless Steel Archive) unpacker for Empire Earth / Art of Conquest.
Format documented by zocker_160 (EE-modders), reimplemented here for scripting.

Usage:
  python ssa_unpack.py <data.ssa> <output_dir> [--list] [--raw]
"""
import os
import sys
import struct
import ctypes
from io import BytesIO

DCL_MAGIC = b"PK01"
SSA_MAGIC = b"rass"
EUR_ENCODING = "ISO-8859-15"


class DCLDecompressor:
    def __init__(self, dll_path: str):
        self.lib = ctypes.CDLL(dll_path)
        self.lib.decompressBytes.argtypes = [
            ctypes.c_char_p, ctypes.c_int,
            ctypes.c_char_p, ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.decompressBytes.restype = ctypes.c_int

    def decompress(self, data: bytes, uncompressed_size: int) -> bytes:
        output = ctypes.create_string_buffer(uncompressed_size)
        out_len = ctypes.c_int(0)
        ret = self.lib.decompressBytes(
            data, len(data), output, ctypes.byref(out_len)
        )
        if ret != 0:
            raise RuntimeError(f"DCL decompress failed with code {ret}")
        return output.raw[: uncompressed_size]


def _huffman(rep, n):
    """code table from the compact length list: -> (count per bit length, symbols ordered by code)"""
    length = []
    for b in rep:
        length += [b & 15] * ((b >> 4) + 1)
    if len(length) != n:
        raise ValueError("bad code length table")
    count = [0] * 14
    for v in length:
        count[v] += 1
    offs = [0] * 14
    for i in range(1, 13):
        offs[i + 1] = offs[i] + count[i]
    symbol = [0] * n
    for s, v in enumerate(length):
        if v:
            symbol[offs[v]] = s
            offs[v] += 1
    return count, symbol


_LIT = _huffman([11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6, 7, 8, 7, 6, 55, 8, 23, 24,
                 12, 11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11, 8, 11, 9, 12,
                 8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27, 44, 253, 253, 253, 252, 252, 252,
                 13, 12, 45, 12, 45, 12, 61, 12, 45, 44, 173], 256)
_LEN = _huffman([2, 35, 36, 53, 38, 23], 16)
_DIST = _huffman([2, 20, 53, 230, 247, 151, 248], 64)
_BASE = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264]
_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]


def explode(data: bytes, uncompressed_size: int = None) -> bytes:
    """PKWARE DCL "implode" stream -> bytes (pure Python, same method as blast.c from zlib/contrib).
    No DLL needed; fast enough for the db files (a few 100 KB)."""
    lit, dic = data[0], data[1]
    if lit > 1 or not 4 <= dic <= 6:
        raise ValueError("not a DCL stream")
    pos, buf, cnt = 2, 0, 0
    out = bytearray()

    def bits(n):
        nonlocal pos, buf, cnt
        while cnt < n:
            buf |= data[pos] << cnt
            pos += 1
            cnt += 8
        v = buf & ((1 << n) - 1)
        buf >>= n
        cnt -= n
        return v

    def decode(table):
        count, symbol = table
        code = first = index = 0
        for ln in range(1, 14):
            code |= bits(1) ^ 1                       # the codes are stored inverted
            c = count[ln]
            if code < first + c:
                return symbol[index + code - first]
            index += c
            first = (first + c) << 1
            code <<= 1
        raise ValueError("bad DCL code")

    while True:
        if bits(1):
            s = decode(_LEN)
            n = _BASE[s] + bits(_EXTRA[s])
            if n == 519:
                break
            sh = 2 if n == 2 else dic
            dist = (decode(_DIST) << sh) + bits(sh) + 1
            if dist > len(out):
                raise ValueError("bad DCL distance")
            for _ in range(n):
                out.append(out[-dist])
        else:
            out.append(decode(_LIT) if lit else bits(8))
    if uncompressed_size is not None and len(out) != uncompressed_size:
        raise ValueError("DCL size mismatch: %d != %d" % (len(out), uncompressed_size))
    return bytes(out)


def read_u32(f) -> int:
    b = f.read(4)
    if len(b) != 4:
        raise EOFError("unexpected EOF")
    return struct.unpack("<I", b)[0]


def parse_ssa(path: str):
    with open(path, "rb") as f:
        magic = f.read(4)
        assert magic == SSA_MAGIC, f"bad magic {magic!r}"
        ver_maj = read_u32(f)
        ver_min = read_u32(f)
        data_start_offset = read_u32(f)
        header_len = 16

        entries = []
        while f.tell() < (data_start_offset + header_len):
            path_length = read_u32(f)
            raw_path = f.read(path_length)
            start = read_u32(f)
            end = read_u32(f)
            size = read_u32(f)
            p = raw_path.strip(b"\x00").decode(EUR_ENCODING).replace("\\", os.sep)
            entries.append({"path": p, "start": start, "end": end, "size": size})

        num_attr = read_u32(f)
        attrs = []
        for _ in range(num_attr):
            klen = read_u32(f)
            key = f.read(klen).strip(b"\x00").decode(EUR_ENCODING)
            vlen = read_u32(f)
            val = f.read(vlen).strip(b"\x00").decode(EUR_ENCODING)
            attrs.append((key, val))

        blobs = []
        for e in entries:
            f.seek(e["start"])
            blobs.append(f.read(e["size"]))

        return {
            "version": (ver_maj, ver_min),
            "data_start_offset": data_start_offset,
            "entries": entries,
            "attributes": attrs,
            "blobs": blobs,
        }


def find_dll() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "libDCL.dll"),
        os.path.join(here, "tools", "eeshi", "EEStudio2", "lib", "DCL", "libDCL.dll"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("libDCL.dll not found")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 1:
        print(__doc__)
        sys.exit(1)

    ssa_path = args[0]
    out_dir = args[1] if len(args) > 1 else None
    list_only = "--list" in flags
    raw = "--raw" in flags

    ssa = parse_ssa(ssa_path)
    print(f"== {os.path.basename(ssa_path)} ==")
    print(f"version: {ssa['version']}, entries: {len(ssa['entries'])}, attributes: {len(ssa['attributes'])}")
    for k, v in ssa["attributes"]:
        print(f"  meta: {k} = {v}")

    if list_only:
        for e in ssa["entries"]:
            comp = "PK01" if ssa["blobs"][ssa['entries'].index(e)][:4] == DCL_MAGIC else "raw"
            print(f"  {e['path']}  ({e['size']} B, {comp})")
        return

    if not out_dir:
        print("output dir required (or use --list)")
        sys.exit(1)

    dcl = None if raw else DCLDecompressor(find_dll())
    n = 0
    for e, blob in zip(ssa["entries"], ssa["blobs"]):
        dest = os.path.join(out_dir, e["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not raw and blob[:4] == DCL_MAGIC:
            unc_size = struct.unpack("<I", blob[4:8])[0]
            data = dcl.decompress(blob[12:], unc_size)
        else:
            data = blob
        with open(dest, "wb") as f:
            f.write(data)
        n += 1
    print(f"extracted {n} files -> {out_dir}")


if __name__ == "__main__":
    main()
