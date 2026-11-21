// NOLIB
// ARG: {players, local, type|null}  - where are the local player's objects of a type (null: the most frequent object class): stacking / zero positions / tiles
const A = ARG;
const pl = ptr(A.players + ptr(A.local).readU32() * 4).readPointer();
let o = pl.add(0x450).readPointer(), n = 0, k = 0, zero = 0;
let mode = null;
if (A.type === null || A.type === undefined) { const cnt = {}; let q = o, m = 0; while (!q.isNull() && m < 30000) { m++; const c = q.add(0x2c).readPointer().toString(); cnt[c] = (cnt[c] || 0) + 1; q = q.add(0xc).readPointer(); }
  mode = Object.entries(cnt).sort((a, b) => b[1] - a[1])[0][0]; }
const exact = {}, tile = {}, coarse = {};
let minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9;
const sample = [];
while (!o.isNull() && n < 30000) { n++;
  const cp = o.add(0x2c).readPointer();
  if (mode ? cp.toString() === mode : cp.add(0x4b8).readU32() === A.type) { k++;
    const x = o.add(0x13c).readFloat(), y = o.add(0x14c).readFloat(), z = o.add(0x15c).readFloat();
    if (x === 0 && y === 0) zero++;
    else { minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y); }
    const e = x.toFixed(2) + ',' + y.toFixed(2); exact[e] = (exact[e] || 0) + 1;
    const t = Math.floor(x) + ',' + Math.floor(y); tile[t] = (tile[t] || 0) + 1;
    if (sample.length < 6) sample.push([x.toFixed(2), y.toFixed(2), z.toFixed(2), o.add(0x30).readPointer().toString()]);
  }
  o = o.add(0xc).readPointer(); }
const ev = Object.values(exact), tv = Object.values(tile);
const stacks = Object.entries(exact).filter(e => e[1] > 1).sort((a, b) => b[1] - a[1]);
send(JSON.stringify({ objects: n, of_type: k, zero_pos: zero, distinct_positions: ev.length, units_sharing_a_position: ev.filter(v => v > 1).reduce((a, b) => a + b, 0),
  biggest_stacks: stacks.slice(0, 8), tiles_used: tv.length, max_per_tile: Math.max.apply(null, tv), box: [minx, maxx, miny, maxy].map(v => Math.round(v * 10) / 10), sample }));
send({ done: true });
