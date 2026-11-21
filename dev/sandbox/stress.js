// NOLIB
const m=Process.getModuleByName('ee_fps.dll');
const sim=new NativeFunction(m.getExportByName('fps_sim'),'void',['int','int','int','int','int','int']);
const st=()=>new NativeFunction(m.getExportByName('fps_state'),'pointer',[])().readCString();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{ const t0=Date.now(); let i=0;
 while(Date.now()-t0<ARG.secs*1000){ i++;
  sim(37,(i%20<10)?6:-6,0,0,-1,0);
  if(i%40===0){ sim(0,0,0x11,1,-1,0);} if(i%40===20){ sim(0,0,0x11,0,-1,0);}   // W
  if(i%55===0){ sim(0,0,0x20,1,-1,0);} if(i%55===15){ sim(0,0,0x20,0,-1,0);}   // D
  if(i%30===0){ sim(0,0,0,0,0,1);} if(i%30===3){ sim(0,0,0,0,0,0);}            // click
  if(i%70===0){ sim(0,0,2+((i/70)%4|0),1,-1,0); } if(i%70===2){ sim(0,0,2+((i/70)%4|0),0,-1,0); }
  if(i%90===0){ sim(0,0,0,0,1,1);} if(i%90===2){ sim(0,0,0,0,1,0);}            // right click zoom
  await sleep(30); }
 send(st()); send({done:true}); })().catch(e=>{send('ERR '+e);send({done:true});});
