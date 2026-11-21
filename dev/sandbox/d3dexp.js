// NOLIB
const out=[];
for(const n of ['DX7HRDisplay.dll','DX7HRTnLDisplay.dll']){ const m=Process.getModuleByName(n); out.push('== '+n); m.enumerateExports().forEach(e=>out.push(e.name)); }
send(out.join('\n')); send({done:true});
