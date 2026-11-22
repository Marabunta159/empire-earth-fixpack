// NOLIB
Process.setExceptionHandler(d=>{ let bt=''; try{ bt=Thread.backtrace(d.context,Backtracer.FUZZY).slice(0,8).map(a=>DebugSymbol.fromAddress(a).toString()).join(' | ');}catch(e){} send('EXC '+d.type+' at '+d.address+' mem '+JSON.stringify(d.memory||{})+' eax='+d.context.eax+' ecx='+d.context.ecx+' esi='+d.context.esi+' edi='+d.context.edi+' :: '+bt); return false; });
send('watching');
