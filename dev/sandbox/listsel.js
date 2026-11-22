// SYMS: ^UIManager::(UpdateUI|GetCurrentForm)$|^UIForm::(GetControlCount|GetControl|GetFormID)$|^UIControl::GetId$|^UIListBox<UWideString>::(ChangeSelectionIndex|GetLineCount|GetHasSelection)$
// ARG: {id: 394, index: 0}  - select a line of a list box on the current form (in-process, no mouse / keyboard)
const GetCurrentForm = tfn('UIManager::GetCurrentForm', 'pointer');
const GetControlCount = tfn('UIForm::GetControlCount', 'uint');
const GetControl = tfn('UIForm::GetControl', 'pointer', ['uint']);
const GetFormID = tfn('UIForm::GetFormID', 'uint');
const GetId = tfn('UIControl::GetId', 'uint');
const Lines = tfn('UIListBox<UWideString>::GetLineCount', 'uint');
const Cur = c => (c.add(0x133).readU8() ? c.add(0x120).readS32() : -1);          // selected line or -1
const Select = tfn('UIListBox<UWideString>::ChangeSelectionIndex', 'void', ['int']);
onUI(mgr => {
  const form = GetCurrentForm(mgr);
  const n = GetControlCount(form);
  for (let i = 0; i < n; i++) {
    const c = GetControl(form, i);
    if (c.isNull() || GetId(c) !== ARG.id) continue;
    const before = Cur(c);
    const lines = Lines(c);
    if (lines > ARG.index) Select(c, ARG.index);
    return { form: GetFormID(form), lines, before, after: Cur(c) };
  }
  return { form: GetFormID(form), error: 'list not found' };
}).then(r => { send(JSON.stringify(r)); finish(); }).catch(e => { send('ERR ' + e); finish(); });
