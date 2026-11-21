// NOLIB
const names=['?BeginScene@DX7Rasterizer@@UAEJPAVGESurface@@K@Z','?EndScene@DX7Rasterizer@@UAEJK@Z','?Clear@DX7Rasterizer@@UAEJABVGEColor@@ABVGERectangle@@K@Z','?ClearZBuffer@DX7Rasterizer@@UAEJMABVGERectangle@@K@Z','?DrawSky@DX7Rasterizer@@UAEJPAVGEModel@@KM_N@Z','?SetViewport@DX7Rasterizer@@UAEXABVGEViewport@@K@Z'];
const log=[]; const cnt={};
for(const dn of ['DX7HRDisplay.dll','DX7HRTnLDisplay.dll']){ const m=Process.getModuleByName(dn);
 for(const n of names){ const a=m.findExportByName(n); if(!a) continue; const k=dn.slice(0,7)+' '+n.split('@')[0];
  Interceptor.attach(a,{onEnter(args){ cnt[k]=(cnt[k]||0)+1; if(log.length<40){ let s=k+' this='+this.context.ecx+' a0='+args[0]+' a1='+args[1]+' a2='+args[2];
    try{ if(/Clear/.test(k)){ s+=' a0f='+(k.includes('ZBuffer')?args[0]:[0,4,8,12].map(o=>args[0].add(o).readFloat().toFixed(2)).join(','))+' rect='+[0,4,8,12].map(o=>args[1].add(o).readU32().toString(16)).join(',')+'/'+[0,4,8,12].map(o=>args[1].add(o).readFloat().toFixed(1)).join(','); } }catch(e){}
    log.push(s);} }}); } }
setTimeout(()=>{ send(JSON.stringify(cnt)+'\n'+log.join('\n')); send({done:true}); },1000);
