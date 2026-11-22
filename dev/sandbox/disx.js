// NOLIB
let a=ptr(ARG.a); const out=[]; for(let i=0;i<ARG.n;i++){ const ins=Instruction.parse(a); out.push(a+'  '+ins.toString()); a=ins.next; } send(out.join('\n')); send({done:true});
