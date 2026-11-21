// SYMS: ^UIManager::(UpdateUI|UpdateMouse|UpdateKeyboard)$
// make the game believe it is the active application (no focus change, no input injection)
const u32 = Process.getModuleByName('user32.dll');
const FindWindowW = new NativeFunction(u32.getExportByName('FindWindowW'), 'pointer', ['pointer', 'pointer']);
const GetWindowThreadProcessId = new NativeFunction(u32.getExportByName('GetWindowThreadProcessId'), 'uint', ['pointer', 'pointer']);
const PostMessageA = new NativeFunction(u32.getExportByName('PostMessageA'), 'int', ['pointer', 'uint', 'uint', 'uint']);
const IsIconic = new NativeFunction(u32.getExportByName('IsIconic'), 'int', ['pointer']);
const IsWindowVisible = new NativeFunction(u32.getExportByName('IsWindowVisible'), 'int', ['pointer']);
const GetWindow = new NativeFunction(u32.getExportByName('GetWindow'), 'pointer', ['pointer', 'uint']);
const GetTopWindow = new NativeFunction(u32.getExportByName('GetTopWindow'), 'pointer', ['pointer']);
const GetClassNameW = new NativeFunction(u32.getExportByName('GetClassNameW'), 'int', ['pointer', 'pointer', 'int']);
const GetWindowTextW = new NativeFunction(u32.getExportByName('GetWindowTextW'), 'int', ['pointer', 'pointer', 'int']);
function myWindows() {
  const out = []; const pidp = Memory.alloc(4); const buf = Memory.alloc(512);
  let h = GetTopWindow(ptr(0));
  while (!h.isNull()) {
    GetWindowThreadProcessId(h, pidp);
    if (pidp.readU32() === Process.id) {
      GetClassNameW(h, buf, 255); const cls = buf.readUtf16String();
      GetWindowTextW(h, buf, 255); const title = buf.readUtf16String();
      out.push({ h: h.toString(), cls, title, visible: IsWindowVisible(h), iconic: IsIconic(h) });
    }
    h = GetWindow(h, 2);
  }
  return out;
}
const wins = myWindows();
send(JSON.stringify(wins));
const main = wins.find(w => w.title === 'Empire Earth' && w.visible) || wins.find(w => w.visible);
let n = 0;
const hk = Interceptor.attach(sym('UIManager::UpdateUI'), { onEnter() { n++; } });
if (main && ARG !== 'probe') {
  PostMessageA(ptr(main.h), 0x001C, 1, 0);      // WM_ACTIVATEAPP TRUE
  PostMessageA(ptr(main.h), 0x0006, 1, 0);      // WM_ACTIVATE WA_ACTIVE
}
setTimeout(() => { hk.detach(); send({ done: true, updateUI_calls_in_2s: n, target: main ? main.h : null }); }, 2000);
