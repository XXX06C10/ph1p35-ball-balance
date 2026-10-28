from pathlib import Path
import json,zipfile,hashlib
R=Path(__file__).resolve().parent;A=Path('D:/AAAProject/FPGA/AAA_LookHere/brake_precise4_archive_20261027')
assert not A.exists()
with zipfile.ZipFile('D:/AAAProject/FPGA/AAA_LookHere/VIS6_brake_precise3_20261027.zip') as z:z.extractall(A/'snapshot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(A/'manifest.json').write_text(json.dumps({'files':{p.relative_to(A).as_posix():sha(p) for p in A.rglob('*') if p.is_file()}},indent=2))
(R/'brake_precise4_lineage.json').write_text(json.dumps({'archive':str(A),'parent_commit':'d9b9dc415ac109f39bb50d708ca5157c1607d021','parent_bit_sha256':sha(R/'output/brake_precise3.bit')},indent=2))
for src,dst in [('verify_brake_precise3.py','verify_brake_precise4.py'),('publish_brake_precise3.py','publish_brake_precise4.py'),('run_brake_precise3_regression.ps1','run_brake_precise4_regression.ps1')]:
 s=(R/src).read_text(encoding='utf-8-sig').replace('brake_precise3','brake_precise4').replace('BRAKE_PRECISE3','BRAKE_PRECISE4').replace('==21','==22').replace('精准回中3_测试说明','精准回中4_测试说明')
 if src.startswith('verify'):
  s=s.replace("markers={'tb_reversal_recovery'","markers={'tb_precise4_noise':'PRECISE4_NOISE_PASS','tb_reversal_recovery'")
  # The unchanged core retains its precise3 actual-clock evidence.
  s=s.replace('evidence/brake_precise4_measurement/recovery_verification.json','evidence/brake_precise3_measurement/recovery_verification.json')
 if src.startswith('publish'):
  s=s.replace("parents={'output/brake_precise2.bit'","parents={'output/brake_precise3.bit':'4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb','output/brake_precise2.bit'")
  s=s.replace("'brake_precise2.bit','brake_precise.bit'","'brake_precise3.bit','brake_precise2.bit','brake_precise.bit'")
  s=s.replace("for folder in ('evidence/brake_precise4_measurement'","for folder in ('evidence/precise4_measurement','evidence/brake_precise3_measurement'")
 (R/dst).write_text(s,encoding='utf8')
for n in ('start_brake_precise3.cmd','brake_precise3_panel_cn.ps1','brake_precise3_controls.ps1'):
 s=(R/'host'/n).read_text(encoding='utf-8-sig').replace('brake_precise3','brake_precise4').replace('BRAKE_PRECISE3','BRAKE_PRECISE4').replace('BrakePrecise3','BrakePrecise4')
 p=R/'host'/n.replace('precise3','precise4')
 p.write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('utf8' if n.endswith('.cmd') else 'utf-8-sig'))
p=R/'build.ps1';p.write_text(p.read_text().replace("'brake_precise3')","'brake_precise3','brake_precise4')"),encoding='utf8')
p=R/'run_sim.ps1';s=p.read_text();s=s.replace("'tb_precise3_policy')","'tb_precise3_policy','tb_precise4_noise')").replace('$taskMarkers=@{',"$taskMarkers=@{tb_precise4_noise='PRECISE4_NOISE_PASS';");p.write_text(s,encoding='utf8')
roster=json.loads((R/'brake_precise3_required_suites.json').read_text())+['tb_precise4_noise'];(R/'brake_precise4_required_suites.json').write_text(json.dumps(roster,indent=2))
print('PRECISE4_BASELINE_ARCHIVED_AND_TOOLS_PREPARED')
