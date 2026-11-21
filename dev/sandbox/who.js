// NOLIB
const a = ptr(ARG.a1), me = ptr(ARG.me);
const out = { a1: a.toString() };
for (let i = 0; i < 9; i++) { const p = ptr(ARG.players + i * 4).readPointer(); if (p.isNull()) continue; let o = p.add(0x450).readPointer(), n = 0; while (!o.isNull()) { if (o.equals(a)) out.found = { player: i, index: n }; n++; o = o.add(0xc).readPointer(); } }
const X = o => +o.add(0x13c).readFloat().toFixed(2), Y = o => +o.add(0x14c).readFloat().toFixed(2);
out.a1_type = a.add(0x2c).readPointer().add(0x4b8).readU32(); out.a1_pos = [X(a), Y(a)]; out.a1_hp = a.add(0x3c).readS32();
out.me_type = me.add(0x2c).readPointer().add(0x4b8).readU32(); out.me_pos = [X(me), Y(me)];
send(JSON.stringify(out)); send({ done: true });
