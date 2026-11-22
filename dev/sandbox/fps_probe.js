// SYMS: ^GEViewport::(SetCamera|GetCamera|GetFieldOfView|GetFrontClippingDistance|GetRearClippingDistance|SetFieldOfView|SetFrontClippingDistance|SetRearClippingDistance)$|^GETransformation::(GetPosition|GetYaw|GetPitch|GetRoll|SetPosition|SetOrientationYPR|SizeOf)(#\d)?$
const A = ARG || {};
const getPos = new NativeFunction(sym(Object.keys(SYM).find(k => k.startsWith('GETransformation::GetPosition') && SYM[k] === Math.max(...Object.keys(SYM).filter(x => x.startsWith('GETransformation::GetPosition')).map(x => SYM[x])))), 'void', ['pointer', 'pointer'], 'thiscall');
const fyaw = tfn('GETransformation::GetYaw', 'float'), fpitch = tfn('GETransformation::GetPitch', 'float'), froll = tfn('GETransformation::GetRoll', 'float');
const fov = tfn('GEViewport::GetFieldOfView', 'float'), fclip = tfn('GEViewport::GetFrontClippingDistance', 'float'), rclip = tfn('GEViewport::GetRearClippingDistance', 'float');
function pos(t) { const p = Memory.alloc(12); getPos(t, p); return [p.readFloat(), p.add(4).readFloat(), p.add(8).readFloat()].map(v => +v.toFixed(2)); }
const seen = {}; let calls = 0;
const h = Interceptor.attach(sym('GEViewport::SetCamera'), {
  onEnter(args) {
    calls++;
    const vp = this.context.ecx.toString(), t = this.context.esp.add(4).readPointer();
    if (!seen[vp]) seen[vp] = { n: 0, tid: this.threadId, caller: DebugSymbol.fromAddress(this.returnAddress).toString() };
    const s = seen[vp]; s.n++;
    s.pos = pos(t); s.ypr = [fyaw(t), fpitch(t), froll(t)].map(v => +(v * 57.2958).toFixed(1));
    s.fov = +fov(this.context.ecx).toFixed(3); s.clip = [fclip(this.context.ecx), rclip(this.context.ecx)].map(v => +v.toFixed(2));
    s.mat = Array.from({ length: 16 }, (_, i) => +t.add(i * 4).readFloat().toFixed(3));
  }
});
setTimeout(() => { h.detach(); send(JSON.stringify({ calls_2s: calls, viewports: seen }, null, 1)); send({ done: true }); }, 2000);
