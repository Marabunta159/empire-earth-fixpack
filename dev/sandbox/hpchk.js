// NOLIB
const u=ptr(ARG.u); send(JSON.stringify({hp:u.add(0x3c).readS32(), ucu:u.add(0x34).readPointer().toString(), ucu2:u.add(0x37c).readPointer().toString(), maxhp:u.add(0x34).readPointer().add(0x144).readS32(), range:u.add(0x34).readPointer().add(0x9c).readFloat()})); send({done:true});
