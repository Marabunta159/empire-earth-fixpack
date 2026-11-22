// NOLIB
function rtti(p){ try{ const vt=p.readPointer(); return vt.sub(4).readPointer().add(12).readPointer().add(8).readCString(); }catch(e){return '?';} }
const pl=ptr(0x918374+ptr(0x918E84).readU32()*4).readPointer();
const g=pl.add(0x9bc).readPointer();
const vt=g.readPointer(); const m=[]; for(let i=0;i<12;i++) m.push(vt.add(i*4).readPointer().toString());
const d=[]; for(let o=0;o<0x40;o+=4) d.push(o.toString(16)+':'+g.add(o).readU32().toString(16));
send(JSON.stringify({g:g.toString(),rt:rtti(g),vt:m,d:d.join(' ')})); send({done:true});
