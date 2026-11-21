// NOLIB
// ARG: {secs:10}  - once per second: unit draw calls per frame (EE exe 0x50b4ac) by caller, plus distinct instances
const secs = (ARG && ARG.secs) || 10;
const SHOW = '?ShowScene@DX7Rasterizer@@UAEJK@Z';
let cur = { n: 0, ra: {} }, last = null, frames = 0;
const h = [Interceptor.attach(ptr(0x50b4ac), { onEnter() { cur.n++; const r = this.returnAddress.toString(); cur.ra[r] = (cur.ra[r] || 0) + 1; } })];
for (const dn of ['DX7HRDisplay.dll', 'DX7HRTnLDisplay.dll']) { const m = Process.findModuleByName(dn); if (!m) continue; const s = m.findExportByName(SHOW);
  if (s) h.push(Interceptor.attach(s, { onEnter() { last = cur; cur = { n: 0, ra: {} }; frames++; } })); }
let t = 0;
const iv = setInterval(() => { t++; send(JSON.stringify({ t, fps: frames, units: last && last.n, by: last && last.ra })); frames = 0;
  if (t >= secs) { clearInterval(iv); h.forEach(x => x.detach()); send({ done: true }); } }, 1000);
