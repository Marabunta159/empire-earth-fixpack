// NOLIB
const m=Process.getModuleByName(ARG.mod); let a=ARG.name?m.getExportByName(ARG.name):m.base.add(ARG.off); const out=[];
for(let i=0;i<(ARG.n||80);i++){ const ins=Instruction.parse(a); out.push(a.sub(m.base)+'  '+ins.toString()); a=ins.next; }
send(out.join('\n')); send({done:true});
