// SYMS: ^UIManager::UpdateUI$
onUI(mgr=>{ const v=mgr.add(0x34).readPointer(); const f=v.sub(4).readPointer(); const r=[]; for(let o=0xd8;o<0xf8;o+=4) r.push(o.toString(16)+':'+f.add(o).readS32()+'/'+f.add(o).readFloat().toFixed(1));
 if(ARG.set){ f.add(0xe4).writeS32(ARG.x); f.add(0xe8).writeS32(ARG.y); }
 return {mgr:mgr.toString(),form:f.toString(),n:(v.sub(mgr.add(0x30).readPointer())).toInt32()/4,r:r.join(' ')}; }).then(x=>{send(JSON.stringify(x));finish();});
