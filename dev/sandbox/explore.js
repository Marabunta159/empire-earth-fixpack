// NOLIB
const exe = Process.getModuleByName(EXE);
function rtti(obj) {
  try {
    const vt = obj.readPointer();
    const col = vt.sub(4).readPointer();
    const td = col.add(12).readPointer();
    return td.add(8).readCString(80).replace('.?AV', '').replace('@@', '');
  } catch (e) { return '?'; }
}
function floats(p, n) {
  const out = [];
  for (let o = 0; o < n; o += 4) {
    let f; try { f = p.add(o).readFloat(); } catch (e) { break; }
    if (isFinite(f) && Math.abs(f) > 0.5 && Math.abs(f) < 2000 && Math.abs(f - Math.round(f * 100) / 100) < 1) out.push('+' + o.toString(16) + '=' + f.toFixed(2));
  }
  return out;
}
function cstrAt(p) { try { const s = p.readCString(48); if (s && s.length > 2 && /^[\x20-\x7e]+$/.test(s)) return s; } catch (e) {} return null; }
const A = ARG;
const pl = ptr(A.players + A.player * 4).readPointer();
send('player ' + A.player + ' @' + pl + ' class ' + rtti(pl));
let o = pl.add(0x450).readPointer(); let n = 0;
while (!o.isNull() && n < (A.max || 20)) {
  const db = o.add(0x2c).readPointer();
  let dbname = null;
  // look for an inline or pointed name in the db object
  for (let off = 0; off < 0x40 && !dbname; off += 4) { dbname = cstrAt(db.add(off)); }
  const unit = o.add(0x30).readPointer();
  send(JSON.stringify({ n, obj: o.toString(), cls: rtti(o), db: db.toString(), dbcls: rtti(db), dbname, dbid_4b8: db.add(0x4b8).readU32(), dbclass_4b4: db.add(0x4b4).readU32(),
    unit: unit.toString(), unitcls: unit.isNull() ? null : rtti(unit), hp3c: o.add(0x3c).readS32(), f: floats(o, 0x120).slice(0, 24) }));
  o = o.add(0xc).readPointer(); n++;
}
send({ done: true });
