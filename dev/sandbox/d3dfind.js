// NOLIB
const out=[];
const mods=Process.enumerateModules().filter(m=>/ddraw|d3d|display|dx7/i.test(m.name));
mods.forEach(m=>out.push(m.name+' '+m.base+' '+m.size+' '+m.path));
// hook Clear (vtable idx 10) by finding device: hook DDraw exports? use EndScene search: scan display module data for pointers to objects whose vtable is in ddraw module
const dd=Process.getModuleByName('DDraw.dll');
function inDD(p){return p.compare(dd.base)>=0 && p.compare(dd.base.add(dd.size))<0;}
for(const m of mods){ if(!/display/i.test(m.name)) continue;
  for(const r of m.enumerateRanges('rw-')){ for(let a=r.base;a.compare(r.base.add(r.size))<0;a=a.add(4)){ let p; try{p=a.readPointer();}catch(e){break;}
     try{ const vt=p.readPointer(); if(inDD(vt)){ const f=vt.add(40).readPointer(); out.push(m.name+'+'+a.sub(m.base)+' obj '+p+' vt '+vt.sub(dd.base)+' [10]='+f.sub(dd.base) + ' n0='+vt.readPointer().sub(dd.base)); } }catch(e){} } } }
send(out.join('\n')); send({done:true});
