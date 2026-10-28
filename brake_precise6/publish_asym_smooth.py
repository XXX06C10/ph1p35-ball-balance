from pathlib import Path
import hashlib,json,zipfile,shutil,subprocess,sys
from asym_smooth_contract import check
R=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
check();v=json.loads((R/'asym_smooth_verification.json').read_text(encoding='utf-8'))
assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_ASYM_SMOOTH' and len(v['suites'])==45
subprocess.run([sys.executable,'source_manifest.py','--check'],cwd=R,check=True)
for rel,h in {**v['wide_schema_sha256'],**v['paired_host_sha256']}.items():assert sha(R/rel)==h,'post-verification edit '+rel
bit=R/v['bit'];assert sha(bit)==v['sha256']
parent=R/'output/full_range.bit';assert sha(parent)=='b60f23a56a79740d850b928adfe9d584db8c66540c229a4597baa35e31fdc91d'
assert sha(R/'output/asym_range.bit')=='46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c'
shutil.copy2(bit,R/'output/asym_smooth.bit')
assert sha(R/'output/asym_range.bit')=='46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c'
assert sha(parent)=='b60f23a56a79740d850b928adfe9d584db8c66540c229a4597baa35e31fdc91d'
(R/'output/asym_smooth_sha256.txt').write_text(v['sha256']+'  asym_smooth.bit\n'+v['sha256']+'  vision_follow_20261022_asym_smooth.bit\n',encoding='ascii')
shutil.copy2(R/'asym恢复与显示延迟_测试说明.md',R/'测试说明.md')
paths=[]
for folder in ('rtl','user_source','td_project','host','sim','references'):
 for p in (R/folder).rglob('*'):
  if p.is_file() and p.relative_to(R).parts[:2]!=('host','logs') and not any(s in ('__pycache__','.git') for s in p.parts) and p.suffix not in ('.vvp','.pyc','.db','.logw','.bak'):paths.append(p)
paths += [p for p in R.iterdir() if p.is_file() and p.suffix in ('.py','.ps1','.tcl','.md','.json','.diff')]
for n in ('asym_smooth.bit','full_range.bit','vision_follow_20261022_asym_smooth.bit','asym_smooth_sha256.txt','settle30.bit','settle30_sha256.txt','brake_hold.bit','asym_range.bit','region_return.bit'):paths.append(R/'output'/n)
run=R/'vision_follow_20261022_Runs/phy_1'
paths += [run/n for n in ('vision_follow_20261022_phy.area','vision_follow_20261022_phy.ts','vision_follow_20261022_pr.timing')]
paths += [R/'build.log',R/'routed_netlist.v',R/'evidence/region_return_before/baseline_phy.area']
for folder in ('evidence/asym_dense_attempt1','evidence/brake_hold_preflight','evidence/brake_hold_measurement','evidence/settle30_measurement','evidence/full_range_measurement','evidence/asym_smooth_measurement','evidence/asym_smooth_attempt1'):
 paths += [p for p in (R/folder).rglob('*') if p.is_file()]
manifest=R/'asym_smooth_delivery_manifest.json';paths=sorted(set(paths)-{manifest});files={p.relative_to(R).as_posix():sha(p) for p in paths}
manifest.write_text(json.dumps({'status':v['status'],'device':v['device'],'bit_sha256':v['sha256'],'source_of_truth':'asym_smooth_verification.json; older reports historical','files':files},ensure_ascii=False,indent=2),encoding='utf-8')
dest=look/'VIS6_asym_smooth_20261026.zip'
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths+[manifest]:z.write(p,p.relative_to(R).as_posix())
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 for rel,h in files.items():assert hashlib.sha256(z.read(rel)).hexdigest()==h,'ZIP mismatch '+rel
(look/'VIS6_asym_smooth_20261026_sha256.txt').write_text(sha(dest)+'  '+dest.name+'\n',encoding='ascii')
print('ASYM_SMOOTH_PUBLISHED',len(files),'files',dest,'ZIP_SHA256',sha(dest),'BIT_SHA256',v['sha256'])
