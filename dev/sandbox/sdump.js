// NOLIB
const s=ptr(ARG.s); const out=[];
for(let o=0;o<0x164;o+=4){const u=s.add(o).readU32(),f=s.add(o).readFloat(); out.push(o.toString(16)+':'+(u===0?'0':(Math.abs(f)>1e-4&&Math.abs(f)<1e6?'f'+(+f.toFixed(3)):(u<100000?'i'+u:'x'+u.toString(16)))));}
send(out.join(' ')); send({done:true});
