"""Freeze the proven actuator, parser, camera, pins and clocks for neutral fix."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lineage=json.loads(read(root/'neutral_lineage.json'));archive=Path(lineage['archive']);before=archive/'project'
for rel,digest in json.loads(read(archive/'manifest.json'))['files'].items():assert sha(archive/rel)==digest,'Neutral rollback changed: '+rel
with zipfile.ZipFile(lineage['archive_zip']) as z:assert z.testzip() is None
allowed={'rtl/vision_follow_control.v','rtl/vision_monitor.v','rtl/vision_monitor_all.v','build.ps1'}
for rel,digest in json.loads(read(before/'build_sources.json')).items():
 if rel not in allowed:assert sha(root/rel)==digest,'Compiled input outside neutral allowlist changed: '+rel
assert sha(root/'output/vision_follow_20261022_response.bit')==lineage['old_bit_sha256'],'Response rollback bit overwritten'
s=read(before/'rtl/vision_monitor.v')
s=s.replace('.center_confirmed(center_confirmed),.frame(result_frame),','.center_confirmed(center_confirmed),.frame(result_frame),.neutral_capture(center_applied),')
s=s.replace('wire auto_run,request,following,external_cancel,key2_event;','wire auto_run,request,following,external_cancel,key2_event,neutral_ready;')
s=s.replace('center_status<=1;end','center_status<=(position>60 || position< -60) ? 8 : 1;end')
s=s.replace('.request(request),.following(following),.external_cancel', '.request(request),.following(following),.neutral_ready(neutral_ready),.external_cancel',1)
s=s.replace('(operating_mode!=1 || center_confirmed);','(operating_mode!=1 || (center_confirmed && neutral_ready));')
assert s==read(root/'rtl/vision_monitor.v'),'Monitor changed beyond K3 neutral wiring/status/readiness'
if __name__=='__main__':print('NEUTRAL_CONTRACT_PASS: actuator/origin/MC/parser/camera/pins/clocks frozen; exact K3 wiring')
