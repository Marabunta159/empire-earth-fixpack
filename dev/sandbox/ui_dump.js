// SYMS: ^UIManager::(UpdateUI|GetCurrentForm)$|^UIForm::(GetControlCount|GetControl|GetFormID)$|^UIControl::(GetType|GetId|GetStringTableID|GetRectangle)$|^UIButton::GetGEText$|^GEText::GetText$
const GetCurrentForm = tfn('UIManager::GetCurrentForm', 'pointer');
const GetControlCount = tfn('UIForm::GetControlCount', 'uint');
const GetControl = tfn('UIForm::GetControl', 'pointer', ['uint']);
const GetFormID = tfn('UIForm::GetFormID', 'uint');
const GetId = tfn('UIControl::GetId', 'uint');
const GetStrId = tfn('UIControl::GetStringTableID', 'uint');
const GetRect = tfn('UIControl::GetRectangle', 'pointer');
const GetGEText = tfn('UIButton::GetGEText', 'pointer');
const GetText = tfn('GEText::GetText', 'pointer');
onUI(mgr => {
  const form = GetCurrentForm(mgr);
  const out = { mgr: mgr.toString(), form: form.toString(), formId: form.isNull() ? -1 : GetFormID(form), controls: [] };
  if (form.isNull()) return out;
  const n = GetControlCount(form);
  for (let i = 0; i < n && i < 400; i++) {
    const c = GetControl(form, i);
    if (c.isNull()) continue;
    const vt = c.readPointer();
    // virtual GetType: find via vtable call is risky; use exported non-virtual wrapper address only if it is not virtual
    let type = -1;
    try { type = new NativeFunction(sym('UIControl::GetType'), 'uint', ['pointer'], 'thiscall')(c); } catch (e) {}
    const r = GetRect(c);
    const rect = [r.readFloat(), r.add(4).readFloat(), r.add(8).readFloat(), r.add(12).readFloat()].map(v => Math.round(v * 1000) / 1000);
    const mod = Process.findModuleByAddress(vt);
    out.controls.push({ i, p: c.toString(), vt: (mod ? mod.name.slice(0, 9) + '+' + vt.sub(mod.base).toString(16) : vt.toString()), id: GetId(c), str: GetStrId(c), rect });
  }
  return out;
}).then(o => { send(JSON.stringify(o)); finish(); }).catch(e => { send('ERR ' + e + '\n' + e.stack); finish(); });
