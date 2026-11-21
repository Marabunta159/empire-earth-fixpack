// NOLIB
// what does the game get from the rasterizer for total / available video memory?  (EE addresses: rasterizer 0x919794, screen 0x919428)
const rast = ptr(0x919794).readPointer();
const screen = ptr(0x919428).readU32();
const vt = rast.readPointer();
const mod = Process.findModuleByAddress(vt);
const out = { display: mod ? mod.name : '?', screen };
for (const [k, n] of [['total', '?GetTotalVideoMemory@DX7Rasterizer@@UAEJKAAK@Z'], ['available', '?GetAvailableVideoMemory@DX7Rasterizer@@UAEJKAAK@Z']]) {
  const a = mod.findExportByName(n);
  const buf = Memory.alloc(8); buf.writeU32(0xdeadbeef);
  const rc = new NativeFunction(a, 'int', ['pointer', 'uint', 'pointer'], 'thiscall')(rast, screen, buf);
  out[k] = { rc, value: buf.readU32(), mb: Math.round(buf.readU32() / 1048576), signed: buf.readS32() };
}
send(JSON.stringify(out)); send({ done: true });
