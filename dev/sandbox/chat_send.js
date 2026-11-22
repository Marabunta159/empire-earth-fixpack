// SYMS: ^UIManager::(UpdateUI|GetCurrentForm)$|^UIForm::(GetControlCount|GetControl|GetFormID)$|^UIControl::(GetId|FireTriggerEvent|GetTriggerEvent)$|^UIEditBox::(SetText|ProcessEnterKey|GetAllText|`vftable')|^UWideString::(UWideString|operator=)$
// type a line into the in-game chat box and "press enter" - all through the engine's own UI objects
const A = ARG;
const GetCurrentForm = tfn('UIManager::GetCurrentForm', 'pointer');
const GetControlCount = tfn('UIForm::GetControlCount', 'uint');
const GetControl = tfn('UIForm::GetControl', 'pointer', ['uint']);
const GetId = tfn('UIControl::GetId', 'uint');
const Fire = tfn('UIControl::FireTriggerEvent', 'void', ['uint']);
const GetTrig = tfn('UIControl::GetTriggerEvent', 'pointer', ['uint']);
const editVt = sym("UIEditBox::`vftable'");
const setTextName = Object.keys(SYM).filter(k => k.startsWith('UIEditBox::SetText'));
const procEnter = sym('UIEditBox::ProcessEnterKey');
let enterIdx = -1;
for (let i = 0; i < 80; i++) if (editVt.add(i * 4).readPointer().equals(procEnter)) { enterIdx = i; break; }
const defctor = new NativeFunction(ptr(A.defctor_iat).readPointer(), 'pointer', ['pointer'], 'thiscall');
const assign = new NativeFunction(ptr(A.assign_iat).readPointer(), 'pointer', ['pointer', 'pointer'], 'thiscall');
function edits(form) {
  const out = []; const n = GetControlCount(form);
  for (let i = 0; i < n; i++) { const c = GetControl(form, i); if (c.isNull()) continue; const vt = c.readPointer();
    // an edit box (or subclass): its vtable slot for ProcessEnterKey exists; test exact vtable or same slot target
    let isEdit = vt.equals(editVt); if (!isEdit) { try { isEdit = vt.add(enterIdx * 4).readPointer().equals(procEnter); } catch (e) {} }
    if (isEdit) out.push({ i, id: GetId(c), p: c }); }
  return out;
}
(async () => {
  const info = await onUI(mgr => { const f = GetCurrentForm(mgr); return { enterIdx, setText: setTextName, edits: edits(f).map(e => ({ i: e.i, id: e.id })) }; });
  send(JSON.stringify(info));
  if (A.text) {
    const r = await onUI(mgr => {
      const f = GetCurrentForm(mgr);
      const e = edits(f).find(e => e.id === A.edit) || edits(f)[0];
      if (!e) return 'no edit box';
      const us = Memory.alloc(0x40); defctor(us); assign(us, Memory.allocAnsiString(A.text));
      // SetText(UWideString const&) is the overload with a pointer argument: pick by trying the one whose rva is larger (0x6DF52)
      const st = new NativeFunction(sym(setTextName.sort((a, b) => SYM[b] - SYM[a])[0]), 'void', ['pointer', 'pointer'], 'thiscall');
      st(e.p, us);
      new NativeFunction(e.p.readPointer().add(enterIdx * 4).readPointer(), 'void', ['pointer'], 'thiscall')(e.p);
      return 'sent via edit id ' + e.id;
    });
    send(r);
  }
  finish();
})().catch(e => { send('ERR ' + e + '\n' + e.stack); finish(); });
