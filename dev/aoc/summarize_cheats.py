import glob, os, struct, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdmp import Dump

def vm(dm):
    if 22 not in dm.streams: return None
    rva, size = dm.streams[22]
    d = dm.d[rva:rva+size]
    rev, flags, pf = struct.unpack_from('<HHI', d, 0)
    vals = struct.unpack_from('<%dQ' % ((size-8)//8), d, 8)
    names = ['PeakWS','WS','QPeakPaged','QPaged','QPeakNonPaged','QNonPaged','Pagefile','PeakPagefile','PeakVirtual','Virtual','Private','PrivateWS','SharedCommit']
    return rev, flags, dict(zip(names, vals))

for p in sorted(glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\CrashDumps\EE-Cheats.exe.*.dmp')), key=os.path.getmtime):
    dm = Dump(p)
    e = dm.exc; c = dm.ctx(e['ctx_rva'])
    t = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%m-%d %H:%M')
    kind = {0:'R',1:'W',8:'X'}.get(e['params'][0],'?') if e['params'] else '?'
    print('-'*110)
    print('%s %s  tid=%d  %s  AV %s @%08X' % (t, os.path.basename(p), e['tid'], dm.describe(e['addr']), kind, e['params'][1] if len(e['params'])>1 else 0))
    v = vm(dm)
    if v:
        rev, flags, k = v
        print('   VM: Virtual=%d MB PeakVirtual=%d MB Private=%d MB WS=%d MB Pagefile=%d MB (rev %d flags %X)' % (k['Virtual']>>20, k['PeakVirtual']>>20, k.get('Private',0)>>20, k['WS']>>20, k['Pagefile']>>20, rev, flags))
    for a, val in dm.stack_scan(c["esp"], 14):
        print('     %s' % dm.describe(val))
