// NOLIB
const v=ptr(0x54a3d2a0).readPointer(); const g=Module.getGlobalExportByName?null:null;
const u=Process.getModuleByName('user32.dll').getExportByName('GetCursorPos');
const dd=Process.getModuleByName('DDRAW.DLL');
const imps=dd.enumerateImports().filter(i=>/CursorPos/.test(i.name)).map(i=>i.name+' '+i.module+' slot '+i.slot+' addr '+i.address);
send('slot '+v+' '+DebugSymbol.fromAddress(v)+' user32 '+u+'\n'+imps.join('\n')+'\n'+Process.findModuleByAddress(v).name); send({done:true});
