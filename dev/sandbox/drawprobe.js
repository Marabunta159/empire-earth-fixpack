// SYMS: ^GERasterizer::(IsPerspectiveModelVisible|IsOrthographicModelVisible)$|^GEModel::(GetName|GetModelOpacity)$
// ARG: {secs:3}  - per-frame statistics of model draws (which models reach the rasterizer, with which lod / opacity)
const secs = (ARG && ARG.secs) || 3;
const DRAW = '?Draw@DX7Rasterizer@@UAEJPAVGEModel@@KM_N@Z', SHOW = '?ShowScene@DX7Rasterizer@@UAEJK@Z';
const frames = [];
let cur = { draws: 0, vis: 0, invis: 0, lod: {}, ret: {}, names: {}, op: {}, opn: {}, ra: {}, t: Date.now() };
const nameCache = {};
function mname(m) {
  const k = m.toString();
  if (k in nameCache) return nameCache[k];
  let s = '?';
  for (const o of [0xd4, 0xd8, 0xdc, 0xe0]) { try { const t = m.add(o).readPointer().readCString(48); if (t && /^[\w .\-]{3,48}$/.test(t)) { s = t; break; } } catch (e) {} }
  nameCache[k] = s; return s;
}
const hooks = [];
for (const dn of ['DX7HRDisplay.dll', 'DX7HRTnLDisplay.dll']) {
  const m = Process.findModuleByName(dn); if (!m) continue;
  const d = m.findExportByName(DRAW), s = m.findExportByName(SHOW);
  if (d) hooks.push(Interceptor.attach(d, {
    onEnter(args) {
      cur.draws++;
      const lod = args[2].toInt32();            // float bits
      cur.lod[lod] = (cur.lod[lod] || 0) + 1;
      const n = mname(args[0]); cur.names[n] = (cur.names[n] || 0) + 1;
      const op = Math.round(args[0].add(0x12c).readFloat() * 10) / 10; cur.op[op] = (cur.op[op] || 0) + 1;
      if (op < 0.95) cur.opn[n] = (cur.opn[n] || 0) + 1;
      const ra = this.returnAddress.toString(); cur.ra[ra] = (cur.ra[ra] || 0) + 1;
    },
    onLeave(r) { const v = r.toInt32(); cur.ret[v] = (cur.ret[v] || 0) + 1; }
  }));
  if (s) hooks.push(Interceptor.attach(s, { onEnter() { frames.push(cur); cur = { draws: 0, vis: 0, invis: 0, lod: {}, ret: {}, names: {}, op: {}, opn: {}, ra: {}, t: Date.now() }; } }));
}
hooks.push(Interceptor.attach(sym('GERasterizer::IsPerspectiveModelVisible'), { onLeave(r) { if (r.toInt32() & 0xff) cur.vis++; else cur.invis++; } }));
function f32(bits) { const b = new ArrayBuffer(4); new Int32Array(b)[0] = bits; return Math.round(new Float32Array(b)[0] * 1000) / 1000; }
setTimeout(() => {
  hooks.forEach(h => h.detach());
  const fr = frames.slice(1);
  const d = fr.map(f => f.draws).sort((a, b) => a - b);
  const last = fr[fr.length - 1] || cur;
  const lod = {}; for (const k in last.lod) lod[f32(parseInt(k))] = last.lod[k];
  const names = Object.entries(last.names).sort((a, b) => b[1] - a[1]).slice(0, 25);
  send(JSON.stringify({ frames: fr.length, fps: Math.round(fr.length / secs), draws_min: d[0], draws_med: d[d.length >> 1], draws_max: d[d.length - 1],
    vis: last.vis, invis: last.invis, ret: last.ret, lod, op: last.op, opn: last.opn, ra: last.ra, names }));
  send({ done: true });
}, secs * 1000);
