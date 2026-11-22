// NOLIB
const m=Process.getModuleByName('ee_fps.dll');
const sim=new NativeFunction(m.getExportByName('fps_sim'),'void',['int','int','int','int','int','int']);
const st=()=>JSON.parse(new NativeFunction(m.getExportByName('fps_state'),'pointer',[])().readCString());
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let s=st(); const u=ptr('0x'+s.unit); const ux=u.add(0x13c).readFloat(), uy=u.add(0x14c).readFloat(), uz=u.add(0x15c).readFloat();
 let best=null; for(let i=0;i<9;i++){const p=ptr(0x918374+i*4).readPointer(); if(p.isNull()||i===ptr(0x918E84).readU32())continue; let o=p.add(0x450).readPointer(); while(!o.isNull()){ const db=o.add(0x2c).readPointer(); if(db.add(0x4b8).readU32()===ARG.type&&o.add(0x3c).readS32()>0){const d=Math.hypot(o.add(0x13c).readFloat()-ux,o.add(0x14c).readFloat()-uy); if(d>ARG.min&&(!best||d<best.d)) best={o,d};} o=o.add(0xc).readPointer(); } }
 if(!best){send('no target');send({done:true});return;}
 const o=best.o, gx=o.add(0x13c).readFloat()-ux, gy=o.add(0x14c).readFloat()-uy, gz=o.add(0x15c).readFloat()+0.5-(uz+0.65);
 const wantYaw=Math.atan2(-gx,gy), wantPitch=Math.atan2(gz,best.d);
 let dyaw=wantYaw-s.yaw; while(dyaw>Math.PI)dyaw-=2*Math.PI; while(dyaw<-Math.PI)dyaw+=2*Math.PI;
 sim(Math.round(-dyaw/0.0025), Math.round(-(wantPitch-s.pitch)/0.0025), 0,0,-1,0);
 await sleep(300);
 if(ARG.weapon) { sim(0,0,1+ARG.weapon,1,-1,0); await sleep(100); sim(0,0,1+ARG.weapon,0,-1,0); await sleep(200); }
 const hp0=o.add(0x3c).readS32();
 sim(0,0,0,0,0,1); const tr=[]; for(let k=0;k<ARG.secs*2;k++){ await sleep(500); tr.push(o.add(0x3c).readS32()); }
 sim(0,0,0,0,0,0); await sleep(500);
 send(JSON.stringify({target:o.toString(),dist:+best.d.toFixed(2),hp0,trace:tr,state:st()}));
 send({done:true});
})().catch(e=>{send("ERR "+e.stack);send({done:true});});
