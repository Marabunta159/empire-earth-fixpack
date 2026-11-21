// SYMS: ^UIManager::(UpdateUI|UpdateMouse|UpdateKeyboard|GetCurrentForm)$|^ISMouse::(Refresh|Suspend|Resume)$|^ISKeyboard::(Refresh|Suspend|Resume)$
const cnt = {};
function count(name, addr) { cnt[name] = 0; Interceptor.attach(addr, { onEnter() { cnt[name]++; if (!cnt['tid_' + name]) cnt['tid_' + name] = this.threadId; } }); }
const u32 = Process.getModuleByName('user32.dll');
['PeekMessageA', 'GetMessageA', 'WaitMessage', 'MsgWaitForMultipleObjects', 'GetForegroundWindow', 'GetActiveWindow', 'GetFocus'].forEach(n => { try { count(n, u32.getExportByName(n)); } catch (e) {} });
Object.keys(SYM).forEach(n => count(n, sym(n)));
const GetForegroundWindow = new NativeFunction(u32.getExportByName('GetForegroundWindow'), 'pointer', []);
const GetWindowThreadProcessId = new NativeFunction(u32.getExportByName('GetWindowThreadProcessId'), 'uint', ['pointer', 'pointer']);
setTimeout(() => {
  const pidp = Memory.alloc(4);
  GetWindowThreadProcessId(GetForegroundWindow(), pidp);
  send(JSON.stringify({ counts_in_3s: cnt, fg_pid: pidp.readU32(), my_pid: Process.id, threads: Process.enumerateThreads().length }));
  Interceptor.detachAll();
  send({ done: true });
}, 3000);
