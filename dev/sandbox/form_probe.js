// formation probe (for net/probe.py): group constructor arguments at game start + every EEMChangeFormation that is executed
function rtti(p) { try { return p.readPointer().sub(4).readPointer().add(12).readPointer().add(8).readCString(); } catch (e) { return '?'; } }
function local() { return ptr(0x918E84).readU32(); }
function comm() { const c = ptr(0x91984C).readPointer(); return c.isNull() ? 'null' : 'mp=' + c.add(0x2e).readU8(); }
let n = 0;
Interceptor.attach(ptr(ARG.ctor), {
  onEnter(args) { this.g = this.context.ecx; this.a = args[0]; },
  onLeave() {
    if (n++ > 40) return;
    const players = []; for (let i = 0; i < 9; i++) players.push(ptr(0x918374 + i * 4).readPointer().toString());
    let extra = '';
    try { extra = ' argRtti=' + rtti(this.a); } catch (e) {}
    send('group ctor: this=' + this.g + ' arg=' + this.a + extra + ' formation=' + rtti(this.g.add(0x34).readPointer()) + ' local=' + local() + ' comm:' + comm() + ' players=' + players.join(','));
  }
});
Interceptor.attach(ptr(0x4b49bc), { onEnter() { const m = this.context.ecx; send('EEMChangeFormation: sender=' + m.add(0xa).readU8() + ' kind=' + m.add(0x10).readU32() + ' flag=' + m.add(0x14).readU8() + ' comm:' + comm()); } });
const pl = ptr(0x918374 + local() * 4).readPointer();
if (!pl.isNull()) { const g = pl.add(0x9bc).readPointer(); send('now: local=' + local() + ' player=' + pl + ' group=' + g + ' group+0x30=' + g.add(0x30).readPointer() + ' formation=' + rtti(g.add(0x34).readPointer()) + ' comm:' + comm()); }
send('formation probe armed');
