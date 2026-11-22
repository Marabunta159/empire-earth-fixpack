// NOLIB
const u32=Process.getModuleByName('user32.dll');
const GetCursorPos=u32.getExportByName('GetCursorPos');
let n=0, last=null;
const callers={};
Interceptor.attach(GetCursorPos,{onEnter(a){this.p=a[0]; const r=this.returnAddress; const k=DebugSymbol.fromAddress(r).toString(); callers[k]=(callers[k]||0)+1;}, onLeave(){ n++; last=[this.p.readS32(),this.p.add(4).readS32()]; if(ARG.x!==undefined){this.p.writeS32(ARG.x);this.p.add(4).writeS32(ARG.y);} }});
setTimeout(()=>{send(JSON.stringify({n,last,callers}));send({done:true});},ARG.secs*1000);
