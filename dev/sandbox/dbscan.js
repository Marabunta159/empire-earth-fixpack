// NOLIB
const vts=ARG.vts.map(v=>ptr(v));
const res=[];
Process.enumerateRanges('rw-').forEach(r=>{ if(r.size>256*1024*1024)return;
 vts.forEach((vt,vi)=>{ const pat=vt.toString(16).padStart(8,'0').match(/../g).reverse().join(' ');
  try{ Memory.scanSync(r.base,r.size,pat).forEach(m=>{const a=m.address; if(a.and(3).toInt32())return; try{ const t=a.add(0x4b8).readU32(), c=a.add(0x4b4).readU32(); if(t>0&&t<2000&&a.add(4).readU32()===1){ const f=o=>+a.add(o).readFloat().toFixed(2); res.push([t,c,a.toString(),a.add(0x560).readU32(),f(0x420),f(0x460),f(0x438),a.add(0x510).readU32(),a.add(0x55c).readU32(),a.add(0x4f0).readU32(),a.add(0x4f4).readU32(),a.add(0x4f8).readU32(),a.add(0x4fc).readU32(),a.add(0x500).readU32(),vi]); } }catch(e){} }); }catch(e){} }); });
res.sort((a,b)=>a[0]-b[0]); send(JSON.stringify(res)); send({done:true});
