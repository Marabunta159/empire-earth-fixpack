// NOLIB
const out=[]; const im=Process.getModuleByName('D3DImm.DLL'); const dd=Process.getModuleByName('DDRAW.DLL');
function inM(m,p){return p.compare(m.base)>=0 && p.compare(m.base.add(m.size))<0;}
const vts={};
for(const r of Process.enumerateRanges('rw-')){ if(r.file) continue; if(r.size>64*1024*1024) continue;
  let buf; try{ buf=r.base.readByteArray(r.size);}catch(e){continue;} const u=new Uint32Array(buf);
  for(let i=0;i<u.length;i++){ const v=u[i]; const p=ptr(v>>>0);
    if(inM(im,p)||inM(dd,p)){ const k=(inM(im,p)?'im+':'dd+')+p.sub(inM(im,p)?im.base:dd.base); (vts[k]=vts[k]||[]).push(r.base.add(i*4)); } } }
for(const k in vts){ if(vts[k].length<200) out.push(k+' x'+vts[k].length+' e.g. '+vts[k].slice(0,3).join(',')); }
send(out.slice(0,200).join('\n')); send({done:true});
