// NOLIB
const m=Process.getModuleByName('DX7HRDisplay.dll'); const cnt={}; const callers={};
for(const n of ['?TransformToCamera@DX7Rasterizer@@UAEXAAVGETerrainMesh@@AAVGEViewport@@M_N2@Z','?Draw@DX7Rasterizer@@UAEJAAVGETerrainMesh@@K_N@Z','?DrawTerrainMaterial@DX7Rasterizer@@MAEJPAVGEViewport@@AAV?$vector@PAUGETMPolygon@GETerrainMesh@@V?$allocator@PAUGETMPolygon@GETerrainMesh@@@std@@@std@@K@Z']){
 const a=m.findExportByName(n); if(!a){continue;} const k=n.split('@')[0]+n.split('@')[1].slice(0,0);
 Interceptor.attach(a,{onEnter(){ cnt[k]=(cnt[k]||0)+1; const r=DebugSymbol.fromAddress(this.returnAddress).toString(); callers[k+' <- '+r]=(callers[k+' <- '+r]||0)+1; }}); }
setTimeout(()=>{send(JSON.stringify(cnt,null,0)+'\n'+JSON.stringify(callers,null,1));send({done:true});},1000);
