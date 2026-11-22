// exception logger (for net/probe.py): first access violations with module-relative backtrace
let n = 0;
function where(a) { const m = Process.findModuleByAddress(a); return m ? m.name + '+0x' + a.sub(m.base).toString(16) : a.toString(); }
Process.setExceptionHandler(d => {
  if (d.type !== 'system' && n++ < 6) {
    let bt = [];
    try { bt = Thread.backtrace(d.context, Backtracer.FUZZY).slice(0, 14).map(where); } catch (e) { bt = ['bt failed ' + e]; }
    const c = d.context;
    send(JSON.stringify({ type: d.type, at: where(d.address), mem: d.memory ? d.memory.operation + ' ' + d.memory.address : null,
      regs: { eax: c.eax, ecx: c.ecx, edx: c.edx, ebx: c.ebx, esi: c.esi, edi: c.edi, esp: c.esp, ebp: c.ebp }, thread: Process.getCurrentThreadId(), bt }));
  }
  return false;
});
send('exception logger armed');
