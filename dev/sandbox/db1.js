// NOLIB
function rtti(p){ try{ const vt=p.readPointer(); const col=vt.sub(4).readPointer(); return col.add(12).readPointer().add(8).readCString(); }catch(e){return '?';} }
const players=i=>ptr(0x918374+i*4).readPointer();
const L=ptr(0x918E84).readU32();
function list(p){const o=[];let u=p.add(0x450).readPointer();while(!u.isNull()){o.push(u);u=u.add(0xc).readPointer();}return o;}
const out={local:L,players:[]};
for(let i=0;i<9;i++){const p=players(i); if(p.isNull())continue; const us=list(p); const m={};
 us.forEach(u=>{const db=u.add(0x2c).readPointer(); const t=db.add(0x4b8).readU32(); const k=t+':'+db; if(!m[k])m[k]={t,cls:db.add(0x4b4).readU32(),db:db.toString(),n:0,urtti:rtti(u),dbrtti:rtti(db),hp:u.add(0x3c).readS32()}; m[k].n++;});
 out.players.push({i,p:p.toString(),rt:rtti(p),units:Object.values(m)});}
send(JSON.stringify(out,null,0)); send({done:true});
