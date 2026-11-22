// NOLIB
const A = ARG;
const pl = ptr(A.players + ptr(A.local).readU32() * 4).readPointer();
let o = pl.add(0x450).readPointer(), n = 0; const cls = {};
while (!o.isNull() && n < 400) {
  n++;
  const c = o.add(0x2c).readPointer(); const k = c.toString();
  if (!cls[k]) {
    const e = { count: 0, offs: [] };
    for (let off = 0; off < 0x900; off += 4) { const v = c.add(off).readU32(); if (v === 204 || v === 32 || v === 480) e.offs.push('0x' + off.toString(16) + '=' + v); }
    try { e.name = c.add(12).readPointer().readCString(40); } catch (x) { e.name = '?'; }
    try { e.name2 = c.add(8).readPointer().readCString(40); } catch (x) { e.name2 = '?'; }
    cls[k] = e;
  }
  cls[k].count++;
  o = o.add(0xc).readPointer();
}
send(JSON.stringify({ n, cls })); send({ done: true });
