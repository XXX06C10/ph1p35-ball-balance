"""Package the verified finite probe. No serial port or board programming."""
from pathlib import Path
import hashlib,json,shutil,zipfile,subprocess,sys
from region_probe_contract import check
R=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
check();v=json.loads((R/'region_probe_verification.json').read_text(encoding='utf-8'))
assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_MEASUREMENT' and len(v['suites'])==26
subprocess.run([sys.executable,'source_manifest.py','--check'],cwd=R,check=True)
for rel,h in v['paired_host_sha256'].items():assert sha(R/rel)==h,'host changed after verification '+rel
bit=R/v['bit'];assert sha(bit)==v['sha256']
shutil.copy2(bit,R/'output/region_probe.bit')
assert sha(R/'output/vision_follow_20261022_easy3.bit')=='3dd2dcd015b9607753f99933919fd81f27313154d5f370da4969461b2327fe97'
(R/'output/region_probe_sha256.txt').write_text(v['sha256']+'  region_probe.bit\n'+v['sha256']+'  vision_follow_20261022_region_probe.bit\n',encoding='ascii')
guide=R/'区域诊断_测试说明.md';shutil.copy2(guide,R/'测试说明.md')
paths=[]
for folder in ['rtl','user_source','td_project','host','sim','references']:
 for p in (R/folder).rglob('*'):
  if p.is_file() and not any(part in ('__pycache__','.git') for part in p.parts) and p.suffix not in ('.vvp','.pyc','.db','.logw','.bak'):
   paths.append(p)
paths += [p for p in R.iterdir() if p.is_file() and p.suffix in ('.py','.ps1','.tcl','.md','.json')]
paths += [p for p in (R/'output').iterdir() if p.is_file() and (p.name in ['region_probe.bit','region_probe_sha256.txt','vision_follow_20261022_region_probe.bit','vision_follow_20261022_easy3.bit','vision_follow_20261022_easy2.bit'])]
run=R/'vision_follow_20261022_Runs/phy_1'
paths += [run/name for name in ['vision_follow_20261022_phy.area','vision_follow_20261022_phy.ts','vision_follow_20261022_pr.timing']]
paths += [R/'build.log',R/'routed_netlist.v']
manifest=R/'region_probe_delivery_manifest.json'
paths=sorted(set(paths)-{manifest})
files={p.relative_to(R).as_posix():sha(p) for p in paths}
data={'status':v['status'],'device':v['device'],'bit_sha256':v['sha256'],'source_of_truth':'region_probe_verification.json; old verification.json describes historical easy3 only','files':files}
manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
dest=look/'VIS5_region_probe_20261025.zip'
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths+[manifest]:z.write(p,p.relative_to(R).as_posix())
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 for rel,h in files.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,'packaged mismatch '+rel
(look/'VIS5_region_probe_20261025_sha256.txt').write_text(sha(dest)+'  '+dest.name+'\n',encoding='ascii')
print('REGION_PUBLISHED',len(files),'files',dest,'ZIP_SHA256',sha(dest),'BIT_SHA256',v['sha256'])
