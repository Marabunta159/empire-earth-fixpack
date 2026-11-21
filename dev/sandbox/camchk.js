// NOLIB
const eng=Process.getModuleByName('Low-Level Engine.dll');
const sc=eng.getExportByName('?SetCamera@GEViewport@@QAEXABVGETransformation@@@Z');
const gc=new NativeFunction(eng.getExportByName('?GetCamera@GEViewport@@QBEABVGETransformation@@XZ'),'pointer',['pointer'],'thiscall');
send('SetCamera bytes '+hexdump(sc,{length:16,header:false}));
let n=0,info=null;
const h=Interceptor.attach(sc,{onEnter(a){ this.vp=this.context.ecx; this.t=this.context.esp.add(4).readPointer(); n++; }, onLeave(){ if(!info){ const c=gc(this.vp); const f=p=>Array.from({length:16},(_,i)=>+p.add(i*4).readFloat().toFixed(2)); info={vp:this.vp.toString(),t:this.t.toString(),arg:f(this.t),cam:f(c)}; } }});
setTimeout(()=>{h.detach(); send(JSON.stringify({n,info})); send({done:true});},1500);
