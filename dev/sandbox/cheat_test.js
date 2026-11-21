// SYMS: ^UIManager::UpdateUI$|^UWideString::UWideString$|^UWideString::~UWideString$
// ARG: addresses + {texts:[...]}: run cheat texts through the game's own lookup + EEMCheatCode message
const A = ARG;
const ctors = Object.keys(SYM).filter(k => k.startsWith('UWideString::UWideString'));
const opnew = new NativeFunction(ptr(A.opnew), 'pointer', ['uint'], 'mscdecl');
const lookup = new NativeFunction(ptr(A.lookup), 'void', ['pointer', 'pointer', 'pointer', 'pointer'], 'thiscall');
const msgctor = new NativeFunction(ptr(A.msgctor), 'pointer', ['pointer', 'uint', 'uint'], 'thiscall');
const assign = new NativeFunction(ptr(A.assign_iat).readPointer(), 'pointer', ['pointer', 'pointer'], 'thiscall');
const defctor = new NativeFunction(ptr(A.defctor_iat).readPointer(), 'pointer', ['pointer'], 'thiscall');
function local() { return ptr(A.players + ptr(A.local).readU32() * 4).readPointer(); }
function objs() { const pl = local(); let o = pl.add(0x450).readPointer(), n = 0; const c = [], t = {}; while (!o.isNull() && n < 9000) { n++; const id = o.add(0x2c).readPointer().add(0x4b8).readU32(); t[id] = (t[id] || 0) + 1; if (id === 32 || id === 480) c.push([id, Math.round(o.add(0x13c).readFloat() * 100) / 100, Math.round(o.add(0x14c).readFloat() * 100) / 100]); o = o.add(0xc).readPointer(); } return { n, citizens: c, types: t }; }
function snap() { return new Uint32Array(local().readByteArray(0x1400)); }
function cam() { return [ptr(A.cam + 0x40).readFloat(), ptr(A.cam + 0x44).readFloat()].map(v => Math.round(v * 100) / 100); }
const out = { flag: ptr(A.flag).readU8(), mp: ptr(A.comm).readPointer().add(A.mp_off).readU8(), localIdx: ptr(A.local).readU32(), cam: cam(), steps: [] };
async function step(text) {
  const before = objs(); const s0 = snap();
  const r = await onUI(mgr => {
    const us = Memory.alloc(0x40); defctor(us);
    assign(us, Memory.allocAnsiString(text));
    const id = Memory.alloc(4), arg = Memory.alloc(4); id.writeU32(0); arg.writeU32(0);
    lookup(ptr(A.cheatMgr).readPointer(), us, id, arg);
    const res = { text, id: id.readU32(), arg: arg.readU32() };
    if (res.id) {
      const msg = opnew(0x18); msgctor(msg, res.id, res.arg);
      const comm = ptr(A.comm).readPointer();
      new NativeFunction(comm.readPointer().add(0x18).readPointer(), 'int', ['pointer', 'pointer', 'uint'], 'thiscall')(comm, msg, 0xff);
    }
    return res;
  });
  await new Promise(r2 => setTimeout(r2, 2000));
  const after = objs(); const s1 = snap();
  const diffs = [];
  for (let i = 0; i < s0.length; i++) if (s0[i] !== s1[i]) { const d = (s1[i] - s0[i]) | 0; if (Math.abs(d) >= 500 && Math.abs(d) <= 200000) diffs.push('+0x' + (i * 4).toString(16) + ':' + s0[i] + '->' + s1[i]); }
  const newc = after.citizens.slice(0, Math.max(0, after.citizens.length - before.citizens.length));
  const nt = {}; for (const k in after.types) { const dd = after.types[k] - (before.types[k] || 0); if (dd) nt[k] = dd; }
  out.steps.push(Object.assign(r, { new_by_type: nt, objects: before.n + ' -> ' + after.n, citizens: before.citizens.length + ' -> ' + after.citizens.length, new_citizens: newc.slice(0, 12), player_field_changes: diffs.slice(0, 12) }));
}
(async () => { for (const t of A.texts) await step(t); send(JSON.stringify(out)); finish(); })().catch(e => { send('ERR ' + e + '\n' + e.stack); finish(); });
