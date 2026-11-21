// NOLIB
const A = ARG;
const pl = ptr(A.players + ptr(A.local).readU32() * 4).readPointer();
let o = pl.add(0x450).readPointer(), n = 0, cit = 0;
while (!o.isNull() && n < 9000) { n++; const id = o.add(0x2c).readPointer().add(0x4b8).readU32(); if (id === 32 || id === 480) cit++; o = o.add(0xc).readPointer(); }
const res = []; for (let i = 0; i < 5; i++) res.push(pl.add(0xaf8 + i * 4).readU32());
send(JSON.stringify({ flag: ptr(A.flag).readU8(), objects: n, citizens: cit, resources: res }));
send({ done: true });
