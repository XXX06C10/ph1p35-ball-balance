from pathlib import Path
import json,hashlib,subprocess
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig')
old=Path(json.loads(read(R/'brake_precise3_lineage.json'))['archive'])/'snapshot'
out=R/'evidence/brake_precise3_measurement'
bench=read(R/'sim/tb_reversal_recovery.v').replace('.REVERSAL_RECOVERY(!LEGACY),','')
(out/'tb_reversal_archived.v').write_text(bench,encoding='utf8')
subprocess.run(['D:/Program Files/iverilog/bin/iverilog.exe','-g2012','-s','tb_reversal_legacy','-o',str(out/'legacy.vvp'),str(old/'rtl/vision_servo_core.v'),str(out/'tb_reversal_archived.v')],cwd=R,check=True)
r=subprocess.run(['D:/Program Files/iverilog/bin/vvp.exe',str(out/'legacy.vvp')],cwd=R,capture_output=True,text=True)
(out/'legacy_reproduction.log').write_text(r.stdout+r.stderr,encoding='utf8')
assert r.returncode==0 and 'REVERSAL_LEGACY_REPRO_PASS SP1 CHECK' in r.stdout
assert 'REVERSAL_CLOCK50_PASS actual50MHz' in read(R/'sim/results/reversal_clock50.log')
report={'status':'PASS','archived_core_sha256':sha(old/'rtl/vision_servo_core.v'),'current_core_sha256':sha(R/'rtl/vision_servo_core.v'),'current_bench_sha256':sha(R/'sim/tb_reversal_recovery.v'),'clock50_log_sha256':sha(R/'sim/results/reversal_clock50.log'),'legacy_log_sha256':sha(out/'legacy_reproduction.log')}
(out/'recovery_verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('RECOVERY_EVIDENCE_PASS archived SP1 deadlock;actual50MHz recovery;source hashes')
