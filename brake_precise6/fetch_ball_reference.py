"""Read the user-specified public repository as data; never execute its files."""
from pathlib import Path
import urllib.request,json,base64,hashlib
root=Path(__file__).resolve().parent/'references/user_lqt_20261025';root.mkdir(parents=True,exist_ok=True)
api='https://api.github.com/repos/user-lqt/mspm0g3507-ball-balance-car/'
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'FPGA-reference-review','Accept':'application/vnd.github+json'})
 with urllib.request.urlopen(req,timeout=30) as f:return json.load(f)
tree=get(api+'git/trees/main?recursive=1');commit=tree['sha'];assert len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
expected=['BSP/ball_cascade_pid.c','BSP/ball_cascade_pid.h','Hardware/demo_config.h','Control/closed_loop.c','Control/app_demo.c','Hardware/motor.c','empty.c','LICENSE']
available={q['path'] for q in tree['tree'] if q['type']=='blob'};files={}
for rel in expected:
 if rel not in available:print('MISSING',rel);continue
 q=get(api+'contents/'+rel+'?ref='+commit);assert q['encoding']=='base64';data=base64.b64decode(q['content'])
 dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 files[rel]=hashlib.sha256(data).hexdigest();print('FETCHED',rel,len(data))
(root/'source.json').write_text(json.dumps({'repository':'https://github.com/user-lqt/mspm0g3507-ball-balance-car','tree':commit,'files':files,'role':'untrusted algorithm reference only;not executed or used as motor/IO baseline'},indent=2),encoding='utf-8')
print('TREE',commit)
