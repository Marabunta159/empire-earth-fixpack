// NOLIB
const u=ptr(ARG.u); const S=ARG.stats.map(s=>ptr(s)); const out=[];
for(let o=0;o<0x400;o+=4){ let v; try{v=u.add(o).readPointer();}catch(e){break;} S.forEach((s,i)=>{ if(v.equals(s)) out.push(['unit+'+o.toString(16),i]); });
 try{ for(let o2=0;o2<0x100;o2+=4){ const w=v.add(o2).readPointer(); S.forEach((s,i)=>{ if(w.equals(s)) out.push(['[unit+'+o.toString(16)+']+'+o2.toString(16),i]); }); } }catch(e){} }
function rtti(p){ try{ const vt=p.readPointer(); return vt.sub(4).readPointer().add(12).readPointer().add(8).readCString(); }catch(e){return '?';} }
send(JSON.stringify({out,rt:rtti(S[0])})); send({done:true});
