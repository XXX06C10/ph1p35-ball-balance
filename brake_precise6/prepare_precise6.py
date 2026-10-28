from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parent;A=Path('D:/AAAProject/FPGA/AAA_LookHere/brake_precise6_archive_20261027');assert not A.exists()
with zipfile.ZipFile('D:/AAAProject/FPGA/AAA_LookHere/VIS6_brake_precise5_20261027.zip') as z:z.extractall(A/'snapshot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(A/'manifest.json').write_text(json.dumps({'files':{p.relative_to(A).as_posix():sha(p) for p in A.rglob('*') if p.is_file()}},indent=2))
(R/'brake_precise6_lineage.json').write_text(json.dumps({'archive':str(A),'parent_commit':'7351ea595865f90f68caaf37781fb5541ff0508c','parent_bit_sha256':sha(R/'output/brake_precise5.bit')},indent=2))
for n in ['verify_brake_precise5.py','publish_brake_precise5.py','run_brake_precise5_regression.ps1']:
 s=(R/n).read_text(encoding='utf-8-sig').replace('brake_precise5','brake_precise6').replace('BRAKE_PRECISE5','BRAKE_PRECISE6').replace('==23','==24').replace('精准回中5_测试说明','精准回中6_测试说明')
 if n.startswith('verify'):
  s=s.replace("markers={'tb_precise5_escape'","markers={'tb_precise6_jitter':'PRECISE6_JITTER_PASS','tb_precise5_escape'")
  s=s.replace("read(parent_snapshot/'rtl/vision_region100.v').replace('module vision_region100 #','module vision_region100_precise4 #')","read(Path(json.loads(read(R/'brake_precise5_lineage.json'))['archive'])/'snapshot/rtl/vision_region100.v').replace('module vision_region100 #','module vision_region100_precise4 #')")
 if n.startswith('publish'):
  s=s.replace("parents={'output/brake_precise4.bit'","parents={'output/brake_precise5.bit':'f1305658cd415ab805f7fdd5a34f43ebfe5c63197dafb1297875793946978b1e','output/brake_precise4.bit'")
  s=s.replace("'brake_precise4.bit','brake_precise3.bit'","'brake_precise5.bit','brake_precise4.bit','brake_precise3.bit'").replace("'evidence/precise5_measurement'","'evidence/precise6_measurement','evidence/precise5_measurement'")
 (R/n.replace('precise5','precise6')).write_text(s,encoding='utf8')
for n in ['start_brake_precise5.cmd','brake_precise5_panel_cn.ps1','brake_precise5_controls.ps1']:
 s=(R/'host'/n).read_text(encoding='utf-8-sig').replace('brake_precise5','brake_precise6').replace('BRAKE_PRECISE5','BRAKE_PRECISE6').replace('BrakePrecise5','BrakePrecise6').replace('精准回中5','精准回中6')
 (R/'host'/n.replace('precise5','precise6')).write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('utf8' if n.endswith('.cmd') else 'utf-8-sig'))
p=R/'build.ps1';p.write_text(p.read_text().replace("'brake_precise5')","'brake_precise5','brake_precise6')"),encoding='utf8')
p=R/'run_sim.ps1';p.write_text(p.read_text().replace("'tb_precise5_escape')","'tb_precise5_escape','tb_precise6_jitter')").replace('$taskMarkers=@{',"$taskMarkers=@{tb_precise6_jitter='PRECISE6_JITTER_PASS';"),encoding='utf8')
(R/'brake_precise6_required_suites.json').write_text(json.dumps(json.loads((R/'brake_precise5_required_suites.json').read_text())+['tb_precise6_jitter'],indent=2))
print('PRECISE6_ARCHIVE_READY')
