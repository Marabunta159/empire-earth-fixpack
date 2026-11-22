// NOLIB  histogram of the tile reference counters of the live terrain mesh
const eng = Process.getModuleByName('Low-Level Engine.dll');
const upd = eng.enumerateExports().find(e => e.name.indexOf('?UpdateFogOfWar@GETerrainMesh@@') === 0).address;
let mesh = null;
const h = Interceptor.attach(upd, { onEnter() { if (!mesh) mesh = this.context.ecx; } });
setTimeout(() => {
  h.detach();
  try {
    const rows = mesh.add(ARG.off).readPointer();
    const hist = { neg: 0, zero: 0, one: 0, vis: 0 }; let n = 0, r = 0, max = 0;
    for (; r < 2000; r++) {
      const cnt = rows.add(r * 12 + 4).readS32(), t = rows.add(r * 12 + 8).readPointer();
      if (cnt <= 0 || cnt > 2000 || t.isNull()) break;
      const a = new Int16Array(t.readByteArray(cnt * 4));
      for (let i = 0; i < cnt; i++) { const v = a[i * 2]; n++; if (v > max) max = v; if (v < 0) hist.neg++; else if (v === 0) hist.zero++; else if (v === 1) hist.one++; else hist.vis++; }
    }
    send(JSON.stringify({ mesh: mesh.toString(), rows: r, tiles: n, hist, max }));
  } catch (e) { send('ERR ' + e); }
  send({ done: true });
}, 6000);
