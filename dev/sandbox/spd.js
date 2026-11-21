// NOLIB
const st=JSON.parse(new NativeFunction(Process.getModuleByName('ee_fps.dll').getExportByName('fps_state'),'pointer',[])().readCString());
const u=ptr('0x'+st.unit), c=u.add(0x34).readPointer(); const v=c.add(0xa8).readFloat(); if(ARG.set) c.add(0xa8).writeFloat(ARG.set);
send(JSON.stringify({speed:v, now:c.add(0xa8).readFloat(), ac:c.add(0xac).readFloat(), b8:c.add(0xb8).readFloat(), bc:c.add(0xbc).readFloat()})); send({done:true});
