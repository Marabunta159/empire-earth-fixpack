// NOLIB
const eng=Process.getModuleByName('Low-Level Engine.dll');
const f=eng.getExportByName('?UpdateUI@UIManager@@UAEJABVGE2DPoint@@@Z');
send('UpdateUI first bytes: '+hexdump(f,{length:8,header:false,ansi:false})+' | fps module loaded: '+(Process.findModuleByName('ee_fps.dll')!==null)); send({done:true});
