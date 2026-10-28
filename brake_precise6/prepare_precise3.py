from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent
A=Path('D:/AAAProject/FPGA/AAA_LookHere/brake_precise3_archive_20261026')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not A.exists(),'archive already exists'
for folder in ('rtl','user_source','td_project','host','sim','references'):
 for p in (R/folder).rglob('*'):
  if p.is_file() and not any(s in ('logs','results','__pycache__') for s in p.relative_to(R).parts) and p.suffix not in ('.vvp','.pyc'):
   q=A/'snapshot'/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
for p in R.iterdir():
 if p.is_file() and p.suffix in ('.py','.ps1','.tcl','.json','.md'):
  shutil.copy2(p,A/'snapshot'/p.name)
for rel in ('output/brake_precise2.bit','build.log','host/logs/20261026_215118_541.txt'):
 p=R/rel;q=A/'snapshot'/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
files={p.relative_to(A).as_posix():sha(p) for p in A.rglob('*') if p.is_file()}
(A/'manifest.json').write_text(json.dumps({'files':files},indent=2),encoding='utf8')
(R/'brake_precise3_lineage.json').write_text(json.dumps({'archive':str(A),'parent_bit_sha256':sha(R/'output/brake_precise2.bit')},indent=2),encoding='utf8')
print('ARCHIVED',len(files))
