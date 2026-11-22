// SYMS: ^UIManager::(UpdateUI|GetCurrentForm|GetFormCount|GetVisibleFormCount)$|^UIForm::(GetControlCount|GetControl|GetFormID)$|^UIControl::(GetId|GetStringTableID|GetRectangle|FireTriggerEvent|GetTriggerEvent)$
// ARG: {click:{id|str|i}, trig:0x3F0, wait:ms, dump:true}  - in-process UI automation (no mouse / keyboard / focus)
const GetCurrentForm = tfn('UIManager::GetCurrentForm', 'pointer');
const GetControlCount = tfn('UIForm::GetControlCount', 'uint');
const GetControl = tfn('UIForm::GetControl', 'pointer', ['uint']);
const GetFormID = tfn('UIForm::GetFormID', 'uint');
const GetId = tfn('UIControl::GetId', 'uint');
const GetStrId = tfn('UIControl::GetStringTableID', 'uint');
const GetRect = tfn('UIControl::GetRectangle', 'pointer');
const Fire = tfn('UIControl::FireTriggerEvent', 'void', ['uint']);
const GetTrig = tfn('UIControl::GetTriggerEvent', 'pointer', ['uint']);
const VT = {};
[['966ac', 'Button'], ['956b0', 'Bitmap'], ['9545c', 'Label?']].forEach(([o, n]) => VT[o] = n);
function controls(form) {
  const out = [];
  const n = GetControlCount(form);
  for (let i = 0; i < n && i < 600; i++) {
    const c = GetControl(form, i);
    if (c.isNull()) continue;
    const vt = c.readPointer();
    const mod = Process.findModuleByAddress(vt);
    const off = mod ? vt.sub(mod.base).toString(16) : vt.toString();
    const r = GetRect(c);
    out.push({ i, p: c, vt: (mod && mod.name.toLowerCase().startsWith('low') ? 'E+' : 'X+') + off, id: GetId(c), str: GetStrId(c),
               rect: [r.readS32(), r.add(4).readS32(), r.add(8).readS32(), r.add(12).readS32()], click: !GetTrig(c, 0x3F0).isNull() });
  }
  return out;
}
function dump(mgr) {
  const form = GetCurrentForm(mgr);
  if (form.isNull()) return { formId: -1, controls: [] };
  return { formId: GetFormID(form), form: form.toString(), controls: controls(form).map(c => Object.assign({}, c, { p: c.p.toString() })) };
}
async function main() {
  const a = ARG || {};
  let res = {};
  if (a.click) {
    res.click = await onUI(mgr => {
      const form = GetCurrentForm(mgr);
      const cs = controls(form);
      const c = cs.find(c => (a.click.id !== undefined && c.id === a.click.id) || (a.click.str !== undefined && c.str === a.click.str) || (a.click.i !== undefined && c.i === a.click.i));
      if (!c) return 'control not found on form ' + GetFormID(form);
      const trig = a.trig || 0x3F0;
      if (GetTrig(c.p, trig).isNull()) return 'control has no trigger 0x' + trig.toString(16);
      Fire(c.p, trig);
      return 'fired 0x' + trig.toString(16) + ' on id ' + c.id + ' (form ' + GetFormID(form) + ')';
    });
  }
  if (a.wait) await new Promise(r => setTimeout(r, a.wait));
  if (a.dump !== false) res.ui = await onUI(dump);
  send(JSON.stringify(res));
  finish();
}
main().catch(e => { send('ERR ' + e + '\n' + e.stack); finish(); });
