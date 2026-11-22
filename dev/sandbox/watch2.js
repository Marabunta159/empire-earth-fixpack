// NOLIB
Process.setExceptionHandler(d=>{ if(d.type==='system') return false; let bt=''; try{ bt=Thread.backtrace(d.context,Backtracer.FUZZY).slice(0,10).map(a=>DebugSymbol.fromAddress(a).toString()).join(' | ');}catch(e){} send('EXC '+d.type+' at '+DebugSymbol.fromAddress(d.address)+' mem '+JSON.stringify(d.memory||{})+' eax='+d.context.eax+' ecx='+d.context.ecx+' edx='+d.context.edx+' esi='+d.context.esi+' edi='+d.context.edi+' :: '+bt); return false; });
send('watching');
