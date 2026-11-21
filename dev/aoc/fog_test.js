// NOLIB  unit test of the patched GETerrainMesh::ReferenceTile / DereferenceTile on a fake mesh
const eng = Process.getModuleByName('Low-Level Engine.dll');
const ex = n => eng.enumerateExports().find(e => e.name.indexOf(n) === 0).address;
const Ref = new NativeFunction(ex('?ReferenceTile@GETerrainMesh@@'), 'pointer', ['pointer', 'int', 'int'], 'thiscall');
const Deref = new NativeFunction(ex('?DereferenceTile@GETerrainMesh@@'), 'pointer', ['pointer', 'int', 'int'], 'thiscall');
const OFF = ARG.off;
const mesh = Memory.alloc(OFF + 16), rows = Memory.alloc(12 * 4), tiles = Memory.alloc(4 * 16);
mesh.add(OFF).writePointer(rows);
for (let y = 0; y < 4; y++) { rows.add(y * 12).writeS32(10); rows.add(y * 12 + 4).writeS32(4); rows.add(y * 12 + 8).writePointer(tiles.add(y * 16)); }
const out = [];
for (const start of [-1, 0, 1, 2, 5]) {
  const t = tiles.add(2 * 16 + 3 * 4);                  // tile x=13, y=2
  t.writeS16(start); const r1 = Ref(mesh, 13, 2); const a = t.readS16();
  t.writeS16(start); const r2 = Deref(mesh, 13, 2); const b = t.readS16();
  out.push('rc=' + start + ': Reference -> ' + a + ', Dereference -> ' + b + (r1.equals(t) && r2.equals(t) ? '' : '  (return value differs!)') + (t.add(2).readU16() === 0 ? '' : ' (neighbour bytes touched!)'));
}
send(out.join('\n')); send({ done: true });
