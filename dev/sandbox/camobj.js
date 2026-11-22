// NOLIB
const c=ptr(0x918CD0); const r=[]; for(let o=0;o<0x100;o+=4){ r.push(o.toString(16)+':'+c.add(o).readFloat().toFixed(3)+'/'+c.add(o).readU32().toString(16)); }
send(r.join('  ')); send({done:true});
