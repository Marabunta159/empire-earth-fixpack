"""pretty-print ui.js output; resolves string ids via Language.dll"""
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langstr
st = langstr.strings(r'<project>\sandbox\Empire Earth\Language.dll')
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('{'):
        print(line[:400]); continue
    o = json.loads(line)
    if 'click' in o: print('CLICK:', o['click'])
    ui = o.get('ui')
    if not ui: continue
    print('FORM %s  (%d controls)' % (ui['formId'], len(ui['controls'])))
    for c in ui['controls']:
        t = st.get(c['str'], '') if c['str'] else ''
        if c['click'] or t or 'ALL' in sys.argv:
            print('  i=%-3d id=%-5d %-9s %s str=%-6d %r %s' % (c['i'], c['id'], c['vt'], 'CLICK' if c['click'] else '     ', c['str'], t[:50], c['rect']))
