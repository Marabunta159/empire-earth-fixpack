// common helpers for sandbox scripts (prepended by sbx.py)
const eng = Process.getModuleByName('Low-Level Engine.dll');
const exe = Process.getModuleByName(EXE);
function sym(n) { if (!(n in SYM)) throw new Error('missing symbol ' + n + ' (add it to the // SYMS: line)'); return eng.base.add(SYM[n]); }
function tfn(n, ret, args) { return new NativeFunction(sym(n), ret, ['pointer'].concat(args || []), 'thiscall'); }
// run fn once on the UI thread (inside UIManager::UpdateUI); calls cb(result, uiManager)
let _uiHook = null;
const _jobs = [];
function onUI(fn) {
  return new Promise((resolve, reject) => {
    _jobs.push({ fn, resolve, reject });
    if (!_uiHook) {
      _uiHook = Interceptor.attach(sym('UIManager::UpdateUI'), {
        onEnter() {
          const mgr = this.context.ecx;
          while (_jobs.length) { const j = _jobs.shift(); try { j.resolve(j.fn(mgr)); } catch (e) { j.reject(e); } }
        }
      });
    }
  });
}
// UWideString: read as text (layout probed at runtime: pointer at +4, try utf16 then ansi)
function ustr(p) {
  try {
    const q = p.add(4).readPointer();
    if (q.isNull()) return '';
    const w = q.readUtf16String(200);
    return w;
  } catch (e) { return '?'; }
}
function finish(extra) { if (_uiHook) { _uiHook.detach(); _uiHook = null; } send(Object.assign({ done: true }, extra || {})); }
