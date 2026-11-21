// NOLIB
const m=Module.load(ARG.dll); send('loaded '+m.base);
const st=new NativeFunction(m.getExportByName('fps_state'),'pointer',[]);
send(st().readCString()); send({done:true});
