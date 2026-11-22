// NOLIB
const dbs=ARG.dbs.map(ptr); const out=[];
for(let off=0;off<0x628;off+=4){ const row=[off.toString(16)]; let interesting=false;
 dbs.forEach(d=>{const u=d.add(off).readU32(), f=d.add(off).readFloat(); let s;
  if(u===0) s='0'; else if(Math.abs(f)>1e-4&&Math.abs(f)<1e6) {s='f'+(+f.toFixed(3)); interesting=true;} else if(u<100000){s='i'+u;interesting=true;} else s='x'+u.toString(16);
  row.push(s);});
 out.push(row.join(' '));}
send(out.join('\n')); send({done:true});
