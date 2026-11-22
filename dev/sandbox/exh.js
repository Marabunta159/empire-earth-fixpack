// NOLIB
function w(s){ const f=new File('<project>/sandbox/exh.txt','a'); f.write(s+'\n'); f.close(); }
Process.setExceptionHandler(d=>{ const c=d.context; let s='EXC '+d.type+' at '+d.address+' '+DebugSymbol.fromAddress(d.address)+' mem '+(d.memory?d.memory.operation+' '+d.memory.address:'')+' eax '+c.eax+' ecx '+c.ecx+' esp '+c.esp;
 try{ s+='\nstack: '+Thread.backtrace(c,Backtracer.FUZZY).slice(0,14).map(a=>DebugSymbol.fromAddress(a).toString()).join(' | ');}catch(e){}
 if(d.type!=='system') w(s); return false; });
const k=Process.getModuleByName('kernel32.dll'), kb=Process.getModuleByName('kernelbase.dll'), nt=Process.getModuleByName('ntdll.dll');
Interceptor.attach(kb.getExportByName('OutputDebugStringA'),{onEnter(a){ w('ODS '+a[0].readCString()+' <- '+DebugSymbol.fromAddress(this.returnAddress)); }});
for(const [m,n] of [[k,'ExitProcess'],[nt,'NtTerminateProcess'],[kb,'TerminateProcess'],[nt,'RtlFailFast'],[kb,'RaiseFailFastException']]){ const a=m.findExportByName(n); if(a) Interceptor.attach(a,{onEnter(x){ w('CALL '+n+' '+x[0]+' '+x[1]+'\n  '+Thread.backtrace(this.context,Backtracer.FUZZY).slice(0,16).map(a=>DebugSymbol.fromAddress(a).toString()).join(' | ')); }}); }
send('armed');
