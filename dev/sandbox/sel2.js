// NOLIB
const pl=ptr(0x918374+ptr(0x918E84).readU32()*4).readPointer();
const g=pl.add(0x9bc).readPointer(); const b=g.add(0x24).readPointer(), en=g.add(0x28).readPointer();
const items=[]; for(let p=b;p.compare(en)<0;p=p.add(4)) items.push(p.readU32().toString(16));
send(JSON.stringify({items})); send({done:true});
