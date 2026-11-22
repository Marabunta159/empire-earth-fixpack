const db=findDb(ARG.type);
const pat=db.toString(16).padStart(8,'0').match(/../g).reverse().join(' ');
const hits=[];
Process.enumerateRanges('rw-').forEach(r=>{ try{ Memory.scanSync(r.base,r.size,pat).forEach(m=>{ const a=m.address.sub(0x60); try{ const rng=a.add(0x9c).readFloat(), los=a.add(0xa4).readFloat(); if(Math.abs(rng-db.add(0x420).readFloat())<3) hits.push([a.toString(),+rng.toFixed(2),+los.toFixed(2),+a.add(0xd8).readFloat().toFixed(1),a.add(0x138).readU32(),a.readU32().toString(16)]); }catch(e){} }); }catch(e){} });
// units of local player of this type
const pl=ptr(0x918374+ptr(0x918E84).readU32()*4).readPointer(); const us=[]; let u=pl.add(0x450).readPointer(); while(!u.isNull()){ if(u.add(0x2c).readPointer().equals(db)) us.push(u.toString()); u=u.add(0xc).readPointer(); }
send(JSON.stringify({db:db.toString(),hits,units:us})); send({done:true});
