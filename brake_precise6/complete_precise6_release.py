from pathlib import Path
import subprocess,time,json,sys
R=Path(__file__).resolve().parent
while not (R/'output/precise6_finalbuild.exit').exists():time.sleep(5)
assert (R/'output/precise6_finalbuild.exit').read_text().strip()=='0','final build failed'
assert (R/'output/precise6_release_regression.exit').read_text().strip()=='0','final regression failed'
assert not (R/'brake_precise6_git.json').exists(),'release already committed; inspect before rerun'
completed=[]
for script in ['verify_brake_precise6.py','finalize_precise6.py','publish_brake_precise6.py','commit_precise6.py','publish_brake_precise6.py']:
 print('RELEASE_STAGE',script,flush=True)
 subprocess.run([sys.executable,script],cwd=R,check=True)
 completed.append(script)
 (R/'output/precise6_release_progress.json').write_text(json.dumps(completed,indent=2))
print('PRECISE6_RELEASE_COMPLETE',flush=True)
