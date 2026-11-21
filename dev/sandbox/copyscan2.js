// helper: find db object for a type id (EEUCLand / EEUCLandCitizen vtables)
function findDb(t){ for(const vt of ['94 21 83 00','08 33 83 00']){ for(const r of Process.enumerateRanges('rw-')){ if(r.size>256*1024*1024)continue; let res=null; try{ for(const m of Memory.scanSync(r.base,r.size,vt)){ const a=m.address; if(a.and(3).toInt32())continue; try{ if(a.add(4).readU32()===1&&a.add(0x4b8).readU32()===t){res=a;break;} }catch(e){} } }catch(e){} if(res)return res; } } return null; }
// NOLIB
const db=findDb(ARG.type); const off=ARG.off, len=ARG.len;
const bytes=new Uint8Array(db.add(off).readByteArray(len)); const pat=Array.from(bytes).map(b=>b.toString(16).padStart(2,'0')).join(' ');
const hits=[];
Process.enumerateRanges('rw-').forEach(r=>{ try{ Memory.scanSync(r.base,r.size,pat).forEach(m=>hits.push(m.address.sub(off).toString())); }catch(e){} });
send(JSON.stringify({db:db.toString(),hits})); send({done:true});
