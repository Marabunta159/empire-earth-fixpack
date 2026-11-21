// NOLIB
function rtti(p){ try{ return p.readPointer().sub(4).readPointer().add(12).readPointer().add(8).readCString(); }catch(e){return '?';} }
const t=ptr(0x8d2044).readPointer(); const out=['table '+t];
for(let i=0;i<12;i++){ let p; try{p=t.add(i*4).readPointer();}catch(e){break;} let w=''; try{ w=[p.add(4).readU32(),p.add(8).readU32(),p.add(12).readU32()].join(','); }catch(e){} out.push(i+': '+p+' '+rtti(p)+' '+w); }
const u=ptr(ARG.u); const b=u.add(0x208).readPointer(); out.push('unit+208 = '+b+' '+rtti(b));
send(out.join('\n')); send({done:true});
