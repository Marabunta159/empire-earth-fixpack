// NOLIB
const base = ptr(ARG.cam);
const out = [];
for (let o = 0; o < 0x140; o += 4) { const f = base.add(o).readFloat(); if (isFinite(f) && Math.abs(f) > 0.01 && Math.abs(f) < 5000) out.push('+' + o.toString(16) + '=' + (Math.round(f * 100) / 100)); }
send(out.join('  '));
const comm = ptr(ARG.comm).readPointer();
send('comm ' + comm + ' +0x2e=' + comm.add(0x2e).readU8() + ' +0x10=' + comm.add(0x10).readU32());
send({ done: true });
