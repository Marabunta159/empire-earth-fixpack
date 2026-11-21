// NOLIB
send(JSON.stringify(Process.enumerateModules().map(m=>m.name).filter(n=>/fps|engine|dinput/i.test(n)))); send(hexdump(ptr(0x40059C),{length:16,header:false})); send({done:true});
