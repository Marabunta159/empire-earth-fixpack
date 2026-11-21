// NOLIB
const c=ptr(0x918CD0); for(const k in ARG){ c.add(parseInt(k,16)).writeFloat(ARG[k]); } setTimeout(()=>{send('ok '+c.add(0x38).readFloat()+' '+c.add(0x70).readFloat());send({done:true});},1500);
