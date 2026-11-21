// NOLIB
const u=Process.getModuleByName('user32.dll');
const Enum=new NativeFunction(u.getExportByName('EnumWindows'),'int',['pointer','pointer']);
const GetPid=new NativeFunction(u.getExportByName('GetWindowThreadProcessId'),'uint',['pointer','pointer']);
const Vis=new NativeFunction(u.getExportByName('IsWindowVisible'),'int',['pointer']);
const Send=new NativeFunction(u.getExportByName('SendMessageA'),'int',['pointer','uint','uint','pointer']);
const pid=Process.id; let hw=null;
const cb=new NativeCallback((h,l)=>{const p=Memory.alloc(4);GetPid(h,p);if(p.readU32()===pid&&Vis(h)){hw=h;return 0;}return 1;},'int',['pointer','pointer']);
Enum(cb,NULL);
send('hwnd '+hw);
Send(hw,0x1C,1,ptr(0)); // WM_ACTIVATEAPP
Send(hw,0x06,1,ptr(0)); // WM_ACTIVATE
Send(hw,0x07,0,ptr(0)); // WM_SETFOCUS
send({done:true});
