// NOLIB
const exe = Process.getModuleByName(EXE);
const A = ARG;   // addresses for this exe
function p(a) { return ptr(a); }
const out = {};
out.cheatFlag = p(A.flag).readU8();
out.options_bytes = Array.from(new Uint8Array(p(A.flag - 0x1a).readByteArray(0x30))).map(b => ('0' + b.toString(16)).slice(-2)).join(' ');
out.localIdx = p(A.local).readU32();
out.playerCount = p(A.players + 0x58).readU32();
out.players = [];
for (let i = 0; i <= out.playerCount && i < 20; i++) {
  const pl = p(A.players + i * 4).readPointer();
  if (pl.isNull()) { out.players.push(null); continue; }
  let n = 0; let o = pl.add(0x450).readPointer(); const types = {};
  while (!o.isNull() && n < 5000) { n++; o = o.add(0xc).readPointer(); }
  out.players.push({ i, p: pl.toString(), id: pl.add(0x45c).readU32(), slot: pl.add(0x464).readU8(), objects: n });
}
send(JSON.stringify(out));
send({ done: true });
