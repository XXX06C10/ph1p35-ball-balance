"""Exact AUTO phase/config adaptation; all other compiled inputs stay frozen."""
from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lineage=json.loads(read(root/'response_lineage.json'));archive=Path(lineage['archive']);before=archive/'project'
for rel,digest in json.loads(read(archive/'manifest.json'))['files'].items():assert sha(archive/rel)==digest,'Archive changed: '+rel
with zipfile.ZipFile(lineage['archive_zip']) as z:assert z.testzip() is None
allowed={'rtl/vision_servo_core.v','rtl/vision_follow_control.v','rtl/vision_monitor.v','rtl/vision_config_rx.v','rtl/vision_monitor_all.v','build.ps1'}
for rel,digest in json.loads(read(before/'build_sources.json')).items():
 if rel not in allowed:assert sha(root/rel)==digest,'Compiled source outside response allowlist changed: '+rel
def response_servo(s):
 s=s.replace('EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1\n','EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1,\n FOLLOW_SETUP_CYCLES=SETUP_CYCLES,FOLLOW_SETTLE_CYCLES=SETTLE_CYCLES\n')
 anchor=' wire [31:0] allowed_error=EXTERNAL_CONTROL && following ? FOLLOW_DEADBAND : DEADBAND;'
 s=s.replace(anchor,anchor+'\n wire [31:0] setup_limit=EXTERNAL_CONTROL && following ? FOLLOW_SETUP_CYCLES : SETUP_CYCLES;\n wire [31:0] settle_limit=EXTERNAL_CONTROL && following ? FOLLOW_SETTLE_CYCLES : SETTLE_CYCLES;')
 s=s.replace('phase_count==SETUP_CYCLES-1','phase_count==setup_limit-1').replace('phase_count==SETTLE_CYCLES-1','phase_count==settle_limit-1')
 return s
assert response_servo(read(before/'rtl/vision_servo_core.v'))==read(root/'rtl/vision_servo_core.v'),'Servo changed beyond AUTO timing mux'
s=read(before/'rtl/vision_config_rx.v')
for a,b in [
 ('DEFAULT_GAIN=4,DEFAULT_LIMIT=12,DEFAULT_MODE=1','DEFAULT_GAIN=3,DEFAULT_LIMIT=32,DEFAULT_MODE=1,DEFAULT_DEADZONE=5,DEFAULT_SLEW=8,DEFAULT_RUNTIME=60'),
 ('center=960,deadzone=20','center=960,deadzone=DEFAULT_DEADZONE'),
 ('follow_sequence=0,runtime_seconds=30','follow_sequence=0,runtime_seconds=DEFAULT_RUNTIME'),
 ('damping=12,slew=2','damping=12,slew=DEFAULT_SLEW'),
 ('center<=960;deadzone<=20','center<=960;deadzone<=DEFAULT_DEADZONE'),
 ('runtime_seconds<=30','runtime_seconds<=DEFAULT_RUNTIME'),
 ('damping<=12;slew<=2','damping<=12;slew<=DEFAULT_SLEW')]:s=s.replace(a,b)
assert s==read(root/'rtl/vision_config_rx.v'),'Parser changed beyond defaults'
assert sha(root/'output/vision_follow_20261022_loss500.bit')==lineage['old_bit_sha256'],'Rollback bit overwritten'
if __name__=='__main__':print('RESPONSE_CONTRACT_PASS: exact AUTO mux/default-only RX and all other compiled files frozen')
