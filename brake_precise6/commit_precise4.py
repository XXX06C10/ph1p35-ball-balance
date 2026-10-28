from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;parent='d9b9dc415ac109f39bb50d708ca5157c1607d021'
env=os.environ.copy();env.update(GIT_INDEX_FILE=str(R/'output/precise4_git.index'),GIT_AUTHOR_NAME='Codex',GIT_AUTHOR_EMAIL='codex@local',GIT_COMMITTER_NAME='Codex',GIT_COMMITTER_EMAIL='codex@local')
def run(args,**kw):return subprocess.run(['git','-c','safe.directory='+R.as_posix()]+args,cwd=R,env=env,check=True,capture_output=True,**kw).stdout
run(['read-tree',parent])
m=json.loads((R/'brake_precise4_delivery_manifest.json').read_text(encoding='utf8'));files=[]
for rel,h in m['files'].items():
 p=R/rel;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,rel
 if rel.startswith(('sim/results/','evidence/','vision_follow_20261022_Runs/')) or rel in ('build.log','routed_netlist.v'):continue
 if p.suffix in ('.png','.diff') and not rel.startswith('user_source/'):continue
 if rel.startswith('output/') and p.name not in ('brake_precise4.bit','brake_precise4_sha256.txt'):continue
 files.append(rel)
paths=R/'output/precise4_git.paths';paths.write_bytes(b''.join(s.encode('utf8')+b'\0' for s in files))
run(['-c','core.autocrlf=false','add','-f','--pathspec-from-file='+str(paths),'--pathspec-file-nul'])
tree=run(['write-tree']).decode().strip();commit=run(['commit-tree',tree,'-p',parent],input=b'Iterate accepted precise3: qualify parked ball from position trend, suppress false derivative noise\n').decode().strip()
run(['update-ref','refs/heads/iterate/brake-precise4-20261027',commit,'0'*40])
assert run(['show',commit+':output/brake_precise4.bit'])==(R/'output/brake_precise4.bit').read_bytes()
report={'commit':commit,'parent':parent,'branch':'iterate/brake-precise4-20261027','index_preserved':True,'bit_sha256':hashlib.sha256((R/'output/brake_precise4.bit').read_bytes()).hexdigest()}
(R/'brake_precise4_git.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
