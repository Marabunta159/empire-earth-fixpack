// SYMS: ^GEViewport::(SetCamera|SetFrontClippingDistance|SetRearClippingDistance|SetFieldOfView)$|^GETransformation::(SetPosition|SetOrientationYPR|GetYaw)(#\d)?$
const A = ARG;
function pick(prefix, maxRva) { const ks = Object.keys(SYM).filter(k => k.startsWith(prefix)); ks.sort((a, b) => SYM[a] - SYM[b]); return sym(maxRva ? ks[ks.length - 1] : ks[0]); }
const setPos = new NativeFunction(pick('GETransformation::SetPosition', true), 'void', ['pointer', 'float', 'float', 'float'], 'thiscall');
const setYPR = new NativeFunction(pick('GETransformation::SetOrientationYPR', true), 'void', ['pointer', 'float', 'float', 'float'], 'thiscall');
const getYaw = tfn('GETransformation::GetYaw', 'float');
const fclip = tfn('GEViewport::SetFrontClippingDistance', 'void', ['float']);
const rclip = tfn('GEViewport::SetRearClippingDistance', 'void', ['float']);
const setFov = tfn('GEViewport::SetFieldOfView', 'void', ['float']);
// pick a unit of the local player by object type
const pl = ptr(A.players + ptr(A.local).readU32() * 4).readPointer();
let o = pl.add(0x450).readPointer(), unit = null, k = 0;
while (!o.isNull()) { if (o.add(0x2c).readPointer().add(0x4b8).readU32() === A.type && k++ === (A.nth || 0)) { unit = o; break; } o = o.add(0xc).readPointer(); }
if (!unit) { send('no unit'); send({ done: true }); }
const T = unit.add(0x130);
const mine = Memory.alloc(0x80);
let applied = 0, clipped = false;
const h = Interceptor.attach(sym('GEViewport::SetCamera'), {
  onEnter(args) {
    const src = this.context.esp.add(4).readPointer();
    Memory.copy(mine, src, 0x40);
    const x = T.add(0x0c).readFloat(), y = T.add(0x1c).readFloat(), z = T.add(0x2c).readFloat();
    const yaw = getYaw(T) + (A.yawOff || 0) * Math.PI / 180;
    setYPR(mine, yaw, (A.pitch || -5) * Math.PI / 180, 0);
    // camera slightly behind the eyes so the own unit is not in view
    const back = A.back || 0.0;
    setPos(mine, x + Math.sin(yaw) * back, y - Math.cos(yaw) * back, z + (A.eye || 0.7));
    this.context.esp.add(4).writePointer(mine);
    if (!clipped) { fclip(this.context.ecx, A.near || 0.05); rclip(this.context.ecx, A.far || 60); if (A.fov) setFov(this.context.ecx, A.fov); clipped = true; }
    applied++;
  }
});
send('unit ' + unit + ' at ' + [T.add(0xc).readFloat(), T.add(0x1c).readFloat(), T.add(0x2c).readFloat()].map(v => v.toFixed(2)).join(',') + ' yaw ' + (getYaw(T) * 57.3).toFixed(1));
setTimeout(() => { h.detach(); send({ done: true, applied }); }, (A.secs || 8) * 1000);
