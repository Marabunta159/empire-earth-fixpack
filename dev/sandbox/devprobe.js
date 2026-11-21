// NOLIB
const m=Process.getModuleByName('DX7HRDisplay.dll'); const im=Process.getModuleByName('D3DImm.DLL');
const out=[]; let n=0;
Interceptor.attach(m.getExportByName('?DrawSky@DX7Rasterizer@@UAEJPAVGEModel@@KM_N@Z'),{onEnter(a){ if(n++>1) return;
  const r=this.context.ecx; const arr=r.add(0x6c).readPointer(); const so=arr.readPointer(); const dev=so.add(0x1c).readPointer(); const vt=dev.readPointer();
  out.push('rast '+r+' arr '+arr+' so '+so+' dev '+dev+' vt '+vt+' inIm '+(vt.compare(im.base)>=0&&vt.compare(im.base.add(im.size))<0));
  const vp=Memory.alloc(64); const gv=new NativeFunction(vt.add(15*4).readPointer(),'int',['pointer','pointer'],'stdcall'); const hr=gv(dev,vp);
  out.push('GetViewport hr '+hr+' '+[0,4,8,12].map(o=>vp.add(o).readU32()).join(',')+' z '+vp.add(16).readFloat()+','+vp.add(20).readFloat());
}});
const es=m.getExportByName('?EndScene@DX7Rasterizer@@UAEJK@Z');
Interceptor.attach(es,{onEnter(a){ if(n<2||n>3) return; n=9; const r=this.context.ecx; const dev=r.add(0x6c).readPointer().readPointer().add(0x1c).readPointer();
  const vp=Memory.alloc(64); const gv=new NativeFunction(dev.readPointer().add(15*4).readPointer(),'int',['pointer','pointer'],'stdcall'); gv(dev,vp);
  out.push('at EndScene viewport '+[0,4,8,12].map(o=>vp.add(o).readU32()).join(','));}});
setTimeout(()=>{send(out.join('\n'));send({done:true});},800);
