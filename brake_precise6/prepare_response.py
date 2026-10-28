"""One-time immutable snapshot of the user's usable loss500 release."""
from pathlib import Path
import hashlib,json,shutil,zipfile,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent
look=Path('D:/AAAProject/FPGA/AAA_LookHere')
archive=look/'成功版本归档/20261023_VIS5_提速前'
assert not archive.exists(),'Archive already exists; never overwrite'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
delivery=json.loads((root/'delivery_manifest.json').read_text(encoding='utf-8-sig'))
for rel,h in delivery['files'].items():assert sha(root/rel)==h,rel
archive.mkdir(parents=True)
for rel in list(delivery['files'])+['delivery_manifest.json']:
 target=archive/'project'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,target)
diag=look/'20261023_纠偏诊断'
for rel in ['vision_panel_cn.ps1','start_panel.cmd','诊断与实施目标.md','logs/20261023_210219_921.txt']:
 target=archive/'diagnostic'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(diag/rel,target)
(archive/'恢复说明.md').write_text('原loss500 bit和源码在project/，中文面板在project/host/。bit SHA256 '+delivery['bit_sha256']+'。需要恢复开发时先复制project到独立工作目录，勿修改本归档。新程序未自动下载或写Flash。用户2026-10-23确认方向正确、调整后有所改善，但响应慢/偏保守；不是精密回中验收。',encoding='utf-8')
files={p.relative_to(archive).as_posix():sha(p) for p in archive.rglob('*') if p.is_file()}
(archive/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(archive.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
 for p in archive.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(archive))
with zipfile.ZipFile(archive.with_suffix('.zip')) as z:assert z.testzip() is None
(root/'response_lineage.json').write_text(json.dumps({'archive':str(archive),'archive_zip':str(archive.with_suffix('.zip')),'old_bit_sha256':delivery['bit_sha256'],'date':'2026-10-23','human_feedback':'Direction correct; G3/DZ5/L24 helped slightly; still slow and conservative. Actual capture retains SL2/100ms and30s. Speed/strength tuning authorized; keep direction normal, bounds/fault guards/loss policy/protocol/pins.'},ensure_ascii=False,indent=2),encoding='utf-8')
agent=root/'AGENTS.md'
agent.write_text('# Authorized response revision (2026-10-23)\n\nUser confirms direction correct and partial improvement but requests faster/stronger correction. Preserve normal direction (gain bit7=0) proven in current capture. Permit documented AUTO-only shorter setup/feedback waits,20ms control tick with SL retaining counts/100ms units, fine-target quantization and stronger bounded defaults. Manual/return pulse timing, all F1-F8,64pulse/5s,MC/P±64,loss500/stream200,protocol/device/pins/clocks unchanged. Immutable response_lineage archive is the rollback. New bit and paired host required. Do not run historical publication scripts or auto-program/Flash.\n\n'+agent.read_text(encoding='utf-8-sig'),encoding='utf-8')
print('RESPONSE_BASELINE_ARCHIVED',len(files),str(archive))
