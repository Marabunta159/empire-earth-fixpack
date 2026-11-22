// NOLIB
const db=findDb(ARG.type); const off=ARG.off, len=ARG.len;
const bytes=new Uint8Array(db.add(off).readByteArray(len)); const pat=Array.from(bytes).map(b=>b.toString(16).padStart(2,'0')).join(' ');
const hits=[];
Process.enumerateRanges('rw-').forEach(r=>{ try{ Memory.scanSync(r.base,r.size,pat).forEach(m=>hits.push(m.address.sub(off).toString())); }catch(e){} });
send(JSON.stringify({db:db.toString(),hits})); send({done:true});
