// NOLIB
const eng = Process.getModuleByName('Low-Level Engine.dll');
const c = {};
['?ReferenceTile@GETerrainMesh@@', '?DereferenceTile@GETerrainMesh@@', '?SetTileReferenceCount@GETerrainMesh@@', '?UpdateFogOfWar@'].forEach(n => {
  eng.enumerateExports().filter(e => e.name.indexOf(n) >= 0).forEach(e => { c[e.name.slice(0, 40)] = 0; Interceptor.attach(e.address, function () { c[e.name.slice(0, 40)]++; }); });
});
setTimeout(() => { send(JSON.stringify(c)); send({ done: true }); }, 14000);
