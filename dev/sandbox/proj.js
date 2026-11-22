// NOLIB
const st=new NativeFunction(Process.getModuleByName('ee_fps.dll').getExportByName('fps_state'),'pointer',[]);
const s=JSON.parse(st().readCString());
const out=[];
for(let i=0;i<9;i++){const p=ptr(0x918374+i*4).readPointer(); if(p.isNull())continue; let u=p.add(0x450).readPointer(); while(!u.isNull()){ const db=u.add(0x2c).readPointer(); const t=db.add(0x4b8).readU32(), c=db.add(0x4b4).readU32(); const x=u.add(0x13c).readFloat()-s.pos[0], y=u.add(0x14c).readFloat()-s.pos[1];
 const depth=x*s.fwd[0]+y*s.fwd[1], lat=x*s.right[0]+y*s.right[1]; if(depth>0.5&&depth<12&&Math.abs(lat)<depth&&c!==1) out.push([i,t,c,+depth.toFixed(1),+lat.toFixed(2),+(1280+1280*lat/depth/0.9).toFixed(0)]); u=u.add(0xc).readPointer(); } }
out.sort((a,b)=>a[3]-b[3]); send(JSON.stringify(out)); send({done:true});
