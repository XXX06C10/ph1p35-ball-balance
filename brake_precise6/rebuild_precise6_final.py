from pathlib import Path
import time,subprocess,os,shutil,json
R=Path(__file__).resolve().parent
while not (R/'output/precise6_build.exit').exists():time.sleep(5)
a=R/'evidence/precise6_superseded_build';a.mkdir(exist_ok=True)
for rel in ['build.log','build_sources.json','vision_follow_20261022_Runs/phy_1/vision_follow_20261022_phy.ts']:
 p=R/rel
 if p.exists():shutil.copy2(p,a/p.name)
(a/'status.json').write_text(json.dumps({'reason':'source refined during first build; first bit is not deliverable; clean final rebuild required','first_exit':(R/'output/precise6_build.exit').read_text()}))
env=os.environ.copy();env['PATH']=str(Path(os.sys.executable).parent)+';'+env['PATH']
r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File','build.ps1','-Release','brake_precise6'],cwd=R,env=env)
raise SystemExit(r.returncode)
