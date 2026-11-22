// NOLIB
const m=Process.getModuleByName('Low-Level Engine.dll'); send(m.enumerateExports().map(e=>e.name).filter(n=>/Cursor|MousePointer|ShowMouse/i.test(n)).join('\n')); send({done:true});
