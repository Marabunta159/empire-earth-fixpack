// NOLIB
// ARG: {secs:6, c1:addr of the units counter (EE 0x912538, AoC 0x928cd8)}  - fps + fill level of the per-frame tables (light: one hook per frame)
const secs = (ARG && ARG.secs) || 6, c1 = ptr((ARG && ARG.c1) || 0x912538);
let frames = 0, mu = 0, ms = 0, mp = 0;
const hs = [];
for (const dn of ['DX7HRDisplay.dll', 'DX7HRTnLDisplay.dll']) { const m = Process.findModuleByName(dn); if (!m) continue; const s = m.findExportByName('?ShowScene@DX7Rasterizer@@UAEJK@Z');
  if (s) hs.push(Interceptor.attach(s, { onEnter() { frames++; const u = c1.readU32(), si = c1.add(4).readU32(), p = c1.add(0xa0 + 0x2a8).readU32(); if (u > mu) mu = u; if (si > ms) ms = si; if (p > mp) mp = p; } })); }
let t = 0;
const iv = setInterval(() => { t++; send(JSON.stringify({ t, fps: frames, units: mu, simple: ms, pick: mp })); frames = 0; mu = ms = mp = 0;
  if (t >= secs) { clearInterval(iv); hs.forEach(x => x.detach()); send({ done: true }); } }, 1000);
