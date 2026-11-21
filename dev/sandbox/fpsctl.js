// NOLIB
// ARG.steps: [{sel:type} | {sim:[dx,dy,key,keyDown,btn,btnDown]} | {wait:ms} | {state:1} | {shot:name}]
const m=Process.getModuleByName('ee_fps.dll');
const sim=new NativeFunction(m.getExportByName('fps_sim'),'void',['int','int','int','int','int','int']);
const st=new NativeFunction(m.getExportByName('fps_state'),'pointer',[]);
const WORLD=ptr(0x918300);
const lookup=new NativeFunction(ptr(0x53b889),'pointer',['pointer','uint'],'thiscall');
const execSelect=new NativeFunction(ptr(0x4BCF73),'void',['pointer'],'thiscall');
const execUnselect=new NativeFunction(ptr(0x4BF9C7),'void',['pointer'],'thiscall');
const L=ptr(0x918E84).readU32(), pl=ptr(0x918374+L*4).readPointer(), slot=pl.add(0x464).readU8();
function list(p){const o=[];let u=p.add(0x450).readPointer();while(!u.isNull()){o.push(u);u=u.add(0xc).readPointer();}return o;}
function onMain(fn){return new Promise(r=>{const h=Interceptor.attach(Process.getModuleByName('user32.dll').getExportByName('PeekMessageA'),{onEnter(){h.detach();try{fn();}catch(e){send('ERR '+e.stack);}r();}});});}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 for(const s of ARG.steps){
  if(s.sel!==undefined){ const u=list(pl).filter(o=>o.add(0x2c).readPointer().add(0x4b8).readU32()===s.sel&&o.add(0x3c).readS32()>0)[s.nth||0]; if(!u){send('no unit of type '+s.sel);continue;}
     await onMain(()=>{const ms=Memory.alloc(0x20);ms.add(0xa).writeU8(slot);execUnselect(ms);ms.add(0x10).writeU32(u.add(0x24).readU32());execSelect(ms);}); send('selected '+u); }
  if(s.spawn!==undefined){ const cam=ptr(0x918CD0); await onMain(()=>{ const hk=new NativeFunction(ptr(0x4B7044),'void',['pointer'],'thiscall'); const m=Memory.alloc(0x24); m.add(0xa).writeU8(0xff); m.add(0x10).writeU32(s.spawn); m.add(0x14).writeFloat(s.x); m.add(0x18).writeFloat(s.y); m.add(0x1c).writeU8(s.owner===undefined?L:s.owner); hk(m); }); send('spawned '+s.spawn); }
  if(s.sim) sim(...s.sim);
  if(s.wait) await sleep(s.wait);
  if(s.state) send(st().readCString());
 }
 send({done:true});
})();
