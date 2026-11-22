from pathlib import Path
import ast,re,sys
p=Path(sys.argv[1])/'urano/native_owner_web_gateway.py'
tree=ast.parse(p.read_text())
names=['_edit_read_timeout','_review_read_timeout']
scope={'re':re}
for name in names:
 matches=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name]
 assert len(matches)==1,name
 exec(compile(ast.Module(body=matches,type_ignores=[]),str(p),'exec'),scope)
ed=scope['_edit_read_timeout']
review=scope['_review_read_timeout']
yes=[
 ('PATCH','/api/v1/edit/shot','','json',95),
 ('GET','/api/v1/edit/shot','index=1','json',95),
 ('GET','/api/v1/edit/shot','index=9999','json',95),
 ('GET','/api/v1/edit/shot/frame','index=1&choice=0&revision='+'a'*20,'shot-frame',95),
 ('GET','/api/v1/edit/timeline','kind=music','json',95),
 ('GET','/api/v1/wizard/review/preview/30','v=abc123','review-media',75),
 ('GET','/api/v1/wizard/review/preview/0','','review-media',75),
]
no=[
 ('POST','/api/v1/edit/shot','','json'),
 ('PATCH','/api/v1/edit/shot','index=1','json'),
 ('PATCH','/api/v1/edit/shot','revision=stale','json'),
 ('GET','/api/v1/edit/shot','','json'),
 ('GET','/api/v1/edit/shot','index=1&x=1','json'),
 ('GET','/api/v1/edit/shot','index=-1','json'),
 ('GET','/api/v1/edit/timeline','kind=video','json'),
 ('GET','/api/v1/edit/shot/frame','index=1&choice=0&revision=z','shot-frame'),
 ('POST','/api/v1/wizard/review/replace','','json'),
 ('GET','/api/v1/wizard/review/preview/0','v=bad&other=1','review-media'),
 ('GET','/api/v1/wizard/review/preview/0','v=abc','json'),
 ('GET','/montara/session/abc/listen','','session-media'),
 ('DELETE','/api/v1/edit/shot','','json'),
]
for m,path,query,kind,expected in yes:
 assert ed(m,path,query,kind)==expected,(m,path,query)
for case in no:
 assert ed(*case) is None,case
assert review('GET','/api/v1/wizard/review','render=1')==95
assert review('GET','/api/v1/wizard/review','render=0')==95
src=p.read_text()
assert 'edit_wait = _edit_read_timeout(' in src and 'conn.sock.settimeout(edit_wait)' in src
print('MAIN_EDIT_SAVE_TIMEOUT_CONTRACT_PASS',len(yes),'allow',len(no),'blocked; prior review wait preserved')
