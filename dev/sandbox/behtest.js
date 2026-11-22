// NOLIB
const u=ptr(ARG.u); const t=ptr(0x8d2044).readPointer();
u.add(0x208).writePointer(t.add(ARG.b*4).readPointer());
const hk=new NativeFunction(ptr(0x4B7044),'void',['pointer'],'thiscall');
const x0=u.add(0x13c).readFloat(), y0=u.add(0x14c).readFloat();
const h=Interceptor.attach(Process.getModuleByName('user32.dll').getExportByName('PeekMessageA'),{onEnter(){h.detach(); const m=Memory.alloc(0x24); m.add(0xa).writeU8(0xff); m.add(0x10).writeU32(23); m.add(0x14).writeFloat(x0+ARG.d); m.add(0x18).writeFloat(y0); m.add(0x1c).writeU8(2); hk(m);}});
setTimeout(()=>{ send(JSON.stringify({b:ARG.b, moved:+Math.hypot(u.add(0x13c).readFloat()-x0,u.add(0x14c).readFloat()-y0).toFixed(2), hp:u.add(0x3c).readS32()})); send({done:true}); }, 7000);
