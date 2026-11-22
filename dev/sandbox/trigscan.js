// SYMS: ^UIManager::(UpdateUI|GetCurrentForm)$|^UIForm::(GetControlCount|GetControl|GetFormID)$|^UIControl::(GetId|GetTriggerEvent|FireTriggerEvent)$
// ARG: {fire:{i:<control index>, trig:<id>}}  - list trigger events of every control on the current form, optionally fire one
const GetCurrentForm = tfn('UIManager::GetCurrentForm', 'pointer');
const GetControlCount = tfn('UIForm::GetControlCount', 'uint');
const GetControl = tfn('UIForm::GetControl', 'pointer', ['uint']);
const GetTrig = tfn('UIControl::GetTriggerEvent', 'pointer', ['uint']);
const Fire = tfn('UIControl::FireTriggerEvent', 'void', ['uint']);
onUI(mgr => {
  const f = GetCurrentForm(mgr); const out = [];
  const n = GetControlCount(f);
  for (let i = 0; i < n && i < 40; i++) { const c = GetControl(f, i); if (c.isNull()) continue; const t = [];
    for (let k = 0x3e0; k < 0x420; k++) if (!GetTrig(c, k).isNull()) t.push('0x' + k.toString(16));
    out.push(i + ':' + t.join('/')); }
  if (ARG && ARG.fire) { Fire(GetControl(f, ARG.fire.i), ARG.fire.trig); out.push('fired'); }
  return out;
}).then(r => { send(r.join('  ')); finish(); }).catch(e => { send('ERR ' + e); finish(); });
