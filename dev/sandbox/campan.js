// NOLIB
const c=ptr(0x918CD0); const x=c.add(0x40).readFloat(), y=c.add(0x44).readFloat();
c.add(0x40).writeFloat(x+ARG.dx); c.add(0x44).writeFloat(y+ARG.dy);
send('cam '+x+','+y+' -> '+c.add(0x40).readFloat()+','+c.add(0x44).readFloat()); send({done:true});
