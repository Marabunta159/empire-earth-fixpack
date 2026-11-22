// NOLIB
// ARG: {players, local, type, set:bool, zoom:float|null}  - centroid of the local player's objects of a type; optionally move the camera there
const A = ARG;
const pl = ptr(A.players + ptr(A.local).readU32() * 4).readPointer();
let o = pl.add(0x450).readPointer(), n = 0, sx = 0, sy = 0, k = 0, minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9;
while (!o.isNull() && n < 20000) { n++; const id = o.add(0x2c).readPointer().add(0x4b8).readU32();
  if (id === A.type) { const x = o.add(0x13c).readFloat(), y = o.add(0x14c).readFloat(); sx += x; sy += y; k++; minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); }
  o = o.add(0xc).readPointer(); }
const c = ptr(0x918CD0);
const before = [c.add(0x38).readFloat(), c.add(0x40).readFloat(), c.add(0x44).readFloat()];
if (A.set && k) { c.add(0x40).writeFloat(sx / k); c.add(0x44).writeFloat(sy / k); }
if (A.zoom) c.add(0x38).writeFloat(A.zoom);
setTimeout(() => { send(JSON.stringify({ objects: n, of_type: k, centroid: [sx / k, sy / k], box: [minx, maxx, miny, maxy], cam_before: before,
  cam_after: [c.add(0x38).readFloat(), c.add(0x40).readFloat(), c.add(0x44).readFloat()] })); send({ done: true }); }, 800);
