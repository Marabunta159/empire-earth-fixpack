// NOLIB
const eng=Process.getModuleByName('Low-Level Engine.dll');
const sc=eng.getExportByName('?SetCamera@GEViewport@@QAEXABVGETransformation@@@Z');
const gc=new NativeFunction(eng.getExportByName('?GetCamera@GEViewport@@QBEABVGETransformation@@XZ'),'pointer',['pointer'],'thiscall');
const seen={};
// hook the trampoline-free entry point after our jmp: watch callers of the engine function via the exe IAT target
const h=Interceptor.attach(sc,{onEnter(a){ const k=this.context.ecx+' '+DebugSymbol.fromAddress(this.returnAddress); const t=this.context.esp.add(4).readPointer(); seen[k]=(seen[k]||0)+1; this.vp=this.context.ecx;}, onLeave(){ }});
setTimeout(()=>{h.detach(); const c=gc(ptr(0x919470)); send(JSON.stringify({seen,camNow:[c.add(12).readFloat(),c.add(28).readFloat(),c.add(44).readFloat()]})); send({done:true});},1500);
