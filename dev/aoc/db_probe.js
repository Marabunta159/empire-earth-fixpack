const exe = Process.enumerateModules()[0];
function where(a) { const m = Process.findModuleByAddress(a); return m ? m.name + '+' + a.sub(m.base).toString(16) : a.toString(); }
let depth = 0;
Interceptor.attach(ptr(0x5cbdf0), { onEnter() { depth = 1; const us = a => { try { return ptr(a).add(4).readPointer().readCString(); } catch (e) { return '?'; } }; send('loader 5cbdf0: name@8e7f10="' + us(0x8e7f10) + '" name@8e7f20="' + us(0x8e7f20) + '" bytes ' + Array.from(new Uint8Array(ptr(0x8e7f10).readByteArray(16))).map(x => ('0' + x.toString(16)).slice(-2)).join('')); }, onLeave(r) { depth = 0; send('loader 5cbdf0 -> ' + r.toInt32()); } });
let n = 0;
Interceptor.attach(ptr(0x5ce10e), { onLeave(r) { if (depth) send('  record ' + (n++) + ' -> ' + r.toInt32()); } });
send('ready');
