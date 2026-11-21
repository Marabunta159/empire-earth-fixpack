// NOLIB
const A = ARG;
const WORLD = ptr(0x918300);
const lookup = new NativeFunction(ptr(0x53b889), 'pointer', ['pointer', 'uint'], 'thiscall');
const execSelect = new NativeFunction(ptr(0x4BCF73), 'void', ['pointer'], 'thiscall');
const execUnselect = new NativeFunction(ptr(0x4BF9C7), 'void', ['pointer'], 'thiscall');
const execAttack = new NativeFunction(ptr(0x4B3958), 'void', ['pointer'], 'thiscall');
const players = i => ptr(A.players + i * 4).readPointer();
const localIdx = ptr(A.local).readU32(), pl = players(localIdx);
function list(p) { const out = []; let o = p.add(0x450).readPointer(); while (!o.isNull()) { out.push(o); o = o.add(0xc).readPointer(); } return out; }
const X = o => o.add(0x13c).readFloat(), Y = o => o.add(0x14c).readFloat(), type = o => o.add(0x2c).readPointer().add(0x4b8).readU32(), cls = o => o.add(0x2c).readPointer().add(0x4b4).readU32();
function idOf(o, pidx) { for (let off = 0; off < 0x80; off += 4) { const v = o.add(off).readU32(); if ((v >>> 24) === pidx && lookup(WORLD, v).equals(o)) return { off, v }; } return null; }
const me = list(pl).filter(o => type(o) === 32)[A.nth || 0];
const myId = idOf(me, localIdx);
// candidate targets: objects of other players with hp > 0 that are not buildings/ambient-trees; nearest first
let cands = [];
for (let i = 0; i < 9; i++) { if (i === localIdx) continue; const p = players(i); if (p.isNull()) continue; list(p).forEach(o => { const hp = o.add(0x3c).readS32(); if (hp > 0 && hp < 5000) cands.push({ o, i, d: Math.hypot(X(o) - X(me), Y(o) - Y(me)), hp, t: type(o), c: cls(o) }); }); }
cands = cands.filter(c => A.cls === undefined || c.c === A.cls).sort((a, b) => a.d - b.d);
send(JSON.stringify(cands.slice(0, 10).map(c => [c.i, c.t, c.c, +c.d.toFixed(1), c.hp])));
const tgt = cands[0];
const tId = idOf(tgt.o, tgt.i);
send(JSON.stringify({ me: me.toString(), myId, target: { p: tgt.o.toString(), player: tgt.i, type: tgt.t, cls: tgt.c, dist: +tgt.d.toFixed(1), hp: tgt.hp, id: tId } }));
// who writes the target's HP?
const writers = {};
const hpAddr = tgt.o.add(0x3c);
Process.setExceptionHandler(d => {
  if (d.type !== 'single-step' && d.type !== 'breakpoint' && d.type !== 'system') return false;
  if (!d.context.pc) return false;
  const k = DebugSymbol.fromAddress(d.context.pc).toString() + ' | ret ' + d.context.esp.readPointer();
  writers[k] = (writers[k] || 0) + 1;
  return true;
});
Process.enumerateThreads().forEach(t => { try { t.setHardwareWatchpoint(0, hpAddr, 4, 'w'); } catch (e) {} });
const slot = pl.add(0x464).readU8();
const ms = Memory.alloc(0x20); ms.add(0xa).writeU8(slot); ms.add(0x10).writeU32(myId.v);
const ma = Memory.alloc(0x20); ma.add(0xa).writeU8(slot); ma.add(0x10).writeU32(tId.v); ma.add(0x14).writeU8(0);
// run on the game's main/UI thread
const h = Interceptor.attach(Process.getModuleByName('user32.dll').getExportByName('PeekMessageA'), { onEnter() { h.detach(); execUnselect(ms); execSelect(ms); execAttack(ma); send('select+attack executed'); } });
const hits = [];
const dmgHook = Interceptor.attach(ptr(0x6172BC), { onEnter() {
  const sp = this.context.esp; const a1 = sp.add(4).readPointer(), dmg = sp.add(8).readS32(), a3 = sp.add(12).readU32(), a4 = sp.add(16).readU32();
  let fromMe = a1.equals(me);
    if (!fromMe && !a1.isNull()) { for (let off = 0; off < 0x400; off += 4) { let v; try { v = a1.add(off).readU32(); } catch (e) { break; }
        if (v === me.toUInt32() || v === myId.v) { fromMe = true; if (!globalThis.linkSent) { globalThis.linkSent = 1; send('projectile -> shooter link at +0x' + off.toString(16) + (v === myId.v ? ' (unit id)' : ' (pointer)')); } break; } } }
    if (this.context.ecx.equals(tgt.o) || fromMe) {
    let nd = dmg; if (fromMe && A.mult) { nd = Math.round(dmg * A.mult); sp.add(8).writeS32(nd); }
    hits.push({ target_is_tgt: this.context.ecx.equals(tgt.o), attacker_is_me: fromMe, a1: a1.toString(), dmg, new_dmg: nd, a3, a4, hp: this.context.ecx.add(0x3c).readS32() });
  } } });
const hp0 = tgt.hp; const trace = [];
const iv = setInterval(() => trace.push(tgt.o.add(0x3c).readS32()), 1000);
setTimeout(() => { clearInterval(iv); Process.enumerateThreads().forEach(t => { try { t.unsetHardwareWatchpoint(0); } catch (e) {} }); dmgHook.detach(); send(JSON.stringify({ hits, hp_before: hp0, hp_per_second: trace, me_pos: [X(me), Y(me)].map(v => +v.toFixed(2)), writers })); send({ done: true }); }, (A.secs || 20) * 1000);
