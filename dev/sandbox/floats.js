// NOLIB
const A = ARG;
const pl = ptr(A.players + A.player * 4).readPointer();
let o = pl.add(0x450).readPointer(); let n = 0;
const rows = [];
while (!o.isNull() && n < 14) {
  const fs = [];
  for (let off = 0; off < 0x340; off += 4) {
    const f = o.add(off).readFloat();
    if (isFinite(f) && Math.abs(f) >= 1 && Math.abs(f) < 1000) fs.push([off, Math.round(f * 100) / 100]);
  }
  rows.push({ n, id: o.add(0x2c).readPointer().add(0x4b8).readU32(), fs });
  o = o.add(0xc).readPointer(); n++;
}
// offsets whose value differs between objects (candidate positions)
const offs = {};
rows.forEach(r => r.fs.forEach(([off, v]) => { (offs[off] = offs[off] || new Set()).add(v); }));
const varying = Object.keys(offs).map(Number).filter(o => offs[o].size >= rows.length - 3).sort((a, b) => a - b);
send('varying float offsets: ' + varying.map(o => '0x' + o.toString(16)).join(' '));
rows.forEach(r => { const m = {}; r.fs.forEach(([off, v]) => { if (varying.includes(off)) m['0x' + off.toString(16)] = v; }); send('obj ' + r.n + ' type ' + r.id + ' ' + JSON.stringify(m)); });
// map size hints
send({ done: true });
