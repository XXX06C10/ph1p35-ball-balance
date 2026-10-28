from pathlib import Path
import hashlib,json,zipfile
R=Path(__file__).resolve().parent;A=Path('D:/AAAProject/FPGA/AAA_LookHere/brake_precise5_archive_20261027')
assert not A.exists()
with zipfile.ZipFile('D:/AAAProject/FPGA/AAA_LookHere/VIS6_brake_precise4_20261027.zip') as z:z.extractall(A/'snapshot')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(A/'manifest.json').write_text(json.dumps({'files':{p.relative_to(A).as_posix():sha(p) for p in A.rglob('*') if p.is_file()}},indent=2))
(R/'brake_precise5_lineage.json').write_text(json.dumps({'archive':str(A),'parent_commit':'c6aca5857e336a77aeb4ca74521a9a32be887528','parent_bit_sha256':sha(R/'output/brake_precise4.bit')},indent=2))
for n in ['verify_brake_precise4.py','publish_brake_precise4.py','run_brake_precise4_regression.ps1']:
 s=(R/n).read_text(encoding='utf-8-sig').replace('brake_precise4','brake_precise5').replace('BRAKE_PRECISE4','BRAKE_PRECISE5').replace('==22','==23').replace('精准回中4_测试说明','精准回中5_测试说明')
 if n.startswith('verify'):
  s=s.replace("markers={'tb_precise4_noise'","markers={'tb_precise5_escape':'PRECISE5_ESCAPE_PASS','tb_precise4_noise'")
  s=s.replace("parent_snapshot/'rtl/vision_region100.v'","Path(json.loads(read(R/'brake_precise4_lineage.json'))['archive'])/'snapshot/rtl/vision_region100.v'")
 if n.startswith('publish'):
  s=s.replace("parents={'output/brake_precise3.bit'","parents={'output/brake_precise4.bit':'36192ca2f4624a53b49f7d9f033ec96159fae465fabd16fbab2976fcc4b147e2','output/brake_precise3.bit'")
  s=s.replace("'brake_precise3.bit','brake_precise2.bit'","'brake_precise4.bit','brake_precise3.bit','brake_precise2.bit'")
  s=s.replace("'evidence/precise4_measurement'","'evidence/precise5_measurement','evidence/precise4_measurement'")
 (R/n.replace('precise4','precise5')).write_text(s,encoding='utf8')
for n in ['start_brake_precise4.cmd','brake_precise4_panel_cn.ps1','brake_precise4_controls.ps1']:
 s=(R/'host'/n).read_text(encoding='utf-8-sig').replace('brake_precise4','brake_precise5').replace('BRAKE_PRECISE4','BRAKE_PRECISE5').replace('BrakePrecise4','BrakePrecise5')
 (R/'host'/n.replace('precise4','precise5')).write_bytes(s.replace('\r\n','\n').replace('\n','\r\n').encode('utf8' if n.endswith('.cmd') else 'utf-8-sig'))
p=R/'build.ps1';p.write_text(p.read_text().replace("'brake_precise4')","'brake_precise4','brake_precise5')"),encoding='utf8')
p=R/'run_sim.ps1';p.write_text(p.read_text().replace("'tb_precise4_noise')","'tb_precise4_noise','tb_precise5_escape')").replace('$taskMarkers=@{',"$taskMarkers=@{tb_precise5_escape='PRECISE5_ESCAPE_PASS';"),encoding='utf8')
(R/'brake_precise5_required_suites.json').write_text(json.dumps(json.loads((R/'brake_precise4_required_suites.json').read_text())+['tb_precise5_escape'],indent=2))
print('PRECISE5_ARCHIVE_READY')
