from pathlib import Path
import hashlib,json,zipfile,shutil,subprocess,sys
from region100_contract import check
R=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
check();v=json.loads((R/'region100_verification.json').read_text(encoding='utf-8'))
assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_REGION100' and len(v['suites'])==15
subprocess.run([sys.executable,'source_manifest.py','--check'],cwd=R,check=True)
for rel,h in {**v['wide_schema_sha256'],**v['paired_host_sha256']}.items():assert sha(R/rel)==h,'post-verification edit '+rel
bit=R/v['bit'];assert sha(bit)==v['sha256']
parents={'output/asym_smooth.bit':'e05a0ae7e29bd28fc95948f379dcd6f449f5f4afa35dbaa85bd62395bf60a37c','output/asym_range.bit':'46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c'}
for p,h in parents.items():assert sha(R/p)==h
shutil.copy2(bit,R/'output/region100.bit')
for p,h in parents.items():assert sha(R/p)==h
(R/'output/region100_sha256.txt').write_text(v['sha256']+'  region100.bit\n'+v['sha256']+'  vision_follow_20261022_region100.bit\n',encoding='ascii')
shutil.copy2(R/'100px稳区_测试说明.md',R/'测试说明.md')
paths=[]
for folder in ('rtl','user_source','td_project','host','sim','references'):
 for p in (R/folder).rglob('*'):
  if p.is_file() and p.relative_to(R).parts[:2]!=('host','logs') and not any(s in ('__pycache__','.git') for s in p.parts) and p.suffix not in ('.vvp','.pyc','.db','.logw','.bak'):paths.append(p)
paths += [p for p in R.iterdir() if p.is_file() and p.suffix in ('.py','.ps1','.tcl','.md','.json','.diff')]
for n in ('region100.bit','vision_follow_20261022_region100.bit','region100_sha256.txt','asym_smooth.bit','asym_smooth_sha256.txt','full_range.bit','asym_range.bit'):paths.append(R/'output'/n)
run=R/'vision_follow_20261022_Runs/phy_1';paths += [run/n for n in ('vision_follow_20261022_phy.area','vision_follow_20261022_phy.ts','vision_follow_20261022_pr.timing')]
paths += [R/'build.log',R/'routed_netlist.v',R/'evidence/region_return_before/baseline_phy.area']
for folder in ('evidence/region100_measurement','evidence/region100_attempt1','evidence/asym_smooth_measurement','evidence/asym_smooth_attempt1'):
 paths += [p for p in (R/folder).rglob('*') if p.is_file()]
manifest=R/'region100_delivery_manifest.json';paths=sorted(set(paths)-{manifest});files={p.relative_to(R).as_posix():sha(p) for p in paths}
manifest.write_text(json.dumps({'status':v['status'],'device':v['device'],'bit_sha256':v['sha256'],'source_of_truth':'region100_verification.json;older reports historical','files':files},ensure_ascii=False,indent=2),encoding='utf-8')
dest=look/'VIS6_region100_20261026.zip'
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths+[manifest]:z.write(p,p.relative_to(R).as_posix())
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 for rel,h in files.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,'ZIP mismatch '+rel
(look/'VIS6_region100_20261026_sha256.txt').write_text(sha(dest)+'  '+dest.name+'\n',encoding='ascii')
print('REGION100_PUBLISHED',len(files),'files',dest,'ZIP_SHA256',sha(dest),'BIT_SHA256',v['sha256'])
