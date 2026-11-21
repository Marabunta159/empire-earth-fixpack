// log every ESVerify failure (expression, line, file) with a backtrace; also native error + process exit
const eng = Process.getModuleByName('Low-Level Engine.dll');
function where(a) { const m = Process.findModuleByAddress(a); return m ? m.name + '+' + a.sub(m.base).toString(16) : a.toString(); }
const v = eng.enumerateExports().filter(e => e.name.indexOf('ESVerify@@') >= 0 || e.name.indexOf('ESAssert') >= 0 || e.name.indexOf('ESFatal') >= 0 || e.name.indexOf('ESRecordNativeError') >= 0);
v.forEach(e => {
  Interceptor.attach(e.address, { onEnter(a) {
    const sp = this.context.esp; let s = e.name.split('@@')[0];
    if (e.name.indexOf('ESVerify') >= 0) { try { s += ' expr="' + sp.add(4).readPointer().readCString() + '" line=' + sp.add(8).readU32() + ' file="' + sp.add(12).readPointer().readCString() + '"'; } catch (x) { s += ' ?'; } }
    else s += ' arg=' + sp.add(4).readU32();
    send(s + '\n   bt ' + Thread.backtrace(this.context, Backtracer.FUZZY).slice(0, 12).map(where).join(' < '));
  } });
});
send('hooks: ' + v.map(e => e.name.split('@@')[0]).join(', '));
