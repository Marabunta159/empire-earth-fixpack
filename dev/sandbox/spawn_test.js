// SYMS: ^UIManager::UpdateUI$
// test: create a unit through the game's own EEMHackANewUnit message (what the scenario editor uses)
const A = ARG;
const opnew = new NativeFunction(ptr(A.opnew), 'pointer', ['uint'], 'mscdecl');
const ctor = new NativeFunction(ptr(A.ctor), 'pointer', ['pointer', 'pointer', 'pointer', 'uint'], 'thiscall');
function count(player) { const pl = ptr(A.players + player * 4).readPointer(); let o = pl.add(0x450).readPointer(), n = 0, cit = 0; while (!o.isNull()) { n++; const id = o.add(0x2c).readPointer().add(0x4b8).readU32(); if (id === A.type) cit++; o = o.add(0xc).readPointer(); } return [n, cit]; }
const before = count(A.owner);
onUI(mgr => {
  const res = [];
  for (let k = 0; k < (A.n || 1); k++) {
    const msg = opnew(0x20);
    const type = Memory.alloc(4); type.writeU32(A.type);
    const pos = Memory.alloc(8); pos.writeFloat(A.x + (k % 4) * 0.8); pos.add(4).writeFloat(A.y + Math.floor(k / 4) * 0.8);
    ctor(msg, type, pos, A.owner);
    const sender = ptr(A.sender).readPointer();
    const send_ = new NativeFunction(sender.readPointer().add(0x18).readPointer(), 'int', ['pointer', 'pointer', 'uint'], 'thiscall');
    res.push(send_(sender, msg, 0xff));
  }
  return res;
}).then(r => {
  setTimeout(() => { send(JSON.stringify({ send_results: r, before, after: count(A.owner) })); finish(); }, 2500);
}).catch(e => { send('ERR ' + e + '\n' + e.stack); finish(); });
