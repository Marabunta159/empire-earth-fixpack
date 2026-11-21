// NOLIB
const a=ptr(ARG.a), b=ptr(ARG.b); const out=[];
for(let o=0;o<0x164;o+=4){const x=a.add(o).readU32(), y=b.add(o).readU32(); if(x!==y) out.push(o.toString(16)+': '+x.toString(16)+' vs '+y.toString(16));}
const sub=(p)=>{const r=[];for(let o=0;o<0x40;o+=4)r.push(p.add(o).readU32().toString(16));return r.join(' ');};
for(const o of [0x64,0x68,0x6c,0x70,0x74,0x78,0x7c,0x80]){ out.push('sub '+o.toString(16)+' A: '+sub(a.add(o).readPointer())); out.push('sub '+o.toString(16)+' B: '+sub(b.add(o).readPointer())); }
send(out.join('\n')); send({done:true});
