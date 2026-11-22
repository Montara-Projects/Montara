from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
from urllib.parse import urlencode
import sys
target=Path(sys.argv[1])/'urano/native_owner_stage_http.py'
spec=spec_from_file_location('candidate_main_stage360',target)
mod=module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
route=mod.native_stage_route
SRC='/var/lib/private/montara-main-testowner/Uploads/'+'a'*32+'/camera.small.mp4'
source=urlencode({'source':SRC})
exact=urlencode({'source':SRC,'shot':'audience','yaw':'24.8','pitch':'12.6','fov':'170','projection_preset':'ultrawide','time_sec':'20'})
valid=[
 ('GET','/api/v1/wizard/spherical-source-frame',source,'review-media'),
 ('GET','/api/v1/wizard/spherical-preview',exact,'review-media'),
 ('GET','/api/v1/wizard/spherical-preview',urlencode({'source':SRC,'yaw':'0'}),'review-media'),
 ('GET','/montara/branding','','json'),
 ('POST','/montara/logo','','logo-upload'),
 ('GET','/montara/logo','t=123456789','review-media'),
]
for method,path,query,kind in valid:
 r=route(method,path,query)
 assert r and r.kind==kind and r.upstream.startswith(path),(path,query,r)
 print('ALLOW',path,kind)
invalid=[
 ('POST','/api/v1/wizard/spherical-source-frame',source),
 ('GET','/api/v1/wizard/spherical-source-frame',''),
 ('GET','/api/v1/wizard/spherical-source-frame','source=/etc/passwd'),
 ('GET','/api/v1/wizard/spherical-source-frame',source+'&source='+SRC),
 ('GET','/api/v1/wizard/spherical-source-frame',source+'&cmd=rm'),
 ('GET','/api/v1/wizard/spherical-source-frame',source.replace('.mp4','.jpg')),
 ('GET','/api/v1/wizard/spherical-source-frame',urlencode({'source':SRC.replace('/Uploads/','/Projects/')})),
 ('GET','/api/v1/wizard/spherical-preview',''),
 ('GET','/api/v1/wizard/spherical-preview',source),
 ('GET','/api/v1/wizard/spherical-preview',exact+'&yaw=30'),
 ('GET','/api/v1/wizard/spherical-preview',exact+'&other=1'),
 ('GET','/api/v1/wizard/spherical-preview',exact.replace('yaw=24.8','yaw=alert')),
 ('GET','/api/v1/wizard/spherical-preview',exact.replace('shot=audience','shot=../x')),
 ('POST','/api/v1/wizard/spherical-preview',exact),
 ('GET','/api/v1/wizard/spherical-preview',urlencode({'source':SRC.replace('/Uploads/','/Projects/'),'yaw':'24.8'})),
 ('GET','/montara/logo','t=evil'),
]
for case in invalid:
 got=route(*case)
 assert got is None,(case,got)
print('MAIN_360_ROUTE_MATRIX_PASS',len(valid),'allowed',len(invalid),'blocked')
