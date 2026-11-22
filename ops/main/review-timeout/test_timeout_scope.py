"""Static decision contract of the reviewed MAIN-only Stage wait adjustment."""
import ast
import re
import sys
from pathlib import Path
target=Path(sys.argv[1])/'urano/native_owner_web_gateway.py'
tree=ast.parse(target.read_text())
func=[n for n in tree.body if isinstance(n,ast.FunctionDef)
      and n.name=='_review_read_timeout']
assert len(func)==1
module=ast.Module(body=func,type_ignores=[])
scope={'re':re}
exec(compile(module,str(target),'exec'),scope)
wait=scope['_review_read_timeout']
yes=[
 ('GET','/api/v1/wizard/review','render=1'),
 ('GET','/api/v1/wizard/review','render=0'),
 ('GET','/api/v1/wizard/review','render=1&shot=0'),
 ('GET','/api/v1/wizard/review','render=0&shot=305'),
]
no=[
 ('GET','/api/v1/wizard/review',''),
 ('GET','/api/v1/wizard/review','render=2'),
 ('GET','/api/v1/wizard/review','render=1&shot=-1'),
 ('GET','/api/v1/wizard/review','render=1&shot=999999'),
 ('GET','/api/v1/wizard/review','render=1&render=0'),
 ('GET','/api/v1/wizard/review','render=1&other=1'),
 ('GET','/api/v1/wizard/review/replace','render=1'),
 ('GET','/api/v1/wizard/status','render=1'),
 ('POST','/api/v1/wizard/review','render=1'),
 ('PATCH','/api/v1/wizard/review','render=1'),
 ('GET','/api/v1/wizard/review','shot=1&render=1'),
 ('GET','/api/v1/wizard/review','render=1&shot=1&x=y'),
]
for item in yes:assert wait(*item)==95.0,item
for item in no:assert wait(*item) is None,item
print('MAIN_REVIEW_SOCKET_TIMEOUT_SCOPE_PASS',len(yes),'allowed',len(no),'blocked')
src=target.read_text()
assert 'review_wait = _review_read_timeout(' in src
assert 'conn.sock.settimeout(review_wait)' in src
print('MAIN_REVIEW_SOCKET_ASSIGNMENT_VERIFIED')
