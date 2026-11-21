// NOLIB
function w(s){ const f=new File('<project>/sandbox/exh.txt','a'); f.write(s+'\n'); f.close(); }
const nt=Process.getModuleByName('ntdll.dll');
Interceptor.attach(nt.getExportByName('KiUserExceptionDispatcher'),{onEnter(){ const sp=this.context.esp; const rec=sp.readPointer(), ctx=sp.add(4).readPointer();
  const code=rec.readU32()>>>0; if(code===0x40010006||code===0x4001000A) return; const addr=rec.add(12).readPointer();
  const eip=ctx.add(0xB8).readPointer(), esp=ctx.add(0xC4).readPointer(), ebp=ctx.add(0xB4).readPointer();
  let s='EXC code '+code.toString(16)+' at '+addr+' '+DebugSymbol.fromAddress(addr)+' p1 '+rec.add(20).readPointer()+' p2 '+rec.add(24).readPointer();
  s+=' eax '+ctx.add(0xB0).readPointer()+' ecx '+ctx.add(0xAC).readPointer()+' edx '+ctx.add(0xA8).readPointer()+' ebx '+ctx.add(0xA4).readPointer()+' esi '+ctx.add(0xA0).readPointer()+' edi '+ctx.add(0x9C).readPointer();
  const st=[]; for(let i=0;i<40;i++){ try{ const v=esp.add(i*4).readPointer(); const m=Process.findModuleByAddress(v); if(m && m.name.match(/exe|dll/i) && !m.name.match(/ntdll|kernel/i)) st.push(m.name+'+'+v.sub(m.base)); }catch(e){} }
  w(s+'\n  thread '+Process.getCurrentThreadId()+' stack: '+st.slice(0,16).join(' | '));
}});
send('armed');
