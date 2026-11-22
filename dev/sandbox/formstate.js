function rtti(p){ try{ return p.readPointer().sub(4).readPointer().add(12).readPointer().add(8).readCString(); }catch(e){ return '?'; } }
rpc.exports={ r(players, local, goff){ const out=['local='+ptr(local).readU32()];
 for(let i=0;i<9;i++){ const p=ptr(players+i*4).readPointer(); if(p.isNull()) continue;
   const g=p.add(goff).readPointer(); let sub='-';
   try{ const sg=g.add(0x3c).readPointer(); if(!sg.isNull()) sub=rtti(sg.add(0x34).readPointer()); }catch(e){}
   out.push(i+' '+rtti(p)+' group='+g+' form='+(g.isNull()?'-':rtti(g.add(0x34).readPointer()))+' sub='+sub); }
 return out; } };
