// persistent probe: NPIMPublish calls + which bind path is taken (NeoEE cave vs. original bind)
const tcp = Process.getModuleByName('TCP Protocol.dll');
function where(a) { const m = Process.findModuleByAddress(a); return m ? m.name + '+' + a.sub(m.base).toString(16) : a.toString(); }
Interceptor.attach(tcp.getExportByName('NPIMPublish'), {
  onEnter(a) {
    const sp = this.context.esp;
    if (ARG.force0) sp.add(8 * 4).writeU8(0);
    const w = []; for (let i = 1; i <= 10; i++) w.push(sp.add(i * 4).readU32().toString(16));
    send('NPIMPublish args=' + w.join(',') + (ARG.force0 ? '  (local flag forced to 0)' : ''));
  },
  onLeave(r) { send('NPIMPublish -> ' + r.toInt32()); }
});
Interceptor.attach(tcp.base.add(0x9000), function () { send('  NEO cave entered (punch_hole) socket=' + this.context.esi); });
Interceptor.attach(tcp.base.add(0x91FF), function () { send('  NEO cave2 entered (get_peer)'); });
if (ARG.patched) Interceptor.attach(tcp.base.add(0x9097), function () { send('  LOCAL path: plain bind, socket=' + this.context.esi); });
send('probe ready tcp ' + tcp.base + ' neoee.dll loaded: ' + (Process.findModuleByName('neoee.dll') !== null));
