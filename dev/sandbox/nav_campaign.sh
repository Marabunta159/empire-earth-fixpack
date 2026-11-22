#!/bin/bash
# in-process navigation: main menu -> single player -> campaign -> Greek campaign -> first scenario -> start
python sbx.py run ui.js '{"click":{"str":8550},"wait":2500,"dump":false}' | python uishow.py
python sbx.py run ui.js '{"click":{"id":358},"wait":3000,"dump":false}' | python uishow.py
python sbx.py run ui.js '{"click":{"id":398},"wait":4000,"dump":false}' | python uishow.py
python sbx.py run ui.js '{"click":{"id":2958},"wait":15000,"dump":false}' | python uishow.py
python sbx.py run ui.js '{"click":{"id":554},"wait":25000}' | python uishow.py | head -4
