from pathlib import Path
import json,hashlib,subprocess,os,datetime
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((R/'brake_precise3_delivery_manifest.json').read_text(encoding='utf8'))
assert sha(R/'output/brake_precise3.bit')=='4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb'
files=[]
for rel,h in manifest['files'].items():
 p=R/rel
 assert sha(p)==h,'delivered file changed: '+rel
 if rel.startswith(('sim/results/','evidence/')) or rel in ('routed_netlist.v','build.log') or rel.startswith('vision_follow_20261022_Runs/'):continue
 if p.suffix in ('.png','.diff') and not rel.startswith('user_source/'):continue
 if rel.startswith('output/') and p.name not in ('brake_precise3.bit','brake_precise3_sha256.txt'):continue
 files.append(rel)
note=R/'accepted_brake_precise3_20261027.json'
note.write_text(json.dumps({'version':'brake_precise3','bit_sha256':sha(R/'output/brake_precise3.bit'),'user_observation':'User reports accurate stops when successful; estimates40% successful and60% stuck elsewhere. Accepted iteration baseline, not overall acceptance.','log':'host/logs/20261027_102218_274.txt','log_sha256':sha(R/'host/logs/20261027_102218_274.txt'),'tag':'baseline/brake-precise3-accepted-20261027'},ensure_ascii=False,indent=2),encoding='utf8')
files += [note.name,'host/logs/20261027_102218_274.txt']
env=os.environ.copy();env['GIT_INDEX_FILE']=str(R/'output/accepted_precise3.index')
env.update(GIT_AUTHOR_NAME='Codex',GIT_AUTHOR_EMAIL='codex@local',GIT_COMMITTER_NAME='Codex',GIT_COMMITTER_EMAIL='codex@local')
git=['git','-c','safe.directory='+R.as_posix()]
def run(args,**kw):return subprocess.run(git+args,cwd=R,env=env,check=True,capture_output=True,**kw).stdout
run(['read-tree','--empty'])
paths=R/'output/accepted_precise3.paths';paths.write_bytes(b''.join(s.encode('utf8')+b'\0' for s in files))
run(['-c','core.autocrlf=false','add','-f','--pathspec-from-file='+str(paths),'--pathspec-file-nul'])
tree=run(['write-tree']).decode().strip()
commit=run(['commit-tree',tree],input=b'Baseline: user-confirmed precise stopping in brake_precise3; preserve40percent success starting point\n').decode().strip()
run(['update-ref','refs/tags/baseline/brake-precise3-accepted-20261027',commit,'0'*40])
run(['update-ref','refs/heads/baseline/brake-precise3-accepted-20261027',commit,'0'*40])
assert run(['show',commit+':output/brake_precise3.bit'])==(R/'output/brake_precise3.bit').read_bytes()
result={'commit':commit,'tree':tree,'tag':'baseline/brake-precise3-accepted-20261027','bit_sha256':sha(R/'output/brake_precise3.bit'),'files':len(files),'index_preserved':True}
(R/'accepted_brake_precise3_git.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result,indent=2))
