// NOLIB
const A=ARG;
const WORLD=ptr(0x918300);
const lookup=new NativeFunction(ptr(0x53b889),'pointer',['pointer','uint'],'thiscall');
const execHack=new NativeFunction(ptr(0x4B7044),'void',['pointer'],'thiscall');
const execSelect=new NativeFunction(ptr(0x4BCF73),'void',['pointer'],'thiscall');
const execUnselect=new NativeFunction(ptr(0x4BF9C7),'void',['pointer'],'thiscall');
const execAttack=new NativeFunction(ptr(0x4B3958),'void',['pointer'],'thiscall');
const players=i=>ptr(0x918374+i*4).readPointer();
const L=ptr(0x918E84).readU32(), pl=players(L), slot=pl.add(0x464).readU8();
function list(p){const o=[];let u=p.add(0x450).readPointer();while(!u.isNull()){o.push(u);u=u.add(0xc).readPointer();}return o;}
const X=o=>o.add(0x13c).readFloat(),Y=o=>o.add(0x14c).readFloat(),type=o=>o.add(0x2c).readPointer().add(0x4b8).readU32(),cls=o=>o.add(0x2c).readPointer().add(0x4b4).readU32();
function idOf(o,p){for(let off=0;off<0x80;off+=4){const v=o.add(off).readU32();if((v>>>24)===p&&lookup(WORLD,v).equals(o))return{off,v};}return null;}
const cam=ptr(0x918CD0); const cx=cam.add(0x40).readFloat(), cy=cam.add(0x44).readFloat();
function onMain(fn){const h=Interceptor.attach(Process.getModuleByName('user32.dll').getExportByName('PeekMessageA'),{onEnter(){h.detach();try{fn();}catch(e){send('ERR '+e.stack);}}});}
const before=new Set(list(pl).map(o=>o.toString()));
onMain(()=>{ const m=Memory.alloc(0x24); m.add(0xa).writeU8(0xff); m.add(0x10).writeU32(A.type); m.add(0x14).writeFloat(cx); m.add(0x18).writeFloat(cy); m.add(0x1c).writeU8(L); execHack(m); });
setTimeout(()=>{
  const me=list(pl).filter(o=>!before.has(o.toString()))[0];
  if(!me){send('no new unit');send({done:true});return;}
  const id=idOf(me,L); send('new unit '+me+' type '+type(me)+' id '+JSON.stringify(id)+' hp '+me.add(0x3c).readS32());
  const db=me.add(0x2c).readPointer();
  let clone=null;
  if(A.clone){ const opnew=new NativeFunction(ptr(0x683718),'pointer',['uint'],'mscdecl'); const ctor=new NativeFunction(ptr(0x627765),'pointer',['pointer','pointer'],'thiscall');
    const orig=me.add(0x34).readPointer(); const c=opnew(0x164); ctor(c,db); Memory.copy(c.add(0x84),orig.add(0x84),0x154-0x84); if(A.cnt!==undefined){c.add(0x154).writeU32(A.cnt);c.add(0x158).writeU32(A.cnt);} send('orig cnt '+orig.add(0x154).readU32()+'/'+orig.add(0x158).readU32());
    c.add(0x9c).writeFloat(A.range); c.add(0xa4).writeFloat(A.los); c.add(0x138).writeU32(A.reload); c.add(0x144).writeU32(A.hp); c.add(0xd8).writeFloat(A.atk);
    me.add(0x34).writePointer(c); me.add(0x37c).writePointer(c); me.add(0x3c).writeS32(A.hp); send('clone '+c+' of '+orig); }
  // target: nearest goat / enemy
  let c=[]; for(let i=0;i<9;i++){if(i===L)continue;const p=players(i);if(p.isNull())continue;list(p).forEach(o=>{const hp=o.add(0x3c).readS32(); if(hp>0&&cls(o)===A.tcls)c.push({o,i,d:Math.hypot(X(o)-X(me),Y(o)-Y(me)),hp});});}
  c.sort((a,b)=>a.d-b.d); const t=c.find(z=>z.d>A.mind)||c[0];
  send('target dist '+t.d.toFixed(2)+' hp '+t.hp+' type '+type(t.o));
  const tid=idOf(t.o,t.i); const p0=[X(me),Y(me)];
  const hits=[]; function rt(p){try{return p.readPointer().sub(4).readPointer().add(12).readPointer().add(8).readCString();}catch(e){return '?';}}
  const dh=Interceptor.attach(ptr(0x6172BC),{onEnter(){const sp=this.context.esp;const a1=sp.add(4).readPointer(); if(this.context.ecx.equals(t.o)){ let sh=null; try{sh=a1.add(0x1e0).readPointer().toString();}catch(e){} hits.push([Date.now()%100000,sp.add(8).readS32(),rt(a1),a1.equals(me),sh===me.toString()]);}}});
  onMain(()=>{const ms=Memory.alloc(0x20);ms.add(0xa).writeU8(slot);ms.add(0x10).writeU32(id.v);const ma=Memory.alloc(0x20);ma.add(0xa).writeU8(slot);ma.add(0x10).writeU32(tid.v);ma.add(0x14).writeU8(0);execUnselect(ms);execSelect(ms);execAttack(ma);});
  setTimeout(()=>{dh.detach(); send(JSON.stringify({moved:Math.hypot(X(me)-p0[0],Y(me)-p0[1]).toFixed(2),hits,thp:t.o.add(0x3c).readS32(),myhp:me.add(0x3c).readS32(),dbNow:me.add(0x2c).readPointer().toString()})); send({done:true});},A.secs*1000);
},1500);
