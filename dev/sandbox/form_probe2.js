// which EEPlayer fields are already valid when its groups are constructed, and which tell human from computer?
const seen = {};
function dump(p) { const o = []; for (let i = 0; i < 0xa0; i += 4) o.push(p.add(i).readU32().toString(16)); return o.join(' '); }
Interceptor.attach(ptr(ARG.ctor), { onEnter(args) { const k = args[0].toString(); if (!seen[k]) { seen[k] = dump(args[0]); send('ctor-time ' + k + ': ' + seen[k]); } } });
rpc.exports = { after() { const out = ['local=' + ptr(0x918E84).readU32()];
  for (let i = 0; i < 9; i++) { const p = ptr(0x918374 + i * 4).readPointer(); if (!p.isNull()) out.push('player[' + i + '] ' + p + ': ' + dump(p)); } return out.join('\n'); } };
send('probe2 armed');
