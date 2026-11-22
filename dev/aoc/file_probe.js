// which files does the game open (db / ssa), and what is the file object handed to the tech tree loader?
const k32 = Process.getModuleByName('KERNELBASE.dll');
function hookCreate(name, wide) {
  Interceptor.attach(k32.getExportByName(name), {
    onEnter(a) { this.n = wide ? a[0].readUtf16String() : a[0].readAnsiString(); },
    onLeave(r) { if (this.n && /\.ssa|\db\|techtree|\.dat$/i.test(this.n)) send(name + ' ' + this.n + ' -> ' + (r.toInt32() === -1 ? 'FAILED' : 'ok')); }
  });
}
hookCreate('CreateFileW', true);
function rtti(obj) { try { const vt = obj.readPointer(); const col = vt.sub(4).readPointer(); const td = col.add(12).readPointer(); return td.add(8).readCString(); } catch (e) { return '?' + e; } }
Interceptor.attach(ptr(0x5cbdf0), { onEnter() {
  const f = this.context.esp.add(4).readPointer();
  send('techtree loader: file object ' + f + ' class ' + rtti(f) + ' bytes ' + Array.from(new Uint8Array(f.readByteArray(0x40))).map(x => ('0' + x.toString(16)).slice(-2)).join(''));
} });
send('ready');
