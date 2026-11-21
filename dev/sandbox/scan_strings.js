// scan the whole process for the given strings (ascii + utf16), report address + owning module
function hex(s) { return Array.from(s).map(c => ('0' + c.charCodeAt(0).toString(16)).slice(-2)).join(' '); }
function hex16(s) { return Array.from(s).map(c => ('0' + c.charCodeAt(0).toString(16)).slice(-2) + ' 00').join(' '); }
const ranges = Process.enumerateRanges('r--');
let out = [];
ARG.forEach(str => {
  [['a', hex(str)], ['w', hex16(str)]].forEach(([enc, pat]) => {
    ranges.forEach(r => {
      try {
        Memory.scanSync(r.base, r.size, pat).forEach(m => {
          const mod = Process.findModuleByAddress(m.address);
          let ctx = '';
          try { ctx = enc === 'a' ? m.address.readCString(60) : m.address.readUtf16String(60); } catch (e) {}
          out.push(str + ' [' + enc + '] @' + m.address + ' ' + (mod ? mod.name + '+0x' + m.address.sub(mod.base).toString(16) : '(heap) prot=' + r.protection) + '  "' + ctx + '"');
        });
      } catch (e) {}
    });
  });
});
out.forEach(l => send(l));
send({ done: true, hits: out.length });
